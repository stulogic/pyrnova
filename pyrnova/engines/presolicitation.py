"""PRE-SOLICITATION ENGINE (deterministic).

Exploits SAM notice classes and status. Structures Sources Sought, RFI, Presolicitation, Special
Notices (and solicitation/amendment/cancellation transitions where present) into candidate
opportunities. This is the commercial wedge: see and qualify federal demand before the obvious RFP.
These signals are the wedge, not a permanent moat.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from ..models import Catalyst, Opportunity
from ..sources.sam import PRESOLICITATION_CLASSES

# How far ahead of an RFP each class typically sits (rough, for lead-time framing / prediction).
_CLASS_LEAD = {
    "sources_sought": "earliest signal — market research, often 6–18 months before award",
    "rfi": "early signal — requirement shaping, often 3–12 months before award",
    "presolicitation": "solicitation imminent — typically weeks before the RFP",
    "special_notice": "context signal — industry day, intent, or program news",
}


def _falsification(notice: dict) -> str:
    reasons = [
        "a Sources Sought / RFI is market research, not a commitment to procure — the requirement may "
        "never reach solicitation",
    ]
    if notice.get("set_aside"):
        reasons.append(
            f"set-aside is '{notice.get('set_aside')}' — verify eligibility before pursuing"
        )
    if notice.get("active") is False:
        reasons.append("notice is inactive/archived — may be superseded or cancelled")
    reasons.append("scope and incumbency may be pre-wired to a specific vendor")
    return "; ".join(reasons)


def detect_presolicitations(
    notices: list[dict],
    *,
    as_of: date,
    include_solicitations: bool = False,
) -> list[Opportunity]:
    """notices: normalized notice dicts (see normalize.normalize_notice)."""
    out: list[Opportunity] = []
    for n in notices:
        cls = n.get("notice_class")
        is_wedge = cls in PRESOLICITATION_CLASSES
        if not is_wedge and not (include_solicitations and cls in {"solicitation", "combined_synopsis_solicitation"}):
            continue
        deadline: Optional[date] = n.get("response_deadline")
        horizon = None
        if isinstance(deadline, date):
            horizon = deadline.toordinal() - as_of.toordinal()
        catalyst = Catalyst(
            kind=cls,
            detected_by="presolicitation_engine",
            horizon_days=horizon,
            summary=_CLASS_LEAD.get(cls, f"{cls} notice"),
            meta={
                "response_deadline": deadline.isoformat() if isinstance(deadline, date) else None,
                "posted_date": n["posted_date"].isoformat() if isinstance(n.get("posted_date"), date) else None,
            },
        )
        opp = Opportunity(
            title=f"{cls.replace('_', ' ').title()}: {n.get('title') or 'untitled notice'}",
            catalyst=catalyst,
            agency=n.get("agency"),
            naics=n.get("naics"),
            psc=n.get("psc"),
            expected_action_at=deadline.isoformat() if isinstance(deadline, date) else None,
            # Pre-solicitation notices are authoritative facts (they were posted); attractiveness depends
            # on how early the class sits and whether a deadline is still open.
            attractiveness=_class_attractiveness(cls, horizon),
            confidence=0.7,
            falsification=_falsification(n),
            recommended_action=(
                "Respond to shape the requirement; map to capability and past performance; identify the "
                "program office contact; watch for the follow-on Presolicitation/Solicitation."
            ),
            meta={
                "notice_id": n.get("notice_id"),
                "solicitation_number": n.get("solicitation_number"),
                "set_aside": n.get("set_aside"),
                "active": n.get("active"),
                "notice_type_raw": n.get("notice_type_raw"),
                "source": "sam_opportunities",
                "url": n.get("url"),
            },
        )
        out.append(opp)
    out.sort(key=lambda o: (_class_order(o.catalyst.kind), o.catalyst.horizon_days or 10**9))
    return out


def _class_attractiveness(cls: str, horizon: Optional[int]) -> float:
    base = {
        "sources_sought": 0.7,
        "rfi": 0.65,
        "presolicitation": 0.6,
        "special_notice": 0.4,
    }.get(cls, 0.5)
    if horizon is not None and horizon < 0:
        base -= 0.3  # deadline passed
    return round(max(0.0, min(1.0, base)), 2)


def _class_order(cls: str) -> int:
    return {"sources_sought": 0, "rfi": 1, "presolicitation": 2, "special_notice": 3}.get(cls, 4)
