"""M13 — controlled live operations: poll cadence + the recording LiveRunner + call telemetry.

Every test is offline: fetchers are injected callables (or none), so no test reaches the network. The
LiveRunner is exercised with a fake fetcher that returns fixed bytes; the real ``http_fetcher`` is unit-
tested only for its request-shaping / throttle-tagging, never against a live endpoint.
"""

import json

import pytest

from pyrnova.archive import LocalEvidenceArchive, sha256_hex
from pyrnova.live_ops import (
    LiveFetchError,
    LiveRunner,
    operating_cost_report,
    usaspending_record_count,
    usaspending_request,
)
from pyrnova.scheduler import (
    CACHE_HIT,
    LIVE_FETCH,
    SKIPPED_NOT_DUE,
    SKIPPED_PAUSED,
    SourceScheduler,
)
from pyrnova.sources.source_state import SourceStateStore

SID = "usaspending"


def _sched(tmp_path, **kw):
    st = SourceStateStore(tmp_path / "state")
    ar = LocalEvidenceArchive(tmp_path / "arch")
    return SourceScheduler(st, archive=ar, budget_epoch="2026-09-09", **kw)


def _payload(q):
    return {"filters": {"q": q}, "fields": ["Award ID"], "page": 1, "limit": 1}


# ------------------------------------------------------------------ poll cadence (WS-A)

def test_source_with_no_interval_is_due_by_default(tmp_path):
    sched = _sched(tmp_path)
    assert sched.due(SID) is True
    assert sched.next_poll_due(SID) is None


def test_not_due_within_interval_then_due_after(tmp_path):
    sched = _sched(tmp_path)
    sched.set_poll_interval(SID, 3600)
    assert sched.due(SID, now=1000.0) is True          # never polled -> due
    sched.mark_polled(SID, now=1000.0)
    assert sched.due(SID, now=1000.0 + 60) is False     # inside the window
    assert sched.due(SID, now=1000.0 + 3600) is True    # window elapsed
    assert sched.get_poll_interval(SID) == 3600.0


def test_poll_skips_when_not_due_without_issuing_request(tmp_path):
    sched = _sched(tmp_path)
    sched.set_poll_interval(SID, 3600)
    calls = {"n": 0}

    def fetch(rq):
        calls["n"] += 1
        return b'{"results":[]}'

    r1 = sched.poll(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                    max_calls=5, fetcher=fetch, now=1000.0)
    assert r1.action == LIVE_FETCH and calls["n"] == 1
    r2 = sched.poll(SID, request=usaspending_request(_payload("b")), mode="LIVE_SAFE",
                    max_calls=5, fetcher=fetch, now=1000.0 + 10)
    assert r2.action == SKIPPED_NOT_DUE and calls["n"] == 1  # no second external call


def test_paused_source_is_never_due(tmp_path):
    sched = _sched(tmp_path)
    sched.pause(SID, reason="operator hold")
    assert sched.due(SID) is False
    r = sched.poll(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                   max_calls=5, fetcher=lambda rq: b"{}")
    assert r.action == SKIPPED_PAUSED


def test_cache_hit_does_not_consume_the_poll_window(tmp_path):
    sched = _sched(tmp_path)
    sched.set_poll_interval(SID, 3600)
    body = b'{"results":[{"Award ID":"X"}]}'
    req = usaspending_request(_payload("a"))
    first = sched.poll(SID, request=req, mode="LIVE_SAFE", max_calls=5,
                       fetcher=lambda rq: body, now=1000.0)
    assert first.action == LIVE_FETCH
    # An identical request inside the window is a CACHE_HIT (dedupe wins) and must NOT be blocked as
    # not-due, because a cache hit spent no poll.
    again = sched.poll(SID, request=req, mode="LIVE_SAFE", max_calls=5,
                       fetcher=lambda rq: body, now=1000.0 + 10)
    assert again.action == CACHE_HIT


# ------------------------------------------------------------------ LiveRunner ledger (WS-A/D)

