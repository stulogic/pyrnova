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
    assert s["records_returned"] == 2 and s["new_records"] == 2


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


def test_usaspending_request_targets_the_public_search_endpoint():
    req = usaspending_request(_payload("a"))
    assert req["method"] == "POST"
    assert req["url"].endswith("/search/spending_by_award/")
    assert "api.usaspending.gov" in req["url"]


def test_usaspending_record_count_is_robust_to_garbage():
    assert usaspending_record_count(b"not json") == 0
    assert usaspending_record_count(json.dumps({"results": [1, 2, 3]}).encode()) == 3
