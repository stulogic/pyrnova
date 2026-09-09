"""M17 — real relationship graph grounding from committed, archived sub-award evidence.

Grounds real ``SUBCONTRACTOR_OF`` edges from the archived USAspending sub-award bytes where Torch
Technologies is the subrecipient, and proves the edge strength mirrors the REAL evidence:
program-anchored deterministic (SAIC, matched on globally-unique PIIDs) vs authoritative-repeat vs weak
single-occurrence — with no fabricated or industry-adjacency edges.
"""

from __future__ import annotations

from pathlib import Path

from pyrnova.grounding_subawards import parse_subawards
from pyrnova.relationships import (
    SUBCONTRACT_RELATION,
    ground_subaward_edges,
    summarize_relationship_graph,
)

_EVIDENCE = Path("examples/real_evidence/usaspending_subawards_torch.json")
# Real, globally-unique SAIC prime PIIDs that Torch subcontracts under (from usaspending_saic.json).
_SAIC_PIIDS = {"47QFSA20F0057", "W31P4Q21F0095", "W9126020FD504"}
_SAIC_NAME = "SCIENCE APPLICATIONS INTERNATIONAL CORPORATION"


def _edges():
    parsed = parse_subawards(_EVIDENCE.read_bytes(), company_name="TORCH TECHNOLOGIES INC")
    return parsed, ground_subaward_edges(
        parsed, sub_ref="co_torch", sub_name="Torch Technologies Inc",
        prime_refs={_SAIC_NAME: "co_saic"}, exposed_prime_award_ids=_SAIC_PIIDS)


def test_edges_are_real_and_directional():
    parsed, edges = _edges()
    assert parsed["partners"], "expected real partner primes in archived evidence"
    assert edges
    for e in edges:
        assert e["relation"] == SUBCONTRACT_RELATION
        assert e["to_ref"] == "co_torch"            # Torch is always the dependent subcontractor
        assert e["from_ref"] != e["to_ref"]         # a company never depends on itself
        assert e["evidence_ids"]                    # every edge is backed by real sub-award ids
        assert e["available_at"]                     # point-in-time: when first knowable


def test_saic_edge_is_program_anchored_deterministic():
    _, edges = _edges()
    saic = next(e for e in edges if e["from_ref"] == "co_saic")
    assert saic["link_class"] == "CONFIRMED"
    assert saic["join_method"] == "deterministic_native_id"
    assert saic["provenance"]["strength"] == "program_anchored"
    # Anchored on the real, globally-unique SAIC PIIDs (never on a short local order number).
    assert set(saic["provenance"]["program_anchor_award_ids"]) == _SAIC_PIIDS
    assert saic["provenance"]["authoritative"] is True


def test_short_order_number_never_creates_a_false_anchor():
    """'0002' is a non-unique local delivery-order number shared across primes; passing it must NOT
    program-anchor any edge (a false deterministic linkage)."""
    parsed = parse_subawards(_EVIDENCE.read_bytes(), company_name="TORCH TECHNOLOGIES INC")
    edges = ground_subaward_edges(parsed, sub_ref="co_torch",
                                  exposed_prime_award_ids={"0002"})
    assert all(not e["provenance"]["program_anchor_award_ids"] for e in edges)
    assert all(e["provenance"]["strength"] != "program_anchored" for e in edges)


def test_single_occurrence_edges_are_weak_and_will_terminate():
    """A prime the company subcontracted under exactly once is a weak edge whose join_method is not in
    propagation's step table -> propagation terminates across it (weak-hop termination)."""
    from pyrnova.propagation import _edge_steps

    _, edges = _edges()
    weak = [e for e in edges if e["provenance"]["strength"] == "weak"]
    assert weak, "expected some single-occurrence weak edges in the real data"
    for e in weak:
        assert e["provenance"]["sub_award_count"] == 1
        assert _edge_steps(e) is None                # terminates propagation
    # Deterministic/inferred edges do carry a finite degradation step.
    strong = [e for e in edges if e["provenance"]["strength"] != "weak"]
    for e in strong:
        assert _edge_steps(e) is not None


def test_graph_summary_denominators():
    _, edges = _edges()
    summary = summarize_relationship_graph(edges)
    assert summary["edges_total"] == len(edges)
    assert summary["relations"] == [SUBCONTRACT_RELATION]
    assert summary["deterministic_edges"] >= 1       # SAIC
    assert summary["weak_terminating_edges"] >= 1
    assert summary["distinct_subs"] == 1
    assert (summary["deterministic_edges"] + summary["inferred_edges"]
            + summary["weak_terminating_edges"]) == summary["edges_total"]
