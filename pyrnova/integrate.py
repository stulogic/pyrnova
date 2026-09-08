"""Conservative evidence/entity integration for M4 program signals."""

from __future__ import annotations

import uuid

from .enrich import connect_event
from .models import Entity, Event, Evidence, Opportunity
from .precursors import ProgramSignal
from .resolve import canonicalize_name


_STAGE_STRENGTH_CAP = {
    "INTENT": 2,
    "AUTHORIZATION": 3,
    "FUNDING": 4,
    "PROGRAM": 3,
    "MARKET_ENGAGEMENT": 3,
    "PROCUREMENT": 5,
    "AWARD": 5,
    "OUTCOME": 5,
}


def sec_issuer_entity(*, cik: str, company_name: str, tickers: list[str] | None = None) -> Entity:
    """Resolve an SEC issuer by official CIK while retaining names/tickers as attributes."""
    digits = str(cik).strip()
    if not digits.isdigit() or len(digits) > 10:
        raise ValueError("CIK must contain 1 to 10 decimal digits")
    normalized = digits.zfill(10)
    entity = Entity(
        kind="commercial_entity",
        name=company_name,
        canonical_name=canonicalize_name(company_name),
        meta={"sec_cik": normalized, "tickers": sorted(set(tickers or []))},
    )
    entity.id = uuid.uuid5(uuid.NAMESPACE_URL, f"pyrnova:sec-cik:{normalized}").hex
    return entity


def attach_program_signal(
    opp: Opportunity,
    signal: ProgramSignal,
    evidence: Evidence,
    *,
    strength: int,
) -> bool:
    """Attach only an explicit program/ref match; return False for unproven relationships.

    This function enriches an existing candidate.  It cannot create one or directly change its
    disposition, which keeps scoring_v1 and the M2 path isolated.
    """
    opportunity_program = opp.meta.get("program_key")
    native_refs = {
        str(value) for value in (
            opp.meta.get("notice_id"), opp.meta.get("solicitation_number"), opp.meta.get("award_id")
        ) if value
    }
    explicit_match = bool(
        opportunity_program and opportunity_program == signal.program_key
        or native_refs.intersection(signal.downstream_refs)
    )
    if not explicit_match:
        return False
    capped_strength = min(int(strength), _STAGE_STRENGTH_CAP[signal.stage])
    if evidence not in opp.evidence:
        opp.evidence.append(evidence)
    event = Event(
        kind="program_signal",
        source_id=signal.source_id,
        source_ref=signal.source_ref,
        summary=signal.summary,
        occurred_at=signal.available_at,
        stage=signal.stage,
        program_key=signal.program_key,
        evidence_ids=[evidence.id],
        meta={
            "agency": signal.agency,
            "funding_source": signal.funding_source,
            "authority": signal.authority,
            "geography": signal.geography,
            "capabilities": list(signal.capabilities),
            "confidence": signal.confidence,
        },
    )
    event.id = uuid.uuid5(uuid.NAMESPACE_URL, f"pyrnova:program-signal:{signal.id}").hex
    connect_event(
        opp,
        event,
        evidence_id=evidence.id,
        predicate="program_chain_evidence",
        role="supporting",
        strength=capped_strength,
        basis=f"explicit program/source reference match at {signal.stage} stage",
    )
    opp.meta.setdefault("upstream_program_signals", []).append({
        "signal_id": signal.id,
        "source_id": signal.source_id,
        "source_ref": signal.source_ref,
        "stage": signal.stage,
        "program_key": signal.program_key,
    })
    return True
