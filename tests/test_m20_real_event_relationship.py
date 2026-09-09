"""M20 honesty gate: real material SEC event + deterministic company/program relationship."""

import json
from pathlib import Path

from pyrnova.adverse_events import parse_sec_corporate_adverse, to_corporate_restructuring_catalyst
from pyrnova.propagation import propagate_threats
from pyrnova.relationships import ground_company_program_edges
from pyrnova.threat import assess_threats, declared_exposures

EVENT = Path("examples/real_evidence/sec_saic_m20_adverse_extract.json")
SUBMISSIONS = Path("examples/real_evidence/sec_submissions_saic.json")
AWARDS = Path("examples/real_evidence/usaspending_saic.json")
CIK = "0001571123"
ACCESSION = "0001571123-26-000029"
RECIPIENT_ID = "20af0683-f17d-1f8f-38ee-2f11bd124559-C"


def _event_and_threat():
    event = parse_sec_corporate_adverse(EVENT.read_bytes())["events"][0]
    exposure = declared_exposures("co_saic", "SAIC", [{
        "relation": "CORPORATE_ENTITY", "target_ref": f"sec:CIK{CIK}",
        "target_name": "SAIC SEC filer", "deterministic": True,
        "available_at": "2017-03-30", "evidence_id": f"sec:CIK{CIK}",
    }], as_of="2026-03-16")
    threats, rejections = assess_threats("co_saic", "SAIC", exposure,
                                         [to_corporate_restructuring_catalyst(event)],
                                         as_of="2026-03-16")
    assert not rejections and len(threats) == 1
    return event, threats[0]


def test_sec_event_is_real_identified_material_and_independently_indexed():
    event, threat = _event_and_threat()
    submissions = json.loads(SUBMISSIONS.read_text())
    recent = submissions["filings"]["recent"]
    i = recent["accessionNumber"].index(ACCESSION)
    assert submissions["cik"] == CIK
    assert recent["form"][i] == "10-K" and recent["filingDate"][i] == "2026-03-16"
    assert event["event_type"] == "MATERIAL_RESTRUCTURING"
    assert event["amount_usd"] == 35_000_000
    assert event["target_ref"] == f"sec:CIK{CIK}"
    assert event["archive_hash"]
    assert threat.mechanism == "CORPORATE_RESTRUCTURING"
    assert threat.severity == "HIGH" and threat.confidence == "HIGH"
    assert threat.status == "MATERIALIZED"
    assert threat.meta["catalyst_class"] == "OBSERVED"
    assert threat.meta["exposure_join_class"] == "deterministic"
    assert threat.meta["adverse_event_family"] == "sec_corporate_adverse_event"


def test_company_to_program_edge_is_exact_real_and_propagates():
    _, threat = _event_and_threat()
    edges = ground_company_program_edges(AWARDS.read_bytes(), company_ref="co_saic",
                                         company_name="SAIC", recipient_id=RECIPIENT_ID)
    edge = next(e for e in edges if e["to_ref"] == "program:W31P4Q21F0095")
    assert edge["relation"] == "COMPANY_TO_PROGRAM"
    assert edge["join_method"] == "deterministic_native_id"
    assert edge["valid_from"] == "2021-03-03" and edge["valid_to"] == "2028-09-23"
    assert edge["provenance"]["recipient_id"] == RECIPIENT_ID
    result = propagate_threats([threat], [edge], as_of="2026-03-16")
    assert result["stats"]["propagated_threats"] == 1
    propagated = result["propagated_threats"][0]
    hop = propagated.meta["propagation_path"][0]
    assert propagated.subject_ref == "program:W31P4Q21F0095"
    assert propagated.confidence == "MEDIUM" and propagated.severity == "MODERATE"
    assert hop["relation"] == "COMPANY_TO_PROGRAM"
    assert hop["valid_from"] == "2021-03-03" and hop["valid_to"] == "2028-09-23"
    assert hop["provenance"]["award_id"] == "W31P4Q21F0095"


def test_relationship_must_be_valid_at_event_time_and_name_is_not_identity():
    _, threat = _event_and_threat()
    edge = next(e for e in ground_company_program_edges(
        AWARDS.read_bytes(), company_ref="co_saic", company_name="SAIC", recipient_id=RECIPIENT_ID)
        if e["to_ref"] == "program:W31P4Q21F0095")
    future = {**edge, "valid_from": "2026-04-01"}
    expired = {**edge, "valid_to": "2026-02-28"}
    for invalid in (future, expired):
        result = propagate_threats([threat], [invalid], as_of="2026-03-16")
        assert result["propagated_threats"] == []
        assert result["stats"]["relationship_temporal_terminations"] == 1
    assert ground_company_program_edges(AWARDS.read_bytes(), company_ref="co_wrong",
                                        company_name="SAIC", recipient_id="wrong-id") == []


def test_sec_family_rejects_unmatched_and_immaterial_events():
    event = parse_sec_corporate_adverse(EVENT.read_bytes())["events"][0]
    exposure = declared_exposures("co_other", "Other", [{
        "relation": "CORPORATE_ENTITY", "target_ref": "sec:CIK0000000001",
        "target_name": "Other filer", "deterministic": True, "available_at": "2020-01-01",
    }], as_of="2026-03-16")
    cat = to_corporate_restructuring_catalyst(event)
    threats, rejections = assess_threats("co_other", "Other", exposure, [cat], as_of="2026-03-16")
    assert not threats and [r.reason_code for r in rejections] == ["NO_EXPOSURE"]
    cat["target_ref"] = "sec:CIK0000000001"
    cat["amount_at_risk_usd"] = 1_000_000
    threats, rejections = assess_threats("co_other", "Other", exposure, [cat], as_of="2026-03-16")
    assert not threats and [r.reason_code for r in rejections] == ["IMMATERIAL"]
