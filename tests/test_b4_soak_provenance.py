import json
from datetime import datetime, timezone

import pytest

from pyrnova.archive import LocalEvidenceArchive
from pyrnova.customers import CustomerProfile, WatchlistEntry, add_watch, upsert_customer
from pyrnova.live_ops_acceptance import SOAK_DESIGNATION, SoakHarness, load_plan
from pyrnova.soak_provenance import build_provenance, verify_provenance
from pyrnova.state import StateStore


REQ = {
    "method": "POST",
    "url": "https://api.usaspending.gov/api/v2/search/spending_by_award/",
    "payload": {"query": "ironmountain"},
}


@pytest.fixture(autouse=True)
def clean_tracked_tree(monkeypatch):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_tracked_changes", lambda _repo: "")


def _plan(tmp_path, commit):
    (tmp_path / "ironmountain.json").write_text(json.dumps({
        "name": "IronMountain Solutions", "recipient_names": ["IronMountain Solutions"],
        "designation": SOAK_DESIGNATION, "agencies": ["Army"], "naics": ["541330"],
        "capabilities": ["engineering"],
    }))
    state = StateStore(tmp_path / "state")
    upsert_customer(state, CustomerProfile(
        customer_id="ironmountain", name="IronMountain Solutions", provenance=SOAK_DESIGNATION,
        effective_from="2026-09-12T00:00:00+00:00",
    ))
    add_watch(state, WatchlistEntry(
        customer_id="ironmountain", object_type="AGENCY", ref="Army",
        valid_from="2026-09-12T00:00:00+00:00",
    ))
    raw = {
        "soak_id": "phase1-test", "soak_test_lens": "IRONMOUNTAIN SOLUTIONS, LLC",
        "designation": SOAK_DESIGNATION, "canonical_commit": commit, "environment": "test",
        "duration_calendar_days": 7, "required_business_days": 5, "evidence_dir": "evidence",
        "state_dir": "state", "source_state_dir": "source-state", "archive_dir": "archive",
        "customers": [{"customer_id": "ironmountain", "profile": "ironmountain.json",
                       "monitored_objects": 1}],
        "sources": [
            {"source_id": "usaspending", "interval_seconds": 604800,
             "max_calls_per_epoch": 2, "request": REQ},
            {"source_id": "sam_opportunities", "interval_seconds": 86400, "max_calls_per_epoch": 2,
             "request": {"method": "GET", "url": "https://api.sam.gov/opportunities/v2/search",
                         "params": {"api_key": "${SAM_API_KEY}", "postedFrom": "{{date_minus_30_mmddyyyy}}",
                                    "postedTo": "{{today_mmddyyyy}}", "limit": 100, "offset": 0}}},
        ],
        "health_thresholds": {"unresolved_p0": 0, "silent_source_failure": 0},
        "failure_thresholds": {"uncontrolled_duplicates": 0, "tenant_leakage": 0},
        "allowed_observation": ["read logs"], "allowed_intervention": ["documented restart"],
        "invalidating_intervention": ["manual ordinary ingestion"],
        "restart_rule": "Any acceptance-critical code change restarts the seven-day window.",
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(raw))
    return path


def _configured(monkeypatch, commit):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: commit)
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type(
        "C", (), {"has_sam": True, "sam_api_key": "secret-not-logged"}
    )())


def _fetch(request):
    if "usaspending" in request["url"]:
        return b'{"results":[]}'
    return b'{"opportunitiesData":[],"totalRecords":0}'


def _run_clean_cycle(tmp_path, monkeypatch, commit="expected"):
    _configured(monkeypatch, commit)
    harness = SoakHarness(load_plan(_plan(tmp_path, commit)), repo=tmp_path)
    harness.start()
    cycle = harness.run_cycle(fetcher=_fetch, now=datetime(2026, 9, 14, 12, tzinfo=timezone.utc))
    assert cycle["ok"] is True
    return harness


