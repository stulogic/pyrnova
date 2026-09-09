"""M16 — bounded, evidence-backed cross-company threat propagation.

One catalyst rarely stops at the directly-exposed company. A sanctioned supplier disrupts Company A; a
subcontractor that depends on A inherits a (weaker) threat; a substitute vendor gains an opportunity.
This module traverses ONLY explicit, evidence-backed relationship edges and degrades as it goes, so it
models a small real network effect without becoming graph spam.

Safety invariants (enforced in code):

* **Bounded depth** — ``max_depth`` hops (default 2); confidence also degrades each hop and terminates
  when it would fall below LOW, so depth is doubly bounded.
* **Confidence never increases** across a hop, and a weak/inferred relationship degrades it faster or
  terminates propagation.
* **Deterministic cycle prevention** — a ref already on the current path is never revisited.
* **Duplicate collapse** — the same (subject, mechanism, root threat) is emitted once; shared evidence
  never multiplies into duplicate threats.
* **No industry-adjacency propagation** — only relations in ``PROPAGATION_RELATIONS`` /
  ``BENEFICIARY_RELATIONS`` traverse; a "same industry" edge never propagates a threat.
* **Provenance per hop** — every propagated threat/opportunity carries its full ``propagation_path``.
* **Point-in-time** — an edge not yet knowable at ``as_of`` is not traversed.
"""

from __future__ import annotations

from typing import Optional

from .models import Threat, to_record
from .threat import CONFIDENCE_LEVELS, SEVERITY_LEVELS, threat_id

# Relations that carry a threat downstream: ``from_ref`` (already exposed) -> ``to_ref`` (newly exposed
# because it depends on / is bound to from_ref).
PROPAGATION_RELATIONS = {
    "SUBCONTRACTOR_OF", "SUPPLIES_TO", "DEPENDS_ON", "TEAMMATE_OF", "SUBSIDIARY_OF", "CUSTOMER_OF",
}
# Relations that turn a threatened entity into someone else's OPPORTUNITY (the beneficiary/substitute).
BENEFICIARY_RELATIONS = {"SUBSTITUTE_FOR", "COMPETES_WITH"}

# How many ordinal steps an edge degrades confidence/severity. A deterministic/confirmed relationship
# costs one step; an inferred one costs two; anything weaker terminates (returned as None below).
_EDGE_STEPS = {"CONFIRMED": 1, "deterministic_identifier": 1, "deterministic_native_id": 1,
               "INFERRED": 2, "inferred_strong_attribute": 2}


def _degrade(level: str, scale: tuple, steps: int) -> Optional[str]:
    """Step ``level`` down ``steps`` on an ordinal ``scale``; None if it would fall below the lowest real
    level (``scale[1]`` — index 0 is UNKNOWN). Never steps up."""
    if level not in scale:
        return None
    idx = scale.index(level) - steps
    return scale[idx] if idx >= 1 else None


def _edge_steps(edge: dict) -> Optional[int]:
    steps = _EDGE_STEPS.get(edge.get("link_class")) or _EDGE_STEPS.get(edge.get("join_method"))
    return steps  # None => a weak/unknown edge; propagation terminates


def _visible_edges(relationships, as_of):
    out = []
    for e in relationships or ():
        av = e.get("available_at")
        if as_of is not None and (not av or av > as_of):
            continue
        out.append(e)
    return out


