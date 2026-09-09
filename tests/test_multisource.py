"""M10 multi-source grounding — focused parser, merger, and integration tests (offline).

All tests read only the already-archived public-domain evidence under examples/real_evidence/.
No live calls. Point-in-time behavior is asserted directly."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyrnova.grounding_recipient import parse_recipient
from pyrnova.grounding_sec import parse_sec_submissions
from pyrnova.grounding_subawards import parse_subawards
from pyrnova.multisource import SourceFact, build_multisource_profile, merge_source_facts

EV = Path("examples/real_evidence")

SAIC_SOURCES = [
    {"kind": "usaspending_prime", "fixture": "usaspending_saic.json"},
    {"kind": "sec_submissions", "fixture": "sec_submissions_saic.json"},
    {"kind": "usaspending_recipient", "fixture": "usaspending_recipient_saic.json",
     "available_at": "2026-09-09"},
]
TORCH_SOURCES = [
    {"kind": "usaspending_prime", "fixture": "usaspending_torch.json"},
    {"kind": "usaspending_subawards", "fixture": "usaspending_subawards_torch.json"},
    {"kind": "usaspending_recipient", "fixture": "usaspending_recipient_torch.json",
     "available_at": "2023-01-01"},
]


# ---------------------------------------------------------------- parsers

def test_sec_submissions_geography_alias_sector():
    facts = parse_sec_submissions((EV / "sec_submissions_saic.json").read_bytes(),
                                  company_name="Science Applications International Corporation")
    by_type = {}
    for f in facts:
        by_type.setdefault(f.fact_type, []).append(f)
    assert any(f.value == "VA" for f in by_type["geography"])
    assert any("SAIC Gemini" in str(f.value) for f in by_type["alias"])  # former name
    assert by_type["sector"] and by_type["sector"][0].evidence_strength == 3
    # every fact carries a real available_at (a filing date)
    assert all(f.available_at for f in facts)


def test_recipient_large_business_holds_no_setaside_cert_but_has_eligibility():
    facts = parse_recipient((EV / "usaspending_recipient_saic.json").read_bytes(),
                            company_name="Science Applications International Corporation",
                            available_at="2026-09-09")
    certs = [f for f in facts if f.fact_type == "certification"]
    elig = [f for f in facts if f.fact_type == "eligibility"]
    assert certs == []  # other_than_small_business -> no socioeconomic set-aside cert
    assert elig and "other_than_small_business" in elig[0].value
    assert any(f.fact_type == "uei" for f in facts)


def test_recipient_requires_observation_date():
    with pytest.raises(ValueError):
        parse_recipient(b"{}", company_name="X", available_at="")


def test_subawards_target_is_subrecipient_and_repeat_is_authoritative():
    parsed = parse_subawards((EV / "usaspending_subawards_torch.json").read_bytes(),
                             company_name="Torch Technologies")
    assert parsed["subawards"], "expected Torch-as-subrecipient rows"
    assert all("TORCH" in (s["subrecipient"] or "").upper() for s in parsed["subawards"])
    saic = next(p for p in parsed["partners"]
                if "SCIENCE APPLICATIONS" in p["name"].upper())
    assert saic["authoritative"] is True  # repeat multi-year relationship
    assert all(h["role"] == "sub" for h in parsed["contract_history"])


# ---------------------------------------------------------------- merger

def test_merge_drops_future_facts_and_resolves_authority():
    facts = [
        SourceFact("geography", "VA", "sec_edgar", "r1", "2015-01-01", 4, 0.9),
        SourceFact("geography", "AL", "usaspending_recipient", "r2", "2030-01-01", 4, 0.9),  # future
        SourceFact("uei", "AAA", "sec_edgar", "r3", "2015-01-01", 4, 0.9),
        SourceFact("uei", "BBB", "usaspending_recipient", "r4", "2015-01-01", 4, 0.9),  # higher authority
    ]
    merged = merge_source_facts(facts, cutoff="2020-01-01")
    assert merged["geography"] == ["VA"]           # future AL dropped
    assert merged["uei"] == "BBB"                   # recipient outranks sec
    assert merged["conflicts"], "authority conflict recorded, not silent"


# ---------------------------------------------------------------- integration

def test_saic_grounds_three_families_with_material_evidence_beyond_prime():
    p = build_multisource_profile("Science Applications International Corporation",
                                  SAIC_SOURCES, "2026-09-09")
    assert p.meta["source_family_count"] >= 2
    assert "sec_edgar" in p.meta["source_families"]           # material beyond USAspending prime
    assert "va" in p.geography                                 # SEC-sourced geography
    assert p.scale.get("max_contract_usd")                     # USAspending scale retained


def test_torch_partner_edges_are_point_in_time_monotonic_no_future_leak():
    early = build_multisource_profile("Torch Technologies", TORCH_SOURCES, "2013-01-01")
    mid = build_multisource_profile("Torch Technologies", TORCH_SOURCES, "2020-01-01")
    saic = "SCIENCE APPLICATIONS INTERNATIONAL CORPORATION"
    assert saic not in early.partners            # not yet an authoritative partner in 2013
    assert saic in mid.partners                  # authoritative by 2020
    assert set(early.partners) <= set(mid.partners)  # partners only grow forward in time


def test_recipient_eligibility_is_not_knowable_before_observation():
    before = build_multisource_profile("Torch Technologies", TORCH_SOURCES, "2020-01-01")
    after = build_multisource_profile("Torch Technologies", TORCH_SOURCES, "2023-06-01")
    assert not before.meta["eligibility"]        # observed 2023-01-01, unknown as of 2020
    assert after.meta["eligibility"]             # knowable by 2023-06-01
