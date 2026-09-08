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
    """Return a system disposition; a reviewer name never implies human acceptance."""
    if opp.catalyst.kind == "recompete_expiry":
        # Expiry is a direct fact but not enough to claim a scarce opportunity without a follow-on signal.
        disposition = "WATCH" if opp.relevance_score >= 0.15 else "REJECT"
        reason = "award expiry requires corroborating procurement evidence before STRIKE"
    elif opp.relevance_score >= relevance_threshold:
        disposition = "STRIKE"
        reason = "direct opportunity signal clears relevance threshold"
    elif opp.relevance_score >= 0.15:
        disposition = "WATCH"
        reason = "some relevance exists but STRIKE threshold is not met"
    else:
        disposition = "REJECT"
        reason = f"relevance {opp.relevance_score:.2f} below actionable floor 0.15"
    return Review(
        opportunity_id=opp.id,
        decision={"STRIKE": "recommend", "WATCH": "watch", "REJECT": "reject"}[disposition],
        reason=(
            f"{reason}; relevance {opp.relevance_score:.2f}; "
            + ("; ".join(opp.relevance_reasons) if opp.relevance_reasons else "capability overlap")
        ),
        confidence=opp.confidence,
        reviewer="auto-recommend/v2",
        system_disposition=disposition,
        score_at_review=opp.relevance_score,
    )


def adjudicate(
    opp: Opportunity,
    *,
    decision: str,
    reviewer: str,
    reason: str = "",
    reviewed_at: Optional[str] = None,
) -> Review:
    human = decision.strip().upper()
    if human not in {"ACCEPT", "WATCH", "REJECT"}:
        raise ValueError("decision must be ACCEPT, WATCH, or REJECT")
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer is required")
    return Review(
        opportunity_id=opp.id,
        decision=human.lower(),
        reason=reason,
        confidence=opp.confidence,
        reviewer=reviewer.strip(),
        human_decision=human,
        system_disposition=opp.meta.get("system_disposition", "WATCH"),
        score_at_review=opp.relevance_score,
        reviewed_at=reviewed_at or datetime.utcnow().isoformat(),
    )


def apply_review(opp: Opportunity, review: Review) -> Opportunity:
    disposition = review.human_decision or review.system_disposition
    opp.meta["system_disposition"] = review.system_disposition
    if disposition in ("ACCEPT", "STRIKE"):
        opp.state = "strike"
        opp.meta["review_status"] = "human_confirmed" if review.human_decision == "ACCEPT" else "pending_human"
    elif disposition == "WATCH":
        opp.state = "reviewing"
        opp.meta["review_status"] = "human_watch" if review.human_decision else "pending_human"
    else:
        opp.state = "rejected"
        opp.meta["review_status"] = "human_rejected" if review.human_decision else "rejected"
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
