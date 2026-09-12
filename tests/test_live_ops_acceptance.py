import json
from datetime import datetime, timezone

import pytest

from pyrnova.customers import CustomerProfile, WatchlistEntry, add_watch, upsert_customer
from pyrnova.live_ops_acceptance import (
    SoakHarness,
    load_plan,
    main,
    preflight,
    record_important_miss,
)
from pyrnova.scheduler import ERROR, LIVE_FETCH, SourceScheduler
from pyrnova.sources.source_state import SourceStateStore
from pyrnova.state import StateStore


REQ = {
    "method": "POST",
    "url": "https://api.usaspending.gov/api/v2/search/spending_by_award/",
    "payload": {"query": "ironmountain"},
}


def test_poll_error_persists_retry_and_explicit_health(tmp_path):
    scheduler = SourceScheduler(SourceStateStore(tmp_path / "state"), budget_epoch="day")
    scheduler.set_poll_interval("usaspending", 3600)

    def fail(_request):
        raise RuntimeError("temporary 503")

    result = scheduler.poll(
        "usaspending", request=REQ, fetcher=fail, mode="LIVE_SAFE", max_calls=5, now=1000
    )
    assert result.action == ERROR
    assert result.retry["retryable"] is True
    retry_at = scheduler.next_poll_due("usaspending")
    assert 1000 < retry_at < 1065  # retry overrides the normal one-hour cadence
    row = scheduler.health(["usaspending"])[0]
    assert row["operational_state"] == "DEGRADED"
    assert row["freshness_state"] == "UNKNOWN"
    assert row["last_error"] == "temporary 503"
    assert row["last_network_attempt_at"].startswith("1970-01-01")


def test_poll_success_clears_retry_and_records_acquisition_health(tmp_path):
    scheduler = SourceScheduler(SourceStateStore(tmp_path / "state"), budget_epoch="day")
    scheduler.set_poll_interval("usaspending", 3600)
    result = scheduler.poll(
        "usaspending", request=REQ, fetcher=lambda _request: b'{"results":[]}',
        mode="LIVE_SAFE", max_calls=5,
    )
    assert result.action == LIVE_FETCH
    row = scheduler.health(["usaspending"])[0]
    assert row["operational_state"] == "HEALTHY"
    assert row["freshness_state"] == "CURRENT"
    assert row["last_successful_acquisition_at"]
    assert row["last_error"] is None


def test_important_miss_record_is_traced_and_idempotent(tmp_path):
    store = StateStore(tmp_path / "state")
    kwargs = dict(
        miss_class="identity", source_id="sam_opportunities", source_ref="notice-1",
        acquisition_ref="sha256:abc", assessment_ref="assessment-1", customer_id="ironmountain",
        relevance_state="NOT_EMITTED", emitted=False,
        detected_at="2026-09-12T12:00:00+00:00", reviewer="operator-1",
        notes="Known notice did not resolve to the watched entity.",
    )
    first = record_important_miss(store, **kwargs)
    second = record_important_miss(store, **kwargs)
    assert first["id"] == second["id"]
    assert store.count("important_misses") == 1
    assert first["source_ref"] == "notice-1" and first["assessment_ref"] == "assessment-1"


