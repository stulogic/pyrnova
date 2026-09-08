"""M9 real-profile temporal grounding and leakage exclusion."""

from pyrnova.grounding import (
    first_supportable_capability_date,
    load_parsed,
    parse_usaspending_awards,
    profile_as_of,
)

TORCH = "examples/real_evidence/usaspending_torch.json"
MTSI = "examples/real_evidence/usaspending_mtsi.json"


def _parsed(path, name):
    return load_parsed(path, company_name=name)


# --- temporal capability evolution ---------------------------------------------

def test_torch_capabilities_evolve_and_scale_is_point_in_time():
    p = _parsed(TORCH, "Torch Technologies")
    caps2010 = {e.label for e in profile_as_of("Torch Technologies", p, "2010-12-31T23:59:59+00:00").capabilities}
    caps2020 = {e.label for e in profile_as_of("Torch Technologies", p, "2020-12-31T23:59:59+00:00").capabilities}
    caps2024 = {e.label for e in profile_as_of("Torch Technologies", p, "2024-12-31T23:59:59+00:00").capabilities}
    assert caps2010 == set()  # only broad early "SERVICES" awards -> no specific capability
    assert "systems_engineering_technical_assistance" in caps2020
    assert "hardware_in_the_loop_simulation" not in caps2020  # HWIL awards are 2021
    assert "hardware_in_the_loop_simulation" in caps2024

    # Scale is a temporal fact: the 2021 $623M award must not inflate the 2020 profile.
    scale2020 = profile_as_of("Torch Technologies", p, "2020-12-31T23:59:59+00:00").scale["max_contract_usd"]
    scale2024 = profile_as_of("Torch Technologies", p, "2024-12-31T23:59:59+00:00").scale["max_contract_usd"]
    assert scale2020 < scale2024
    assert scale2020 < 623310899  # the 2021 mega-award is excluded at the 2020 cutoff


def test_first_supportable_capability_dates_are_real():
    p = _parsed(TORCH, "Torch Technologies")
    assert first_supportable_capability_date(p, "systems_engineering_technical_assistance") == "2018-05-23"
    assert first_supportable_capability_date(p, "hardware_in_the_loop_simulation") == "2021-01-15"
    assert first_supportable_capability_date(p, "environmental_remediation") is None  # Torch never did this


# --- future-evidence leakage exclusion (hard gate) -----------------------------

def test_future_awards_are_excluded_from_earlier_profile():
    p = _parsed(MTSI, "Modern Technology Solutions")
    prof2021 = profile_as_of("Modern Technology Solutions", p, "2021-06-30T23:59:59+00:00")
    refs = {e.source_ref for e in prof2021.capabilities} | {h.get("award_ref") for h in prof2021.contract_history}
    # The 2024 (Digital Bloodhound) and 2025 (ARCWERX ARTEMIS) awards must NOT appear in a 2021 profile.
    assert "47QFMA24F0023" not in refs
    assert "47QFSA25F0011" not in refs
    # ...but a 2019 award should be present.
    prof2024 = profile_as_of("Modern Technology Solutions", p, "2025-12-31T23:59:59+00:00")
    refs2024 = {h.get("award_ref") for h in prof2024.contract_history}
    assert "47QFSA25F0011" in refs2024  # available once the cutoff reaches it


def test_no_cutoff_uses_all_evidence():
    p = _parsed(TORCH, "Torch Technologies")
    full = profile_as_of("Torch Technologies", p, None)
    assert len(full.contract_history) == p["award_count"]


def test_parse_is_deterministic_and_temporally_provenanced():
    raw = open(TORCH, "rb").read()
    a = parse_usaspending_awards(raw, company_name="Torch Technologies")
    b = parse_usaspending_awards(raw, company_name="Torch Technologies")
    assert a == b
    assert all(aw["available_at"] for aw in a["awards"])  # every fact carries temporal provenance
