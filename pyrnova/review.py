"""REVIEW — human adjudication is authoritative; here we record it as labeled intelligence work.

In v1 the pipeline produces a deterministic *recommendation*; a human confirms via the CLI (--reviewer),
which upgrades the recommendation to an accepted STRIKE. Every decision (accept/reject/recommend) is
recorded with its reason — that record is the benchmark corpus and the customer-relevance label.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from .models import Opportunity, Prediction, Review


def recommend(opp: Opportunity, *, relevance_threshold: float, reviewer: Optional[str]) -> Review:
    """Deterministic recommendation. If a human reviewer is named, it is recorded as an accept."""
    relevant = opp.relevance_score >= relevance_threshold
    if not relevant:
        return Review(
            opportunity_id=opp.id,
            decision="reject",
            reason=f"relevance {opp.relevance_score:.2f} < threshold {relevance_threshold:.2f}",
            confidence=opp.confidence,
            reviewer=reviewer or "auto-recommend/v1",
        )
    decision = "accept" if reviewer else "recommend"
    return Review(
        opportunity_id=opp.id,
        decision=decision,
        reason=(
            f"relevance {opp.relevance_score:.2f} ≥ threshold; "
            + ("; ".join(opp.relevance_reasons) if opp.relevance_reasons else "capability overlap")
        ),
        confidence=opp.confidence,
        reviewer=reviewer or "auto-recommend/v1",
    )


def apply_review(opp: Opportunity, review: Review) -> Opportunity:
    if review.decision in ("accept", "recommend"):
        opp.state = "strike"
        opp.meta["review_status"] = "human_confirmed" if review.decision == "accept" else "pending_human"
    else:
        opp.state = "rejected"
        opp.meta["review_status"] = "rejected"
    return opp


def make_prediction(opp: Opportunity, *, as_of: date) -> Prediction:
    """A falsifiable, gradeable statement tied to the opportunity's precursor class."""
    cls = opp.catalyst.kind
    lead = opp.catalyst.horizon_days
    resolve_by = None
    if opp.expected_action_at:
        resolve_by = opp.expected_action_at
    elif lead is not None:
        resolve_by = (as_of + timedelta(days=max(lead, 0))).isoformat()

    if cls == "recompete_expiry":
        statement = (
            f"A recompete solicitation for the requirement currently held by "
            f"{opp.incumbent or 'the incumbent'} ({opp.agency or 'agency'}) will be posted on SAM.gov "
            f"on or before {opp.expected_action_at or 'the expiry date'}."
        )
    else:
        statement = (
            f"The {cls.replace('_', ' ')} '{opp.title}' will progress toward a solicitation/award; "
            f"track for the follow-on notice."
        )
    return Prediction(
        opportunity_id=opp.id,
        statement=statement,
        precursor_class=cls,
        resolve_by=resolve_by,
        lead_time_days=lead,
        meta={"agency": opp.agency, "incumbent": opp.incumbent, "value_usd": opp.value_usd},
    )
