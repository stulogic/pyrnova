"""M12 — durable source integration: scheduler/jobs over control + source-state + archive (offline).

Exercises budgets, dedupe/cache, archive, backoff, circuit breaker, checkpoint/resume, source health,
and operator controls. Offline is the default: no test makes a network call, and the scheduler only ever
invokes a fetcher a caller explicitly supplies under an explicit live mode.
"""

import pytest

from pyrnova.archive import LocalEvidenceArchive, sha256_hex
from pyrnova.ops import OperatorConsole
from pyrnova.scheduler import (
    CACHE_HIT,
    CIRCUIT_OPEN,
    ERROR,
    LIVE_FETCH,
    OFFLINE_REPLAY,
    SKIPPED_BUDGET,
    SKIPPED_OFFLINE,
    SKIPPED_PAUSED,
    SourceScheduler,
)
from pyrnova.sources.control import CircuitState, SourceMode
from pyrnova.sources.source_state import SourceStateStore
from pyrnova.state import StateStore

REQ = {"method": "POST", "url": "https://api.usaspending.gov/api/v2/search/spending_by_award/",
       "payload": {"q": "x"}}


def _sched(tmp_path, **kw):
    st = SourceStateStore(tmp_path / "state")
    ar = LocalEvidenceArchive(tmp_path / "arch")
    return SourceScheduler(st, archive=ar, budget_epoch="2026-09-09", **kw)


# ---------------------------------------------------------------- offline default

def test_offline_default_never_fetches_and_skips_without_fixture(tmp_path):
    sched = _sched(tmp_path)
    r = sched.run_job("usaspending", request=REQ)  # no fetcher, no fixture
    assert r.action == SKIPPED_OFFLINE and r.mode == "OFFLINE"


def test_offline_replay_archives_fixture_without_network(tmp_path):
    sched = _sched(tmp_path)
    body = b'{"rows":[1,2,3]}'
    r = sched.run_job("usaspending", request=REQ, offline_bytes=body, checkpoint="page:2")
    assert r.action == OFFLINE_REPLAY
    assert r.content_sha256 == sha256_hex(body) and r.from_archive
    assert r.checkpoint == "page:2"


# ---------------------------------------------------------------- dedupe / cache

def test_repeat_request_is_served_from_cache_index(tmp_path):
    sched = _sched(tmp_path)
    body = b'{"rows":[1]}'
    sched.run_job("usaspending", request=REQ, offline_bytes=body)
    again = sched.run_job("usaspending", request=REQ, offline_bytes=body)
    assert again.action == CACHE_HIT and again.from_archive
    assert again.content_sha256 == sha256_hex(body)


# ---------------------------------------------------------------- budget (durable)

def test_budget_is_enforced_and_persists_across_restart(tmp_path):
    sched = _sched(tmp_path)
    fetch = lambda rq: b'{"live":1}'  # noqa: E731
    a = sched.run_job("usaspending", request=dict(REQ, payload={"q": "a"}),
                      fetcher=fetch, mode="LIVE_SAFE", max_calls=1)
    b = sched.run_job("usaspending", request=dict(REQ, payload={"q": "b"}),
                      fetcher=fetch, mode="LIVE_SAFE", max_calls=1)
    assert a.action == LIVE_FETCH and b.action == SKIPPED_BUDGET
    # A fresh scheduler over the same durable state inherits the exhausted budget within the epoch.
    reborn = SourceScheduler(SourceStateStore(tmp_path / "state"),
                             archive=LocalEvidenceArchive(tmp_path / "arch"), budget_epoch="2026-09-09")
    c = reborn.run_job("usaspending", request=dict(REQ, payload={"q": "c"}),
                       fetcher=fetch, mode="LIVE_SAFE", max_calls=1)
    assert c.action == SKIPPED_BUDGET


def test_new_budget_epoch_resets_the_count(tmp_path):
    sched = _sched(tmp_path)
    fetch = lambda rq: b'{"live":1}'  # noqa: E731
    sched.run_job("usaspending", request=dict(REQ, payload={"q": "a"}),
                  fetcher=fetch, mode="LIVE_SAFE", max_calls=1)
    fresh = SourceScheduler(SourceStateStore(tmp_path / "state"),
                            archive=LocalEvidenceArchive(tmp_path / "arch"), budget_epoch="2026-09-10")
    r = fresh.run_job("usaspending", request=dict(REQ, payload={"q": "b"}),
                      fetcher=fetch, mode="LIVE_SAFE", max_calls=1)
    assert r.action == LIVE_FETCH  # a new epoch starts with a fresh budget


# ---------------------------------------------------------------- backoff + circuit breaker

