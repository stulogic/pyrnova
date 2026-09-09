"""M20 corpus, metrics, selectivity, and thin Operations Panel acceptance."""

import hashlib
from pathlib import Path

import pytest

from pyrnova import threat
from pyrnova.adverse_events import parse_sec_corporate_adverse, to_corporate_restructuring_catalyst
from pyrnova.ops import OperatorConsole
from pyrnova.selectivity import run_selectivity, source_run_funnel
from pyrnova.sources import ofac

CORPUS = "examples/replay/corpus_m20.json"
EVENT = Path("examples/real_evidence/sec_saic_m20_adverse_extract.json")
DESIGNATIONS = ofac.parse_ofac_csv(Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")
FROZEN = {
    "examples/replay/corpus_m15.json": "7849beae3282d76a99f7a8e3d00f80665ae5ad4284fc55c8ef499c8d836bd2b4",
    "examples/replay/corpus_m16.json": "8d42c7e9206182dd31e3fad60db59dbab053b8d95e113eb2bc10279e0e9ceb69",
    "examples/replay/corpus_m17.json": "f9ac9458901dcda480ce2b25e9463a8c8ae85dee658b021a8e617dbea5343bb8",
    "examples/replay/corpus_m18.json": "7fdfad85a582861f74457e41578750ac41e49501d4ca6a2d4e88ef570d007004",
    "examples/replay/corpus_m19.json": "60f581c9c573bf6766e4e176e7cbc2b418bc9f5f176c51c57efd64a64ce4baa7",
}


@pytest.fixture(scope="module")
def replayed():
    payload = threat.load_threat_corpus(CORPUS)
    return payload, threat.run_threat_corpus(payload, DESIGNATIONS)


def test_m20_extends_frozen_m19_and_all_cases_pass(replayed):
    for path, expected in FROZEN.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    payload, results = replayed
    assert len(payload["threat_cases"]) == 74
    assert sum(1 for r in results if r["case_id"].startswith("m20")) == 8
    assert not [r["case_id"] for r in results if not r["ok"]]


def test_third_family_real_new_relation_and_selective_severity(replayed):
    _, results = replayed
    summary = threat.summarize_m20(results)
    assert summary["adverse_event_families_exercised"] == [
        "contract_modification", "regulatory_adverse_event", "sec_corporate_adverse_event"]
    relation = summary["relationship_type_diversity"]
    assert "COMPANY_TO_PROGRAM" in relation["real_relationship_types"]
    assert relation["propagation_chains_by_type"]["COMPANY_TO_PROGRAM"] == 1
    assert relation["unique_entity_pairs"] >= 15
    assert summary["multi_family_selectivity"]["sec_corporate_adverse_event"]["rejections"] >= 2
    severe = summary["high_critical_outcomes"]
    assert severe["resolved"] >= 1 and severe["materialized"] >= 1
    assert severe["unresolved"] >= 1
    assert summary["relationship_temporal_terminations"] >= 1


def test_real_chain_provenance_and_no_explosion(replayed):
    _, results = replayed
    result = next(r for r in results if r["case_id"] == "m20-real-sec-restructuring-company-program")
    direct = result["threats"][0]
    propagated = result["propagation"]["propagated_threats"][0]
    hop = propagated["meta"]["propagation_path"][0]
    assert direct["severity"] == "HIGH" and direct["confidence"] == "HIGH"
    assert propagated["severity"] == "MODERATE" and propagated["confidence"] == "MEDIUM"
    assert hop["relation"] == "COMPANY_TO_PROGRAM"
    assert hop["source_id"] == "usaspending"
    assert hop["join_method"] == "deterministic_native_id"
    assert hop["valid_from"] <= direct["available_at"] <= hop["valid_to"]
    summary = threat.summarize_m20(results)
    assert summary["propagation_quality"]["confidence_never_increases"] is True
    assert summary["propagation_quality"]["propagation_explosion"] is False
    assert summary["temporal_leakage_violations"] == 0


def test_sec_family_uses_same_selectivity_and_panel_paths():
    parsed = parse_sec_corporate_adverse(EVENT.read_bytes())
    catalyst = to_corporate_restructuring_catalyst(parsed["events"][0])
    monitored = [
        {"ref": "co_saic", "name": "SAIC", "exposure_records": [{
            "relation": "CORPORATE_ENTITY", "target_ref": "sec:CIK0001571123",
            "target_name": "SAIC SEC filer", "deterministic": True,
            "available_at": "2017-03-30", "evidence_id": "sec:CIK0001571123"}]},
        {"ref": "co_other", "name": "Other", "exposure_records": [{
            "relation": "CORPORATE_ENTITY", "target_ref": "sec:CIK0000000001",
            "target_name": "Other SEC filer", "deterministic": True,
            "available_at": "2020-01-01", "evidence_id": "sec:CIK0000000001"}]},
    ]
    result = run_selectivity(monitored, catalyst_records=[catalyst], raw_event_count=1,
                             as_of="2026-03-16", stream_name="sec_corporate_adverse_event")
    assert result["funnel"]["threats_emitted"] == 1
    assert result["funnel"]["zero_threat_rejections"] == 1
    run = source_run_funnel(result, source_id="sec_edgar", run_id="m20-sec-1",
                            calls_made=0, calls_avoided=8, records_received=1, changed_records=1)
    assert run["calls_made"] == 0 and run["calls_avoided"] == 8
    view = OperatorConsole.adverse_catalyst_view(parsed, {"unique_relationship_types": ["COMPANY_TO_PROGRAM"]})
    event = view["catalysts"][0]
    assert view["family"] == "sec_corporate_adverse_event"
    assert event["event_type"] == "MATERIAL_RESTRUCTURING"
    assert event["cik"] == "0001571123" and event["amount_usd"] == 35_000_000
