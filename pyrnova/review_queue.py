"""M6 human review queue for uncertain inferred cross-source joins.

The M6 inference engine computes a confidence for each candidate cross-source relationship.
Candidates that land in the ambiguous band [0.45, 0.60) are neither auto-accepted nor auto-rejected;
they are "deferred" for a human reviewer. This module persists that queue and the resulting
adjudications through StateStore (append-only JSONL), mirroring the idioms in review.py/models.py.

The engine hands us plain dicts (see the deferred-join shape in the M6 spec) — this module never
imports engine types, only StateStore and stdlib.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

from .state import StateStore

QUEUE_STREAM = "join_review_queue"
REVIEWS_STREAM = "join_reviews"

VALID_DECISIONS = {"ACCEPT_JOIN", "REJECT_JOIN", "WATCH"}


def _uid() -> str:
    return uuid.uuid4().hex


@dataclass
class JoinReview:
    relationship_id: str
    decision: str  # ACCEPT_JOIN | REJECT_JOIN | WATCH
    reviewer: str
    reason: str
    pre_review_confidence: float
    automated_recommendation: str
    prior_disposition: Optional[str] = None
    reviewed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    subject_id: Optional[str] = None
    object_id: Optional[str] = None
    predicate: Optional[str] = None
    join_method: Optional[str] = None
    first_observed_at: Optional[str] = None
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


def _to_record(obj: Any) -> dict:
    return asdict(obj)


def _pending_queue_state(store: StateStore) -> dict[str, dict]:
    """Deterministically reduce the append-only queue log to the latest state per relationship_id.

    Returns a dict of relationship_id -> latest queue record, filtered to those whose latest
    status is "pending" (i.e. enqueued and not yet resolved by an adjudication).
    """
    latest: dict[str, dict] = {}
    for record in store.read(QUEUE_STREAM):
        rel_id = record.get("relationship_id")
        if not rel_id:
            continue
        latest[rel_id] = record
    return {rel_id: rec for rel_id, rec in latest.items() if rec.get("status") == "pending"}


def enqueue_deferred(store: StateStore, deferred: dict) -> dict:
    """Persist a pending review item for a deferred join. Idempotent on relationship_id."""
    rel_id = deferred["relationship_id"]
    pending = _pending_queue_state(store)
    if rel_id in pending:
        return pending[rel_id]

    record = {
        "id": _uid(),
        "relationship_id": rel_id,
        "left_id": deferred.get("left_id"),
        "right_id": deferred.get("right_id"),
        "subject_id": deferred.get("subject_id"),
        "object_id": deferred.get("object_id"),
        "predicate": deferred.get("predicate"),
        "pre_review_confidence": deferred.get("pre_review_confidence"),
        "join_method": deferred.get("join_method"),
        "automated_recommendation": deferred.get("automated_recommendation"),
        "rationale": deferred.get("rationale"),
        "evidence_ids": deferred.get("evidence_ids", []),
        "first_observed_at": deferred.get("first_observed_at"),
        "status": "pending",
    }
    store.append(QUEUE_STREAM, record)
    return record


def pending_reviews(store: StateStore) -> list[dict]:
    """Return currently pending join reviews (enqueued, not yet dispositioned)."""
    return list(_pending_queue_state(store).values())


def adjudicate_join(
    store: StateStore,
    relationship_id: str,
    *,
    decision: str,
    reviewer: str,
    reason: str = "",
) -> JoinReview:
    """Record a human disposition for a pending deferred join."""
    human = decision.strip().upper() if decision else ""
    if human not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of {sorted(VALID_DECISIONS)}, got {decision!r}")
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer is required")

    pending = _pending_queue_state(store)
    item = pending.get(relationship_id)
    if item is None:
        raise ValueError(f"no pending join review found for relationship_id={relationship_id!r}")

    join_review = JoinReview(
        relationship_id=relationship_id,
        decision=human,
        reviewer=reviewer.strip(),
        reason=reason,
        pre_review_confidence=item.get("pre_review_confidence"),
        automated_recommendation=item.get("automated_recommendation"),
        prior_disposition=item.get("automated_recommendation"),
        reviewed_at=datetime.utcnow().isoformat(),
        subject_id=item.get("subject_id"),
        object_id=item.get("object_id"),
        predicate=item.get("predicate"),
        join_method=item.get("join_method"),
        first_observed_at=item.get("first_observed_at"),
    )
    store.append(REVIEWS_STREAM, _to_record(join_review))

    store.append(
        QUEUE_STREAM,
        {
            "id": _uid(),
            "relationship_id": relationship_id,
            "status": "resolved",
            "review_id": join_review.id,
            "decision": human,
        },
    )
    return join_review


def override_rate(store: StateStore) -> dict:
    """Compute aggregate human-override statistics over all adjudicated join reviews."""
    total = 0
    accepts = 0
    rejects = 0
    watches = 0
    overrides = 0

    for record in store.read(REVIEWS_STREAM):
        total += 1
        decision = record.get("decision")
        automated = record.get("automated_recommendation")
        if decision == "ACCEPT_JOIN":
            accepts += 1
        elif decision == "REJECT_JOIN":
            rejects += 1
        elif decision == "WATCH":
            watches += 1

        # automated "DEFER" agrees only with human WATCH; ACCEPT_JOIN/REJECT_JOIN are overrides.
        if automated == "DEFER":
            if decision != "WATCH":
                overrides += 1
        else:
            # For any other automated recommendation, treat disagreement literally.
            if decision != automated:
                overrides += 1

    rate = (overrides / total) if total else 0.0
    return {
        "total": total,
        "accepts": accepts,
        "rejects": rejects,
        "watches": watches,
        "overrides": overrides,
        "human_override_rate": rate,
    }
