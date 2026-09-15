"""B2.3 — opportunity-specific Buyer Intelligence."""

from pyrnova.buyer_intelligence import build_buyer_intelligence
from pyrnova.customer_intelligence import PUBLIC_EVIDENCE, PYRNOVA_DERIVED


RELATED = [
    {"source_id": "sam_opportunities", "source_ref": "N-1", "title": "Radar sustainment",
     "value_usd": 4_000_000.0, "set_aside": "SBA", "vehicle": "SeaPort-NxG", "recipient": "Acme",
     "available_at": "2023-01-01"},
    {"source_id": "sam_opportunities", "source_ref": "N-2", "title": "Radar sustainment II",
     "value_usd": 6_000_000.0, "set_aside": "SBA", "recipient": "Acme", "available_at": "2023-07-01"},
    {"source_id": "usaspending", "source_ref": "A-3", "title": "Radar award",
     "value_usd": 20_000_000.0, "recipient": "BigCo", "available_at": "2024-01-01"},
]


def test_organizational_identity_is_public_evidence():
    bi = build_buyer_intelligence(agency="Department of the Army", sub_agency="RCCTO",
                                  contracting_office="ACC-RSA", related_records=RELATED)
    assert bi.by_dimension("contracting_agency")[0].provenance_class == PUBLIC_EVIDENCE
    assert bi.by_dimension("sub_agency")[0].value == "RCCTO"
    assert not bi.is_unknown


def test_cadence_and_scale_are_derived():
    bi = build_buyer_intelligence(agency="Army", related_records=RELATED)
    cadence = bi.by_dimension("buying_cadence")[0]
    assert cadence.provenance_class == PYRNOVA_DERIVED and cadence.value > 0
    scale = bi.by_dimension("typical_award_scale")[0]
    assert scale.value["max"] == 20_000_000.0 and scale.value["n"] == 3


def test_set_aside_behavior_and_incumbents():
    bi = build_buyer_intelligence(agency="Army", related_records=RELATED)
    sba = bi.by_dimension("set_aside_behavior")[0]
    assert sba.value["set_aside"] == "SBA" and sba.value["count"] == 2
    vendors = {f.value for f in bi.incumbent_vendors()}
    assert {"Acme", "BigCo"} <= vendors


def test_thin_evidence_is_unknown_not_invented():
    bi = build_buyer_intelligence(agency=None, related_records=[])
    assert bi.is_unknown is True
    assert bi.by_dimension("buying_cadence") == []
    assert bi.by_dimension("typical_award_scale") == []


def test_single_procurement_cadence_is_unknown():
    bi = build_buyer_intelligence(agency="Army", related_records=[RELATED[0]])
    cadence = bi.by_dimension("buying_cadence")[0]
    assert cadence.value is None and cadence.uncertainty


def test_poc_only_from_named_official_notice():
    bi = build_buyer_intelligence(agency="Army", related_records=RELATED,
                                  pocs=[{"name": "J. Doe", "role": "KO", "notice_ref": "sam:N-1"},
                                        {"name": ""}])  # blank ignored
    pocs = bi.by_dimension("procurement_poc")
    assert len(pocs) == 1 and pocs[0].value["notice_ref"] == "sam:N-1"