def test_live_runner_records_efficiency_ledger(tmp_path):
    sched = _sched(tmp_path)
    body = json.dumps({"results": [{"Award ID": "A"}, {"Award ID": "B"}]}).encode()
    runner = LiveRunner(sched, SID, mode="LIVE_SAFE", max_calls=10,
                        fetcher=lambda rq: body, record_counter=usaspending_record_count)
    e1 = runner.run(usaspending_request(_payload("a")))
    assert e1.action == LIVE_FETCH
    assert e1.requests_sent == 1 and e1.call_avoided == 0
    assert e1.records_returned == 2 and e1.is_new_content is True
    # Identical request -> cache hit, no call, counted as avoided.
    e2 = runner.run(usaspending_request(_payload("a")))
    assert e2.action == CACHE_HIT and e2.call_avoided == 1 and e2.requests_sent == 0
    s = runner.summary()
    assert s["requests_sent"] == 1 and s["calls_avoided"] == 1 and s["cache_hits"] == 1
    assert s["records_returned"] == 4 and s["new_records"] == 2
    assert e2.records_returned == 2 and s["unchanged_records"] == 2


def test_live_runner_marks_unchanged_content_on_identical_bytes(tmp_path):
    sched = _sched(tmp_path)
    body = json.dumps({"results": [{"Award ID": "A"}]}).encode()
    runner = LiveRunner(sched, SID, mode="LIVE_SAFE", max_calls=10, fetcher=lambda rq: body,
                        record_counter=usaspending_record_count)
    runner.run(usaspending_request(_payload("a")))          # new
    e = runner.run(usaspending_request(_payload("a")))       # same fingerprint -> cache hit
    assert e.is_new_content is False


# ------------------------------------------------------------------ throttle categorization (WS-F)

def test_throttle_tagged_exception_increments_throttle_metric(tmp_path):
    sched = _sched(tmp_path)

    def throttled(rq):
        raise LiveFetchError("HTTP 429", status=429, failure_category="throttle")

    r = sched.run_job(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                      max_calls=5, fetcher=throttled)
    assert r.action == "error"
    snap = sched.control_for(SID).snapshot()
    assert snap["throttles"] == 1  # categorized as throttle, not a generic service fault


def test_untagged_fetcher_error_is_generic_service_fault(tmp_path):
    sched = _sched(tmp_path)

    def boom(rq):
        raise RuntimeError("connection reset")

    r = sched.run_job(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                      max_calls=5, fetcher=boom)
    assert r.action == "error"
    snap = sched.control_for(SID).snapshot()
    assert snap["throttles"] == 0 and snap["retryable_errors"] == 1


# ------------------------------------------------------------------ restart / resume (WS-B)

def test_cadence_and_dedupe_survive_a_fresh_scheduler_object(tmp_path):
    body = b'{"results":[{"Award ID":"A"}]}'
    req = usaspending_request(_payload("a"))
    sched1 = _sched(tmp_path)
    sched1.set_poll_interval(SID, 3600)
    r1 = sched1.poll(SID, request=req, mode="LIVE_SAFE", max_calls=5,
                     fetcher=lambda rq: body, now=1000.0)
    assert r1.action == LIVE_FETCH

    # A brand-new scheduler reading the same state dir (simulating a process restart) must not re-issue
    # the archived request and must remember the cadence clock.
    sched2 = _sched(tmp_path)
    assert sched2.due(SID, now=1000.0 + 10) is False
    calls = {"n": 0}

    def fetch(rq):
        calls["n"] += 1
        return body

    r2 = sched2.poll(SID, request=req, mode="LIVE_SAFE", max_calls=5, fetcher=fetch, now=1000.0 + 4000)
    assert r2.action == CACHE_HIT and calls["n"] == 0  # dedupe wins; zero new external calls after restart


# ------------------------------------------------------------------ telemetry (WS-H)

