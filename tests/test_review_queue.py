from __future__ import annotations

import pytest

from pyrnova.review_queue import (
    JoinReview,
    adjudicate_join,
    enqueue_deferred,
    override_rate,
    pending_reviews,
)
from pyrnova.state import StateStore


def _deferred(relationship_id="rel-1", **overrides):
    base = {
        "relationship_id": relationship_id,
        "left_id": "left-1",
        "right_id": "right-1",
        "subject_id": "subj-1",
        "object_id": "obj-1",
        "predicate": "same_program",
        "pre_review_confidence": 0.52,
        "join_method": "inferred_strong_attribute",
        "automated_recommendation": "DEFER",
        "rationale": "attribute overlap but ambiguous",
        "evidence_ids": ["ev-1", "ev-2"],
        "first_observed_at": "2026-01-01T00:00:00",
    }
    base.update(overrides)
    return base


def test_enqueue_then_pending(tmp_path):
    store = StateStore(tmp_path)
    enqueue_deferred(store, _deferred())
    pending = pending_reviews(store)
    assert len(pending) == 1
    assert pending[0]["relationship_id"] == "rel-1"
    assert pending[0]["status"] == "pending"


def test_enqueue_idempotent(tmp_path):
    store = StateStore(tmp_path)
    enqueue_deferred(store, _deferred())
    enqueue_deferred(store, _deferred())
    pending = pending_reviews(store)
    assert len(pending) == 1


def test_adjudicate_accept(tmp_path):
    store = StateStore(tmp_path)
    enqueue_deferred(store, _deferred())
    review = adjudicate_join(
        store, "rel-1", decision="ACCEPT_JOIN", reviewer="alice", reason="looks right"
    )
    assert isinstance(review, JoinReview)
    assert review.decision == "ACCEPT_JOIN"
    assert review.reviewer == "alice"
    assert review.reason == "looks right"
    assert pending_reviews(store) == []


def test_adjudicate_reject(tmp_path):
    store = StateStore(tmp_path)
    enqueue_deferred(store, _deferred())
    review = adjudicate_join(store, "rel-1", decision="REJECT_JOIN", reviewer="bob")
    assert review.decision == "REJECT_JOIN"
    assert pending_reviews(store) == []


def test_adjudicate_watch(tmp_path):
    store = StateStore(tmp_path)
    enqueue_deferred(store, _deferred())
    review = adjudicate_join(store, "rel-1", decision="WATCH", reviewer="carol")
    assert review.decision == "WATCH"
    assert pending_reviews(store) == []


def test_prior_automated_state_retained(tmp_path):
    store = StateStore(tmp_path)
    enqueue_deferred(store, _deferred(automated_recommendation="DEFER", pre_review_confidence=0.47))
    review = adjudicate_join(store, "rel-1", decision="ACCEPT_JOIN", reviewer="alice")
    assert review.automated_recommendation == "DEFER"
    assert review.pre_review_confidence == 0.47


def test_adjudicate_unknown_relationship_raises(tmp_path):
    store = StateStore(tmp_path)
    with pytest.raises(ValueError):
        adjudicate_join(store, "does-not-exist", decision="ACCEPT_JOIN", reviewer="alice")


def test_adjudicate_invalid_decision_raises(tmp_path):
    store = StateStore(tmp_path)
    enqueue_deferred(store, _deferred())
    with pytest.raises(ValueError):
        adjudicate_join(store, "rel-1", decision="MAYBE", reviewer="alice")


def test_adjudicate_missing_reviewer_raises(tmp_path):
    store = StateStore(tmp_path)
    enqueue_deferred(store, _deferred())
    with pytest.raises(ValueError):
        adjudicate_join(store, "rel-1", decision="ACCEPT_JOIN", reviewer="")


def test_persistence_across_fresh_store(tmp_path):
    store1 = StateStore(tmp_path)
    enqueue_deferred(store1, _deferred())
    adjudicate_join(store1, "rel-1", decision="ACCEPT_JOIN", reviewer="alice", reason="ok")

    store2 = StateStore(tmp_path)
    assert pending_reviews(store2) == []
    reviews = list(store2.read("join_reviews"))
    assert len(reviews) == 1
    assert reviews[0]["relationship_id"] == "rel-1"
    assert reviews[0]["decision"] == "ACCEPT_JOIN"


def test_override_rate_math(tmp_path):
    store = StateStore(tmp_path)
    enqueue_deferred(store, _deferred(relationship_id="rel-1"))
    enqueue_deferred(store, _deferred(relationship_id="rel-2"))
    adjudicate_join(store, "rel-1", decision="ACCEPT_JOIN", reviewer="alice")
    adjudicate_join(store, "rel-2", decision="WATCH", reviewer="bob")

    stats = override_rate(store)
    assert stats["total"] == 2
    assert stats["accepts"] == 1
    assert stats["watches"] == 1
    assert stats["rejects"] == 0
    assert stats["human_override_rate"] == 0.5


def test_override_rate_empty(tmp_path):
    store = StateStore(tmp_path)
    stats = override_rate(store)
    assert stats["total"] == 0
    assert stats["human_override_rate"] == 0.0
