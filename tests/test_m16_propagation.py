"""M16 — cross-company threat propagation: bounded, cycle-safe, confidence-degrading, no graph spam."""

from __future__ import annotations

from pyrnova import propagation
from pyrnova.models import Threat
from pyrnova.threat import CONFIDENCE_LEVELS, threat_id


def _seed(subject="co_a", mechanism="PROGRAM_CANCELLATION_OR_DELAY", conf="HIGH", sev="HIGH"):
    t = Threat(subject_ref=subject, subject_name=subject, mechanism=mechanism,
               confidence=conf, severity=sev, evidence_ids=["ev:root"], catalyst_id="cat_root")
    t.id = threat_id(subject, mechanism, "root")
    return t


def _edge(frm, to, relation="SUBCONTRACTOR_OF", link_class="CONFIRMED", av="2024-01-01"):
    return {"from_ref": frm, "to_ref": to, "relation": relation, "link_class": link_class,
            "evidence_ids": [f"ev:{frm}->{to}"], "available_at": av, "to_name": to}


def test_single_hop_degrades_confidence_and_severity():
    res = propagation.propagate_threats([_seed()], [_edge("co_a", "co_b")])
    assert len(res["propagated_threats"]) == 1
    pt = res["propagated_threats"][0]
    assert pt.subject_ref == "co_b"
    assert pt.meta["propagated"] is True
    assert pt.meta["propagation_depth"] == 1
    # HIGH degrades to MEDIUM across a confirmed hop; never increases.
    assert CONFIDENCE_LEVELS.index(pt.confidence) < CONFIDENCE_LEVELS.index("HIGH")
    assert pt.confidence == "MEDIUM"
    assert pt.meta["propagation_path"][-1]["from_ref"] == "co_a"


def test_depth_is_bounded():
    edges = [_edge("co_a", "co_b"), _edge("co_b", "co_c"), _edge("co_c", "co_d")]
    res = propagation.propagate_threats([_seed()], edges, max_depth=2)
    refs = {t.subject_ref for t in res["propagated_threats"]}
    assert refs == {"co_b", "co_c"}          # co_d beyond max_depth
    assert res["stats"]["max_depth_reached"] == 2


def test_confidence_exhaustion_terminates_before_max_depth():
    # HIGH -> MEDIUM -> LOW -> (below LOW) terminates, so a long chain stops on its own.
    edges = [_edge("co_a", "co_b"), _edge("co_b", "co_c"), _edge("co_c", "co_d")]
    res = propagation.propagate_threats([_seed(conf="HIGH")], edges, max_depth=5)
    refs = {t.subject_ref for t in res["propagated_threats"]}
    assert "co_d" not in refs                 # confidence exhausted at depth 3
    assert res["stats"]["weak_or_exhausted_terminations"] >= 1


def test_cycle_is_prevented_deterministically():
    edges = [_edge("co_a", "co_b"), _edge("co_b", "co_a")]
    res = propagation.propagate_threats([_seed()], edges, max_depth=5)
    assert res["stats"]["cycles_prevented"] >= 1
    # co_a is never re-threatened as a propagated node
    assert all(t.subject_ref != "co_a" for t in res["propagated_threats"])


def test_weak_relationship_terminates_propagation():
    res = propagation.propagate_threats([_seed()],
                                        [_edge("co_a", "co_b", link_class="name_only_weak")])
    assert res["propagated_threats"] == []
    assert res["stats"]["weak_or_exhausted_terminations"] == 1


def test_industry_adjacency_never_propagates():
    res = propagation.propagate_threats([_seed()],
                                        [_edge("co_a", "co_b", relation="SAME_INDUSTRY")])
    assert res["propagated_threats"] == []   # relation not in the allowed set


def test_duplicate_evidence_not_multiplied():
    # Two paths a->b and a->c->b to the same node/mechanism collapse to one propagated threat for b.
    edges = [_edge("co_a", "co_b"), _edge("co_a", "co_c"), _edge("co_c", "co_b")]
    res = propagation.propagate_threats([_seed()], edges, max_depth=3)
    b_threats = [t for t in res["propagated_threats"] if t.subject_ref == "co_b"]
    assert len(b_threats) == 1
    assert res["stats"]["duplicate_threats_suppressed"] >= 1


def test_beneficiary_opportunity_not_a_threat():
    res = propagation.propagate_threats(
        [_seed()], [_edge("co_a", "co_sub", relation="SUBSTITUTE_FOR")])
    assert res["propagated_threats"] == []
    assert len(res["beneficiary_opportunities"]) == 1
    opp = res["beneficiary_opportunities"][0]
    assert opp["subject_ref"] == "co_sub"
    assert opp["catalyst_id"] == "cat_root"
    assert opp["root_threat_id"] == res["beneficiary_opportunities"][0]["root_threat_id"]


def test_point_in_time_edge_excluded():
    res = propagation.propagate_threats([_seed()],
                                        [_edge("co_a", "co_b", av="2025-01-01")], as_of="2024-06-01")
    assert res["propagated_threats"] == []
