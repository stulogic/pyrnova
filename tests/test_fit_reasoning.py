"""B2.6 — evidence-linked Customer Fit reasoning (FOR / AGAINST / UNKNOWN)."""

from pyrnova.company import build_profile
from pyrnova.customers import CustomerProfile
from pyrnova.customer_intelligence import build_customer_intelligence
from pyrnova.fit import FitResult
from pyrnova.fit_reasoning import FOR, AGAINST, UNKNOWN_VERDICT, build_fit_reasoning
from pyrnova.vehicle_access import assess_vehicle_access


def _fit(posture="SUPPORT", fit=True):
    return FitResult(
        consequence_id="c1", company_id="mtsi", posture=posture, fit=fit, fit_confidence=0.6,
        dimensions=[
            {"name": "CAPABILITY_FIT", "verdict": "POSITIVE", "confidence": 0.8,
             "evidence_ids": ["usaspending:cap-1"], "basis": "radar manufacturing evidenced"},
            {"name": "SCALE", "verdict": "NEGATIVE", "confidence": 0.5, "evidence_ids": [],
             "basis": "opportunity far exceeds observed scale"},
            {"name": "GEOGRAPHY", "verdict": "UNKNOWN", "confidence": 0.0, "evidence_ids": [],
             "basis": "no place-of-performance on file"},
        ],
        blockers=[],
    )


def test_dimensions_map_to_for_against_unknown_with_evidence():
    r = build_fit_reasoning(_fit())
    assert {x.dimension for x in r.reasons_for} == {"CAPABILITY_FIT"}
    assert r.reasons_for[0].evidence_ids == ("usaspending:cap-1",)
    assert {x.dimension for x in r.reasons_against} == {"SCALE"}
    assert {x.dimension for x in r.unknowns} == {"GEOGRAPHY"}
    assert r.posture == "SUPPORT" and "FOR:" in r.explanation


def test_fatal_blocker_is_decisive_against():
    fr = _fit(posture="NO_FIT", fit=False)
    fr.blockers = [{"code": "no_required_capability", "detail": "no evidenced capability", "fatal": True}]
    r = build_fit_reasoning(fr)
    assert r.decisive_factor == "no_required_capability"
    assert any(x.decisive for x in r.reasons_against)


def test_agency_familiarity_and_no_access_are_folded_in():
    company = build_profile("MTSI", contract_history=[
        {"agency": "Department of the Army", "award_ref": "W-1", "available_at": "2023-01-01"},
        {"agency": "Department of the Army", "award_ref": "W-2", "available_at": "2024-01-01"},
    ])
    ci = build_customer_intelligence(company=company)
    access = assess_vehicle_access(current_vehicle="Agency IDIQ")  # no held access -> NO_KNOWN_ACCESS
    r = build_fit_reasoning(_fit(), customer_intelligence=ci, access=access)
    assert any(x.dimension == "agency_familiarity" and x.verdict == FOR for x in r.reasons_for)
    assert any(x.dimension == "access" and x.verdict == AGAINST for x in r.reasons_against)
    assert r.decisive_factor == "no_known_access"


def test_unsupported_customer_claim_becomes_an_unknown():
    company = build_profile("MTSI", records=[{"source_id": "usaspending", "source_ref": "cap-1",
                                              "naics": "334511", "available_at": "2024-01-01"}])
    customer = CustomerProfile(customer_id="mtsi", name="MTSI",
                              capabilities=["radar_component_manufacturing", "space_launch"])
    ci = build_customer_intelligence(customer=customer, company=company)
    r = build_fit_reasoning(_fit(), customer_intelligence=ci)
    assert any(x.dimension == "capability_claim" and "space_launch" in x.statement for x in r.unknowns)
