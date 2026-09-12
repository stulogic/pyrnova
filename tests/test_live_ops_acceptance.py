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
    SOAK_DESIGNATION,
)
from pyrnova.scheduler import ERROR, LIVE_FETCH, SourceScheduler
from pyrnova.sources.source_state import SourceStateStore
from pyrnova.state import StateStore


REQ = {
    "method": "POST",
    "url": "https://api.usaspending.gov/api/v2/search/spending_by_award/",
    "payload": {"query": "ironmountain"},
}


@pytest.fixture(autouse=True)
def clean_test_repository(monkeypatch):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_tracked_changes", lambda _repo: "")


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
        "designation": SOAK_DESIGNATION,
        "agencies": ["Army"], "naics": ["541330"], "capabilities": ["engineering"],
    }))
    state = StateStore(tmp_path / "state")
    upsert_customer(state, CustomerProfile(
        customer_id="ironmountain", name="IronMountain Solutions",
        provenance=SOAK_DESIGNATION,
        effective_from="2026-09-12T00:00:00+00:00",
    ))
    add_watch(state, WatchlistEntry(
        customer_id="ironmountain", object_type="AGENCY", ref="Army",
        valid_from="2026-09-12T00:00:00+00:00",
    ))
    raw = {
        "soak_id": "phase1-test", "soak_test_lens": "IRONMOUNTAIN SOLUTIONS, LLC",
        "designation": SOAK_DESIGNATION,
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


def test_preflight_rejects_dirty_tracked_tree_and_commercial_label(tmp_path, monkeypatch):
    path = _plan(tmp_path, "expected")
    raw = json.loads(path.read_text())
    raw["customer_1"] = "IronMountain Solutions"
    path.write_text(json.dumps(raw))
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_tracked_changes", lambda _repo: " M file.py")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type("C", (), {"has_sam": True})())
    result = preflight(load_plan(path), repo=tmp_path)
    assert result["ok"] is False
    assert any("uncommitted tracked changes" in error for error in result["errors"])
    assert any("customer_1 must not label" in error for error in result["errors"])


def test_foreground_cycle_proves_idempotency_without_starting_soak(tmp_path, monkeypatch):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type(
        "C", (), {"has_sam": True, "sam_api_key": "configured"}
    )())
    path = _plan(tmp_path, "expected")
    profile = tmp_path / "ironmountain.json"
    raw = json.loads(profile.read_text())
    raw.pop("naics")  # unsupported NAICS is optional, not an invented runtime requirement
    profile.write_text(json.dumps(raw))
    harness = SoakHarness(load_plan(path), repo=tmp_path)
    result = harness.run_foreground(fetcher=lambda request: (
        b'{"results":[]}' if "usaspending" in request["url"]
        else b'{"opportunitiesData":[],"totalRecords":0}'
    ))
    assert result["ok"] is True
    assert result["idempotency"]["inserted"] == result["idempotency"]["updated"] == 0
    assert not (tmp_path / "evidence" / "manifest.json").exists()
    assert (tmp_path / "evidence" / "foreground_validation.json").is_file()


def test_copied_example_plan_paths_resolve_from_documented_destination(tmp_path):
    from pathlib import Path

    raw = json.loads((Path(__file__).parents[1] / "ops" / "phase1_soak_plan.example.json").read_text())
    destination = tmp_path / "var" / "phase1_soak" / "plan.json"
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(raw))
    plan = load_plan(destination)
    assert plan.evidence_dir == destination.parent / "evidence"
    assert (destination.parent / raw["state_dir"]).resolve() == tmp_path / "var" / "state"


def test_failed_foreground_does_not_run_repairing_idempotency_fanout(tmp_path, monkeypatch):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type(
        "C", (), {"has_sam": True, "sam_api_key": "configured"}
    )())
    harness = SoakHarness(load_plan(_plan(tmp_path, "expected")), repo=tmp_path)
    result = harness.run_foreground(fetcher=lambda request: (
        b"malformed" if "usaspending" in request["url"]
        else b'{"opportunitiesData":[],"totalRecords":0}'
    ))
    assert result["ok"] is False
    assert result["idempotency"]["skipped"] is True
    assert not (tmp_path / "evidence" / "manifest.json").exists()


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


