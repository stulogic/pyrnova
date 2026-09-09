"""Archived SEC EDGAR ``submissions`` bytes -> company SourceFacts (M10).

For public companies only. Turns an archived SEC ``data.sec.gov/submissions/CIK*.json``
response into temporally-provenanced SourceFacts: operating geography (business address),
name aliases (current + former names), and sector (SIC description, observability only).

Point-in-time honesty: every fact's ``available_at`` is a real SEC filing date on or before
which the fact was disclosed. Entity-level facts (HQ geography, sector) are anchored to the
earliest 10-K filing date present; a former name is anchored to the start of the period it was used.

Revenue/scale from ``companyfacts`` is intentionally NOT ingested (observability only, and
USAspending already supplies contract scale) — documented as insufficient rather than archived.

Self-contained: imports only from ``pyrnova.multisource``. No imports from fit/replay/scoring.
"""

from __future__ import annotations

import json

from .multisource import SourceFact

SEC_SOURCE_ID = "sec_edgar"


def _anchor_filing_date(payload: dict) -> str | None:
    """Earliest 10-K filing date in the recent-filings block, else earliest filing date, else None."""
    recent = ((payload.get("filings") or {}).get("recent") or {})
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    tenk = sorted(d for f, d in zip(forms, dates) if f == "10-K" and d)
    if tenk:
        return tenk[0]
    all_dates = sorted(d for d in dates if d)
    return all_dates[0] if all_dates else None


def parse_sec_submissions(raw: bytes, *, company_name: str, source_id: str = SEC_SOURCE_ID) -> list[SourceFact]:
    """Parse archived SEC submissions bytes into SourceFacts. Never raises; returns [] on bad input."""
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []

    cik = payload.get("cik")
    ref = f"sec:CIK{cik}" if cik else "sec:submissions"
    anchor = _anchor_filing_date(payload)
    facts: list[SourceFact] = []

    # Geography + facility from the registered business address (SEC-disclosed, strength 4).
    business = ((payload.get("addresses") or {}).get("business") or {})
    state = business.get("stateOrCountry")
    city = business.get("city")
    if state:
        facts.append(SourceFact(
            fact_type="geography", value=str(state).strip(), source_id=source_id,
            source_ref=ref, available_at=anchor, evidence_strength=4, confidence=0.9,
            provenance="SEC submissions business address state",
        ))
        location = ", ".join(p for p in [str(city).strip() if city else None, str(state).strip()] if p)
        if location:
            facts.append(SourceFact(
                fact_type="facility", value={"location": location, "kind": "headquarters"},
                source_id=source_id, source_ref=ref, available_at=anchor,
                evidence_strength=4, confidence=0.9, provenance="SEC submissions HQ address",
            ))

    # Aliases: current name (anchor date) + former names (each with its own from-date).
    name = payload.get("name")
    if name:
        facts.append(SourceFact(
            fact_type="alias", value=str(name).strip(), source_id=source_id, source_ref=ref,
            available_at=anchor, evidence_strength=4, confidence=0.95, provenance="SEC current name",
        ))
    for former in payload.get("formerNames") or []:
        fn = (former or {}).get("name")
        if fn:
            facts.append(SourceFact(
                fact_type="alias", value=str(fn).strip(), source_id=source_id, source_ref=ref,
                available_at=(former.get("from") or "")[:10] or anchor, evidence_strength=4,
                confidence=0.9, provenance="SEC former name",
            ))

    # Sector (SIC) — observability only; strength 3.
    sic_desc = payload.get("sicDescription")
    if sic_desc:
        facts.append(SourceFact(
            fact_type="sector", value=str(sic_desc).strip(), source_id=source_id, source_ref=ref,
            available_at=anchor, evidence_strength=3, confidence=0.7, provenance="SEC SIC description",
        ))
    return facts
