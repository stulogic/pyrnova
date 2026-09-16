"""Global Kernel <-> National Domain contract + Australian national increment.

Covers success criteria for the international framework:
  1. global/national code boundary exists and is tested;
  2. US behaviour is declared, not changed (see the rest of the suite for US intactness);
  3. AU national domain is executable and runs THROUGH the shared kernel;
  4. an AU historical/replay flow exercises the module through the shared intelligence chain;
  5. UK/CA/NZ seams exist without falsely implementing unresolved national truth;
  6. no forbidden source activation (NZ GETS hard lock; UNKNOWN => DENY).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyrnova.decision_lead_time import TemporalAnchors
from pyrnova.domains import (
    all_domains, get_domain, operational_domains, ProhibitedSourceIngestion, SourceActivation,
)
from pyrnova.domains.pipeline import (
    ASOFViolation, NationalEvidence, NationalOpportunity, assess_access,
    derive_material_change, derive_material_change_fixture, to_decision,
)

CORPUS = Path(__file__).resolve().parent.parent / "examples" / "au_replay" / "corpus.json"
NZ_CORPUS = Path(__file__).resolve().parent.parent / "examples" / "nz_replay" / "corpus.json"
UK_CORPUS = Path(__file__).resolve().parent.parent / "examples" / "uk_replay" / "corpus.json"


# --- 1. registry / boundary -----------------------------------------------------------------------

def test_registry_has_five_domains_us_au_nz_uk_operational():
    codes = {d.code for d in all_domains()}
    assert codes == {"US", "AU", "GB", "CA", "NZ"}
    # US, AU, NZ, the UK (GB) and now Canada (CA) are validated AND have owner build authority.
    assert {d.code for d in operational_domains()} == {"US", "AU", "NZ", "GB", "CA"}
    assert get_domain("uk").code == "GB"  # alias, case-insensitive


def test_canada_is_operational_with_no_numeric_dlt_threshold():
    # Canadian build authority granted (PYRNOVA-CA-SPEC-001 + HISTORICAL-VALIDATION-001/002 accepted).
    ca = get_domain("CA")
    assert ca.validated is True and ca.build_authority is True
    # NO Canadian national numeric DLT threshold is authorized or required — calibration stays None.
    assert ca.dlt_calibration is None


def test_uk_is_operational_with_no_numeric_dlt_threshold():
    uk = get_domain("GB")
    assert uk.validated is True and uk.build_authority is True
    # n=3 strict-qualifying cases: NO UK numeric DLT threshold is authorized. DLT is an observed attribute.
    assert uk.dlt_calibration is None


# --- 5. national truth kept national (not flattened) ----------------------------------------------

def test_national_route_and_industrial_semantics_are_distinct_not_universal():
    au = get_domain("AU")
    # FMS, GtG and open competition are DISTINCT national meanings, never collapsed.
    assert au.known_route("FMS") and au.known_route("GTG") and au.known_route("OPEN")
    assert au.routes["FMS"] != au.routes["GTG"]
    # AIC is distinct from sovereign capability; foreign ownership is NOT ineligibility.
    assert "AIC_ALIGNED" in au.industrial_position_classes
    assert "SOVEREIGN_CAPABILITY" in au.industrial_position_classes
    assert "FOREIGN_OWNED_LOCALLY_PRESENT" in au.industrial_position_classes
    ca = get_domain("CA")
    assert ca.evidence_languages == ("en", "fr")  # bilingual original-language authority


# --- 6. no forbidden source activation ------------------------------------------------------------

def test_nz_gets_is_a_hard_lock():
    nz = get_domain("NZ")
    assert nz.source("nz_gets").activation is SourceActivation.PROHIBITED
    assert nz.is_ingestible("nz_gets") is False
    with pytest.raises(ProhibitedSourceIngestion):
        nz.assert_ingestible("nz_gets")
    # A fixture/replay path must ALSO refuse a prohibited source.
    ev = NationalEvidence("x", "nz_gets", "2020-01-01", "AWARD", "OPEN")
    with pytest.raises(ProhibitedSourceIngestion):
        derive_material_change_fixture(nz, ev, as_of="2021-01-01")


def test_unknown_source_denied_and_non_active_not_live_ingestible():
    au = get_domain("AU")
    # AusTender is FIXTURE_ONLY -> not ACTIVE -> live ingestion denied (UNKNOWN => DENY).
    assert au.is_ingestible("au_austender") is False
    ev = NationalEvidence("e", "au_austender", "2022-01-01", "APPROACH_TO_MARKET", "OPEN")
    with pytest.raises(PermissionError):
        derive_material_change(au, ev, as_of="2022-06-01")


# --- 3 & 4. AU executable + replay through the shared chain ----------------------------------------

def test_au_replay_runs_through_shared_kernel():
    au = get_domain("AU")
    corpus = json.loads(CORPUS.read_text())
    assert corpus["domain"] == "AU"
    qualifying = 0
    for case in corpus["cases"]:
        ev = NationalEvidence(
            evidence_id=case["evidence_id"], source_id=case["source_id"],
            available_at=case["available_at"], lifecycle_stage=case["lifecycle_stage"],
            route=case["route"])
        mc = derive_material_change_fixture(
            au, ev, as_of="2024-01-01", important_miss_kind=case["important_miss_kind"],
            mc_id=case["case_id"])
        # National meaning preserved on the change.
        assert mc.route == case["route"]
        assert mc.lifecycle_stage in au.lifecycle
        assert mc.important_miss_kind in au.important_miss
        acc = assess_access(au, access_class=case["access_class"],
                            industrial_position=case["industrial_position"])
        opp = NationalOpportunity(material_change=mc, access=acc, customer_id="eval-au")
        a = case["anchors"]
        anchors = TemporalAnchors(t0_source_available_at=a["t0"], t1_acquired_at=a["t1"],
                                  t4_customer_ready_at=a["t4"], benchmark_b=a["benchmark_b"])
        dec = to_decision(au, opp, anchors=anchors, as_of="2024-01-01")
        # Shared decision object composed; national data travels on it.
        rec = dec.to_record()
        assert dec.material_changes[0]["route_meaning"] == au.routes[case["route"]]
        assert dec.uncertainty["access_verdict"] == case["access_class"]
        # DLT-to-Market established only when a benchmark exists (national qualifying vs not).
        established = dec.decision_lead_time["external_lead_time_established"]
        assert established is case["expect_qualifying"]
        if established:
            qualifying += 1
    # The corpus's qualifying subset exercised the DLT engine (as in the accepted replay design).
    assert qualifying == 3


def test_nz_replay_runs_through_shared_kernel():
    nz = get_domain("NZ")
    corpus = json.loads(NZ_CORPUS.read_text())
    assert corpus["domain"] == "NZ"
    # GETS must never appear as a source in the NZ replay corpus.
    assert all(case["source_id"] != "nz_gets" for case in corpus["cases"])
    qualifying = 0
    for case in corpus["cases"]:
        ev = NationalEvidence(
            evidence_id=case["evidence_id"], source_id=case["source_id"],
            available_at=case["available_at"], lifecycle_stage=case["lifecycle_stage"],
            route=case["route"])
        mc = derive_material_change_fixture(
            nz, ev, as_of="2024-01-01", important_miss_kind=case["important_miss_kind"],
            mc_id=case["case_id"])
        # NZ national meaning preserved on the change (route/stage/miss are NZ truth).
        assert mc.route == case["route"] and nz.known_route(mc.route)
        assert mc.lifecycle_stage in nz.lifecycle
        assert mc.important_miss_kind in nz.important_miss
        acc = assess_access(nz, access_class=case["access_class"],
                            industrial_position=case["industrial_position"])
        opp = NationalOpportunity(material_change=mc, access=acc, customer_id="eval-nz")
        a = case["anchors"]
        anchors = TemporalAnchors(t0_source_available_at=a["t0"], t1_acquired_at=a["t1"],
                                  t4_customer_ready_at=a["t4"], benchmark_b=a["benchmark_b"])
        dec = to_decision(nz, opp, anchors=anchors, as_of="2024-01-01")
        assert dec.material_changes[0]["route_meaning"] == nz.routes[case["route"]]
        assert dec.uncertainty["access_verdict"] == case["access_class"]
        established = dec.decision_lead_time["external_lead_time_established"]
        assert established is case["expect_qualifying"]
        if established:
            qualifying += 1
    # Five corpus cases carry a benchmark and exercise the shared DLT engine; the cancellation does not.
    assert qualifying == 5


def test_uk_replay_runs_through_shared_kernel_without_numeric_dlt_gate():
    uk = get_domain("GB")
    corpus = json.loads(UK_CORPUS.read_text())
    assert corpus["domain"] == "GB"
    materialized = 0
    for case in corpus["cases"]:
        if case["source_id"] == "uk_ssro":
            continue  # DECLARED source — exercised as a rights block elsewhere, not through the DLT engine
        ev = NationalEvidence(
            evidence_id=case["evidence_id"], source_id=case["source_id"],
            available_at=case["available_at"], lifecycle_stage=case["lifecycle_stage"], route=case["route"])
        mc = derive_material_change_fixture(
            uk, ev, as_of="2024-01-01", mc_id=case["case_id"],
            consequential_change_kind=case["consequential_change_kind"], sscr_qdc=case["sscr_qdc"])
        assert mc.route == case["route"] and uk.known_route(mc.route)
        assert mc.lifecycle_stage in uk.lifecycle
        assert uk.known_consequential_state(mc.consequential_change_kind)
        acc = assess_access(uk, access_class=case["access_class"], industrial_position=case["industrial_position"])
        opp = NationalOpportunity(material_change=mc, access=acc, customer_id="eval-uk")
        a = case["anchors"]
        anchors = TemporalAnchors(t0_source_available_at=a["t0"], t1_acquired_at=a["t1"],
                                  t4_customer_ready_at=a["t4"], benchmark_b=a["benchmark_b"])
        dec = to_decision(uk, opp, anchors=anchors, as_of="2024-01-01")
        # DLT is recorded as an ATTRIBUTE where a benchmark exists — but it is NEVER a UK acceptance gate:
        # zero-DLT cases (post-award, framework, international) still project as valid opportunities.
        assert dec.decision_lead_time["external_lead_time_established"] is case["expect_qualifying"]
        assert dec.material_changes[0]["route_meaning"] == uk.routes[case["route"]]
        materialized += 1
    assert materialized == 8  # 8 OGL-backed cases run through the shared kernel; SSRO case is blocked
    # No UK numeric DLT threshold exists to gate on.
    assert uk.dlt_calibration is None


def test_strict_as_of_blocks_future_evidence():
    au = get_domain("AU")
    future = NationalEvidence("f", "au_austender", "2099-01-01", "EVALUATION", "OPEN")
    with pytest.raises(ASOFViolation):
        derive_material_change_fixture(au, future, as_of="2024-01-01")


def test_au_calibration_is_the_cited_accepted_result():
    au = get_domain("AU")
    cal = au.dlt_calibration
    assert cal.median_dlt_to_market_days == 654.5 and cal.p25_days == 105.0
    assert cal.corpus_size == 44 and cal.qualifying_cases == 24
    assert "PYRNOVA-AU-SPEC-001" in cal.source_reference


def test_nz_calibration_is_the_cited_accepted_result_and_not_inflated():
    nz = get_domain("NZ")
    assert nz.validated is True and nz.build_authority is True
    cal = nz.dlt_calibration
    # The CITED accepted NZ historical validation numbers — not invented, not inflated.
    assert cal.median_dlt_to_market_days == 491.0 and cal.p25_days == 292.0
    assert cal.corpus_size == 36 and cal.qualifying_cases == 17
    assert "PYRNOVA-NZ-SPEC-001" in cal.source_reference


def test_nz_national_truth_is_distinct_not_flattened_into_au():
    nz, au = get_domain("NZ"), get_domain("AU")
    # NZ routes are NZ meanings, not AU's — DIRECT_SOURCE and PANEL are NZ-specific, FMS is not an NZ route.
    assert nz.known_route("DIRECT_SOURCE") and nz.known_route("PANEL")
    assert not nz.known_route("FMS")
    # Thin Prime is an ACCESS class only — never an Industrial Position.
    assert "THIN_PRIME" in nz.access_classes
    assert "THIN_PRIME" not in nz.industrial_position_classes
    # economic benefit != sovereign capability != resilience (three distinct Industrial Positions).
    for ip in ("ECONOMIC_BENEFIT", "SOVEREIGN_CAPABILITY", "RESILIENCE_RELEVANT"):
        assert ip in nz.industrial_position_classes
    # NZ lifecycle is its own, not AU's.
    assert nz.lifecycle != au.lifecycle


def test_nz_source_families_codified_fail_closed_except_replay_evidence():
    nz = get_domain("NZ")
    # GETS is the hard lock.
    assert nz.source("nz_gets").activation is SourceActivation.PROHIBITED
    # Only the lawful historical/replay evidence family is FIXTURE_ONLY (replay-derived, live NOT active).
    assert nz.source("nz_mod").activation is SourceActivation.FIXTURE_ONLY
    assert nz.is_ingestible("nz_mod") is False  # FIXTURE_ONLY is not live-ingestible
    # Every civil/caution candidate family is DECLARED (UNKNOWN => DENY) — not activated by history alone.
    for sid in ("nz_treasury", "nz_linz", "nz_greater_wellington", "nz_police", "nz_nzta"):
        assert nz.source(sid).activation is SourceActivation.DECLARED
        assert nz.is_ingestible(sid) is False