def propagate_threats(
    seed_threats: list[Threat],
    relationships: list[dict],
    *,
    max_depth: int = 2,
    as_of: Optional[str] = None,
) -> dict:
    """Propagate seed (direct) threats across explicit relationship edges.

    Returns ``{"propagated_threats", "beneficiary_opportunities", "stats"}``. Propagated threats keep the
    root mechanism, are flagged ``meta.propagated=True``, degrade severity + confidence each hop, and
    carry a full ``propagation_path``. Beneficiary opportunities are emitted where a threatened entity has
    a SUBSTITUTE_FOR/COMPETES_WITH relation (no threat created for them).
    """
    edges = _visible_edges(relationships, as_of)
    out_by_from: dict[str, list[dict]] = {}
    for e in edges:
        out_by_from.setdefault(e.get("from_ref"), []).append(e)

    propagated: list[Threat] = []
    opportunities: list[dict] = []
    seen_threats: set[tuple] = set()   # (to_ref, mechanism, root_id) — duplicate collapse
    seen_opps: set[tuple] = set()
    cycles_prevented = 0
    terminated_weak = 0
    duplicates_suppressed = 0

    for seed in seed_threats:
        root_id = seed.id
        # BFS frontier entries: (current_ref, confidence, severity, depth, path)
        frontier = [(seed.subject_ref, seed.confidence, seed.severity, 0, [seed.subject_ref])]
        while frontier:
            ref, conf, sev, depth, path = frontier.pop(0)
            if depth >= max_depth:
                continue
            for edge in out_by_from.get(ref, []):
                to_ref = edge.get("to_ref")
                relation = edge.get("relation")
                if not to_ref or relation not in (PROPAGATION_RELATIONS | BENEFICIARY_RELATIONS):
                    continue
                if to_ref in path:              # deterministic cycle prevention
                    cycles_prevented += 1
                    continue
                steps = _edge_steps(edge)
                if steps is None:               # weak/unknown edge — terminate this branch
                    terminated_weak += 1
                    continue
                new_conf = _degrade(conf, CONFIDENCE_LEVELS, steps)
                if new_conf is None:            # confidence exhausted — terminate (depth bound)
                    terminated_weak += 1
                    continue
                new_path = path + [to_ref]
                hop = {"from_ref": ref, "to_ref": to_ref, "relation": relation,
                       "evidence_ids": edge.get("evidence_ids", []), "link_class": edge.get("link_class"),
                       "depth": depth + 1}

                if relation in BENEFICIARY_RELATIONS:
                    key = (to_ref, "BENEFICIARY", root_id)
                    if key not in seen_opps:
                        seen_opps.add(key)
                        opportunities.append({
                            "id": "opp_" + threat_id(to_ref, "BENEFICIARY", f"{root_id}:{depth+1}")[4:],
                            "subject_ref": to_ref, "subject_name": edge.get("to_name") or to_ref,
                            "kind": "SUBSTITUTE_OR_COMPETITOR_OPPORTUNITY", "relation": relation,
                            "catalyst_id": seed.catalyst_id, "root_threat_id": root_id,
                            "confidence": new_conf, "propagation_depth": depth + 1,
                            "evidence_ids": sorted(set(seed.evidence_ids) | set(hop["evidence_ids"])),
                            "propagation_path": (seed.meta.get("propagation_path") or []) + [hop],
                            "note": ("the same catalyst that threatens the exposed entity creates a "
                                     "substitution/competitive opportunity here"),
                        })
                    continue   # a beneficiary does not itself carry the threat further

                new_sev = _degrade(sev, SEVERITY_LEVELS, 1) or "LOW"
                key = (to_ref, seed.mechanism, root_id)
                if key in seen_threats:         # duplicate collapse (shared evidence not multiplied)
                    duplicates_suppressed += 1
                    continue
                seen_threats.add(key)
                pt = Threat(
                    subject_ref=to_ref, subject_name=edge.get("to_name") or to_ref,
                    mechanism=seed.mechanism, exposure_ids=list(seed.exposure_ids),
                    catalyst_id=seed.catalyst_id,
                    affected_value_category=seed.affected_value_category,
                    economic_effect=(f"propagated {seed.mechanism} via {relation.replace('_', ' ')} from "
                                     f"{seed.subject_name}: {edge.get('to_name') or to_ref} inherits "
                                     f"indirect exposure"),
                    severity=new_sev, severity_basis=f"indirect (hop {depth + 1}) exposure to {ref}",
                    confidence=new_conf,
                    confidence_basis=f"degraded {seed.confidence}->{new_conf} across {depth + 1} hop(s)",
                    horizon=seed.horizon, status="ACTIVE",
                    evidence_ids=sorted(set(seed.evidence_ids) | set(hop["evidence_ids"])),
                    meta={"propagated": True, "root_threat_id": root_id,
                          "propagation_depth": depth + 1,
                          "catalyst_class": seed.meta.get("catalyst_class", "MODELED"),
                          # M19: the deterministic-vs-inferred exposure authority is retained on every hop
                          # so a propagated threat from a deterministic observed exposure stays auditable.
                          "exposure_join_class": seed.meta.get("exposure_join_class", "candidate"),
                          "adverse_event_family": seed.meta.get("adverse_event_family"),
                          "propagation_path": (seed.meta.get("propagation_path") or []) + [hop]},
                )
                pt.id = threat_id(to_ref, seed.mechanism, f"{root_id}:{depth + 1}")
                propagated.append(pt)
                frontier.append((to_ref, new_conf, new_sev, depth + 1, new_path))

    max_reached = max([t.meta["propagation_depth"] for t in propagated]
                      + [o["propagation_depth"] for o in opportunities] + [0])
    return {
        "propagated_threats": propagated,
        "beneficiary_opportunities": opportunities,
        "stats": {
            "seed_threats": len(seed_threats),
            "propagated_threats": len(propagated),
            "beneficiary_opportunities": len(opportunities),
            "max_depth_reached": max_reached,
            "max_depth_allowed": max_depth,
            "cycles_prevented": cycles_prevented,
            "weak_or_exhausted_terminations": terminated_weak,
            "duplicate_threats_suppressed": duplicates_suppressed,
        },
    }


def persist_propagation(store, result: dict) -> None:
    for pt in result["propagated_threats"]:
        store.append("propagated_threats", to_record(pt))
    for opp in result["beneficiary_opportunities"]:
        store.append("beneficiary_opportunities", opp)