def test_operating_cost_report_rolls_calls_and_avoidance(tmp_path):
    sched = _sched(tmp_path)
    body = b'{"results":[]}'
    runner = LiveRunner(sched, SID, mode="LIVE_SAFE", max_calls=10, fetcher=lambda rq: body)
    runner.run(usaspending_request(_payload("a")))   # live
    runner.run(usaspending_request(_payload("a")))   # cache hit
    runner.run(usaspending_request(_payload("b")))   # live
    rep = operating_cost_report(sched, source_ids=[SID], window_seconds=3600)
    assert rep["total_calls_made"] == 2
    assert rep["total_calls_avoided"] == 1
    src = rep["sources"][0]
    assert src["source_id"] == SID
    assert src["avoidance_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert src["projected_calls_per_day"] == pytest.approx(2 * 86400 / 3600, abs=0.1)


# ------------------------------------------------------------------ http_fetcher shaping (no network)

def test_http_fetcher_rejects_request_without_url():
    with pytest.raises(LiveFetchError):
        __import__("pyrnova.live_ops", fromlist=["http_fetcher"]).http_fetcher({"method": "GET"})


def test_http_fetcher_preserves_provider_retry_after(monkeypatch):
    monkeypatch.setattr(
        "pyrnova.live_ops.http.get_bytes_response",
        lambda *a, **k: (429, b"", {"Retry-After": "90"}),
    )
    with pytest.raises(LiveFetchError) as caught:
        __import__("pyrnova.live_ops", fromlist=["http_fetcher"]).http_fetcher(
            {"method": "GET", "url": "https://provider.example/data"}
        )
    assert caught.value.failure_category == "throttle"
    assert caught.value.retry_after_seconds == 90


def test_http_fetcher_transport_error_never_retains_query_credential(monkeypatch):
    from requests.exceptions import ConnectionError

    def fail(*args, **kwargs):
        raise ConnectionError("failed /search?api_key=private-test-key")

    monkeypatch.setattr("pyrnova.live_ops.http.get_bytes_response", fail)
    with pytest.raises(LiveFetchError) as caught:
        __import__("pyrnova.live_ops", fromlist=["http_fetcher"]).http_fetcher(
            {"url": "https://api.sam.gov/search?api_key=private-test-key"}
        )
    assert "ConnectionError" in str(caught.value)
    assert "private-test-key" not in str(caught.value)
    assert "api_key" not in str(caught.value)


def test_scheduler_retry_uses_provider_retry_after(tmp_path):
    sched = _sched(tmp_path)

    def throttled(_request):
        raise LiveFetchError("HTTP 429", status=429, failure_category="throttle",
                             retry_after_seconds=90)

    result = sched.poll(
        SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
        max_calls=5, fetcher=throttled, now=1000,
    )
    assert result.retry["provider_retry_after_seconds"] == 90
    assert sched.next_poll_due(SID) == 1090


def test_usaspending_request_targets_the_public_search_endpoint():
    req = usaspending_request(_payload("a"))
    assert req["method"] == "POST"
    assert req["url"].endswith("/search/spending_by_award/")
    assert "api.usaspending.gov" in req["url"]


def test_usaspending_record_count_is_robust_to_garbage():
    with pytest.raises(ValueError):
        usaspending_record_count(b"not json")
    assert usaspending_record_count(json.dumps({"results": [1, 2, 3]}).encode()) == 3


# ------------------------------------------------------------------ fault injection (WS-F)

def test_health_surfaces_durable_budget_after_restart(tmp_path):
    sched = _sched(tmp_path)
    sched.run_job(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                  max_calls=3, fetcher=lambda rq: b'{"results":[]}')
    fresh = _sched(tmp_path)  # simulate restart: health must still know the ceiling and remaining
    row = fresh.health([SID])[0]
    assert row["budget_limit"] == 3 and row["budget_remaining"] == 2


def test_circuit_breaker_state_persists_across_restart(tmp_path):
    sched = _sched(tmp_path)

    def boom(rq):
        raise RuntimeError("provider 500")

    # Default failure threshold is 3; drive the breaker open.
    for _ in range(3):
        sched.run_job(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                      max_calls=10, fetcher=boom)
    fresh = _sched(tmp_path)
    assert fresh.control_for(SID).circuit_state.value == "open"
    # A reborn scheduler must not call the fetcher while the circuit is open (no call storm).
    called = {"n": 0}

    def counting(rq):
        called["n"] += 1
        raise RuntimeError("should not run")

    r = fresh.run_job(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                      max_calls=10, fetcher=counting)
    assert r.action == "circuit_open" and called["n"] == 0
    fresh.reset_breaker(SID)
    assert _sched(tmp_path).control_for(SID).circuit_state.value == "closed"


def test_archive_failure_after_live_fetch_is_handled_without_crash_or_storm(tmp_path):
    from pyrnova.archive import LocalEvidenceArchive

    class BoomArchive(LocalEvidenceArchive):
        def put(self, *a, **k):
            raise IOError("disk full")

    st = SourceStateStore(tmp_path / "state")
    sched = SourceScheduler(st, archive=BoomArchive(tmp_path / "arch"), budget_epoch="e")
    calls = {"n": 0}

    def fetch(rq):
        calls["n"] += 1
        return b'{"results":[]}'

    # Threshold failures should open the circuit and stop calling the fetcher — no unbounded retry storm.
    for _ in range(5):
        r = sched.run_job(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                          max_calls=50, fetcher=fetch)
        assert r.action in ("error", "circuit_open")  # never an unhandled exception
    assert sched.control_for(SID).circuit_state.value == "open"
    assert calls["n"] < 5  # the breaker stopped the storm before every attempt hit the network
    # State is not half-written: the failed request was never indexed as a served response.
    assert len(st.load(SID).get("requests") or {}) == 0


def test_malformed_live_bytes_are_archived_without_corrupting_downstream(tmp_path):
    sched = _sched(tmp_path)
    runner = LiveRunner(sched, SID, mode="LIVE_SAFE", max_calls=5,
                        fetcher=lambda rq: b"<<not json at all>>",
                        record_counter=usaspending_record_count)
    e = runner.run(usaspending_request(_payload("a")))
    assert e.action == LIVE_FETCH           # archived exact bytes even though unparseable
    assert e.records_returned is None      # unavailable is distinct from a genuine empty response
    assert e.counting_error and runner.summary()["records_returned"] is None
    # Repeat is a clean cache hit — the malformed payload did not corrupt the dedupe index.
    again = runner.run(usaspending_request(_payload("a")))
    assert again.action == CACHE_HIT


def test_budget_exhaustion_never_invokes_the_fetcher(tmp_path):
    sched = _sched(tmp_path)
    calls = {"n": 0}

    def fetch(rq):
        calls["n"] += 1
        return b'{"results":[]}'

    sched.run_job(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                  max_calls=1, fetcher=fetch)
    assert calls["n"] == 1
    r = sched.run_job(SID, request=usaspending_request(_payload("b")), mode="LIVE_SAFE",
                      max_calls=1, fetcher=fetch)
    assert r.action == "skipped_budget" and calls["n"] == 1  # no call attempted once budget is gone


# ------------------------------------------------------------------ Operations Panel (WS-G)

def test_ops_panel_surfaces_m13_operating_state(tmp_path):
    from pyrnova.ops import OperatorConsole
    from pyrnova.state import StateStore

    state_dir = tmp_path / "srcstate"
    sched = SourceScheduler(SourceStateStore(state_dir),
                            archive=LocalEvidenceArchive(tmp_path / "arch"), budget_epoch="e")
    sched.set_poll_interval(SID, 3600)
    body = json.dumps({"results": [{"Award ID": "A"}]}).encode()
    sched.run_job(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                  max_calls=5, fetcher=lambda rq: body)
    sched.run_job(SID, request=usaspending_request(_payload("a")), mode="LIVE_SAFE",
                  max_calls=5, fetcher=lambda rq: body)  # cache hit

    console = OperatorConsole(StateStore(tmp_path / "opsstate"), tmp_path / "profiles",
                              tmp_path / "out", source_state_dir=state_dir)
    ops = console.source_operations()
    assert ops["configured"] is True
    row = next(r for r in ops["sources"] if r["source_id"] == SID)
    # M13 operating state is visible: cadence, budget, calls made/avoided, cache hits, circuit.
    for field in ("poll_interval_seconds", "next_poll_at", "due", "budget_limit", "budget_remaining",
                  "calls_made", "calls_avoided", "cache_hits", "circuit_state"):
        assert field in row
    assert row["calls_made"] == 1 and row["calls_avoided"] == 1 and row["cache_hits"] == 1
    # The operating-cost / call-telemetry view is attached.
    cost = ops["operating_cost"]
    assert cost["total_calls_made"] == 1 and cost["total_calls_avoided"] == 1
    csrc = next(c for c in cost["sources"] if c["source_id"] == SID)
    assert csrc["cache_hit_rate"] == pytest.approx(0.5, abs=1e-3)


def test_ops_panel_operating_state_degrades_without_source_dir(tmp_path):
    from pyrnova.ops import OperatorConsole
    from pyrnova.state import StateStore

    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "p", tmp_path / "o")
    ops = console.source_operations()
    assert ops["configured"] is False and ops["sources"] == []