def test_manifest_pins_commit_and_provenance_chain_verifies(tmp_path, monkeypatch):
    harness = _run_clean_cycle(tmp_path, monkeypatch)
    manifest = json.loads((tmp_path / "evidence" / "manifest.json").read_text())
    assert manifest["commit"] == "expected"

    archive = LocalEvidenceArchive(harness.archive_dir)
    prov = build_provenance(harness.evidence_dir, archive=archive, write=True)
    assert prov["ok"] is True
    assert prov["pinned_commit"] == "expected"
    assert prov["soak_cycles"] == 1
    assert prov["artifacts_verified"] == 2  # usaspending + sam raw bytes both re-hashed
    assert prov["chain_sha256"]
    assert (tmp_path / "evidence" / "provenance.json").is_file()

    # Re-derivation over untouched evidence reproduces the exact chain and confirms the stored record.
    again = verify_provenance(harness.evidence_dir, archive=archive)
    assert again["ok"] is True
    assert again["chain_sha256"] == prov["chain_sha256"]


def test_run_cycle_fails_closed_on_commit_drift(tmp_path, monkeypatch):
    _configured(monkeypatch, "expected")
    harness = SoakHarness(load_plan(_plan(tmp_path, "expected")), repo=tmp_path)
    harness.start()
    # Acceptance-critical code changed mid-soak: the pinned commit no longer matches HEAD.
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "changed")
    with pytest.raises(RuntimeError, match="immutability violated"):
        harness.run_cycle(fetcher=_fetch, now=datetime(2026, 9, 14, 12, tzinfo=timezone.utc))
    events = (tmp_path / "evidence" / "events.jsonl").read_text()
    assert '"invalidates_soak": true' in events
    # The recorded invalidating intervention makes provenance fail closed.
    prov = build_provenance(harness.evidence_dir)
    assert prov["ok"] is False
    assert any("invalidating intervention" in e for e in prov["errors"])


def test_run_cycle_fails_closed_on_dirty_tracked_tree(tmp_path, monkeypatch):
    _configured(monkeypatch, "expected")
    harness = SoakHarness(load_plan(_plan(tmp_path, "expected")), repo=tmp_path)
    harness.start()
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_tracked_changes", lambda _repo: " M pyrnova/x.py")
    with pytest.raises(RuntimeError, match="immutability violated"):
        harness.run_cycle(fetcher=_fetch, now=datetime(2026, 9, 14, 12, tzinfo=timezone.utc))


def test_provenance_detects_forged_cycle_commit(tmp_path, monkeypatch):
    harness = _run_clean_cycle(tmp_path, monkeypatch)
    # Forge a cycle that claims a different commit than the pinned one.
    cycles = tmp_path / "evidence" / "cycles.jsonl"
    forged = {"id": "cycle_forged", "phase": "SOAK", "commit": "other", "plan_hash": "x",
              "at": "2026-09-15T12:00:00+00:00", "sources": [], "ok": True}
    with cycles.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(forged) + "\n")
    prov = build_provenance(harness.evidence_dir)
    assert prov["ok"] is False
    assert any("not pinned commit" in e for e in prov["errors"])


def test_provenance_detects_tampered_artifact_and_stale_chain(tmp_path, monkeypatch):
    harness = _run_clean_cycle(tmp_path, monkeypatch)
    archive = LocalEvidenceArchive(harness.archive_dir)
    build_provenance(harness.evidence_dir, archive=archive, write=True)
    # Overwrite one archived artifact's bytes in place.
    artifact = next(p for p in harness.archive_dir.rglob("*") if p.is_file())
    artifact.write_bytes(b'{"results":[{"tampered":true}]}')
    result = verify_provenance(harness.evidence_dir, archive=archive)
    assert result["ok"] is False
    assert any("hash" in e for e in result["errors"])
    assert any("disagrees with recomputed chain" in e for e in result["errors"])


def test_provenance_binds_pinned_commit_to_staged_release(tmp_path, monkeypatch):
    harness = _run_clean_cycle(tmp_path, monkeypatch)
    archive = LocalEvidenceArchive(harness.archive_dir)
    not_released = build_provenance(harness.evidence_dir, archive=archive,
                                    released_shas={"some-other-sha"})
    assert not_released["ok"] is False
    assert any("not a staged immutable release" in e for e in not_released["errors"])
    released = build_provenance(harness.evidence_dir, archive=archive,
                               released_shas={"expected"})
    assert released["ok"] is True
