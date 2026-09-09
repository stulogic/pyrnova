"""M14 — cross-source intelligence chains.

Connect evidence from multiple source families into one coherent intelligence interpretation, reusing
the frozen M5/M6 chain engine (`chains.resolve_chain`) and the M10 multi-source company grounding
(`multisource.build_multisource_profile`). This module adds **no new join semantics**: it only
normalizes records from additional families into the existing `ProgramSignal` record shape and reports
the resulting relationships, so every acceptance property the chain engine already guarantees
(deterministic-first joins, anchored/auditable inference, weak-join rejection, point-in-time truth,
temporal chain confidence) holds unchanged.

Two demonstrated chains (see `docs/replay/M14_MULTISOURCE_EXPANSION.md`):

- **R&D precursor -> procurement.** SBIR/STTR awards (PROGRAM stage) and a later USAspending prime
  award (AWARD stage) for the same firm, anchored on the firm's authoritative recipient **UEI**. An
  SBIR award for a different firm/UEI is a rejected weak join, never linked on agency/topic alone.
- **Corporate + procurement entity linkage.** SEC EDGAR + USAspending evidence for one real public
  contractor, deterministically merged by `multisource` (recipient/UEI/CIK), reported as the count of
  contributing source families.

Pure with respect to scoring: this module never creates a candidate, never promotes a disposition, and
never changes `scoring_v1`/`fit.py`.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .chains import resolve_chain, signals_from_records


def usaspending_award_records(
    raw: bytes,
    *,
    uei: str,
    company_name: Optional[str] = None,
    max_records: int = 1,
    program_prefix: str = "usaspending",
) -> list[dict]:
    """Normalize USAspending ``spending_by_award`` result bytes into AWARD-stage chain records.

    ``uei`` is the firm's authoritative recipient UEI (from the USAspending *recipient* endpoint, the
    authoritative identity source) — award result rows do not themselves carry a UEI, so it is passed in
    rather than inferred. Award *amount* is deliberately omitted: a per-firm award total is not a single
    award's value and must not be compared against an SBIR award amount in the inference engine.
    Records are filtered to ``company_name`` when given and capped at ``max_records`` (the earliest
    knowable award is sufficient to anchor the entity chain).
    """
    payload = json.loads(raw) if raw else {}
    results = (payload or {}).get("results") or []
    records: list[dict] = []
    for row in results:
        recipient = row.get("Recipient Name") or row.get("recipient_name")
        if company_name and recipient and company_name.strip().lower() not in recipient.strip().lower():
            continue
        award_id = row.get("Award ID") or row.get("generated_internal_id") or row.get("internal_id")
        if not award_id:
            continue
        available_at = _iso_date(row.get("Start Date") or row.get("Action Date"))
        records.append({
            "source_id": "usaspending",
            "source_ref": str(award_id),
            "stage": "AWARD",
            "program_key": f"{program_prefix}:{award_id}",
            "summary": row.get("Description") or "USAspending prime award",
            "available_at": available_at,
            "agency": row.get("Awarding Agency") or row.get("awarding_agency"),
            "recipient": recipient,
            "recipient_uei": str(uei).strip().upper() if uei else None,
            "amount_usd": None,  # aggregate/row total is not a comparable single-award value
            "record_kind": "prime_award",
            "confidence": "KNOWN",
            "program_identifier": None,
        })
        if len(records) >= max_records:
            break
    return records


def build_cross_source_chain(
    *records_by_family: list[dict],
    as_of: Optional[str] = None,
) -> dict:
    """Resolve a cross-source chain from records supplied by two or more families and summarize it.

    Records must already be in the chain-record shape emitted by the source normalizers
    (``sources.sbir.parse_sbir_awards``, :func:`usaspending_award_records`, etc.). Returns a structured,
    auditable summary: accepted relationships (join method, predicate, confidence, temporal ordering,
    provenance), deferred joins, rejected weak joins with reasons, entity relationships, the distinct
    source families involved, and the observed precursor->successor lead time.
    """
    all_records: list[dict] = [r for group in records_by_family for r in group]
    signals = signals_from_records(all_records, as_of=as_of)
    resolution = resolve_chain(signals)

    by_id = {s.id: s for s in resolution.signals}
    accepted = []
    for rel in resolution.relationships:
        subj, obj = by_id.get(rel.subject_id), by_id.get(rel.object_id)
        accepted.append({
            "join_method": rel.join_method,
            "predicate": rel.predicate,
            "confidence": rel.confidence,
            "subject": rel.meta.get("subject_source"),
            "object": rel.meta.get("object_source"),
            "subject_family": subj.source_id if subj else None,
            "object_family": obj.source_id if obj else None,
            "subject_stage": rel.meta.get("subject_stage"),
            "object_stage": rel.meta.get("object_stage"),
            "first_observed_at": rel.first_observed_at,
            "rationale": rel.rationale,
        })

    cross_family_accepted = [
        a for a in accepted if a["subject_family"] and a["object_family"]
        and a["subject_family"] != a["object_family"]
    ]

    return {
        "families": sorted({r["source_id"] for r in all_records}),
        "signals": len(resolution.signals),
        "accepted_joins": accepted,
        "cross_family_accepted_joins": cross_family_accepted,
        "deferred_joins": [d.to_queue_record() for d in resolution.deferred],
        "rejected_weak_joins": [
            {"reason": rj.reason, "detail": rj.detail} for rj in resolution.rejected
        ],
        "entity_relationships": [
            {"subject": r.subject_id, "predicate": r.predicate, "object": r.object_id,
             "join_method": r.join_method, "confidence": r.confidence}
            for r in resolution.entity_relationships
        ],
        "chain_confidence": resolution.confidence,
        "lead_time_days": _lead_time_days(cross_family_accepted, by_id),
        "metrics": resolution.metrics(),
    }


def corporate_procurement_linkage(
    company_name: str,
    *,
    cutoff: Optional[str],
    sources: list[dict],
    evidence_dir: Optional[Any] = None,
) -> dict:
    """Deterministic corporate + procurement entity linkage for one real firm via `multisource`.

    ``sources`` follows ``multisource.build_multisource_profile`` (a list of ``{"kind", "fixture"}``,
    with ``available_at`` on a ``usaspending_recipient`` entry). Returns the contributing source
    families, their count, the merged authoritative identity (UEI/sector), any recorded fact conflicts,
    and the point-in-time cutoff — the SEC-filing + USAspending + company-profile chain from the M14
    spec, joined deterministically (never on fuzzy name similarity alone).
    """
    from .multisource import build_multisource_profile

    profile = build_multisource_profile(company_name, sources, cutoff, evidence_dir=evidence_dir)
    meta = profile.meta
    return {
        "company": company_name,
        "cutoff": cutoff,
        "source_families": meta.get("source_families", []),
        "source_family_count": meta.get("source_family_count", 0),
        "uei": meta.get("uei"),
        "sector": meta.get("sector"),
        "fact_conflicts": meta.get("fact_conflicts", []),
        "join_method": "deterministic_entity_merge",  # recipient/UEI/CIK — multisource authority order
        "source_fact_count": len(meta.get("source_facts", [])),
    }


def persist_chain(store: Any, chain: dict, *, chain_id: str, title: str) -> dict:
    """Append a compact, durable record of a demonstrated cross-source chain for the Operations Panel.

    Stores only the summary the panel needs (families, join counts, confidence, lead time) — not raw
    evidence. Uses the engine's append-only JSONL contract (`state.StateStore`)."""
    record = {
        "id": chain_id,
        "title": title,
        "families": chain.get("families", []),
        "cross_family_accepted": len(chain.get("cross_family_accepted_joins", [])),
        "rejected_weak_joins": len(chain.get("rejected_weak_joins", [])),
        "deferred_joins": len(chain.get("deferred_joins", [])),
        "chain_confidence": (chain.get("chain_confidence") or {}).get("value"),
        "lead_time_days": chain.get("lead_time_days"),
    }
    store.append("cross_source_chains", record)
    return record


def _iso_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else (text or None)


def _lead_time_days(cross_family_joins: list[dict], by_id: dict) -> Optional[int]:
    """Max observed precursor->successor lead time (days) across cross-family accepted joins."""
    from datetime import date

    best: Optional[int] = None
    for a in cross_family_joins:
        subj = next((s for s in by_id.values() if f"{s.source_id}:{s.source_ref}" == a["subject"]), None)
        obj = next((s for s in by_id.values() if f"{s.source_id}:{s.source_ref}" == a["object"]), None)
        if not (subj and obj and subj.available_at and obj.available_at):
            continue
        try:
            d0 = date.fromisoformat(subj.available_at[:10])
            d1 = date.fromisoformat(obj.available_at[:10])
        except ValueError:
            continue
        delta = (d1 - d0).days
        if best is None or delta > best:
            best = delta
    return best


__all__ = [
    "usaspending_award_records",
    "build_cross_source_chain",
    "corporate_procurement_linkage",
    "persist_chain",
]
