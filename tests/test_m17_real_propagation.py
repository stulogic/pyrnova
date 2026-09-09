"""M17 — the corpus propagation edges are REAL: they are derivable from the archived sub-award bytes.

This is the honesty gate for the two flagship propagation cases. It proves the SAIC->Torch edge used in
corpus_m17 is not asserted out of thin air: grounding the archived sub-award evidence with
``pyrnova.relationships.ground_subaward_edges`` reproduces the same deterministic edge, and the corpus's
cited sub-award evidence ids are real rows in that evidence. It also demonstrates end-to-end weak-hop
termination across a REAL single-occurrence edge.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyrnova.grounding_subawards import parse_subawards
from pyrnova.propagation import propagate_threats
from pyrnova.relationships import ground_subaward_edges

_EVIDENCE = Path("examples/real_evidence/usaspending_subawards_torch.json")
_CORPUS = json.loads(Path("examples/replay/corpus_m17.json").read_text())
_SAIC_PIIDS = {"47QFSA20F0057", "W31P4Q21F0095", "W9126020FD504"}
_SAIC_NAME = "SCIENCE APPLICATIONS INTERNATIONAL CORPORATION"


def _parsed():
    return parse_subawards(_EVIDENCE.read_bytes(), company_name="TORCH TECHNOLOGIES INC")


def _grounded_saic_edge():
    edges = ground_subaward_edges(
        _parsed(), sub_ref="co_torch", sub_name="Torch Technologies Inc",
        prime_refs={_SAIC_NAME: "co_saic"}, exposed_prime_award_ids=_SAIC_PIIDS)
    return next(e for e in edges if e["from_ref"] == "co_saic")


def _corpus_case(case_id):
    return next(c for c in _CORPUS["threat_cases"] if c["case_id"] == case_id)


def test_flagship_edges_match_grounded_real_edge():
    """The corpus SAIC->Torch edges are the SAME deterministic edge grounding derives from real bytes."""
    grounded = _grounded_saic_edge()
    assert grounded["link_class"] == "CONFIRMED"
    assert grounded["join_method"] == "deterministic_native_id"
    real_sub_ids = {str(s["sub_award_id"]) for s in _parsed()["subawards"]}
    for cid in ("m17-real-propagation-saic-gsa", "m17-real-propagation-saic-army"):
        edge = _corpus_case(cid)["relationships"][0]
        assert edge["from_ref"] == grounded["from_ref"] == "co_saic"
        assert edge["to_ref"] == grounded["to_ref"] == "co_torch"
        assert edge["relation"] == grounded["relation"]
        assert edge["link_class"] == grounded["link_class"]
        assert edge["join_method"] == grounded["join_method"]
        # The sub-award ids the corpus cites as evidence are REAL rows in the archived bytes.
        for ev in edge["evidence_ids"]:
            assert ev.split(":")[-1] in real_sub_ids


def test_real_program_anchor_ids_are_real_saic_awards():
    """The deterministic anchor is a real SAIC prime award that Torch really subcontracts under."""
    saic_prime_ids = {r.get("Award ID") for r in
                      json.loads(Path("examples/real_evidence/usaspending_saic.json").read_bytes())["results"]}
    anchors = set(_grounded_saic_edge()["provenance"]["program_anchor_award_ids"])
    assert anchors == _SAIC_PIIDS
    assert anchors <= saic_prime_ids                 # every anchor is a real SAIC prime PIID


def test_weak_hop_terminates_end_to_end_on_a_real_edge():
    """Feeding propagate_threats a REAL single-occurrence (weak) prime edge yields zero propagation:
    the weak hop terminates rather than manufacturing an indirect threat."""
    parsed = _parsed()
    all_edges = ground_subaward_edges(parsed, sub_ref="co_torch",
                                      exposed_prime_award_ids=_SAIC_PIIDS)
    weak = next(e for e in all_edges if e["provenance"]["strength"] == "weak")
    # Seed a direct threat on the weak edge's prime, then offer ONLY that weak edge to propagation.
    from pyrnova.models import Threat
    seed = Threat(subject_ref=weak["from_ref"], subject_name=weak["from_name"],
                  mechanism="PROGRAM_CONTRACTION", severity="HIGH", confidence="HIGH",
                  horizon="NEAR_TERM", status="ACTIVE")
    result = propagate_threats([seed], [weak], max_depth=2, as_of="2025-01-01")
    assert result["stats"]["propagated_threats"] == 0
    assert result["stats"]["weak_or_exhausted_terminations"] >= 1
