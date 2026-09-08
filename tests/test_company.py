"""Tests for pyrnova.company — durable, evidence-linked COMPANY capability profile (M8)."""

from __future__ import annotations

import dataclasses

from pyrnova.company import (
    CapabilityEvidence,
    CompanyProfile,
    company_id,
    normalize_company_capabilities,
    build_profile,
    profile_from_dict,
    to_record,
)


# ---------------------------------------------------------------------------
# company_id
# ---------------------------------------------------------------------------

def test_company_id_deterministic_and_suffix_insensitive():
    a = company_id("Acme Radar Systems Inc")
    b = company_id("Acme Radar Systems, Inc.")
    c = company_id("ACME RADAR SYSTEMS LLC")
    assert a == b == c
    assert a.startswith("co_")


def test_company_id_different_for_different_names():
    a = company_id("Acme Radar Systems Inc")
    b = company_id("Beta Shipbuilding Corp")
    assert a != b


def test_company_id_stable_across_calls():
    assert company_id("Zeta Corp") == company_id("Zeta Corp")


# ---------------------------------------------------------------------------
# capability provenance
# ---------------------------------------------------------------------------

def test_naics_record_yields_specific_capability_with_provenance():
    records = [{
        "source_id": "sam_gov",
        "source_ref": "notice-123",
        "available_at": "2025-01-01",
        "naics": "334511",
        "title": "Radar component procurement",
    }]
    caps = normalize_company_capabilities(records)
    assert len(caps) == 1
    ev = caps[0]
    assert ev.label == "radar_component_manufacturing"
    assert ev.specificity == "specific"
    assert ev.source_id == "sam_gov"
    assert ev.source_ref == "notice-123"
    assert ev.available_at == "2025-01-01"
    assert ev.raw_phrase  # non-empty
    assert ev.basis


def test_reject_overly_broad_capability():
    records = [{
        "source_id": "src",
        "source_ref": "ref-1",
        "available_at": "2025-01-01",
        "title": "technology consulting services",
    }]
    caps = normalize_company_capabilities(records)
    assert caps == []


# ---------------------------------------------------------------------------
# point-in-time filtering
# ---------------------------------------------------------------------------

def test_point_in_time_excludes_future_capability_record():
    records = [
        {
            "source_id": "src",
            "source_ref": "ref-past",
            "available_at": "2024-01-01",
            "naics": "334511",
        },
        {
            "source_id": "src",
            "source_ref": "ref-future",
            "available_at": "2026-06-01",
            "naics": "336611",  # shipbuilding
        },
    ]
    caps = normalize_company_capabilities(records, as_of="2025-01-01")
    labels = {c.label for c in caps}
    assert "radar_component_manufacturing" in labels
    assert "shipbuilding" not in labels


def test_point_in_time_excludes_missing_available_at_when_as_of_given():
    records = [{
        "source_id": "src",
        "source_ref": "ref-nodate",
        "naics": "334511",
        # no available_at
    }]
    caps = normalize_company_capabilities(records, as_of="2025-01-01")
    assert caps == []


def test_point_in_time_contract_history_excludes_future_entries():
    profile = build_profile(
        "Acme Corp",
        records=(),
        contract_history=[
            {"agency": "DoD", "value_usd": 100.0, "available_at": "2024-06-01"},
            {"agency": "DoD", "value_usd": 200.0, "available_at": "2026-06-01"},
            {"agency": "DoD", "value_usd": 300.0},  # no available_at
        ],
        as_of="2025-01-01",
    )
    assert len(profile.contract_history) == 1
    assert profile.contract_history[0]["value_usd"] == 100.0


# ---------------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------------

def test_dedup_same_label_keeps_highest_confidence_and_merges_provenance():
    records = [
        {
            "source_id": "src_a",
            "source_ref": "ref-a",
            "available_at": "2025-01-01",
            "naics": "334511",  # confidence 0.9
        },
        {
            "source_id": "src_b",
            "source_ref": "ref-b",
            "available_at": "2025-02-01",
            "capability_terms": ["radar"],  # keyword confidence 0.55
        },
    ]
    caps = normalize_company_capabilities(records)
    radar_caps = [c for c in caps if c.label == "radar_component_manufacturing"]
    assert len(radar_caps) == 1
    assert radar_caps[0].confidence == 0.9
    assert radar_caps[0].source_ref == "ref-a"

    profile = build_profile("Acme Corp", records=records)
    # provenance reflects the surviving (highest-confidence) evidence's source_ref
    assert "ref-a" in profile.provenance


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------

