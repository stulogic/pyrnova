"""Focused tests for the Customer Usefulness Ledger / Decision Memory (B1.4)."""

import pytest

from pyrnova.customers import GLOBAL_INTELLIGENCE_STREAMS
from pyrnova.decision_memory import (
    STREAM_DISPOSITIONS,
    Disposition,
    disposition_history,
    latest_disposition,
    list_dispositions,
    record_disposition,
)
from pyrnova.state import StateStore


def _store(tmp_path):
    return StateStore(tmp_path / "state")


def test_record_and_read_back_with_unknown_defaults(tmp_path):
    store = _store(tmp_path)
    record_disposition(store, Disposition(customer_id="c1", intelligence_ref="mc-1"))
    row = latest_disposition(store, "c1", "mc-1")
    assert row["origin"] == "CUSTOMER_FEEDBACK"
    # Everything genuinely unspecified stays UNKNOWN, never a fabricated value.
    for field in ("novelty", "relevance", "pursuit", "timing", "value", "important_miss", "reason", "outcome"):
        assert row[field] == "UNKNOWN"


def test_full_disposition_roundtrip_and_linkage(tmp_path):
    store = _store(tmp_path)
    record_disposition(store, Disposition(
        customer_id="c1", intelligence_ref="mc-1",
        novelty="NEW_TO_CUSTOMER", relevance="RELEVANT", pursuit="PURSUE",
        timing="EARLY_ENOUGH", value="ACTIONABLE", important_miss="NO", reason="GOOD_LEAD",
        note="strong C4ISR fit", outcome="BID",
        signal_ref="sig-9", evidence_refs=("ev-1", "ev-2"),
        pyrnova_assessment_ref="assess-7", outcome_ref="out-3",
    ))
    row = latest_disposition(store, "c1", "mc-1")
    assert row["pursuit"] == "PURSUE" and row["outcome"] == "BID"
    assert row["evidence_refs"] == ["ev-1", "ev-2"]
    assert row["pyrnova_assessment_ref"] == "assess-7"
    assert row["signal_ref"] == "sig-9" and row["outcome_ref"] == "out-3"


@pytest.mark.parametrize("field,bad", [
    ("novelty", "MAYBE"), ("relevance", "SORTA"), ("pursuit", "BID"),
    ("timing", "LATE"), ("value", "GREAT"), ("outcome", "WON"), ("reason", "BECAUSE"),
])
def test_invalid_vocabulary_is_rejected(tmp_path, field, bad):
    with pytest.raises(ValueError):
        Disposition(customer_id="c1", intelligence_ref="mc-1", **{field: bad})


def test_append_only_versions_latest_wins_history_preserved(tmp_path):
    store = _store(tmp_path)
    record_disposition(store, Disposition(customer_id="c1", intelligence_ref="mc-1",
                                          pursuit="WATCH", recorded_at="2026-03-01T00:00:00+00:00"))
    record_disposition(store, Disposition(customer_id="c1", intelligence_ref="mc-1",
                                          pursuit="PURSUE", outcome="BID",
                                          recorded_at="2026-03-05T00:00:00+00:00"))
    assert latest_disposition(store, "c1", "mc-1")["pursuit"] == "PURSUE"
    history = disposition_history(store, "c1", "mc-1")
    assert [h["pursuit"] for h in history] == ["WATCH", "PURSUE"]  # earlier reaction NOT overwritten


def test_as_of_selects_effective_version(tmp_path):
    store = _store(tmp_path)
    record_disposition(store, Disposition(customer_id="c1", intelligence_ref="mc-1",
                                          pursuit="WATCH", recorded_at="2026-03-01T00:00:00+00:00"))
    record_disposition(store, Disposition(customer_id="c1", intelligence_ref="mc-1",
                                          pursuit="PURSUE", recorded_at="2026-03-05T00:00:00+00:00"))
    early = latest_disposition(store, "c1", "mc-1", as_of="2026-03-02T00:00:00+00:00")
    assert early["pursuit"] == "WATCH"


def test_tenancy_isolation_between_customers(tmp_path):
    store = _store(tmp_path)
    record_disposition(store, Disposition(customer_id="c1", intelligence_ref="mc-1", pursuit="PURSUE"))
    record_disposition(store, Disposition(customer_id="c2", intelligence_ref="mc-1", pursuit="PASS"))
    assert latest_disposition(store, "c2", "mc-1")["pursuit"] == "PASS"
    assert [r["customer_id"] for r in list_dispositions(store, "c1")] == ["c1"]
    # c2 cannot see c1's private disposition object list
    assert all(r["customer_id"] == "c2" for r in list_dispositions(store, "c2"))


def test_dispositions_never_touch_global_intelligence_streams(tmp_path):
    store = _store(tmp_path)
    record_disposition(store, Disposition(customer_id="c1", intelligence_ref="mc-1", value="ACTIONABLE"))
    assert store.count(STREAM_DISPOSITIONS) == 1
    for stream in GLOBAL_INTELLIGENCE_STREAMS:
        assert store.count(stream) == 0


def test_note_is_length_capped(tmp_path):
    d = Disposition(customer_id="c1", intelligence_ref="mc-1", note="x" * 900)
    assert len(d.note) == 500