def test_important_miss_cli_records_and_lists(tmp_path, capsys):
    state_dir = tmp_path / "state"
    assert main([
        "record-miss", "--state-dir", str(state_dir), "--miss-class", "delivery",
        "--source-id", "sam_opportunities", "--source-ref", "notice-2",
        "--customer-id", "ironmountain", "--reviewer", "operator-1",
    ]) == 0
    recorded = json.loads(capsys.readouterr().out)
    assert recorded["miss_class"] == "delivery"
    assert main(["list-misses", "--state-dir", str(state_dir)]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert [row["id"] for row in listed] == [recorded["id"]]


def _plan(tmp_path, commit):
    profile = tmp_path / "ironmountain.json"
    profile.write_text(json.dumps({
        "name": "IronMountain Solutions", "recipient_names": ["IronMountain Solutions"],
        "agencies": ["Army"], "naics": ["541330"], "capabilities": ["engineering"],
    }))
    state = StateStore(tmp_path / "state")
    upsert_customer(state, CustomerProfile(
        customer_id="ironmountain", name="IronMountain Solutions",
        effective_from="2026-09-12T00:00:00+00:00",
    ))
    add_watch(state, WatchlistEntry(
        customer_id="ironmountain", object_type="AGENCY", ref="Army",
        valid_from="2026-09-12T00:00:00+00:00",
    ))
    raw = {
        "soak_id": "phase1-test", "customer_1": "IronMountain Solutions",
        "canonical_commit": commit, "environment": "test", "duration_calendar_days": 7,
        "required_business_days": 5, "evidence_dir": "evidence", "state_dir": "state",
        "source_state_dir": "source-state", "archive_dir": "archive",
        "customers": [{"customer_id": "ironmountain", "profile": "ironmountain.json",
                       "monitored_objects": 1}],
        "sources": [
            {"source_id": "usaspending", "interval_seconds": 604800,
             "max_calls_per_epoch": 2, "request": REQ},
            {"source_id": "sam_opportunities", "interval_seconds": 86400,
             "max_calls_per_epoch": 2,
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


def test_preflight_fails_closed_when_customer_lens_is_absent(tmp_path, monkeypatch):
    path = _plan(tmp_path, "expected")
    raw = json.loads(path.read_text())
    raw["customers"][0]["customer_id"] = "missing"
    path.write_text(json.dumps(raw))
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type("C", (), {"has_sam": True})())
    result = preflight(load_plan(path), repo=tmp_path)
    assert result["ok"] is False
    assert any("persisted customer Lens not found" in error for error in result["errors"])


def test_harness_runs_acquisition_pipeline_fanout_and_writes_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type(
        "C", (), {"has_sam": True, "sam_api_key": "secret-not-logged"}
    )())
    plan = load_plan(_plan(tmp_path, "expected"))
    harness = SoakHarness(plan, repo=tmp_path)
    manifest = harness.start()
    assert manifest["status"] == "SOAK_IN_PROGRESS"

    def fetch(request):
        if "usaspending" in request["url"]:
            return b'{"results":[]}'
        assert request["params"]["api_key"] == "secret-not-logged"
        return b'{"opportunitiesData":[],"totalRecords":0}'

    cycle = harness.run_cycle(
        fetcher=fetch, now=datetime(2026, 9, 14, 12, tzinfo=timezone.utc)
    )
    assert cycle["ok"] is True
    assert {row["action"] for row in cycle["sources"]} == {LIVE_FETCH}
    assert cycle["fanout"]["failure_count"] == 0
    evidence = (tmp_path / "evidence" / "cycles.jsonl").read_text()
    assert "secret-not-logged" not in evidence
    assert (tmp_path / "evidence" / "status.json").is_file()
    assert SourceStateStore(tmp_path / "source-state").get_checkpoint("usaspending") == cycle["id"]

    # A heartbeat inside both source cadence windows performs no external calls and no redundant fan-out.
    def no_fetch(_request):
        raise AssertionError("not-due heartbeat must not call a provider")

    heartbeat = harness.run_cycle(
        fetcher=no_fetch, now=datetime(2026, 9, 14, 12, 1, tzinfo=timezone.utc)
    )
    assert {row["action"] for row in heartbeat["sources"]} == {"skipped_not_due"}
    assert heartbeat["fanout"]["skipped"] is True


def test_harness_preserves_pending_archive_on_processing_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type(
        "C", (), {"has_sam": True, "sam_api_key": "configured"}
    )())
    plan = load_plan(_plan(tmp_path, "expected"))
    harness = SoakHarness(plan, repo=tmp_path)
    harness.start()

    def fetch(request):
        if "usaspending" in request["url"]:
            return b"malformed"
        return b'{"opportunitiesData":[],"totalRecords":0}'

    cycle = harness.run_cycle(
        fetcher=fetch, now=datetime(2026, 9, 14, 12, tzinfo=timezone.utc)
    )
    assert cycle["ok"] is False
    source_state = SourceStateStore(tmp_path / "source-state")
    assert source_state.get_checkpoint("usaspending") is None
    assert source_state.load("usaspending")["pending_processing"]["content_sha256"]
    health = next(row for row in cycle["source_health"]["sources"]
                  if row["source_id"] == "usaspending")
    assert health["operational_state"] == "DEGRADED"


def test_pipeline_customer_id_is_persisted_for_fanout(tmp_path, profile, award_rows, as_of):
    from pyrnova.archive import LocalEvidenceArchive
    from pyrnova.pipeline import run

    store = StateStore(tmp_path / "state")
    run(
        profile=profile, customer_id="tenant-1", award_rows=award_rows, notice_rows=[],
        archive=LocalEvidenceArchive(tmp_path / "archive"), store=store, as_of=as_of,
    )
    assert all(row["customer_id"] == "tenant-1" for row in store.read("opportunities"))
