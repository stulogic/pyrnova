"""B4.6 — immutable release / deploy / rollback contract.

Proves: releases are immutable and SHA-stamped; activation is atomic and fails closed on a
missing/unhealthy release (no silent partial release); rollback returns code to the prior release; and
code rollback NEVER touches durable state (data recovery is a separate operation).
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

import pytest

from pyrnova import access
from pyrnova import release as rel
from pyrnova.ops import OperatorConsole
from pyrnova.ops_server import AccessPolicy, make_handler
from pyrnova.state import StateStore

_DEMO = Path("examples/material_changes_demo")


def _fake_source(tmp_path, marker="v1"):
    src = tmp_path / f"src_{marker}"
    (src / "pyrnova").mkdir(parents=True)
    (src / "pyrnova" / "__init__.py").write_text(f"# {marker}\n")
    (src / "requirements.lock.txt").write_text("requests==2.32.5\n")
    (src / "README.md").write_text(marker)
    # things that must NOT be copied into an immutable release:
    (src / ".git").mkdir()
    (src / ".git" / "HEAD").write_text("ref: refs/heads/main")
    (src / "state").mkdir()
    (src / "state" / "opportunities.jsonl").write_text('{"id":"x"}\n')
    (src / "var").mkdir()
    return src


def test_stage_release_is_immutable_and_sha_stamped(tmp_path):
    root = tmp_path / "srv"
    src = _fake_source(tmp_path)
    m = rel.stage_release(root, src, sha="abc123")
    rel_dir = root / "releases" / "abc123"
    assert rel_dir.is_dir()
    manifest = rel.read_manifest(rel_dir)
    assert manifest["sha"] == "abc123" and manifest["lock_sha256"]
    # runtime/derived state + VCS metadata are excluded from the immutable artifact
    assert not (rel_dir / ".git").exists()
    assert not (rel_dir / "state").exists()
    assert not (rel_dir / "var").exists()
    assert (rel_dir / "pyrnova" / "__init__.py").exists()
    # immutable: refuses to overwrite an existing SHA
    with pytest.raises(FileExistsError):
        rel.stage_release(root, src, sha="abc123")


def test_activate_is_atomic_and_health_gated(tmp_path):
    root = tmp_path / "srv"
    rel.stage_release(root, _fake_source(tmp_path, "v1"), sha="sha_v1")
    rec = rel.activate(root, "sha_v1")
    assert rec["action"] == "activate" and rec["sha"] == "sha_v1"
    assert rel.current_sha(root) == "sha_v1"
    # missing release -> fail closed, current unchanged
    with pytest.raises(FileNotFoundError):
        rel.activate(root, "does_not_exist")
    assert rel.current_sha(root) == "sha_v1"
    # unhealthy release -> fail closed
    (root / "releases" / "sha_bad").mkdir(parents=True)  # no manifest / pyrnova / lock
    with pytest.raises(RuntimeError):
        rel.activate(root, "sha_bad")
    assert rel.current_sha(root) == "sha_v1"


def test_rollback_returns_prior_code_and_never_touches_state(tmp_path):
    root = tmp_path / "srv"
    # durable state lives OUTSIDE the release root and must survive a code rollback untouched
    state_root = tmp_path / "state"
    state_root.mkdir()
    state_file = state_root / "opportunities.jsonl"
    state_file.write_text('{"id":"live-data"}\n')

    rel.stage_release(root, _fake_source(tmp_path, "v1"), sha="sha_v1")
    rel.stage_release(root, _fake_source(tmp_path, "v2"), sha="sha_v2")
    rel.activate(root, "sha_v1")
    rel.activate(root, "sha_v2")
    assert rel.current_sha(root) == "sha_v2"

    rb = rel.rollback(root)
    assert rb["action"] == "rollback" and rel.current_sha(root) == "sha_v1"
    # code rollback did not touch durable state (data recovery is a distinct operation)
    assert state_file.read_text() == '{"id":"live-data"}\n'


def test_rollback_fails_closed_without_prior(tmp_path):
    root = tmp_path / "srv"
    rel.stage_release(root, _fake_source(tmp_path, "v1"), sha="only")
    rel.activate(root, "only")
    with pytest.raises(RuntimeError):
        rel.rollback(root)


def test_activation_history_is_audited(tmp_path):
    root = tmp_path / "srv"
    rel.stage_release(root, _fake_source(tmp_path, "v1"), sha="s1")
    rel.stage_release(root, _fake_source(tmp_path, "v2"), sha="s2")
    rel.activate(root, "s1")
    rel.activate(root, "s2")
    hist = rel.activation_history(root)
    assert [h["sha"] for h in hist] == ["s1", "s2"]
    assert hist[-1]["previous"] == "s1"
    log = (root / "activations.jsonl").read_text().splitlines()
    for line in log:
        json.loads(line)  # durable, parseable audit


def test_healthz_is_public_and_reports_release(tmp_path, monkeypatch):
    # B4.6 deploy health verification: /healthz is reachable WITHOUT a credential even under enforced auth.
    store = StateStore(tmp_path / "state")
    spec = importlib.util.spec_from_file_location("demo_seed_customers", _DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)
    policy = AccessPolicy.decide("0.0.0.0", store)  # non-local bind -> auth enforced
    assert policy.require_auth
    console = OperatorConsole(store, tmp_path / "p", tmp_path / "o",
                              mc_store=StateStore(_DEMO / "state"), customer_store=store,
                              cmc_store=StateStore(tmp_path / "cmc"),
                              access_check=access.request_access_check)
    handler_cls = make_handler(console, policy, store)
    h = handler_cls.__new__(handler_cls)
    h.path = "/healthz"
    h.headers = {"Content-Length": "0"}
    h.rfile = io.BytesIO(b"")
    h.wfile = io.BytesIO()
    h.end_headers = lambda *a, **k: None
    h.send_header = lambda *a, **k: None
    status = {}
    h.send_response = lambda code, *a, **k: status.update(code=code)
    # Report a release SHA from a manifest in the CWD (as WorkingDirectory=/srv/pyrnova/current would).
    monkeypatch.chdir(tmp_path)
    (tmp_path / "RELEASE.json").write_text(json.dumps({"sha": "deadbeef"}))
    h.do_GET()
    body = json.loads(h.wfile.getvalue().decode())
    assert status["code"] == 200 and body["status"] == "ok" and body["release"] == "deadbeef"
