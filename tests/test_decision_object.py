"""B2.10 — Integrated Decision Object: representative end-to-end assembly."""

import json

from pyrnova.chains import resolve_chain, signals_from_records
from pyrnova.budget_lineage import build_budget_lineage
from pyrnova.company import build_profile
from pyrnova.customers import CustomerProfile
from pyrnova.customer_intelligence import build_customer_intelligence
from pyrnova.buyer_intelligence import build_buyer_intelligence
from pyrnova.competitive_intelligence import build_competitive_intelligence
from pyrnova.vehicle_access import assess_vehicle_access
from pyrnova.fit import FitResult
from pyrnova.fit_reasoning import build_fit_reasoning
from pyrnova.pursuit import decide_pursuit, PURSUE, WATCH, INVESTIGATE, PASS
from pyrnova.material_change_consequence import assess_material_change_consequence
from pyrnova.decision_object import assemble_decision

PK = "disa:cloud-modernization"


def _scenario():
    records = [
        {"source_id": "appropriations", "source_ref": "ap-1", "stage": "AUTHORIZATION", "program_key": PK,
         "available_at": "2025-02-01", "summary": "FY26 appropriation"},
        {"source_id": "acquisition_forecast", "source_ref": "fc-1", "stage": "MARKET_ENGAGEMENT",
         "program_key": PK, "available_at": "2025-04-01", "summary": "forecast"},
        {"source_id": "sam_opportunities", "source_ref": "sol-1", "stage": "PROCUREMENT", "program_key": PK,
         "available_at": "2025-07-01", "summary": "solicitation", "procurement_id": "DISA-26-R-1",
         "notice_type": "solicitation"},
        {"source_id": "sam_opportunities", "source_ref": "sol-1-a1", "stage": "PROCUREMENT", "program_key": PK,
         "available_at": "2025-07-20", "summary": "amendment", "procurement_id": "DISA-26-R-1",
         "notice_type": "amendment"},
    ]
    chain = resolve_chain(signals_from_records(records))
    company = build_profile("MTSI", records=[{"source_id": "usaspending", "source_ref": "cap-1",
                                              "naics": "334511", "available_at": "2024-01-01"}],
                            contract_history=[{"agency": "DISA", "award_ref": "W-1", "vehicle": "OASIS+",
                                               "available_at": "2024-01-01"}])
    customer = CustomerProfile(customer_id="mtsi", name="MTSI",
                              capabilities=["radar_component_manufacturing"], agencies=["DISA"])
    ci = build_customer_intelligence(customer=customer, company=company, as_of="2025-08-01")
    buyer = build_buyer_intelligence(agency="DISA", related_records=[
        {"source_id": "sam_opportunities", "source_ref": "N-old", "value_usd": 3e6, "set_aside": "SBA",
         "available_at": "2023-01-01"}])
    comp = build_competitive_intelligence(incumbent={"name": "BigCo", "evidence_ref": "W-old"},
                                          current_contract={"award_id": "W-old", "period_start": "2021-01-01",
                                                            "period_end": "2026-03-01", "available_at": "2021-01-01"},
                                          as_of="2025-08-01")
    access = assess_vehicle_access(current_vehicle="OASIS+", customer_vehicles=["OASIS+"])
    fit = FitResult(consequence_id="c1", company_id="mtsi", posture="PRIME", fit=True, fit_confidence=0.7,
                    dimensions=[{"name": "CAPABILITY_FIT", "verdict": "POSITIVE", "confidence": 0.8,
                                 "evidence_ids": ["usaspending:cap-1"], "basis": "radar evidenced"}],
                    blockers=[])
    fr = build_fit_reasoning(fit, customer_intelligence=ci, access=access)
    verdict = decide_pursuit(fit_reasoning=fr, access=access, competitive=comp,
                             detection_disposition="STRIKE", timing={"actionable": True})
    mc = assess_material_change_consequence({"kind": "amendment", "id": "mc-1", "materiality": "MEDIUM",
                                             "program_key": PK, "evidence_ids": ["sam:sol-1-a1"]})
    return dict(chain=chain, bl=build_budget_lineage(chain), ci=ci, buyer=buyer, comp=comp,
                access=access, fr=fr, verdict=verdict, mc=mc)


def test_integrated_decision_composes_all_capabilities():
    s = _scenario()
    d = assemble_decision(
        opportunity_ref="DISA-26-R-1", chain_resolution=s["chain"], budget_lineage=s["bl"],
        material_changes=[s["mc"]], customer_intelligence=s["ci"], buyer_intelligence=s["buyer"],
        competitive_intelligence=s["comp"], vehicle_access=s["access"], fit_reasoning=s["fr"],
        pursuit_verdict=s["verdict"],
        decision_lead_time={"lead_time_days": 150, "basis": "authorization->solicitation"},
        decision_memory={"customer_id": "mtsi", "intelligence_ref": "mc-1", "pursuit": "PURSUED"},
        as_of="2025-08-01")

    # program_key inferred from the single-program chain.
    assert d.program_key == PK
    assert d.current_stage == "PROCUREMENT"
    assert d.disposition in (PURSUE, WATCH, INVESTIGATE, PASS)
    # Reversal conditions are sourced from the pursuit verdict (not recomputed).
    assert d.reversal_conditions == s["verdict"].reversal_conditions and d.reversal_conditions
    # Lifecycle reflects B2.1 procurement instance(s).
    assert d.lifecycle["instances"] and d.lifecycle["current_instance"]["procurement_id"] == "DISA-26-R-1"


def test_record_is_a_self_contained_serializable_contract():
    s = _scenario()
    d = assemble_decision(opportunity_ref="DISA-26-R-1", program_key=PK, chain_resolution=s["chain"],
                          budget_lineage=s["bl"], material_changes=[s["mc"]], customer_intelligence=s["ci"],
                          buyer_intelligence=s["buyer"], competitive_intelligence=s["comp"],
                          vehicle_access=s["access"], fit_reasoning=s["fr"], pursuit_verdict=s["verdict"],
                          decision_lead_time={"lead_time_days": 150},
                          decision_memory={"pursuit": "PURSUED"}, as_of="2025-08-01")
    rec = d.to_record()
    for key in ("opportunity_ref", "current_stage", "disposition", "lifecycle", "budget_lineage",
                "material_changes", "customer_intelligence", "buyer_intelligence",
                "competitive_intelligence", "vehicle_access", "fit_reasoning", "pursuit_verdict",
                "reversal_conditions", "decision_lead_time", "decision_memory",
                "referenced_evidence_ids", "uncertainty"):
        assert key in rec
    # Fully JSON-serializable (Bundle 3 can present it without touching the domain layer).
    json.dumps(rec)
    # The evidence index aggregates references from multiple components (no duplication of facts).
    assert "usaspending:cap-1" in rec["referenced_evidence_ids"]
    assert rec["uncertainty"]["access_verdict"] == "DIRECT_ACCESS"


def test_partial_assembly_degrades_gracefully():
    # Only a pursuit verdict + chain: the object still assembles and serializes.
    s = _scenario()
    d = assemble_decision(opportunity_ref="DISA-26-R-1", chain_resolution=s["chain"],
                          pursuit_verdict=s["verdict"])
    rec = d.to_record()
    assert rec["buyer_intelligence"] is None and rec["fit_reasoning"] is None
    assert rec["disposition"] == s["verdict"].disposition
    json.dumps(rec)
