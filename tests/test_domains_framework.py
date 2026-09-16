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


# --- 1. registry / boundary -----------------------------------------------------------------------

def test_registry_has_five_domains_only_us_and_au_operational():
    codes = {d.code for d in all_domains()}
    assert codes == {"US", "AU", "GB", "CA", "NZ"}
    assert {d.code for d in operational_domains()} == {"US", "AU"}  # validated AND build authority
    assert get_domain("uk").code == "GB"  # alias, case-insensitive


def test_unvalidated_domain_may_not_carry_fabricated_calibration():
    for code in ("GB", "CA"):
        d = get_domain(code)
        assert d.validated is False and d.dlt_calibration is None and d.build_authority is False


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
