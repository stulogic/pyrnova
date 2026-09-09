"""M17 — real economic relationship graph grounding.

M16 proved the propagation *semantics* (bounded, degrading, cycle-safe) on illustrative edges. M17's
primary target is to feed those semantics REAL, evidence-backed relationship edges derived from archived
authoritative bytes — never from shared industry or fuzzy-name similarity.

This module turns the output of :func:`pyrnova.grounding_subawards.parse_subawards` (where the target
company is the SUBRECIPIENT) into canonical propagation edges in the exact shape
:func:`pyrnova.propagation.propagate_threats` consumes: a ``SUBCONTRACTOR_OF`` edge
``from_ref`` (the exposed prime) -> ``to_ref`` (the dependent subcontractor).

Real evidence strength is mapped HONESTLY to propagation behavior (see ``pyrnova.propagation``):

* **Program-anchored** — a sub-award whose ``prime_award_id`` matches a prime award the prime is known
  to be exposed on (deterministic native-id linkage): ``link_class="CONFIRMED"`` /
  ``join_method="deterministic_native_id"`` (one degradation step — the strongest real edge).
* **Authoritative repeat partner** — the company subcontracts under the prime ``>= repeat_min`` times or
  across ``>= 2`` distinct years, but no sub-award ties to a *known-exposed* prime award:
  ``link_class="INFERRED"`` / ``join_method="inferred_strong_attribute"`` (degrades faster).
* **Single occurrence** — one sub-award under the prime: ``join_method="name_only_weak"``, which
  ``propagation`` treats as a weak edge that TERMINATES propagation (weak-hop termination). The edge is
  still retained (real, auditable) so the relationship is visible even though a threat does not cross it.

Every edge retains subject/object/relation, source, evidence ids, ``available_at`` (first knowable),
``join_method``, ``link_class``, a numeric ``confidence``, and full provenance. Deterministic identity.
Self-contained: no imports from scoring/fit/replay.
"""

from __future__ import annotations

from typing import Optional

# The one relation this grounding emits. Kept in sync with pyrnova.propagation.PROPAGATION_RELATIONS.
SUBCONTRACT_RELATION = "SUBCONTRACTOR_OF"

# link_class / join_method by real evidence strength -> matches pyrnova.propagation._EDGE_STEPS.
_STRENGTH = {
    "program_anchored": ("CONFIRMED", "deterministic_native_id", 0.9),
    "authoritative": ("INFERRED", "inferred_strong_attribute", 0.6),
    "weak": ("REJECTED", "name_only_weak", 0.3),
}


def _canon_ref(name: str) -> str:
    """A deterministic, human-readable ref for a company lacking a supplied ref."""
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return "co_" + (slug[:40] or "unknown")


def ground_subaward_edges(
    parsed: dict,
    *,
    sub_ref: str,
    sub_name: Optional[str] = None,
    prime_refs: Optional[dict] = None,
    exposed_prime_award_ids: Optional[set] = None,
    repeat_min: int = 2,
    min_anchor_id_len: int = 6,
) -> list[dict]:
    """Ground real ``SUBCONTRACTOR_OF`` edges from ``parse_subawards`` output.

    ``parsed`` is the dict returned by :func:`pyrnova.grounding_subawards.parse_subawards`; the target
    company (``sub_ref``/``sub_name``) is the subrecipient on every sub-award. Each partner (prime) yields
    at most one edge ``prime -> sub`` whose strength reflects the real evidence:

    * program-anchored when any of the partner's sub-awards has a ``prime_award_id`` in
      ``exposed_prime_award_ids`` (the awards the prime is separately known to be exposed on),
    * else authoritative when repeat/multi-year (``partners[].authoritative``),
    * else weak (single occurrence).

    ``prime_refs`` maps a prime name -> a caller-chosen ``from_ref`` (so an edge lines up with the direct
    threat's ``subject_ref``); absent an entry a deterministic ref is derived from the prime name. Returns
    edges sorted by descending total sub-award value. Never raises on empty/partial input.
    """
    prime_refs = prime_refs or {}
    exposed_prime_award_ids = {str(a) for a in (exposed_prime_award_ids or set())}
    sub_name = sub_name or parsed.get("company_name") or sub_ref
    source_id = parsed.get("source_id", "usaspending_subawards")

    subs_by_prime: dict[str, list[dict]] = {}
    for s in parsed.get("subawards", []):
        if s.get("prime"):
            subs_by_prime.setdefault(s["prime"], []).append(s)

    edges: list[dict] = []
    for partner in parsed.get("partners", []):
        prime = partner.get("name")
        if not prime:
            continue
        rows = subs_by_prime.get(prime, [])
        # A deterministic anchor requires a globally-unique PIID. Short local order numbers (e.g. "0002")
        # collide across primes, so they are never allowed to manufacture a deterministic edge.
        anchor_ids = sorted({str(r.get("prime_award_id")) for r in rows
                             if r.get("prime_award_id")
                             and len(str(r.get("prime_award_id"))) >= min_anchor_id_len
                             and str(r.get("prime_award_id")) in exposed_prime_award_ids})
        if anchor_ids:
            strength = "program_anchored"
        elif partner.get("authoritative"):
            strength = "authoritative"
        else:
            strength = "weak"
        link_class, join_method, confidence = _STRENGTH[strength]

        evidence_ids = sorted({str(r.get("sub_award_id")) for r in rows if r.get("sub_award_id")})
        from_ref = prime_refs.get(prime) or _canon_ref(prime)
        edges.append({
            "from_ref": from_ref,
            "from_name": prime,
            "to_ref": sub_ref,
            "to_name": sub_name,
            "relation": SUBCONTRACT_RELATION,
            "link_class": link_class,
            "join_method": join_method,
            "confidence": confidence,
            "evidence_ids": evidence_ids,
            "available_at": partner.get("first_observed_at"),
            "source_id": source_id,
            "provenance": {
                "strength": strength,
                "sub_award_count": partner.get("sub_award_count"),
                "total_subaward_usd": partner.get("total_subaward_usd"),
                "years": partner.get("years"),
                "authoritative": bool(partner.get("authoritative")),
                "program_anchor_award_ids": anchor_ids,
            },
        })

    edges.sort(key=lambda e: -(e["provenance"].get("total_subaward_usd") or 0.0))
    return edges


def summarize_relationship_graph(edges: list[dict]) -> dict:
    """Compact, denominator-honest rollup of a grounded relationship graph."""
    by_strength: dict[str, int] = {}
    for e in edges:
        s = e.get("provenance", {}).get("strength", "unknown")
        by_strength[s] = by_strength.get(s, 0) + 1
    program_anchored = by_strength.get("program_anchored", 0)
    return {
        "edges_total": len(edges),
        "by_strength": dict(sorted(by_strength.items())),
        "relations": sorted({e["relation"] for e in edges}),
        "deterministic_edges": program_anchored,
        "inferred_edges": by_strength.get("authoritative", 0),
        "weak_terminating_edges": by_strength.get("weak", 0),
        "distinct_primes": len({e["from_ref"] for e in edges}),
        "distinct_subs": len({e["to_ref"] for e in edges}),
    }
