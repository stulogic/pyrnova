"""Durable cross-restart source state — focused tests (offline, no HTTP)."""

from __future__ import annotations

from pyrnova.sources.control import CircuitState, SourceControl, SourceMode
from pyrnova.sources.source_state import SourceStateStore


def test_budget_survives_restart_and_stops(tmp_path):
    store = SourceStateStore(tmp_path)
    c1 = SourceControl(SourceMode.LIVE_SAFE, max_calls=3)
    c1.prepare()  # 1
    c1.prepare()  # 2
    store.persist_control("sam", c1, budget_epoch="2026-09-09")

    # Fresh process/control hydrated from disk: the two prior calls are remembered.
    c2 = store.hydrate_control("sam", SourceControl(SourceMode.LIVE_SAFE, max_calls=3),
                               budget_epoch="2026-09-09")
    assert c2.budget.calls_made == 2
    c2.prepare()  # 3 -> budget now exhausted
    import pytest
    with pytest.raises(Exception):
        c2.prepare()


def test_budget_resets_on_new_epoch(tmp_path):
    store = SourceStateStore(tmp_path)
    c1 = SourceControl(SourceMode.LIVE_SAFE, max_calls=5)
    c1.prepare(); c1.prepare()
    store.persist_control("sam", c1, budget_epoch="2026-09-09")
    c2 = store.hydrate_control("sam", SourceControl(SourceMode.LIVE_SAFE, max_calls=5),
                               budget_epoch="2026-09-10")  # new day
    assert c2.budget.calls_made == 0


def test_breaker_state_persists(tmp_path):
    store = SourceStateStore(tmp_path)
    c1 = SourceControl(SourceMode.LIVE_SAFE, max_calls=10)
    for _ in range(3):
        c1.record_failure("throttle")
    assert c1.circuit_state == CircuitState.OPEN
    store.persist_control("sam", c1, budget_epoch="e")
    c2 = store.hydrate_control("sam", SourceControl(SourceMode.LIVE_SAFE, max_calls=10),
                               budget_epoch="e")
    assert c2.breaker.state == CircuitState.OPEN
    assert c2.breaker.next_permitted_poll == c1.breaker.next_permitted_poll


def test_request_dedupe_index(tmp_path):
    store = SourceStateStore(tmp_path)
    assert store.seen_request("sam", "fp1") is None
    store.record_request("sam", "fp1", content_sha256="abc", fetched_at="2026-09-09T00:00:00Z")
    hit = store.seen_request("sam", "fp1")
    assert hit["content_sha256"] == "abc"
    # survives a fresh store instance (persisted to disk)
    assert SourceStateStore(tmp_path).seen_request("sam", "fp1")["fetched_at"].startswith("2026-09-09")


def test_checkpoint_roundtrip_and_isolation(tmp_path):
    store = SourceStateStore(tmp_path)
    assert store.get_checkpoint("sec_edgar") is None
    store.set_checkpoint("sec_edgar", "2024-03-20")
    assert store.get_checkpoint("sec_edgar") == "2024-03-20"
    assert store.get_checkpoint("sam") is None  # per-source isolation


def test_corrupt_and_missing_document_are_safe(tmp_path):
    store = SourceStateStore(tmp_path)
    (tmp_path / "sam.json").write_text("{not json", encoding="utf-8")
    doc = store.load("sam")
    assert doc["requests"] == {} and doc["checkpoint"] is None


def test_source_id_is_path_safe(tmp_path):
    store = SourceStateStore(tmp_path)
    store.set_checkpoint("../evil/../x", "v")  # must not escape root
    assert list(tmp_path.glob("*.json"))
    assert not (tmp_path.parent / "evil").exists()
