"""Backup + isolated restore verification (Phase 1 operational blocker).

Covers: deterministic manifest + integrity verification, fail-closed on corruption / missing artifact /
incompatible format / unsafe target, isolated restore round-trip, and the acceptance semantics —
canonical identity, customer isolation, provenance, temporal/AS-OF, checkpoints/idempotency, safe
derived regeneration, source-rights reconciliation, and the negative non-resurrection test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyrnova import access, backup
from pyrnova.state import StateStore


# ------------------------------------------------------------------ fixture source runtime

def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


@pytest.fixture
def source_root(tmp_path: Path) -> Path:
    """A controlled Pyrnova source runtime with two tenants and a restricted-source history record."""
    root = tmp_path / "src"
    state = root / "var" / "state"
    archive = root / "var" / "archive"

    # Two tenants (application-layer isolation, keyed by customer_id).
    _write_jsonl(state / "customers.jsonl", [
        {"_ts": "2026-09-10T12:00:00", "customer_id": "torch", "name": "Torch Technologies"},
        {"_ts": "2026-09-10T12:00:01", "customer_id": "dap", "name": "DAP Inc"},
    ])

    # Material changes: one currently-displayable (usaspending, GREEN) and one whose source became
    # restricted under current policy (reuters, BLACK) — the non-resurrection fixture. Both carry
    # deterministic canonical ids and point-in-time temporal fields.
    _write_jsonl(state / "customer_material_changes.jsonl", [
        {
            "_ts": "2026-09-10T12:00:02",
            "customer_id": "torch", "record_id": "cmc_torch_allowed_0001",
            "material_change_id": "thr_torchallowed01", "disposition": "OPPORTUNITY",
            "content_hash": "aaaa1111", "content_version": 1,
            "intelligence_observed_at": "2026-08-31", "first_relevant_at": "2026-08-31",
            "valid_from": "2026-09-10T12:00:02+00:00", "ingest_run_id": "fanrun_alpha",
            "source_ids": ["usaspending"],
            "source_refs": {"evidence_ids": ["usaspending:award:AB123"], "archive_hash": "aaaa1111",
                            "source_ref": "usaspending:award:AB123"},
        },
        {
            "_ts": "2026-09-10T12:00:03",
            "customer_id": "dap", "record_id": "cmc_dap_restricted_0002",
            "material_change_id": "thr_daprestricted2", "disposition": "THREAT",
            "content_hash": "bbbb2222", "content_version": 1,
            "intelligence_observed_at": "2026-08-15", "first_relevant_at": "2026-08-15",
            "valid_from": "2026-09-10T12:00:03+00:00", "ingest_run_id": "fanrun_beta",
            "source_ids": ["reuters"],
            "source_refs": {"source_ref": "reuters:article:99", "archive_hash": "bbbb2222"},
        },
    ])

    # Operational checkpoints / idempotency ledger.
    _write_jsonl(state / "fanout_runs.jsonl", [
        {"_ts": "2026-09-10T12:00:02", "id": "fanrun_alpha", "cursor": 10},
        {"_ts": "2026-09-10T12:00:03", "id": "fanrun_beta", "cursor": 20},
    ])

    # Opportunities with canonical ids + first-seen temporal state (the moat).
    _write_jsonl(state / "opportunities.jsonl", [
        {"_ts": "2026-09-01T00:00:00", "id": "opp_stable_0001", "first_seen_at": "2026-09-01T00:00:00",
         "source_id": "usaspending"},
    ])

    # A derived, regenerable stream that MUST NOT be captured.
    _write_jsonl(state / "replay_results.jsonl", [
        {"_ts": "2026-09-01T00:00:00", "id": "replay_1", "derived": True},
    ])

    # Content-addressed evidence object + observation sidecar.
    content = b'{"award_id":"AB123","amount":1000000}'
    import hashlib
    sha = hashlib.sha256(content).hexdigest()
    obj = archive / "usaspending" / sha[:2] / sha
    obj.parent.mkdir(parents=True, exist_ok=True)
    obj.write_bytes(content)
    _write_jsonl(archive / "usaspending" / sha[:2] / f"{sha}.observations.jsonl", [
        {"id": "ev1", "source_id": "usaspending", "content_sha256": sha, "first_seen_at": "2026-09-01T00:00:00"},
    ])

    # Schema identity.
    (root / "db").mkdir(parents=True, exist_ok=True)
    (root / "db" / "schema.sql").write_text("-- pyrnova schema\n", encoding="utf-8")

    # A real credential (only a salted hash is persisted; no plaintext secret in storage).
    meta, token = access.create_credential(StateStore(state), customer_id="torch", role="customer")
    # Stash the plaintext token on the fixture object via a side file the tests can read.
    (tmp_path / "plaintext_token.txt").write_text(token, encoding="utf-8")
    return root


# ------------------------------------------------------------------ integrity + format

def test_backup_manifest_deterministic_and_verifies(source_root, tmp_path):
    b1 = tmp_path / "b1"
    m = backup.create_backup(source_root, b1, source_commit="deadbeef", now="2026-09-14T00:00:00+00:00")
    assert m.status == "complete"
    assert m.manifest_sha256 == m.compute_manifest_sha256()
    # Deterministic: a second capture of the same state yields the same file inventory checksum.
    b2 = tmp_path / "b2"
    m2 = backup.create_backup(source_root, b2, source_commit="deadbeef", now="2026-09-14T00:00:00+00:00")
    assert m.manifest_sha256 == m2.manifest_sha256
    res = backup.verify_backup(b1)
    assert res.ok, res.problems
    assert res.checked == len(m.files)


def test_backup_excludes_derived_and_keeps_durable(source_root, tmp_path):
    b = tmp_path / "b"
    m = backup.create_backup(source_root, b)
    paths = {e.path for e in m.files}
    assert "state/customers.jsonl" in paths
    assert "state/fanout_runs.jsonl" in paths
    assert "schema.sql" in paths
    assert any(p.startswith("archive/") for p in paths)
    # Derived stream is excluded from capture but explicitly recorded as regenerable.
    assert not (b / "state" / "replay_results.jsonl").exists()
    assert "replay_results" in m.derived_excluded


def test_credentials_capture_has_no_plaintext_secret(source_root, tmp_path):
    b = tmp_path / "b"
    backup.create_backup(source_root, b)
    token = (tmp_path / "plaintext_token.txt").read_text().strip()
    secret = token.split(".", 1)[1]
    cred_file = b / "state" / "credentials.jsonl"
    assert cred_file.exists()
    blob = cred_file.read_text()
    assert secret not in blob            # plaintext secret never persisted -> never in backup
    assert "secret_hash" in blob         # only the salted one-way hash is captured


def test_verify_fails_on_corruption(source_root, tmp_path):
    b = tmp_path / "b"
    backup.create_backup(source_root, b)
    target = b / "state" / "customers.jsonl"
    target.write_text(target.read_text() + "tampered\n", encoding="utf-8")
    res = backup.verify_backup(b)
    assert not res.ok
    assert any("checksum mismatch" in p or "size mismatch" in p for p in res.problems)


def test_verify_fails_on_missing_artifact(source_root, tmp_path):
    b = tmp_path / "b"
    backup.create_backup(source_root, b)
    (b / "state" / "customers.jsonl").unlink()
    res = backup.verify_backup(b)
    assert not res.ok
    assert any("missing artifact" in p for p in res.problems)


def test_verify_fails_on_incompatible_format_version(source_root, tmp_path):
    b = tmp_path / "b"
    backup.create_backup(source_root, b)
    mf = b / "MANIFEST.json"
    data = json.loads(mf.read_text())
    data["format_version"] = 999
    mf.write_text(json.dumps(data))
    with pytest.raises(backup.BackupFormatError):
        backup.verify_backup(b)


# ------------------------------------------------------------------ independent copy + restore

def test_restore_roundtrip_via_independent_copy(source_root, tmp_path):
    import shutil
    b = tmp_path / "b"
    backup.create_backup(source_root, b)
    # SOURCE -> BACKUP -> INDEPENDENT COPY -> CLEAN RESTORE TARGET.
    independent = tmp_path / "independent_copy"
    shutil.copytree(b, independent)
    target = tmp_path / "restore_target"
    res = backup.restore_backup(independent, target)
    assert res.restored_files == len(res.manifest.files)
    # Restored durable files are byte-identical to source.
    assert (target / "var" / "state" / "customers.jsonl").read_bytes() == \
        (source_root / "var" / "state" / "customers.jsonl").read_bytes()
    assert (target / "db" / "schema.sql").exists()


def test_restore_refuses_unsafe_soak_target(source_root, tmp_path):
    b = tmp_path / "b"
    backup.create_backup(source_root, b)
    unsafe = tmp_path / "runtime" / "var" / "state"
    unsafe.mkdir(parents=True)
    with pytest.raises(backup.UnsafeRestoreTarget):
        backup.restore_backup(b, unsafe)


def test_restore_refuses_nonempty_target(source_root, tmp_path):
    b = tmp_path / "b"
    backup.create_backup(source_root, b)
    target = tmp_path / "notclean"
    target.mkdir()
    (target / "junk").write_text("x")
    with pytest.raises(backup.UnsafeRestoreTarget):
        backup.restore_backup(b, target)


def test_restore_fails_closed_on_corrupt_backup(source_root, tmp_path):
    b = tmp_path / "b"
    backup.create_backup(source_root, b)
    t = b / "state" / "opportunities.jsonl"
    t.write_bytes(t.read_bytes() + b"corruption")
    target = tmp_path / "restore_target"
    with pytest.raises(backup.BackupIntegrityError):
        backup.restore_backup(b, target)
    # Fail-closed: nothing partially materialised.
    assert not target.exists() or not any(target.iterdir())


# ------------------------------------------------------------------ acceptance semantics

@pytest.fixture
def restored(source_root, tmp_path):
    b = tmp_path / "b"
    backup.create_backup(source_root, b)
    target = tmp_path / "restore_target"
    backup.restore_backup(b, target)
    return target


def _load(target: Path, stream: str) -> list[dict]:
    p = target / "var" / "state" / f"{stream}.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def test_canonical_ids_preserved(restored, source_root):
    src_ids = {r["record_id"] for r in _load(source_root, "customer_material_changes")}
    got_ids = {r["record_id"] for r in _load(restored, "customer_material_changes")}
    assert got_ids == src_ids
    # Opportunity canonical id + first-seen survive without regeneration.
    opp = _load(restored, "opportunities")[0]
    assert opp["id"] == "opp_stable_0001"
    assert opp["first_seen_at"] == "2026-09-01T00:00:00"


def test_customer_isolation_preserved(restored):
    recs = _load(restored, "customer_material_changes")
    by_cust = {}
    for r in recs:
        by_cust.setdefault(r["customer_id"], []).append(r["record_id"])
    assert by_cust["torch"] == ["cmc_torch_allowed_0001"]
    assert by_cust["dap"] == ["cmc_dap_restricted_0002"]
    # No record leaks another tenant's id.
    assert not any(r["customer_id"] not in {"torch", "dap"} for r in recs)


def test_provenance_preserved(restored, source_root):
    src = {r["record_id"]: r for r in _load(source_root, "customer_material_changes")}
    got = {r["record_id"]: r for r in _load(restored, "customer_material_changes")}
    for rid, r in got.items():
        assert r["source_refs"] == src[rid]["source_refs"]  # SOURCE FACT / provenance intact
        assert r["disposition"] == src[rid]["disposition"]   # PYRNOVA DERIVED disposition intact


def test_temporal_as_of_preserved(restored, source_root):
    src = {r["record_id"]: r for r in _load(source_root, "customer_material_changes")}
    for r in _load(restored, "customer_material_changes"):
        s = src[r["record_id"]]
        assert r["intelligence_observed_at"] == s["intelligence_observed_at"]
        assert r["first_relevant_at"] == s["first_relevant_at"]
        assert r["valid_from"] == s["valid_from"]


def test_checkpoint_idempotency_preserved(restored, source_root):
    src = _load(source_root, "fanout_runs")
    got = _load(restored, "fanout_runs")
    assert {r["id"]: r["cursor"] for r in got} == {r["id"]: r["cursor"] for r in src}
    # Idempotency: restored record ids are unique (no duplicate processing / replay-from-zero).
    rids = [r["record_id"] for r in _load(restored, "customer_material_changes")]
    assert len(rids) == len(set(rids))


def test_safe_derived_regeneration(restored):
    s1 = backup.regenerate_derived_summary(restored)
    s2 = backup.regenerate_derived_summary(restored)
    assert s1 == s2                                   # deterministic regeneration
    assert s1["streams"]["customers"] == 2
    assert s1["archive_objects"] == 1                 # regenerated content index from restored bytes
    assert s1["customers"]["torch"]["customer_material_changes"] == 1


def test_source_rights_reconciliation_allows_current_and_blocks_restricted(restored):
    report = backup.reconcile_display(restored)
    assert report.total == 2
    by_rec = {d.record_id: d for d in report.decisions}
    # Currently-permitted source stays displayable.
    assert by_rec["cmc_torch_allowed_0001"].allowed is True
    # Restricted source is blocked from display after restore.
    assert by_rec["cmc_dap_restricted_0002"].allowed is False
    assert "reuters" in report.blocked_source_ids()


def test_non_resurrection_history_retained_but_not_displayed(restored):
    """The restricted record's durable evidence survives restore, but is NOT resurrected to display."""
    # History retained in durable restored state:
    recs = {r["record_id"] for r in _load(restored, "customer_material_changes")}
    assert "cmc_dap_restricted_0002" in recs
    # But reconciliation forbids display and the gate emits only a minimal (reference-only) projection.
    from pyrnova.sources import rights
    report = backup.reconcile_display(restored)
    blocked = next(d for d in report.decisions if d.record_id == "cmc_dap_restricted_0002")
    assert blocked.allowed is False
    assert blocked.reason_code.startswith("CLASS_")   # BLACK-class source denied by current policy
