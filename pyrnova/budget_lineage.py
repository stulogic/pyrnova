"""B2.9 — Budget → Program → Procurement lineage (representative, source-rights-bounded).

With official first-party appropriations and acquisition-forecast artifacts now permitted (see the
PRELAUNCH-CONVERGENCE-001 Bundle 2 rights ruling), Pyrnova can trace a coherent capital-to-procurement
story: appropriation / program funding → program activity → forecast / procurement precursor → Sources
Sought → (pre)solicitation → award. This module does NOT ingest the federal budget universe. It presents
a lineage VIEW over an already-resolved chain (:func:`pyrnova.chains.resolve_chain`): it only surfaces
relationships that were actually formed on shared program identity or an authoritative crosswalk — it
invents no linkage — and it records the bounded coverage gap where a stage is missing rather than
broadening indiscriminately.

Point-in-time integrity is inherited from the chain engine: because the view reads a resolution built
from AS-OF-filtered signals, an early cutoff shows only the upstream funding evidence and never leaks a
future award. Every link carries its confidence and the time it became knowable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .lineage import LINEAGE_PREDICATES
from .precursors import PRECURSOR_STAGES

BUDGET_LINEAGE_VERSION = "budget_lineage_v1"

# The capital-to-procurement spine (ordered subset of PRECURSOR_STAGES).
_FUNDING_STAGES = ("INTENT", "AUTHORIZATION", "FUNDING")
_PROGRAM_STAGES = ("PROGRAM", "MARKET_ENGAGEMENT")
_PROCUREMENT_STAGES = ("PROCUREMENT", "AWARD")
_SPINE = _FUNDING_STAGES + _PROGRAM_STAGES + _PROCUREMENT_STAGES
_STAGE_ORDER = {s: i for i, s in enumerate(PRECURSOR_STAGES)}


@dataclass
class LineageLink:
    from_stage: str
    to_stage: str
    predicate: str
    confidence: float
    join_method: Optional[str]
    knowable_at: Optional[str]
    evidence_ids: list[str] = field(default_factory=list)
    subject_source: Optional[str] = None
    object_source: Optional[str] = None

    def to_record(self) -> dict:
        return {
            "from_stage": self.from_stage, "to_stage": self.to_stage, "predicate": self.predicate,
            "confidence": self.confidence, "join_method": self.join_method, "knowable_at": self.knowable_at,
            "evidence_ids": self.evidence_ids, "subject_source": self.subject_source,
            "object_source": self.object_source,
        }


@dataclass
class BudgetLineageView:
    program_keys: list[str]
    stages_present: list[str]
    links: list[LineageLink] = field(default_factory=list)
    funding_anchor: Optional[dict] = None
    procurement_endpoint: Optional[dict] = None
    award: Optional[dict] = None
    funding_to_procurement_linked: bool = False
    is_complete: bool = False
    coverage_gaps: list[str] = field(default_factory=list)
    earliest_funding_knowable_at: Optional[str] = None
    latest_knowable_at: Optional[str] = None
    summary: str = ""
    version: str = BUDGET_LINEAGE_VERSION

    def to_record(self) -> dict:
        return {
            "budget_lineage_version": self.version, "program_keys": self.program_keys,
            "stages_present": self.stages_present, "links": [l.to_record() for l in self.links],
            "funding_anchor": self.funding_anchor, "procurement_endpoint": self.procurement_endpoint,
            "award": self.award, "funding_to_procurement_linked": self.funding_to_procurement_linked,
            "is_complete": self.is_complete, "coverage_gaps": self.coverage_gaps,
            "earliest_funding_knowable_at": self.earliest_funding_knowable_at,
            "latest_knowable_at": self.latest_knowable_at, "summary": self.summary,
        }


def _sig_ref(sig) -> dict:
    return {"stage": sig.stage, "source_id": sig.source_id, "source_ref": sig.source_ref,
            "program_key": sig.program_key, "available_at": sig.available_at, "summary": sig.summary}


def build_budget_lineage(resolution: Any, *, as_of: Optional[str] = None) -> BudgetLineageView:
    """Extract the budget→program→procurement lineage view from a resolved chain."""
    signals = list(getattr(resolution, "signals", ()) or ())
    spine_signals = [s for s in signals if s.stage in _SPINE]
    # Representative (earliest) signal per stage; signals are already stage/time ordered.
    rep: dict[str, Any] = {}
    for s in sorted(spine_signals, key=lambda x: (_STAGE_ORDER[x.stage], x.available_at or "")):
        rep.setdefault(s.stage, s)

    stages_present = [s for s in _SPINE if s in rep]
    program_keys = sorted({s.program_key for s in spine_signals})

    # Forward backbone relationships (exclude backward intra-stage lineage edges).
    rel_by_pair = {}
    for r in getattr(resolution, "relationships", ()) or ():
        if r.predicate in LINEAGE_PREDICATES or r.predicate in ("CONTRADICTS", "CORROBORATES"):
            continue
        rel_by_pair[(r.subject_id, r.object_id)] = r

    links: list[LineageLink] = []
    for earlier, later in zip(stages_present, stages_present[1:]):
        subj, obj = rep[earlier], rep[later]
        r = rel_by_pair.get((subj.id, obj.id))
        if r is None:
            # Occupied but not directly linked -> a bounded coverage gap, never an invented edge.
            continue
        links.append(LineageLink(
            from_stage=earlier, to_stage=later, predicate=r.predicate, confidence=r.confidence,
            join_method=r.join_method, knowable_at=r.first_observed_at or r.available_at,
            evidence_ids=list(r.evidence_ids or []),
            subject_source=(r.meta or {}).get("subject_source"),
            object_source=(r.meta or {}).get("object_source")))

    funding_stage = next((s for s in _FUNDING_STAGES if s in rep), None)
    procurement_present = "PROCUREMENT" in rep
    funding_anchor = _sig_ref(rep[funding_stage]) if funding_stage else None
    procurement_endpoint = _sig_ref(rep["PROCUREMENT"]) if procurement_present else None
    award = _sig_ref(rep["AWARD"]) if "AWARD" in rep else None

    # A coherent funding→procurement chain: every consecutive occupied step from the funding anchor
    # through PROCUREMENT is linked (no gap in the walked spine).
    funding_to_procurement_linked = False
    if funding_stage and procurement_present:
        walk = [s for s in stages_present
                if _STAGE_ORDER[funding_stage] <= _STAGE_ORDER[s] <= _STAGE_ORDER["PROCUREMENT"]]
        linked_pairs = {(l.from_stage, l.to_stage) for l in links}
        funding_to_procurement_linked = all((a, b) in linked_pairs for a, b in zip(walk, walk[1:])) and len(walk) >= 2

    # Coverage gaps: absent spine stages between funding anchor and the furthest procurement stage.
    coverage_gaps: list[str] = []
    if funding_stage:
        furthest = "AWARD" if award else ("PROCUREMENT" if procurement_present else None)
        if furthest:
            lo, hi = _STAGE_ORDER[funding_stage], _STAGE_ORDER[furthest]
            for stage in _SPINE:
                if lo < _STAGE_ORDER[stage] < hi and stage not in rep:
                    coverage_gaps.append(f"missing {stage} evidence between funding and procurement")
            # Unlinked-but-present adjacent stages also count as a bounded gap.
            for a, b in zip(stages_present, stages_present[1:]):
                if (a, b) not in {(l.from_stage, l.to_stage) for l in links} and _STAGE_ORDER[b] <= hi:
                    coverage_gaps.append(f"{a}->{b} present but not linked on shared identity")

    is_complete = funding_to_procurement_linked and award is not None
    knowables = [s.available_at for s in spine_signals if s.available_at]
    funding_knowables = [rep[s].available_at for s in _FUNDING_STAGES if s in rep and rep[s].available_at]

    if funding_to_procurement_linked:
        anchor_src = f"{funding_anchor['source_id']}:{funding_anchor['source_ref']}"
        summary = (f"Procurement traces to upstream funding evidence {anchor_src} "
                   f"({funding_stage}) via {len(links)} linked stage(s)"
                   + (" through award" if award else "") + ".")
    elif funding_stage and procurement_present:
        summary = "Funding and procurement are both observed but not linked on shared identity (coverage gap)."
    elif funding_stage:
        summary = "Upstream funding observed; no downstream procurement yet (bounded coverage gap)."
    else:
        summary = "No upstream funding evidence in this chain."

    return BudgetLineageView(
        program_keys=program_keys, stages_present=stages_present, links=links,
        funding_anchor=funding_anchor, procurement_endpoint=procurement_endpoint, award=award,
        funding_to_procurement_linked=funding_to_procurement_linked, is_complete=is_complete,
        coverage_gaps=coverage_gaps,
        earliest_funding_knowable_at=min(funding_knowables) if funding_knowables else None,
        latest_knowable_at=max(knowables) if knowables else None, summary=summary,
    )