@pytest.mark.parametrize("source_id,expected,sha", [
    ("usaspending", 14, "df603dca8d27bbae28bf83d33117c6a43d74ea2614c80321ff366ac7834010de"),
    ("sam_opportunities", 100, "c84b27447a621078093ae0675ec6fd517955b16764d91d0b201322bac8636ce6"),
])
def test_retained_real_page_counter_ledger_and_parser_agree(tmp_path, source_id, expected, sha):
    from functools import partial
    from pathlib import Path
    from pyrnova.archive import LocalEvidenceArchive, sha256_hex
    from pyrnova.live_ops import LiveRunner, source_record_count
    from pyrnova.live_ops_acceptance import _parse_source

    raw = (Path(__file__).parent / "fixtures/live_source_counts" / (source_id + ".json")).read_bytes()
    assert sha256_hex(raw) == sha
    scheduler = SourceScheduler(SourceStateStore(tmp_path / "source-state"),
                                archive=LocalEvidenceArchive(tmp_path / "archive"))
    request = {"method": "GET", "url": "https://example.test/retained"}
    scheduler.run_job(source_id, request=request, mode="OFFLINE", offline_bytes=raw)
    runner = LiveRunner(scheduler, source_id, mode="OFFLINE",
                        record_counter=partial(source_record_count, source_id))
    entry = runner.run(request)
    assert entry.requests_sent == 0
    assert entry.records_returned == expected
    assert entry.counting_error is None
    assert sum(map(len, _parse_source(source_id, raw))) == expected
    assert runner.summary()["records_returned"] == expected


def test_unwired_counter_is_unknown_in_entry_and_summary(tmp_path):
    from pyrnova.archive import LocalEvidenceArchive
    from pyrnova.live_ops import LiveRunner

    scheduler = SourceScheduler(SourceStateStore(tmp_path / "source-state"),
                                archive=LocalEvidenceArchive(tmp_path / "archive"))
    runner = LiveRunner(scheduler, "usaspending", fetcher=lambda _r: b'{"results":[{}]}')
    entry = runner.run(REQ)
    assert entry.action == LIVE_FETCH
    assert entry.records_returned is None and entry.counting_error
    summary = runner.summary()
    assert summary["records_returned"] is None
    assert summary["new_records"] is None and summary["unchanged_records"] is None
    assert summary["unknown_record_counts"] == 1


@pytest.mark.parametrize("source_id,key", [("usaspending", "results"),
                                            ("sam_opportunities", "opportunitiesData")])
@pytest.mark.parametrize("value", [None, {}, "rows"])
def test_malformed_source_rows_are_not_zero(source_id, key, value):
    from pyrnova.live_ops import source_record_count

    with pytest.raises(ValueError):
        source_record_count(source_id, json.dumps({key: value}).encode())
    with pytest.raises(ValueError):
        source_record_count(source_id, b"{}")


def test_false_zero_counter_fails_cycle_and_preserves_pending(tmp_path, monkeypatch):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type(
        "C", (), {"has_sam": True, "sam_api_key": "configured"}
    )())
    monkeypatch.setattr("pyrnova.live_ops_acceptance.source_record_count", lambda _sid, _raw: 0)
    harness = SoakHarness(load_plan(_plan(tmp_path, "expected")), repo=tmp_path)
    result = harness.run_foreground(fetcher=lambda request: (
        b'{"results":[{}]}' if "usaspending" in request["url"]
        else b'{"opportunitiesData":[{}],"totalRecords":100}'
    ))
    assert result["ok"] is False and result["cycle"]["fanout"]["skipped"]
    assert all("processing_error" in source for source in result["cycle"]["sources"])
    for sid in ("usaspending", "sam_opportunities"):
        assert harness.source_state.get_checkpoint(sid) is None
        assert harness.source_state.load(sid)["pending_processing"]


def test_cycle_counts_match_archives_and_written_ledgers(tmp_path, monkeypatch):
    from pyrnova.live_ops import source_record_count

    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type(
        "C", (), {"has_sam": True, "sam_api_key": "configured"}
    )())
    harness = SoakHarness(load_plan(_plan(tmp_path, "expected")), repo=tmp_path)
    result = harness.run_foreground(fetcher=lambda request: (
        b'{"results":[]}' if "usaspending" in request["url"]
        else b'{"opportunitiesData":[],"totalRecords":999}'
    ))
    assert result["ok"]
    cycle = result["cycle"]
    saved = json.loads((harness.evidence_dir / "foreground_cycles.jsonl").read_text())
    validation = json.loads((harness.evidence_dir / "foreground_validation.json").read_text())
    assert saved == cycle == validation["cycle"]
    for source in cycle["sources"]:
        raw = harness.archive.get(source["content_sha256"], source["source_id"])
        assert source_record_count(source["source_id"], raw) == source["records_returned"] == 0
    assert all(row["freshness_state"] == "CURRENT" for row in cycle["source_health"]["sources"]
               if row["source_id"] in {"usaspending", "sam_opportunities"})


