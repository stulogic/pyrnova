"""Tests for pyrnova.capabilities — deterministic specific-capability extraction."""

from __future__ import annotations

from pyrnova.capabilities import CapabilityClass, extract_capabilities


def test_naics_extraction_specific_label():
    record = {"naics": "334511", "title": "Search radar array procurement"}
    results = extract_capabilities(record)
    assert len(results) >= 1
    top = results[0]
    assert top.label == "radar_component_manufacturing"
    assert top.confidence >= 0.85
    assert top.source_fields.get("naics") == "334511"


def test_psc_extraction_specific_label():
    record = {"psc": "F003", "title": "Site cleanup requirement"}
    results = extract_capabilities(record)
    assert len(results) == 1
    top = results[0]
    assert top.label == "environmental_remediation"
    assert top.confidence >= 0.85
    assert top.source_fields.get("psc") == "F003"


def test_multiword_phrase_extraction():
    record = {"title": "Contract for environmental remediation at former base"}
    results = extract_capabilities(record)
    assert len(results) == 1
    assert results[0].label == "environmental_remediation"
    assert 0.6 <= results[0].confidence < 0.9
    assert results[0].source_fields.get("phrase") == "environmental remediation"


def test_broad_terms_alone_reject():
    record = {"title": "General technology consulting services"}
    results = extract_capabilities(record)
    assert results == []


def test_broad_naics_psc_absent_and_broad_text_yields_empty():
    record = {"description": "management support solutions"}
    assert extract_capabilities(record) == []


def test_evidence_id_flows_into_evidence_ids():
    record = {"naics": "562910", "title": "Remediation services"}
    results = extract_capabilities(record, evidence_id="ev-123")
    assert len(results) == 1
    assert results[0].evidence_ids == ("ev-123",)


def test_evidence_id_absent_yields_empty_tuple():
    record = {"naics": "562910"}
    results = extract_capabilities(record)
    assert results[0].evidence_ids == ()


def test_source_fields_populated():
    record = {"naics": "238210", "psc": "Z2AA", "title": "Electrical construction wiring upgrade"}
    results = extract_capabilities(record)
    # naics and psc both map to electrical_construction and should merge into one entry
    assert len(results) == 1
    top = results[0]
    assert top.label == "electrical_construction"
    assert top.source_fields.get("naics") == "238210"
    assert top.source_fields.get("psc") == "Z2AA"


def test_deterministic_repeated_calls_identical():
    record = {
        "naics": "334511",
        "psc": "5895",
        "title": "Radar and electronic countermeasures suite",
        "description": "semiconductor process integration",
        "capability_terms": ["battery manufacturing"],
    }
    first = extract_capabilities(record, evidence_id="ev-abc")
    second = extract_capabilities(record, evidence_id="ev-abc")
    assert first == second
    labels_first = [c.label for c in first]
    labels_second = [c.label for c in second]
    assert labels_first == labels_second


def test_dedup_same_label_via_naics_and_phrase_merges_provenance():
    record = {"naics": "334511", "title": "Radar system replacement"}
    results = extract_capabilities(record, evidence_id="ev-1")
    matches = [c for c in results if c.label == "radar_component_manufacturing"]
    assert len(matches) == 1
    top = matches[0]
    # NAICS match should win on confidence (0.9) over the "radar" keyword match (0.55)
    assert top.confidence >= 0.85
    assert "naics" in top.source_fields
    assert "phrase" in top.source_fields


def test_missing_fields_no_error_empty_result():
    assert extract_capabilities({}) == []
    assert extract_capabilities({"naics": None, "psc": "", "title": None}) == []


def test_result_ordering_deterministic_by_confidence_then_label():
    record = {
        "naics": "334511",  # radar_component_manufacturing, 0.9
        "description": "environmental remediation and cloud security review",  # two 0.7 phrase hits
    }
    results = extract_capabilities(record)
    confidences = [c.confidence for c in results]
    assert confidences == sorted(confidences, reverse=True)
    # among equal confidence, labels should be ascending
    for i in range(len(results) - 1):
        if results[i].confidence == results[i + 1].confidence:
            assert results[i].label < results[i + 1].label


def test_capability_class_is_frozen_dataclass_with_contract_fields():
    fields = CapabilityClass.__dataclass_fields__
    assert set(fields.keys()) == {
        "label", "display", "confidence", "evidence_ids", "source_fields", "basis",
    }
    inst = CapabilityClass(
        label="radar_component_manufacturing",
        display="Radar component manufacturing",
        confidence=0.9,
        evidence_ids=("e1",),
        source_fields={"naics": "334511"},
        basis="test",
    )
    try:
        inst.label = "changed"  # type: ignore[misc]
        assert False, "expected frozen dataclass to reject mutation"
    except Exception:
        pass
