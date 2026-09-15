"""B2.2 — Customer Intelligence Profile: provenance-distinct, evidence-backed."""

from pyrnova.company import build_profile
from pyrnova.customers import CustomerProfile
from pyrnova.customer_intelligence import (
    CUSTOMER_SUPPLIED, PUBLIC_EVIDENCE, PYRNOVA_DERIVED,
    build_customer_intelligence,
)


def _company():
    return build_profile(
        "Modern Technology Solutions",
        records=[{"source_id": "usaspending", "source_ref": "cap-1", "naics": "334511",
                  "available_at": "2024-01-01"}],
        certifications=["ISO 9001"],
        exclusions=["no wetware"],
        contract_history=[
            {"agency": "Department of the Army", "value_usd": 5_000_000.0, "role": "prime",
             "award_ref": "W911-A", "vehicle": "SeaPort-NxG", "available_at": "2023-01-01"},
            {"agency": "Department of the Army", "value_usd": 12_000_000.0, "role": "prime",
             "award_ref": "W911-B", "available_at": "2024-06-01"},
        ],
        as_of="2025-01-01",
    )


def _customer():
    return CustomerProfile(
        customer_id="mtsi", name="MTSI",
        capabilities=["radar_component_manufacturing", "hypersonics_test"],
        agencies=["Department of the Army"],
        effective_from="2025-01-01T00:00:00+00:00",
    )


def test_facts_are_provenance_distinct():
    prof = build_customer_intelligence(customer=_customer(), company=_company(), as_of="2025-02-01")
    classes = {f.provenance_class for f in prof.facts}
    assert classes == {CUSTOMER_SUPPLIED, PUBLIC_EVIDENCE, PYRNOVA_DERIVED}
    # A customer claim never masquerades as public evidence.
    claimed = prof.claimed_capabilities()
    assert all(f.provenance_class == CUSTOMER_SUPPLIED for f in claimed)
    assert all(f.uncertainty for f in claimed)


def test_public_capability_is_evidence_backed():
    prof = build_customer_intelligence(company=_company())
    supported = prof.supported_capabilities()
    assert any(f.key == "radar_component_manufacturing" for f in supported)
    cap = next(f for f in supported if f.key == "radar_component_manufacturing")
    assert cap.evidence_ids and cap.available_at == "2024-01-01"


def test_agency_familiarity_is_derived_from_repeat_contracts():
    prof = build_customer_intelligence(company=_company())
    served = {f.key: f for f in prof.agencies_served()}
    army = served["department of the army"]
    assert army.provenance_class == PYRNOVA_DERIVED
    assert set(army.evidence_ids) == {"W911-A", "W911-B"}
    assert army.uncertainty == ""  # two contracts -> not tentative


def test_claimed_but_unsupported_capability_is_a_derived_gap():
    prof = build_customer_intelligence(customer=_customer(), company=_company())
    gaps = {f.key for f in prof.unsupported_claims()}
    # radar is publicly evidenced; hypersonics_test is only claimed -> a gap.
    assert "hypersonics_test" in gaps
    assert "radar_component_manufacturing" not in gaps


def test_supplied_priorities_and_exclusions_are_carried_as_claims():
    prof = build_customer_intelligence(
        customer=_customer(), company=_company(),
        strategic_priorities=["directed energy"], strategic_exclusions=["nuclear"],
        preferred_deal_shapes=["prime IDIQ"],
    )
    dims = {f.dimension for f in prof.by_provenance(CUSTOMER_SUPPLIED)}
    assert {"strategic_priority", "strategic_exclusion", "preferred_deal_shape"} <= dims
    rec = prof.to_record()
    assert rec["provenance_counts"][PUBLIC_EVIDENCE] > 0


def test_vehicle_access_evidence_is_public():
    prof = build_customer_intelligence(company=_company())
    vehicles = prof.by_dimension("vehicle_access")
    assert any(f.value == "SeaPort-NxG" and f.provenance_class == PUBLIC_EVIDENCE for f in vehicles)