def test_fetcher_error_records_backoff_and_opens_circuit(tmp_path):
    sched = _sched(tmp_path)

    def boom(rq):
        raise RuntimeError("503 service unavailable")

    results = []
    for i in range(3):  # default breaker threshold is 3 consecutive failures
        results.append(sched.run_job("usaspending", request=dict(REQ, payload={"q": i}),
                                      fetcher=boom, mode="LIVE_SAFE", max_calls=10))
    assert all(r.action == ERROR for r in results)
    assert results[0].retry and results[0].retry["delay_seconds"] >= 0
    # Circuit is now open; the next job is deferred without calling the fetcher.
    nxt = sched.run_job("usaspending", request=dict(REQ, payload={"q": "after"}),
                        fetcher=boom, mode="LIVE_SAFE", max_calls=10)
    assert nxt.action == CIRCUIT_OPEN
    row = next(r for r in sched.health() if r["source_id"] == "usaspending")
    assert row["circuit_state"] == CircuitState.OPEN.value


def test_reset_breaker_clears_open_circuit(tmp_path):
    sched = _sched(tmp_path)

    def boom(rq):
        raise RuntimeError("err")

    for i in range(3):
        sched.run_job("usaspending", request=dict(REQ, payload={"q": i}),
                      fetcher=boom, mode="LIVE_SAFE", max_calls=10)
    sched.reset_breaker("usaspending")
    row = next(r for r in sched.health() if r["source_id"] == "usaspending")
    assert row["circuit_state"] == CircuitState.CLOSED.value


# ---------------------------------------------------------------- checkpoint / resume

def test_checkpoint_persists_for_resume(tmp_path):
    sched = _sched(tmp_path)
    sched.run_job("usaspending", request=REQ, offline_bytes=b"{}", checkpoint="cursor:page-5")
    reborn = SourceScheduler(SourceStateStore(tmp_path / "state"))
    assert reborn.state.get_checkpoint("usaspending") == "cursor:page-5"


# ---------------------------------------------------------------- operator controls

def test_pause_blocks_jobs_and_resume_restores(tmp_path):
    sched = _sched(tmp_path)
    fetch = lambda rq: b"{}"  # noqa: E731
    sched.pause("usaspending", reason="maintenance")
    paused = sched.run_job("usaspending", request=REQ, fetcher=fetch, mode="LIVE_SAFE", max_calls=5)
    assert paused.action == SKIPPED_PAUSED and "maintenance" in paused.reason
    sched.resume("usaspending")
    ok = sched.run_job("usaspending", request=REQ, fetcher=fetch, mode="LIVE_SAFE", max_calls=5)
    assert ok.action == LIVE_FETCH


def test_operator_mode_override_persists(tmp_path):
    sched = _sched(tmp_path)  # default OFFLINE
    assert sched.effective_mode("usaspending") == SourceMode.OFFLINE
    sched.set_mode("usaspending", "LIVE_SAFE")
    reborn = SourceScheduler(SourceStateStore(tmp_path / "state"))
    assert reborn.effective_mode("usaspending") == SourceMode.LIVE_SAFE
    reborn.clear_mode("usaspending")
    assert reborn.effective_mode("usaspending") == SourceMode.OFFLINE


# ---------------------------------------------------------------- health report

def test_health_report_aggregates_sources(tmp_path):
    sched = _sched(tmp_path)
    sched.run_job("usaspending", request=REQ, offline_bytes=b"{}")
    sched.pause("sam_opportunities", reason="no key")
    report = sched.health_report()
    assert report["default_mode"] == "OFFLINE"
    assert report["source_count"] >= 2
    assert report["paused_count"] >= 1
    assert report["total_calls_avoided"] >= 1
    usasp = next(r for r in report["sources"] if r["source_id"] == "usaspending")
    assert usasp["indexed_requests"] == 1 and usasp["calls_avoided"] >= 1


# ---------------------------------------------------------------- ops panel extension

def test_ops_panel_surfaces_durable_source_operations(tmp_path):
    sched = _sched(tmp_path)
    sched.run_job("usaspending", request=REQ, offline_bytes=b"{}")
    console = OperatorConsole(StateStore(tmp_path / "ops"), tmp_path / "profiles",
                              tmp_path / "out", source_state_dir=tmp_path / "state")
    ops = console.source_operations()
    assert ops["configured"] is True
    assert any(s["source_id"] == "usaspending" for s in ops["sources"])


def test_ops_panel_degrades_without_source_state_dir(tmp_path):
    console = OperatorConsole(StateStore(tmp_path / "ops"), tmp_path / "profiles", tmp_path / "out")
    ops = console.source_operations()
    assert ops == {"configured": False, "source_count": 0, "sources": []}


# ---------------------------------------------------------------- acceptance forbids cache

def test_acceptance_mode_never_serves_from_cache(tmp_path):
    sched = _sched(tmp_path)
    sched.run_job("usaspending", request=REQ, offline_bytes=b"{}")  # seed the cache index
    fetch = lambda rq: b'{"fresh":1}'  # noqa: E731
    r = sched.run_job("usaspending", request=REQ, fetcher=fetch, mode="ACCEPTANCE", max_calls=5)
    assert r.action == LIVE_FETCH  # ACCEPTANCE demands a fresh retrieval, not the cached bytes
