"""Material Changes read model (M22-A).

Answers the Phase 1 dominant customer question — "What materially changed since I last looked, and why
does it matter to me?" — as a read-optimized projection over Pyrnova's existing append-only intelligence
streams (``threats``, ``propagated_threats``, ``opportunities``, ``commercial_consequences``,
``outcomes``). It runs deterministic customer-relevance filtering and structured projection, never runtime
LLM reasoning, and never a parallel intelligence system.

Doctrine honored (see ``docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md``, D-041, D-046, D-055):

* OBSERVED fact and PYRNOVA ASSESSMENT are kept in separate structured blocks — never flattened.
* Point-in-time truth: a change is only visible when ``available_at <= as_of`` (no future leakage).
* Deterministic relevance only, with an inspectable basis; weak text similarity is never relevance.
* Evidence is referenced by id/provenance, never copied wholesale; independence is reported
  conservatively (distinct authoritative sources), never implying corroboration Pyrnova does not have.
* Customer isolation: a change not relevant to a customer is not returned for that customer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

# Disposition vocabulary (functional, literal — Product Language Authority D-041).
DISPOSITION_THREAT = "THREAT"
DISPOSITION_OPPORTUNITY = "OPPORTUNITY"
DISPOSITION_MONITORING = "MONITORING"

# Relevance bases, strongest first. The basis is customer-inspectable (D-046).
RELEVANCE_ORDER = [
    "DIRECT_SUBJECT",       # the customer entity is itself the affected subject
    "WATCHED_ENTITY",       # an entity the customer watches is affected (e.g. a parent/prime)
    "WATCHED_PROGRAM",      # a program/contract the customer watches is affected
    "CAPABILITY_MATCH",     # a customer capability class matches the change's requirement
    "AGENCY_INTEREST",      # an agency of interest to the customer (monitoring-grade)
]
_RELEVANCE_RANK = {name: i for i, name in enumerate(RELEVANCE_ORDER)}

_SEVERITY_ORDER = ["UNKNOWN", "LOW", "MODERATE", "HIGH", "CRITICAL"]
_CONFIDENCE_ORDER = ["UNKNOWN", "LOW", "MEDIUM", "HIGH"]


@dataclass
class CustomerContext:
    """The minimum customer intelligence needed to answer "why does this matter to this organization?".

    Compact and extensible; reuses existing canonical entity refs and program identifiers. Not a tenancy
    platform or CRM. ``entity_refs`` are the canonical refs the customer *is* (used for DIRECT_SUBJECT);
    ``watched_entity_refs`` / ``watched_programs`` are what it monitors.
    """

    customer_id: str
    name: str
    entity_refs: list[str] = field(default_factory=list)
    watched_entity_refs: list[str] = field(default_factory=list)
    watched_programs: list[str] = field(default_factory=list)
    agencies: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "CustomerContext":
        allowed = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in (data or {}).items() if k in allowed})

    def _norm(self, values: Iterable[str]) -> set[str]:
        return {str(v).strip().lower() for v in values if v is not None and str(v).strip()}


def _in(value: Optional[str], pool: set[str]) -> bool:
    return bool(value) and str(value).strip().lower() in pool


def assess_relevance(change: dict, ctx: CustomerContext) -> Optional[dict]:
    """Deterministic customer relevance. Returns an inspectable basis, or ``None`` when not relevant.

    The change dict is a normalized internal shape (see ``_normalize_*``) carrying ``subject_ref``,
    ``affected_program``, ``agency``, and ``capability_classes``. Relevance is never inferred from free
    text; it requires a matching canonical ref, program identifier, agency, or capability class.
    """
    entity_refs = ctx._norm(ctx.entity_refs)
    watched_entities = ctx._norm(ctx.watched_entity_refs)
    watched_programs = ctx._norm(ctx.watched_programs)
    agencies = ctx._norm(ctx.agencies)
    capabilities = ctx._norm(ctx.capabilities)

    subject = change.get("subject_ref")
    program = change.get("affected_program")
    reasons: list[dict] = []

    if _in(subject, entity_refs):
        reasons.append({"basis": "DIRECT_SUBJECT",
                        "detail": f"{change.get('affected_entity') or subject} is the customer entity."})
    if _in(subject, watched_entities):
        reasons.append({"basis": "WATCHED_ENTITY",
                        "detail": f"{change.get('affected_entity') or subject} is on the customer watchlist."})
    # A propagation path may touch a watched entity even when the terminal subject differs.
    for ref in change.get("path_refs", []) or []:
        if _in(ref, watched_entities) and not any(r["basis"] == "WATCHED_ENTITY" for r in reasons):
            reasons.append({"basis": "WATCHED_ENTITY",
                            "detail": f"Watched entity {ref} lies on the propagation path."})
    if _in(program, watched_programs):
        reasons.append({"basis": "WATCHED_PROGRAM",
                        "detail": f"Program/contract {program} is on the customer watchlist."})
    matched_caps = sorted(capabilities.intersection(ctx._norm(change.get("capability_classes", []))))
    if matched_caps:
        reasons.append({"basis": "CAPABILITY_MATCH",
                        "detail": f"Matches customer capability: {', '.join(matched_caps)}."})
    if _in(change.get("agency"), agencies):
        reasons.append({"basis": "AGENCY_INTEREST",
                        "detail": f"{change.get('agency')} is an agency of interest."})

    if not reasons:
        return None
    reasons.sort(key=lambda r: _RELEVANCE_RANK.get(r["basis"], 99))
    primary = reasons[0]
    return {"basis": primary["basis"], "detail": primary["detail"], "reasons": reasons}


def _disposition(change: dict, relevance: dict) -> str:
    kind = change["_kind"]
    if kind in ("threat", "propagated_threat"):
        # Agency-only relevance to a threat is monitoring-grade, not a customer-specific threat.
        if relevance["basis"] == "AGENCY_INTEREST":
            return DISPOSITION_MONITORING
        return DISPOSITION_THREAT
    if kind == "opportunity":
        state = (change.get("_state") or "").lower()
        return DISPOSITION_OPPORTUNITY if state in ("strike", "candidate", "reviewing") else DISPOSITION_MONITORING
    return DISPOSITION_MONITORING


def _rank_severity(sev: Optional[str]) -> int:
    return _SEVERITY_ORDER.index(sev) if sev in _SEVERITY_ORDER else 0


def _rank_confidence(conf: Optional[str]) -> int:
    return _CONFIDENCE_ORDER.index(conf) if conf in _CONFIDENCE_ORDER else 0


def _evidence_block(change: dict) -> dict:
    """Reference evidence by id/provenance only; report independence conservatively (distinct sources).

    Multiple evidence rows from the SAME authoritative source are NOT independent confirmations.
    """
    ev_ids = list(change.get("evidence_ids") or [])
    sources = [s for s in (change.get("evidence_sources") or []) if s]
    distinct_sources = sorted(set(sources))
    raw_authoritative = False
    try:
        from .sources.registry import get_spec, StorageMode
        # A stored archive hash is raw authority only when the canonical source
        # profile actually permits RAW_ALLOWED.  Normalized-only evidence keeps
        # its original hash but must never be labelled as raw bytes.
        profiled = [get_spec(str(s)).policy for s in sources if s]
        raw_authoritative = bool(change.get("archive_hash")) and bool(profiled) and all(
            p is not None and StorageMode(p.raw_storage) is StorageMode.RAW_ALLOWED for p in profiled
        )
    except (KeyError, TypeError, ValueError):
        raw_authoritative = False
    return {
        "evidence_count": len(ev_ids),
        "evidence_ids": ev_ids,
        "independent_source_count": len(distinct_sources),
        "sources": distinct_sources,
        "single_source": len(distinct_sources) <= 1,
        "catalyst_class": change.get("catalyst_class"),  # OBSERVED vs MODELED (origin, not corroboration)
        "raw_authoritative_bytes": raw_authoritative,
        "archive_hash": change.get("archive_hash"),
    }


def project_material_change(change: dict, relevance: dict) -> dict:
    """Build the read-optimized Material Change projection for one relevant change.

    OBSERVED fact and PYRNOVA ASSESSMENT live in separate blocks (never flattened). IDs/provenance are
    preserved so a client can inspect the underlying evidence/entity/program without the projection
    duplicating whole evidence bodies.
    """
    disposition = _disposition(change, relevance)
    observed = {
        "event_type": change.get("event_type"),
        "event_summary": change.get("event_summary"),
        "affected_entity": change.get("affected_entity"),
        "affected_entity_ref": change.get("subject_ref"),
        "affected_program": change.get("affected_program"),
        "agency": change.get("agency"),
        "event_time": change.get("event_time") or "UNKNOWN",
        "observed_at": change.get("observed_at") or "UNKNOWN",  # when Pyrnova could first know it
        "catalyst_class": change.get("catalyst_class"),         # OBSERVED (real event) vs MODELED
        # Opportunity-only distinctions (§55): the known contract value and the expected-action deadline.
        # Absent (None) on threats/monitoring, so the client renders them only where they are real.
        "value_usd": change.get("value_usd"),
        "expected_action_at": change.get("event_time") if disposition == DISPOSITION_OPPORTUNITY else None,
    }
    assessment = {
        "disposition": disposition,
        "mechanism": change.get("mechanism"),
        "consequence": change.get("consequence"),
        "materiality": change.get("severity", "UNKNOWN"),       # severity ordinal (if true)
        "confidence": change.get("confidence", "UNKNOWN"),      # evidence strength (orthogonal)
        "affected_value_category": change.get("affected_value_category"),
        "is_assessment": True,
        "assessment_engine": change.get("engine_version", "threat_v1"),
    }
    return {
        "id": change["id"],
        "kind": change["_kind"],
        "title": change.get("title") or change.get("event_summary") or change.get("mechanism") or "Material change",
        "disposition": disposition,
        "observed": observed,
        "assessment": assessment,
        "relevance": relevance,
        "evidence": _evidence_block(change),
        "uncertainty": change.get("uncertainty") or [],
        "lifecycle_state": change.get("lifecycle_state", "UNKNOWN"),
        "outcome_state": change.get("outcome_state", "UNKNOWN"),
        "propagation": change.get("propagation"),
        "refs": {
            "subject_ref": change.get("subject_ref"),
            "catalyst_id": change.get("catalyst_id"),
            "program": change.get("affected_program"),
            "evidence_ids": list(change.get("evidence_ids") or []),
            "root_change_id": change.get("root_change_id"),
        },
        "provenance": {
            "source_ref": change.get("source_ref"),
            "archive_hash": change.get("archive_hash"),
            "adverse_event_family": change.get("adverse_event_family"),
        },
        "available_at": change.get("observed_at"),  # the point-in-time gate value (for sorting/filtering)
    }


def _threat_change(rec: dict, kind: str) -> dict:
    meta = rec.get("meta") or {}
    path = meta.get("propagation_path") or []
    path_refs = []
    for hop in path:
        for key in ("from_ref", "to_ref"):
            ref = hop.get(key)
            if ref:
                path_refs.append(ref)
    uncertainty = []
    for fal in rec.get("falsifiers") or []:
        detail = fal.get("detail") if isinstance(fal, dict) else str(fal)
        if detail:
            uncertainty.append({"type": "FALSIFIER", "detail": detail})
    # Point-in-time floor: an event-caused threat is not knowable before its triggering event, even if a
    # supporting relationship was knowable earlier. observed_at is the latest of the knowability inputs.
    observed_at = max(
        (v for v in (rec.get("available_at"), rec.get("first_observed_at"), meta.get("event_time")) if v),
        default=None,
    )
    return {
        "_kind": kind,
        "id": rec.get("id"),
        "subject_ref": rec.get("subject_ref"),
        "affected_entity": rec.get("subject_name"),
        "affected_program": meta.get("affected_program") or meta.get("program_key"),
        "agency": meta.get("agency"),
        "event_type": meta.get("event_type") or meta.get("adverse_event_family"),
        "event_summary": meta.get("event_summary") or rec.get("economic_effect"),
        "title": meta.get("title") or rec.get("economic_effect") or rec.get("mechanism"),
        "mechanism": rec.get("mechanism"),
        "consequence": rec.get("economic_effect"),
        "severity": rec.get("severity", "UNKNOWN"),
        "confidence": rec.get("confidence", "UNKNOWN"),
        "affected_value_category": rec.get("affected_value_category"),
        "event_time": meta.get("event_time"),
        "observed_at": observed_at,
        "catalyst_class": meta.get("catalyst_class", "MODELED"),
        "catalyst_id": rec.get("catalyst_id"),
        "adverse_event_family": meta.get("adverse_event_family"),
        "source_ref": meta.get("source_ref"),
        "archive_hash": meta.get("archive_hash"),
        "evidence_ids": rec.get("evidence_ids") or [],
        "evidence_sources": meta.get("evidence_sources") or [],
        "lifecycle_state": rec.get("status", "UNKNOWN"),
        "outcome_state": (meta.get("outcome") or {}).get("label") or meta.get("outcome_state", "UNKNOWN"),
        "engine_version": rec.get("engine_version", "threat_v1"),
        "uncertainty": uncertainty,
        "path_refs": path_refs,
        "root_change_id": meta.get("root_threat_id"),
        "propagation": {
            "is_propagated": kind == "propagated_threat",
            "depth": meta.get("propagation_depth", 0),
            "path": path,
            "exposure_join_class": meta.get("exposure_join_class"),
        } if (kind == "propagated_threat" or meta.get("propagation_path")) else None,
    }


def _opportunity_change(rec: dict) -> dict:
    meta = rec.get("meta") or {}
    evidence = rec.get("evidence") or []
    # The affected entity is the canonical entity this opportunity concerns (e.g. the incumbent the
    # customer IS, or a watched entity) — NOT the tenant ``customer_id``. Conflating them broke
    # DIRECT_SUBJECT relevance and investigation links, since the customer's ``entity_refs`` hold the
    # canonical ``co_*`` ref, not the tenant id. Prefer an explicit canonical subject; fall back to
    # ``customer_id`` only for legacy pipeline opportunities that carry no canonical subject (§10 of the
    # engineering doctrine: no silent identity guess — we use what is asserted, else the tenant id).
    subject_ref = meta.get("subject_ref") or rec.get("subject_ref") or rec.get("customer_id")
    subject_name = meta.get("subject_name") or rec.get("subject_name") or rec.get("customer_id")
    program = meta.get("program_key") or meta.get("award_id")
    value_usd = rec.get("value_usd")
    return {
        "_kind": "opportunity",
        "_state": rec.get("state"),
        "id": rec.get("id"),
        "subject_ref": subject_ref,
        "affected_entity": subject_name,
        "affected_program": program,
        "agency": rec.get("agency"),
        "event_type": (rec.get("catalyst") or {}).get("kind"),
        "event_summary": rec.get("title"),
        "title": rec.get("title"),
        "mechanism": (rec.get("catalyst") or {}).get("kind"),
        "consequence": rec.get("recommended_action"),
        "severity": "UNKNOWN",
        "confidence": _score_to_ordinal(rec.get("confidence")),
        # Known dollar value of the incumbent contract at recompete — an OBSERVED fact, not an estimate.
        "value_usd": value_usd,
        "affected_value_category": "REVENUE" if value_usd else None,
        "capability_classes": rec.get("relevance_reasons") or [],
        "event_time": rec.get("expected_action_at"),
        "observed_at": meta.get("source_as_of") or rec.get("_ts"),
        "catalyst_class": "MODELED",
        "source_ref": meta.get("source_ref") or (evidence[0].get("source_ref") if evidence else None),
        "archive_hash": meta.get("archive_hash"),
        "evidence_ids": [ev.get("id") for ev in evidence if ev.get("id")],
        "evidence_sources": [ev.get("source_id") for ev in evidence if ev.get("source_id")],
        "lifecycle_state": rec.get("state", "candidate"),
        "outcome_state": "UNKNOWN",
        "uncertainty": [{"type": "FALSIFICATION", "detail": rec.get("falsification")}]
        if rec.get("falsification") else [],
        "path_refs": [],
    }


def _score_to_ordinal(score) -> str:
    try:
        s = float(score or 0)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if s >= 0.75:
        return "HIGH"
    if s >= 0.5:
        return "MEDIUM"
    if s > 0:
        return "LOW"
    return "UNKNOWN"


def _visible(change: dict, as_of: Optional[str]) -> bool:
    """Point-in-time gate: a change is visible only once Pyrnova could know it (no future leakage)."""
    if not as_of:
        return True
    observed = change.get("observed_at")
    return not observed or str(observed) <= str(as_of)


def build_material_changes(
    *,
    threats: Iterable[dict] = (),
    propagated_threats: Iterable[dict] = (),
    opportunities: Iterable[dict] = (),
    context: CustomerContext,
    as_of: Optional[str] = None,
    disposition: Optional[str] = None,
) -> list[dict]:
    """Assemble the customer's Material Changes feed from existing intelligence records.

    Deterministic, point-in-time, customer-isolated. ``disposition`` optionally filters to
    THREAT / OPPORTUNITY / MONITORING. Ordering is stable: relevance strength, then severity, then
    confidence, then most-recent observation, then id.
    """
    normalized: list[dict] = []
    for rec in threats:
        normalized.append(_threat_change(rec, "threat"))
    for rec in propagated_threats:
        normalized.append(_threat_change(rec, "propagated_threat"))
    for rec in opportunities:
        normalized.append(_opportunity_change(rec))

    out: list[dict] = []
    for change in normalized:
        if not _visible(change, as_of):
            continue
        relevance = assess_relevance(change, context)
        if not relevance:
            continue  # customer isolation: not relevant → not returned
        projection = project_material_change(change, relevance)
        if disposition and projection["disposition"] != disposition.strip().upper():
            continue
        out.append(projection)

    out.sort(key=lambda p: (
        _RELEVANCE_RANK.get(p["relevance"]["basis"], 99),
        -_rank_severity(p["assessment"]["materiality"]),
        -_rank_confidence(p["assessment"]["confidence"]),
        _neg_str(p.get("available_at")),
        p["id"] or "",
    ))
    return out


def _neg_str(value: Optional[str]) -> str:
    # Sort most-recent observation first: invert lexical order of the ISO timestamp.
    if not value:
        return "￿"  # unknown observation time sorts last
    return "".join(chr(0x10FFFF - ord(c)) if ord(c) < 0x10FFFF else c for c in str(value))
