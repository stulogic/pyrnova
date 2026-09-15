"""B2.10 — Integrated Decision Object.

One coherent per-(customer, opportunity) decision object that COMPOSES the Bundle-2 capabilities rather
than duplicating any persisted fact. It references the canonical underlying records/views:

    opportunity identity + lifecycle (B2.1)          buyer intelligence (B2.3)
    budget→procurement lineage (B2.9)                incumbent/competitive intelligence (B2.4)
    material-change consequences (B2.8)              vehicle/access (B2.5)
    customer intelligence profile (B2.2)             fit reasoning (B2.6)
    pursuit verdict + reversal conditions (B2.7)     decision lead time / decision memory (Bundle 1)

The reversal conditions, current stage, evidence index and uncertainty are DERIVED FROM the composed
components (e.g. reversal conditions come straight from the Pursuit Verdict), never recomputed or copied.
``to_record()`` emits the serialized contract that Bundle 3 can present without reaching back into the
domain layer. Temporal/provenance integrity is inherited from the components: this object introduces no
new inference and leaks no future knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

DECISION_OBJECT_VERSION = "integrated_decision_v1"


def _rec(obj: Any) -> Any:
    """Serialize a component via its to_record() if present, else pass a dict/None through."""
    if obj is None:
        return None
    if hasattr(obj, "to_record"):
        return obj.to_record()
    return obj


def _evidence_from_facts(facts: Sequence[Any]) -> set[str]:
    out: set[str] = set()
    for f in facts or ():
        out.update(getattr(f, "evidence_ids", ()) or ())
    return out


@dataclass
class IntegratedDecision:
    opportunity_ref: str
    program_key: Optional[str] = None
    as_of: Optional[str] = None
    # composed components (canonical objects; referenced, never duplicated)
    chain_resolution: Any = None
    budget_lineage: Any = None
    material_changes: list = field(default_factory=list)
    customer_intelligence: Any = None
    buyer_intelligence: Any = None
    competitive_intelligence: Any = None
    vehicle_access: Any = None
    fit_reasoning: Any = None
    pursuit_verdict: Any = None
    decision_lead_time: Any = None
    decision_memory: Any = None
    version: str = DECISION_OBJECT_VERSION

    # --- derived-from-components views (no recomputation) ---------------------------------------
    @property
    def disposition(self) -> Optional[str]:
        return getattr(self.pursuit_verdict, "disposition", None)

    @property
    def reversal_conditions(self) -> list:
        return list(getattr(self.pursuit_verdict, "reversal_conditions", []) or [])

    @property
    def current_stage(self) -> Optional[str]:
        cr = self.chain_resolution
        if cr is not None:
            stages = list(getattr(cr, "stages_present", ()) or ())
            if stages:
                return stages[-1]
        return None

    @property
    def lifecycle(self) -> dict:
        cr = self.chain_resolution
        lineage = getattr(cr, "lineage", None) if cr is not None else None
        if lineage is None:
            return {}
        program = self.program_key
        current = lineage.current_instance(program) if program else None
        return {
            "instances": [
                {"procurement_id": i.procurement_id, "disposition": i.disposition, "live": i.live,
                 "opened_at": i.opened_at, "reissue_of": i.reissue_of, "reissued_by": i.reissued_by}
                for i in getattr(lineage, "instances", ())
            ],
            "current_instance": (
                {"procurement_id": current.procurement_id, "disposition": current.disposition,
                 "live": current.live} if current else None),
        }

    @property
    def referenced_evidence_ids(self) -> list[str]:
        """An INDEX of evidence ids referenced across components (references, not copied facts)."""
        ev: set[str] = set()
        ev.update(getattr(self.pursuit_verdict, "decisive_evidence", ()) or ())
        fr = self.fit_reasoning
        if fr is not None:
            for bucket in (fr.reasons_for, fr.reasons_against, fr.unknowns):
                for r in bucket:
                    ev.update(getattr(r, "evidence_ids", ()) or ())
        for comp in (self.buyer_intelligence, self.competitive_intelligence, self.vehicle_access,
                     self.customer_intelligence):
            ev |= _evidence_from_facts(getattr(comp, "facts", ()) if comp is not None else ())
        bl = self.budget_lineage
        if bl is not None:
            for link in getattr(bl, "links", ()) or ():
                ev.update(getattr(link, "evidence_ids", ()) or [])
        return sorted(e for e in ev if e)

    @property
    def uncertainty(self) -> dict:
        return {
            "pursuit": getattr(self.pursuit_verdict, "uncertainty", None),
            "open_unknowns": list(getattr(self.pursuit_verdict, "unknowns", []) or []),
            "buyer_unknown": bool(getattr(self.buyer_intelligence, "is_unknown", False)),
            "competitive_unknown": bool(getattr(self.competitive_intelligence, "is_unknown", False)),
            "access_verdict": getattr(self.vehicle_access, "verdict", None),
            "coverage_gaps": list(getattr(self.budget_lineage, "coverage_gaps", []) or []),
        }

    def to_record(self) -> dict:
        """The serialized Bundle-3 contract, composed from canonical component records."""
        return {
            "integrated_decision_version": self.version,
            "opportunity_ref": self.opportunity_ref,
            "program_key": self.program_key,
            "as_of": self.as_of,
            "current_stage": self.current_stage,
            "disposition": self.disposition,
            "lifecycle": self.lifecycle,
            "budget_lineage": _rec(self.budget_lineage),
            "material_changes": [_rec(m) for m in self.material_changes],
            "customer_intelligence": _rec(self.customer_intelligence),
            "buyer_intelligence": _rec(self.buyer_intelligence),
            "competitive_intelligence": _rec(self.competitive_intelligence),
            "vehicle_access": _rec(self.vehicle_access),
            "fit_reasoning": _rec(self.fit_reasoning),
            "pursuit_verdict": _rec(self.pursuit_verdict),
            "reversal_conditions": self.reversal_conditions,
            "decision_lead_time": _rec(self.decision_lead_time),
            "decision_memory": _rec(self.decision_memory),
            "referenced_evidence_ids": self.referenced_evidence_ids,
            "uncertainty": self.uncertainty,
        }


def assemble_decision(
    *,
    opportunity_ref: str,
    program_key: Optional[str] = None,
    chain_resolution: Any = None,
    budget_lineage: Any = None,
    material_changes: Sequence[Any] = (),
    customer_intelligence: Any = None,
    buyer_intelligence: Any = None,
    competitive_intelligence: Any = None,
    vehicle_access: Any = None,
    fit_reasoning: Any = None,
    pursuit_verdict: Any = None,
    decision_lead_time: Any = None,
    decision_memory: Any = None,
    as_of: Optional[str] = None,
) -> IntegratedDecision:
    """Compose one integrated decision object from the canonical Bundle-2 components."""
    if program_key is None and chain_resolution is not None:
        keys = list(getattr(chain_resolution, "program_keys", ()) or ())
        program_key = keys[0] if len(keys) == 1 else program_key
    return IntegratedDecision(
        opportunity_ref=opportunity_ref, program_key=program_key, as_of=as_of,
        chain_resolution=chain_resolution, budget_lineage=budget_lineage,
        material_changes=list(material_changes), customer_intelligence=customer_intelligence,
        buyer_intelligence=buyer_intelligence, competitive_intelligence=competitive_intelligence,
        vehicle_access=vehicle_access, fit_reasoning=fit_reasoning, pursuit_verdict=pursuit_verdict,
        decision_lead_time=decision_lead_time, decision_memory=decision_memory,
    )
