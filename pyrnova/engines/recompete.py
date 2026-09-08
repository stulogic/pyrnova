"""RECOMPETE / EXPIRY ENGINE (deterministic).

Identifies contracts likely to return to market from period-of-performance end dates within a forward
window. Contract expiry alone is NOT treated as predictive intelligence — it is a high-confidence ENTRY
signal that becomes valuable once matched to capability, pre-solicitation activity, incumbent/history,
timing and actionability. Each candidate carries a mandatory falsification note and emits a prediction
for later outcome grading.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Optional

from ..models import Catalyst, Opportunity


def _attractiveness_from_amount(amount: Optional[float]) -> float:
    """Log-scaled 0..1: ~$100k -> ~0.3, ~$10M -> ~0.7, ~$1B -> ~1.0. Deterministic, monotonic."""
    if not amount or amount <= 0:
        return 0.0
    return max(0.0, min(1.0, (math.log10(amount) - 4.0) / 5.0))


def _falsification(months: float, amount: Optional[float]) -> str:
    reasons = []
    if months is not None and months < 3:
        reasons.append(
            "expiry is imminent (<3 months); a recompete solicitation may already be published or the "
            "period may be extended via option/bridge rather than re-competed"
        )
    reasons.append(
        "the award may carry unexercised option years — expiry may be deferred, not a true recompete"
    )
    reasons.append(
        "the incumbent may be strongly entrenched (past performance, transition risk), lowering "
        "displaceability"
    )
    reasons.append(
        "the requirement may be consolidated, restructured, or moved onto a different vehicle/IDIQ"
    )
    return "; ".join(reasons)


def detect_recompetes(
    awards: list[dict],
    *,
    as_of: date,
    window_days: int = 540,
    min_amount: float = 0.0,
) -> list[Opportunity]:
    """awards: normalized award dicts (see normalize.normalize_award)."""
    out: list[Opportunity] = []
    horizon_end = as_of.toordinal() + window_days
    for a in awards:
        end = a.get("end_date")
        if not isinstance(end, date):
            continue
        days_to_expiry = end.toordinal() - as_of.toordinal()
        if days_to_expiry < 0 or end.toordinal() > horizon_end:
            continue
        amount = a.get("amount")
        if amount is not None and amount < min_amount:
            continue
        months = round(days_to_expiry / 30.4, 1)
        catalyst = Catalyst(
            kind="recompete_expiry",
            detected_by="recompete_engine",
            horizon_days=days_to_expiry,
            summary=f"Contract period of performance ends {end.isoformat()} ({months} months).",
            meta={"end_date": end.isoformat(), "months_to_expiry": months},
        )
        title = (
            f"Recompete watch: {a.get('agency') or 'agency'} — incumbent "
            f"{a.get('recipient_name') or 'unknown'} (ends {end.isoformat()})"
        )
        opp = Opportunity(
            title=title,
            catalyst=catalyst,
            agency=a.get("agency"),
            incumbent=a.get("recipient_name"),
            naics=a.get("naics"),
            value_usd=amount,
            expected_action_at=end.isoformat(),
            attractiveness=_attractiveness_from_amount(amount),
            # Confidence in the ENTRY signal: expiry dates are authoritative, so confidence in the fact
            # is high; confidence that it becomes a real recompete is moderated by the falsification.
            confidence=round(0.75 - min(0.25, max(0.0, (3 - months) * 0.08)) if months else 0.6, 2),
            falsification=_falsification(months, amount),
            recommended_action=(
                "Confirm option-year status and re-compete intent; check SAM for a Sources Sought / "
                "Presolicitation on this requirement; assess incumbent displaceability and capability fit."
            ),
            meta={
                "award_id": a.get("award_id"),
                "sub_agency": a.get("sub_agency"),
                "contract_type": a.get("contract_type"),
                "months_to_expiry": months,
                "source": "usaspending",
                "url": a.get("url"),
            },
        )
        out.append(opp)
    # Rank: soonest, highest value first.
    out.sort(key=lambda o: (o.catalyst.horizon_days or 10**9, -(o.value_usd or 0)))
    return out
