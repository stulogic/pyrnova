"""Archived USAspending recipient-profile bytes -> company SourceFacts (M10).

Turns an archived ``/api/v2/recipient/{id}/`` response into SourceFacts about a company's
eligibility categories, held socioeconomic set-aside certifications, UEI, and location. This is
the USAspending award-detail / recipient family — material evidence BEYOND prime award history.

Only genuine socioeconomic set-aside categories map to *held* certifications. A large business
(``other_than_small_business``) holds none of them, so a small-business set-aside requirement
correctly becomes an eligibility blocker via the existing fit engine — no fabrication.

The recipient snapshot has no intrinsic historical date, so its ``available_at`` MUST be supplied
by the caller (the observation date). This keeps the point-in-time gate honest: a recipient fact is
knowable only as of when it was observed, never retroactively.

Self-contained: imports only from ``pyrnova.multisource``. No imports from fit/replay/scoring.
"""

from __future__ import annotations

import json

from .multisource import SourceFact

RECIPIENT_SOURCE_ID = "usaspending_recipient"

# USAspending business_type code -> held socioeconomic set-aside certification (specific only).
BUSINESS_TYPE_CERT = {
    "small_business": "small business",
    "8a_program_participant": "8(a)",
    "8a_joint_venture": "8(a)",
    "woman_owned_business": "woman-owned small business",
    "economically_disadvantaged_women_owned_small_business": "edwosb",
    "women_owned_small_business": "woman-owned small business",
    "veteran_owned_business": "veteran-owned small business",
    "service_disabled_veteran_owned_business": "sdvosb",
    "historically_underutilized_business_zone_hubzone_firm": "hubzone",
    "minority_owned_business": "minority-owned business",
}


def parse_recipient(raw: bytes, *, company_name: str, available_at: str,
                    source_id: str = RECIPIENT_SOURCE_ID) -> list[SourceFact]:
    """Parse archived recipient bytes into SourceFacts, stamped with the observation ``available_at``.

    Never raises; returns [] on bad input. ``available_at`` is required and must be the date the
    snapshot was observed (recipient categories carry no intrinsic historical date)."""
    if not available_at:
        raise ValueError("parse_recipient requires an explicit observation available_at")
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []

    uei = payload.get("uei")
    ref = f"usaspending:recipient:{payload.get('recipient_id') or uei or 'unknown'}"
    facts: list[SourceFact] = []
    business_types = [str(t) for t in (payload.get("business_types") or [])]

    # Held socioeconomic certifications (specific set-asides only).
    for code in business_types:
        cert = BUSINESS_TYPE_CERT.get(code)
        if cert:
            facts.append(SourceFact(
                fact_type="certification", value=cert, source_id=source_id, source_ref=ref,
                available_at=available_at, evidence_strength=4, confidence=0.85,
                provenance=f"USAspending recipient business_type {code}",
            ))

    # Eligibility categories (observability; also lets a small-business set-aside block a large firm).
    if business_types:
        facts.append(SourceFact(
            fact_type="eligibility", value=sorted(set(business_types)), source_id=source_id,
            source_ref=ref, available_at=available_at, evidence_strength=4, confidence=0.85,
            provenance="USAspending recipient business_types",
        ))

    # UEI (identity/observability).
    if uei:
        facts.append(SourceFact(
            fact_type="uei", value=str(uei), source_id=source_id, source_ref=ref,
            available_at=available_at, evidence_strength=4, confidence=0.95,
            provenance="USAspending recipient UEI",
        ))

    # Location (state) -> geography.
    location = payload.get("location") or {}
    state = location.get("state_code")
    if state:
        facts.append(SourceFact(
            fact_type="geography", value=str(state).strip(), source_id=source_id, source_ref=ref,
            available_at=available_at, evidence_strength=4, confidence=0.85,
            provenance="USAspending recipient location state",
        ))
    return facts