def test_build_profile_is_deterministic():
    records = [{
        "source_id": "src",
        "source_ref": "ref-1",
        "available_at": "2025-01-01",
        "naics": "334511",
    }]
    p1 = build_profile("Acme Corp", records=records, naics=["334511"], geography=["Virginia"])
    p2 = build_profile("Acme Corp", records=records, naics=["334511"], geography=["Virginia"])
    assert to_record(p1) == to_record(p2)


# ---------------------------------------------------------------------------
# aliases / profile_from_dict
# ---------------------------------------------------------------------------

def test_aliases_retained():
    profile = build_profile("Acme Corp", aliases=["Acme Radar", "Acme Systems"])
    assert profile.aliases == ["Acme Radar", "Acme Systems"]


def test_profile_from_dict_maps_fields_correctly():
    d = {
        "name": "Acme Corp",
        "aliases": ["Acme"],
        "capability_records": [{
            "source_id": "src",
            "source_ref": "ref-1",
            "available_at": "2025-01-01",
            "naics": "334511",
        }],
        "naics": ["334511"],
        "psc": ["5840"],
        "certifications": ["ISO9001"],
        "clearances": ["FCL_SECRET"],
        "geography": ["Virginia"],
        "facilities": [{"location": "Arlington, VA", "type": "hq"}],
        "scale": {"employees": 250},
        "contract_history": [{"agency": "DoD", "value_usd": 500.0, "available_at": "2024-01-01"}],
        "partners": ["Beta LLC"],
        "exclusions": ["consumer_electronics"],
    }
    profile = profile_from_dict(d)
    assert profile.name == "Acme Corp"
    assert profile.aliases == ["Acme"]
    assert len(profile.capabilities) == 1
    assert profile.capabilities[0].label == "radar_component_manufacturing"
    assert profile.naics == ["334511"]
    assert profile.psc == ["5840"]
    assert profile.certifications == ["ISO9001"]
    assert profile.clearances == ["FCL_SECRET"]
    assert profile.geography == ["virginia"]
    assert profile.facilities == [{"location": "Arlington, VA", "type": "hq"}]
    assert profile.scale == {"employees": 250}
    assert len(profile.contract_history) == 1
    assert profile.partners == ["Beta LLC"]
    assert profile.exclusions == ["consumer_electronics"]
    assert profile.id == profile.company_id


def test_profile_from_dict_tolerates_missing_keys():
    profile = profile_from_dict({"name": "Bare Corp"})
    assert profile.name == "Bare Corp"
    assert profile.capabilities == []
    assert profile.contract_history == []


# ---------------------------------------------------------------------------
# available_at / first_observed_at
# ---------------------------------------------------------------------------

def test_first_observed_at_from_earliest_evidence():
    records = [
        {"source_id": "src", "source_ref": "ref-1", "available_at": "2025-03-01", "naics": "334511"},
        {"source_id": "src", "source_ref": "ref-2", "available_at": "2024-05-01", "naics": "336611"},
    ]
    profile = build_profile(
        "Acme Corp",
        records=records,
        contract_history=[{"agency": "DoD", "value_usd": 1.0, "available_at": "2023-01-01"}],
    )
    assert profile.first_observed_at == "2023-01-01"
    assert profile.available_at == "2023-01-01"


def test_available_at_uses_as_of_when_given():
    records = [{"source_id": "src", "source_ref": "ref-1", "available_at": "2024-01-01", "naics": "334511"}]
    profile = build_profile("Acme Corp", records=records, as_of="2025-06-01")
    assert profile.available_at == "2025-06-01"
    assert profile.first_observed_at == "2024-01-01"


def test_first_observed_at_none_when_no_evidence():
    profile = build_profile("Empty Corp")
    assert profile.first_observed_at is None
    assert profile.available_at is None


# ---------------------------------------------------------------------------
# field contract checks
# ---------------------------------------------------------------------------

def test_capability_evidence_field_contract():
    fields = {f.name for f in dataclasses.fields(CapabilityEvidence)}
    assert fields == {
        "label", "display", "confidence", "specificity", "source_id", "source_ref",
        "raw_phrase", "available_at", "basis",
    }


def test_company_profile_field_contract():
    fields = {f.name for f in dataclasses.fields(CompanyProfile)}
    assert fields == {
        "company_id", "name", "aliases", "capabilities", "naics", "psc", "certifications",
        "clearances", "geography", "facilities", "scale", "contract_history", "partners",
        "exclusions", "first_observed_at", "available_at", "provenance", "id", "meta",
    }