@pytest.mark.parametrize("defect", [None, "counter", "hash", "checkpoint", "pending", "due", "intervention"])
def test_retained_gate_is_read_only_current_and_fails_closed(tmp_path, monkeypatch, defect):
    from pathlib import Path
    from pyrnova.live_ops import source_record_count

    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type(
        "C", (), {"has_sam": True, "sam_api_key": "configured"}
    )())
    original_plan = load_plan(_plan(tmp_path, "expected"))
    original_harness = SoakHarness(original_plan, repo=tmp_path)
    result = original_harness.run_foreground(fetcher=lambda request: (
        b'{"results":[]}' if "usaspending" in request["url"]
        else b'{"opportunitiesData":[],"totalRecords":0}'
    ))
    assert result["ok"]
    original_path = original_harness.evidence_dir / "foreground_validation.json"
    # Reproduce historical false-zero telemetry using the retained real pages, with a correctly
    # checkpointed completed acquisition. Production evidence is never modified by this test.
    historical = json.loads(original_path.read_text())
    for source in historical["cycle"]["sources"]:
        sid = source["source_id"]
        raw = (Path(__file__).parent / "fixtures/live_source_counts" / (sid + ".json")).read_bytes()
        ev = original_harness.archive.put(raw, source_id=sid, retention_tier="B")
        source["content_sha256"] = ev.content_sha256
        original_harness.source_state.record_request(
            sid, source["request_fingerprint"], content_sha256=ev.content_sha256,
            source_url="https://example.test/retained", fetched_at=historical["cycle"]["at"],
        )
    original_path.write_text(json.dumps(historical))
    raw_plan = dict(original_plan.raw, evidence_dir="corrected-evidence")
    corrected_path = tmp_path / "corrected-plan.json"
    corrected_path.write_text(json.dumps(raw_plan))
    harness = SoakHarness(load_plan(corrected_path), repo=tmp_path)
    if defect == "counter":
        monkeypatch.setattr("pyrnova.live_ops_acceptance.source_record_count", lambda _sid, _raw: 0)
    if defect in {"checkpoint", "pending", "due"}:
        doc = original_harness.source_state.load("usaspending")
        if defect == "checkpoint":
            doc["checkpoint"] = "different-cycle"
        elif defect == "pending":
            doc["pending_processing"] = {"content_sha256": "pending"}
        else:
            doc["schedule"]["last_polled"] = 0
        original_harness.source_state.save("usaspending", doc)
    if defect == "hash":
        row = historical["cycle"]["sources"][0]
        original_harness.archive._path(row["source_id"], row["content_sha256"]).write_bytes(b"corrupted")
    if defect == "intervention":
        (original_path.parent / "events.jsonl").write_text(json.dumps({"invalidates_soak": True}) + "\n")
    originals = {p: p.read_bytes() for directory in (
        original_harness.evidence_dir, original_harness.source_state_dir, original_harness.archive_dir,
        original_harness.state_dir,
    ) for p in directory.rglob("*") if p.is_file()}
    verified = harness.verify_retained_foreground(original_path)
    assert verified["ok"] == (defect is None)
    assert verified["additional_provider_calls"] == verified["manual_repairs"] == 0
    assert all(p.read_bytes() == before for p, before in originals.items())
    assert not (harness.evidence_dir / "manifest.json").exists()
    if defect is None:
        assert [r["records_returned"] for r in verified["cycle"]["sources"]] == [14, 100]
        assert all(r["prior_records_returned"] == 0 for r in verified["cycle"]["sources"])
        saved = json.loads((harness.evidence_dir / "foreground_cycles.jsonl").read_text())
        assert saved == verified["cycle"]
        for artifact, ledger in zip(verified["artifact_verification"], saved["sources"]):
            assert artifact["actual_count"] == artifact["recorded_count"] == ledger["records_returned"]
    else:
        assert verified["errors"]


def test_retained_gate_refuses_to_overwrite_original_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    monkeypatch.setattr("pyrnova.live_ops_acceptance.load_config", lambda: type(
        "C", (), {"has_sam": True, "sam_api_key": "configured"}
    )())
    harness = SoakHarness(load_plan(_plan(tmp_path, "expected")), repo=tmp_path)
    with pytest.raises(RuntimeError, match="new evidence directory"):
        harness.verify_retained_foreground(harness.evidence_dir / "foreground_validation.json")


@pytest.mark.parametrize("gate", [None, {"ok": False},
                                  {"ok": True, "cycle": {"commit": "wrong", "plan_hash": "wrong"}}])
def test_service_refuses_missing_failed_or_unpinned_start_gate(tmp_path, monkeypatch, gate):
    monkeypatch.setattr("pyrnova.live_ops_acceptance._repo_commit", lambda _repo: "expected")
    harness = SoakHarness(load_plan(_plan(tmp_path, "expected")), repo=tmp_path)
    if gate is not None:
        harness.evidence_dir.mkdir()
        (harness.evidence_dir / "foreground_validation.json").write_text(json.dumps(gate))
    with pytest.raises(RuntimeError, match="gate"):
        harness.serve()
    assert not (harness.evidence_dir / "manifest.json").exists()
