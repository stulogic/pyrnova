"""Canadian replay estate (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, CA vertical, boundary B).

Proves the accepted Canadian replay corpus runs THROUGH the shared kernel with Canadian national truth
preserved: mechanism classification, QUALIFIED timing (EXACT/BOUNDED/CONTAMINATED/N_A/UNKNOWN with NO
numeric DLT threshold), the corrected 2006 airlift doctrine, CPSP chronology + preserved provenance
conflict, TAPV bounded, CUAS zero-lead, LVM contamination, bilingual EN/FR original-language authority with
PYRNOVA-DERIVED translation + cross-language entity linkage, ITB/VP as a SEPARATE evidenced field, and
Access vs Canadian Industrial Position separation. Lawful, clearly-fixture evidence only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyrnova.domains import get_domain
from pyrnova.domains.pipeline import (
    NationalEvidence, assess_access, derive_material_change, derive_material_change_fixture,
)

CA = get_domain("CA")
CORPUS = json.loads(Path("examples/ca_replay/corpus.json").read_text(encoding="utf-8"))
BY_ID = {c["case_id"]: c for c in CORPUS["cases"]}


def _mc(case):
    ev = NationalEvidence(case["evidence_id"], case["source_id"], case["available_at"],
                          case["lifecycle_stage"], case["route"],
                          language=case.get("language", "en"),
                          translation=case.get("translation"), entity_key=case.get("entity_key"))
    return ev, derive_material_change_fixture(
        CA, ev, as_of="2025-06-01", mc_id=f"CA:{case['case_id']}",
        consequential_change_kind=case.get("consequential_change_kind"),
        mechanism=case.get("mechanism"), timing_class=case.get("timing_class", "UNKNOWN"),
        itb_vp=case.get("itb_vp", "UNKNOWN"))


def test_corpus_is_canadian_and_runs_through_shared_kernel():
    assert CORPUS["domain"] == "CA"
    for case in CORPUS["cases"]:
        if case["source_id"] == "ca_dcb":
            continue  # DECLARED => DENY: proven separately (honestly blocked)
        _ev, mc = _mc(case)
        assert mc.domain_code == "CA"
        assert CA.known_route(mc.route)
        assert mc.lifecycle_stage in CA.lifecycle
        assert CA.known_mechanism(mc.mechanism)
        assert mc.timing_class in CA.timing_classes
        acc = assess_access(CA, access_class=case["access_class"],
                            industrial_position=case["industrial_position"])
        assert acc.verdict in CA.access_classes


def test_domain_registration_and_no_numeric_dlt_threshold():
    assert CA.validated is True and CA.build_authority is True
    assert CA.dlt_calibration is None  # NO Canadian national numeric DLT threshold


# --- mechanism classification ----------------------------------------------------------------------

def test_all_five_mechanism_families_present_in_estate():
    seen = {_mc(c)[1].mechanism for c in CORPUS["cases"] if c["source_id"] != "ca_dcb"}
    assert {"COMPETITIVE_OPEN", "DIRECTED_OEM", "FMS_GTG", "STRATEGIC_SOURCE", "DIGITAL_ICT"} <= seen


def test_unknown_mechanism_fails_loud():
    ev = NationalEvidence("x", "ca_canadabuys_dataset", "2020-01-01", "SOLICITATION", "OPEN_COMPETITIVE")
    with pytest.raises(ValueError):
        derive_material_change_fixture(CA, ev, as_of="2025-06-01", mechanism="NOT_A_MECHANISM")


# --- QUALIFIED timing, never fabricated as exact ---------------------------------------------------

def test_timing_classes_are_qualified_not_fabricated():
    assert _mc(BY_ID["ca-gbad-open"])[1].timing_class == "EXACT"           # both endpoints defensible
    assert _mc(BY_ID["ca-tapv-bounded"])[1].timing_class == "BOUNDED"      # earlier 2009 LOI; day unresolved
    assert _mc(BY_ID["ca-lvm-contaminated"])[1].timing_class == "CONTAMINATED"  # earlier 2011/2014 engagement
    assert _mc(BY_ID["ca-cuas-zerolead"])[1].timing_class == "N_A"         # zero / no-pre-market-lead
    assert _mc(BY_ID["ca-msvs-reissued"])[1].timing_class == "UNKNOWN"


def test_corrected_2006_airlift_is_bounded_not_exact_not_fabricated_14day():
    mc = _mc(BY_ID["ca-cc177-bounded2006"])[1]
    # The invalidated exact 6-day 2006 DLT is NOT resurrected, and NOT replaced by a fabricated value.
    assert mc.timing_class == "BOUNDED"
    assert mc.timing_class != "EXACT"


def test_unknown_timing_class_fails_loud():
    ev = NationalEvidence("x", "ca_canadabuys_dataset", "2020-01-01", "SOLICITATION", "OPEN_COMPETITIVE")
    with pytest.raises(ValueError):
        derive_material_change_fixture(CA, ev, as_of="2025-06-01", timing_class="SIX_DAYS")


# --- CPSP chronology + preserved provenance conflict -----------------------------------------------

def test_cpsp_first_defensible_rfi_and_preserved_provenance_conflict():
    case = BY_ID["ca-cpsp-chronology"]
    assert case["available_at"] == "2024-09-15"          # first defensible RFI chronology
    conflict = case["provenance_conflict"]
    # Contradictory 16/17 September administrative metadata is PRESERVED, not silently normalized.
    assert conflict["administrative_metadata"] == ["2024-09-16", "2024-09-17"]
    assert _mc(case)[1].timing_class == "BOUNDED"


# --- bilingual EN/FR original-language authority ---------------------------------------------------

def test_french_original_is_authoritative_and_translation_is_derived():
    ev, mc = _mc(BY_ID["ca-victoria-bilingual"])
    assert ev.language == "fr"                    # French ORIGINAL evidence is original evidence
    assert ev.translation is not None and ev.translation["derived"] is True  # translation is PYRNOVA DERIVED
    assert ev.translation["language"] == "en"
    # A cross-language entity key links EN/FR variants without treating differing strings as different progs.
    assert ev.entity_key == "programme:victoria-class-modernization"


# --- ITB/VP is a SEPARATE evidenced field, never derived -------------------------------------------

def test_itb_vp_is_evidenced_and_survives_inaccessible_prime():
    mc = _mc(BY_ID["ca-cmma-itbvp"])[1]
    assert mc.itb_vp == "VALUE_PROPOSITION_RELEVANT"   # evidenced field
    # ITB applies to an FMS acquisition — ITB obligation is not restricted to open competition.
    assert _mc(BY_ID["ca-himars-fms"])[1].itb_vp == "ITB_OBLIGATION_APPLIES"


def test_itb_vp_never_derived_from_a_free_string():
    ev = NationalEvidence("x", "ca_canadabuys_dataset", "2020-01-01", "SOLICITATION", "OPEN_COMPETITIVE")
    with pytest.raises(ValueError):
        derive_material_change_fixture(CA, ev, as_of="2025-06-01", itb_vp="APPLIES_BECAUSE_BIG_CONTRACT")


# --- Access vs Canadian Industrial Position separation (Industrial Position != nationality/Access) --

def test_access_and_industrial_position_are_separate_axes():
    # An Industrial Position value cannot be used as an Access class...
    with pytest.raises(ValueError):
        assess_access(CA, access_class="STRATEGIC_SOURCE_STATUS", industrial_position="INCUMBENCY")
    # ...and an Access value cannot be used as an Industrial Position.
    with pytest.raises(ValueError):
        assess_access(CA, access_class="OEM_CONTROLLED", industrial_position="STRATEGIC_SOURCE_PRIME")
    ok = assess_access(CA, access_class="STRATEGIC_SOURCE_PRIME", industrial_position="STRATEGIC_SOURCE_STATUS")
    assert ok.verdict == "STRATEGIC_SOURCE_PRIME" and ok.industrial_position == "STRATEGIC_SOURCE_STATUS"


# --- FMS / strategic-source / OEM-incumbent semantics ----------------------------------------------

def test_fms_and_open_competition_are_distinct_national_meanings():
    assert CA.routes["FMS"] != CA.routes["OPEN_COMPETITIVE"]
    assert CA.routes["STRATEGIC_PARTNERSHIP"] != CA.routes["OPEN_COMPETITIVE"]
    fms = _mc(BY_ID["ca-himars-fms"])[1]
    assert fms.mechanism == "FMS_GTG" and fms.timing_class == "N_A"  # open-market prime DLT N_A


def test_strategic_source_downstream_is_not_open_prime():
    mc = _mc(BY_ID["ca-nss-strategic"])[1]
    assert mc.mechanism == "STRATEGIC_SOURCE" and mc.route == "STRATEGIC_PARTNERSHIP"
    acc = assess_access(CA, access_class="NESTED_SUBCOMPETITION", industrial_position="STRATEGIC_SOURCE_STATUS")
    assert acc.verdict == "NESTED_SUBCOMPETITION"  # NOT OPEN_COMPETITION


def test_directed_oem_absence_of_open_prime_is_not_absence_of_opportunity():
    mc = _mc(BY_ID["ca-cormorant-oem"])[1]
    assert mc.mechanism == "DIRECTED_OEM" and mc.route == "DIRECTED_OEM"
    # Access is OEM-controlled, but the change keeps the opportunity open (supply-chain access).
    assert mc.consequential_change_kind == "SUPPLY_CHAIN_ACCESS_CHANGED"


def test_live_ingestion_denied_for_fixture_only_source():
    # ca_canadabuys_dataset is FIXTURE_ONLY: the LIVE path denies it (UNKNOWN => DENY for production).
    ev = NationalEvidence("x", "ca_canadabuys_dataset", "2020-01-01", "SOLICITATION", "OPEN_COMPETITIVE")
    with pytest.raises(PermissionError):
        derive_material_change(CA, ev, as_of="2025-06-01")
