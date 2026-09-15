"""B2.5 — Vehicle / Access analysis.

Answers the pursuit-gating question a strong capability fit cannot answer on its own: CAN THIS CUSTOMER
ACTUALLY REACH THIS WORK? A strong technical fit with no procurement access is not a strong pursuit.

From the opportunity's acquisition posture (current/anticipated vehicle, contract type, acquisition path,
eligible holders, ceiling/expiration) and the customer's known vehicle access, it produces a decision-
useful verdict:

* ``DIRECT_ACCESS``     — the customer can pursue directly (holds the vehicle, or the path is open).
* ``TEAMING_REQUIRED``  — access runs through a vehicle the customer does not hold; a teammate/prime that
                          holds it is likely required.
* ``NO_KNOWN_ACCESS``   — a restricting vehicle/path is known and no access path is supported.
* ``UNKNOWN``           — the acquisition path is not yet knowable; access cannot be asserted.

It deliberately stops at recognizing the NEED for a teammate/vehicle — it does not build a teaming
marketplace or partner-discovery engine (that stays deferred). Every fact carries provenance, evidence,
and uncertainty; unknown access fails to UNKNOWN, never to an optimistic assumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from .customer_intelligence import PUBLIC_EVIDENCE, PYRNOVA_DERIVED

VEHICLE_ACCESS_VERSION = "vehicle_access_v1"

DIRECT_ACCESS = "DIRECT_ACCESS"
TEAMING_REQUIRED = "TEAMING_REQUIRED"
NO_KNOWN_ACCESS = "NO_KNOWN_ACCESS"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AccessFact:
    dimension: str      # current_vehicle | anticipated_vehicle | acquisition_path | contract_type |
                        # eligible_holder | customer_vehicle_access | incumbent_access |
                        # task_order_history | ceiling | expiration
    key: str
    value: Any
    provenance_class: str = PUBLIC_EVIDENCE
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    available_at: Optional[str] = None
    uncertainty: str = ""
    basis: str = ""

    def to_record(self) -> dict:
        return {
            "dimension": self.dimension, "key": self.key, "value": self.value,
            "provenance_class": self.provenance_class, "evidence_ids": list(self.evidence_ids),
            "confidence": self.confidence, "available_at": self.available_at,
            "uncertainty": self.uncertainty, "basis": self.basis,
        }


@dataclass
class AccessAssessment:
    verdict: str
    teaming_required: Optional[bool]
    required_vehicle: Optional[str]
    summary: str
    opportunity_ref: Optional[str] = None
    as_of: Optional[str] = None
    facts: list[AccessFact] = field(default_factory=list)
    version: str = VEHICLE_ACCESS_VERSION

    @property
    def is_unknown(self) -> bool:
        return self.verdict == UNKNOWN

    def by_dimension(self, dimension: str) -> list[AccessFact]:
        return [f for f in self.facts if f.dimension == dimension]

    def to_record(self) -> dict:
        return {
            "vehicle_access_version": self.version, "verdict": self.verdict,
            "teaming_required": self.teaming_required, "required_vehicle": self.required_vehicle,
            "summary": self.summary, "opportunity_ref": self.opportunity_ref, "as_of": self.as_of,
            "facts": [f.to_record() for f in self.facts],
        }


def _norm(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _path_is_open(acquisition_path: Optional[str], contract_type: Optional[str]) -> bool:
    text = f"{_norm(acquisition_path)} {_norm(contract_type)}"
    # Full-and-open / open-market with no vehicle gate means anyone eligible may bid directly.
    return ("full" in text and "open" in text) or "open market" in text or "open_market" in text


def assess_vehicle_access(
    *,
    opportunity_ref: Optional[str] = None,
    current_vehicle: Optional[str] = None,
    anticipated_vehicle: Optional[str] = None,
    acquisition_path: Optional[str] = None,
    contract_type: Optional[str] = None,
    vehicle_holders: Sequence[str] = (),
    customer_vehicles: Sequence[str] = (),
    incumbent_vehicles: Sequence[str] = (),
    task_order_history: Sequence[dict] = (),
    ceiling: Optional[Any] = None,
    expiration: Optional[str] = None,
    as_of: Optional[str] = None,
) -> AccessAssessment:
    """Assess whether the customer can reach the opportunity, and whether teaming is required."""
    facts: list[AccessFact] = []
    operative = current_vehicle or anticipated_vehicle
    op_key = _norm(operative) if operative else None
    customer_vehicle_keys = {_norm(v) for v in customer_vehicles if v}

    if current_vehicle:
        facts.append(AccessFact("current_vehicle", _norm(current_vehicle), current_vehicle, PUBLIC_EVIDENCE,
                                confidence=0.9, available_at=as_of, basis="vehicle named on the opportunity"))
    if anticipated_vehicle:
        facts.append(AccessFact("anticipated_vehicle", _norm(anticipated_vehicle), anticipated_vehicle,
                                PUBLIC_EVIDENCE, confidence=0.6, uncertainty="anticipated, not yet confirmed",
                                basis="anticipated acquisition vehicle"))
    if acquisition_path:
        facts.append(AccessFact("acquisition_path", _norm(acquisition_path), acquisition_path, PUBLIC_EVIDENCE,
                                confidence=0.8, basis="acquisition path of record"))
    if contract_type:
        facts.append(AccessFact("contract_type", _norm(contract_type), contract_type, PUBLIC_EVIDENCE,
                                confidence=0.8, basis="contract type of record"))
    for holder in vehicle_holders:
        facts.append(AccessFact("eligible_holder", _norm(holder), holder, PUBLIC_EVIDENCE, confidence=0.7,
                                basis="current/eligible holder of the operative vehicle"))
    for v in customer_vehicles:
        facts.append(AccessFact("customer_vehicle_access", _norm(v), v, PUBLIC_EVIDENCE, confidence=0.7,
                                basis="vehicle the customer is known to hold"))
    for v in incumbent_vehicles:
        facts.append(AccessFact("incumbent_access", _norm(v), v, PUBLIC_EVIDENCE, confidence=0.6,
                                basis="vehicle through which the incumbent holds the work"))
    for to in task_order_history:
        facts.append(AccessFact("task_order_history", str(to.get("ref") or to.get("vehicle") or "task_order"),
                                {k: to.get(k) for k in ("ref", "vehicle", "value_usd", "available_at") if to.get(k) is not None},
                                PUBLIC_EVIDENCE, tuple(r for r in (to.get("ref"),) if r), confidence=0.7,
                                available_at=to.get("available_at"), basis="prior task-order relationship on the vehicle"))
    if ceiling is not None:
        facts.append(AccessFact("ceiling", "ceiling_usd", ceiling, PUBLIC_EVIDENCE, confidence=0.7,
                                basis="vehicle/contract ceiling where material"))
    if expiration is not None:
        facts.append(AccessFact("expiration", "expires", expiration, PUBLIC_EVIDENCE, confidence=0.7,
                                available_at=as_of, basis="vehicle/contract expiration where material"))

    # --- Verdict --------------------------------------------------------------------------------
    holder_keys = {_norm(h) for h in vehicle_holders if h}
    if _path_is_open(acquisition_path, contract_type):
        verdict, teaming, required = DIRECT_ACCESS, False, None
        summary = "Open / full-and-open acquisition path: the customer can pursue directly without a held vehicle."
    elif op_key is None:
        verdict, teaming, required = UNKNOWN, None, None
        summary = "Acquisition vehicle/path is not yet knowable; direct access cannot be asserted (UNKNOWN)."
    elif op_key in customer_vehicle_keys:
        verdict, teaming, required = DIRECT_ACCESS, False, None
        summary = f"The customer holds {operative}; a direct-access path is supported."
    elif customer_vehicle_keys or holder_keys:
        # A restricting vehicle is known and the customer does not hold it, but access exists via a holder.
        verdict, teaming, required = TEAMING_REQUIRED, True, operative
        summary = (f"Access runs through {operative}, which the customer does not hold. "
                   f"A teammate/prime holding {operative} is likely required.")
    else:
        verdict, teaming, required = NO_KNOWN_ACCESS, True, operative
        summary = (f"Access runs through {operative}; no customer or eligible-holder access path is known "
                   f"(NO_KNOWN_ACCESS). A teammate/prime holding {operative} would be required.")

    facts.append(AccessFact("acquisition_path", "access_verdict", verdict, PYRNOVA_DERIVED, confidence=0.7,
                            uncertainty="" if verdict != UNKNOWN else "insufficient acquisition evidence",
                            basis="derived access verdict"))
    return AccessAssessment(verdict=verdict, teaming_required=teaming, required_vehicle=required,
                            summary=summary, opportunity_ref=opportunity_ref, as_of=as_of, facts=facts)
