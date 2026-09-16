"""B4.1 — deterministic per-opportunity decision recomputation.

Bundle 3 correctly displayed UNKNOWN for the Bundle-2 verdicts (buyer intelligence, incumbent/competitive
assessment, vehicle/access, customer fit, pursuit) because those verdicts were never persisted or
recomputed per opportunity. This module closes that gap WITHOUT introducing a second decision engine: it
DERIVES the verdicts on demand from the already-persisted, accepted evidence carried on an opportunity
record by driving the accepted Bundle-2 builders — :func:`build_buyer_intelligence`,
:func:`build_competitive_intelligence`, :func:`assess_vehicle_access`, :func:`build_fit_reasoning` and
:func:`decide_pursuit`.

Doctrine:
    * No fabricated values. A component is derived ONLY where the persisted opportunity carries the
      accepted evidence the corresponding Bundle-2 builder needs; otherwise it stays ``None`` (UNKNOWN).
    * Deterministic. The result is a pure function of the persisted opportunity record + the customer
      profile + ``as_of`` — no wall-clock, no randomness — so historical replay reconstructs the same
      verdict.
    * Provenance / AS-OF integrity retained. Evidence ids are threaded into every derived component; the
      ``as_of`` cutoff is passed through to every builder that honours it.
    * Access is asserted conservatively: DIRECT_ACCESS is derived only where the customer is the evidenced
      incumbent currently performing the contract being recompeted (they demonstrably hold the work). We
      never assert an access path we cannot evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .buyer_intelligence import build_buyer_intelligence
from .competitive_intelligence import build_competitive_intelligence
from .fit import FitResult
from .fit_reasoning import build_fit_reasoning
from .pursuit import decide_pursuit
from .vehicle_access import assess_vehicle_access

OPPORTUNITY_RECOMPUTE_VERSION = "opportunity_recompute_v1"


@dataclass
class RecomputedComponents:
    """The Bundle-2 decision components derived for one opportunity. Any field is ``None`` (UNKNOWN)
    where the persisted opportunity carries insufficient accepted evidence to support it."""

    buyer_intelligence: Any = None
    competitive_intelligence: Any = None
    vehicle_access: Any = None
    fit_reasoning: Any = None
    pursuit_verdict: Any = None
    customer_is_incumbent: bool = False
    version: str = OPPORTUNITY_RECOMPUTE_VERSION


def _norm(value: Any) -> Optional[str]:
    return str(value).strip().casefold() if value else None


def _primary_evidence_id(o: dict) -> Optional[str]:
    for e in (o.get("evidence") or []):
        if e.get("id"):
            return e.get("id")
    return None


def _customer_is_incumbent(o: dict, customer_profile: Any) -> bool:
    """True only when persisted evidence identifies the customer as the incumbent on this opportunity.

    The authoritative signal is the structured subject reference on the opportunity matching one of the
    customer's own entity references (e.g. ``co_torch`` == ``co_torch``). A normalised incumbent-name /
    customer-name containment is accepted as a secondary signal.
    """
    if customer_profile is None:
        return False
    meta = o.get("meta") or {}
    subject_ref = _norm(meta.get("subject_ref"))
    entity_refs = {_norm(r) for r in (getattr(customer_profile, "entity_refs", []) or [])}
    if subject_ref and subject_ref in entity_refs:
        return True
    inc = _norm(o.get("incumbent"))
    name = _norm(getattr(customer_profile, "name", None))
    if inc and name and (inc == name or inc.startswith(name) or name.startswith(inc)):
        return True
    return False


def recompute_decision_components(o: dict, *, customer_profile: Any = None,
                                  as_of: Optional[str] = None) -> RecomputedComponents:
    """Derive the Bundle-2 decision components for one persisted opportunity ``o`` (a dict as stored in
    the ``opportunities`` collection). Returns :class:`RecomputedComponents`; each field is ``None`` where
    the evidence is genuinely insufficient. Pure/deterministic given (``o``, ``customer_profile``, ``as_of``)."""
    meta = o.get("meta") or {}
    # National records carry their OWN acquisition access/Industrial-Position truth (kept national on the
    # meta["national"] block and surfaced by the decision view). The Bundle-2 recompute here is US-semantic
    # (US "incumbent", US vehicle/access, US-calibrated pursuit); running it on a national record would
    # import US access assumptions into another nation. So national records stay UNKNOWN for these US
    # components — their national access truth is authoritative, not a US-derived verdict.
    if meta.get("national"):
        return RecomputedComponents(customer_is_incumbent=False)
    agency = o.get("agency")
    sub_agency = meta.get("sub_agency")
    ev_id = _primary_evidence_id(o)
    award_id = meta.get("award_id") or meta.get("program_key") or o.get("program_key")
    contract_type = meta.get("contract_type")
    incumbent_name = o.get("incumbent")
    source_as_of = meta.get("source_as_of")
    value_usd = o.get("value_usd")
    catalyst = o.get("catalyst") or {}
    expiry = o.get("expected_action_at") or (catalyst.get("meta") or {}).get("end_date")
    effective_as_of = as_of or source_as_of
    is_incumbent = _customer_is_incumbent(o, customer_profile)

    comp = RecomputedComponents(customer_is_incumbent=is_incumbent)

    # --- Buyer intelligence (B2.3): a named buyer agency is sufficient accepted evidence. ---------
    if agency:
        related = [{"source_id": e.get("source_id"), "source_ref": e.get("source_ref"),
                    "value_usd": value_usd, "available_at": e.get("first_seen_at") or source_as_of}
                   for e in (o.get("evidence") or [])]
        comp.buyer_intelligence = build_buyer_intelligence(
            agency=agency, sub_agency=sub_agency, opportunity_ref=o.get("id"),
            related_records=related, as_of=effective_as_of)

    # --- Incumbent / competitive (B2.4): a named incumbent with a cited award record. -------------
    if incumbent_name:
        comp.competitive_intelligence = build_competitive_intelligence(
            incumbent={"name": incumbent_name, "evidence_ref": ev_id},
            current_contract={"award_id": award_id, "agency": agency, "value_usd": value_usd,
                              "period_end": expiry, "available_at": source_as_of},
            as_of=effective_as_of)

    # --- Vehicle / access (B2.5): DIRECT_ACCESS only where the customer holds the work. -----------
    if is_incumbent and (award_id or contract_type):
        operative = award_id or contract_type
        comp.vehicle_access = assess_vehicle_access(
            opportunity_ref=o.get("id"), current_vehicle=operative,
            customer_vehicles=[operative], expiration=expiry, as_of=effective_as_of)

    # --- Customer fit (B2.6): only with an evidence-linked fit signal. ----------------------------
    fit_dims: list[dict] = []
    if is_incumbent and ev_id:
        fit_dims.append({
            "name": "INCUMBENT_PERFORMANCE", "verdict": "POSITIVE", "confidence": 0.8,
            "evidence_ids": [ev_id],
            "basis": f"customer is the evidenced incumbent performing {award_id or 'the current contract'}",
        })
    if fit_dims:
        company_id = getattr(customer_profile, "customer_id", None) or o.get("customer_id")
        fit_result = FitResult(consequence_id=o.get("id"), company_id=company_id, posture="DEFEND",
                               fit=True, fit_confidence=0.7, dimensions=fit_dims, blockers=[])
        comp.fit_reasoning = build_fit_reasoning(fit_result, access=comp.vehicle_access)

    # --- Pursuit verdict (B2.7): only with an evidence-backed fit reason. -------------------------
    if comp.fit_reasoning is not None and any(r.evidence_ids for r in comp.fit_reasoning.reasons_for):
        # A dated recompete with an expiry is actionable timing; absent a date, leave timing to defaults.
        timing = {"actionable": True} if expiry else None
        comp.pursuit_verdict = decide_pursuit(
            fit_reasoning=comp.fit_reasoning, access=comp.vehicle_access,
            competitive=comp.competitive_intelligence, timing=timing, as_of=effective_as_of)

    return comp
