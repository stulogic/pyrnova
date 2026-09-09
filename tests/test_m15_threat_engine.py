"""M15 — threat engine: mechanisms, severity/confidence separation, zero-threat, duality,
company surface, outcome linkage, and temporal replay."""

from __future__ import annotations

import pytest

from pyrnova import threat
from pyrnova.models import Exposure
from pyrnova.sources import ofac


DESIGNATIONS = ofac.parse_ofac_csv(
    open("tests/fixtures/ofac_sdn_sample.csv", "rb").read(), list_name="sdn"
)


def _incumbency(program="prog:x", amount=30_000_000, as_of=None):
    awards = [{"source_ref": "usa:a", "available_at": "2020-01-01", "recipient_uei": "UEI123",
               "program_key": program, "program_name": "Program X", "amount_usd": amount,
               "agency": "Army"}]
    return threat.incumbency_exposures("co_sub", "Sub", "UEI123", awards, as_of=as_of)


# ---------------------------------------------------------------- sanctions mechanism

def test_sanctions_confirmed_exposure_emits_active_threat():
    recs = [{"source_ref": "sam:1", "available_at": "2023-01-01", "relation": "SUPPLIER",
             "counterparty_name": "Global Defense Supply LLC", "counterparty_ofac_ent_num": 10002}]
    exposures, weak = threat.sanctions_exposures("co_a", "Acme", recs, DESIGNATIONS)
    threats, rej = threat.assess_threats("co_a", "Acme", exposures, [], weak_candidates=weak)
    assert len(threats) == 1
    t = threats[0]
    assert t.mechanism == "SANCTIONS_EXPOSURE"
    assert t.status == "ACTIVE"
    assert t.confidence == "HIGH"          # deterministic identifier
    assert t.severity == "HIGH"            # supplier dependency
    assert t.horizon == "IMMEDIATE"
    assert t.falsifiers and any(f["fatal"] for f in t.falsifiers)
    assert t.id == threat.threat_id("co_a", "SANCTIONS_EXPOSURE", t.exposure_ids and
                                    exposures[0].target_ref)


def test_weak_name_match_is_rejected_not_a_threat():
    recs = [{"source_ref": "r", "available_at": "2023-01-01", "relation": "CUSTOMER",
             "counterparty_name": "Northstar Logistics of Ohio"}]
    exposures, weak = threat.sanctions_exposures("co_b", "B", recs, DESIGNATIONS)
    threats, rej = threat.assess_threats("co_b", "B", exposures, [], weak_candidates=weak)
    assert threats == []
    assert len(rej) == 1 and rej[0].reason_code == "WEAK_NAME_MATCH_ONLY"


def test_sanctions_unknown_when_no_linkage():
    recs = [{"source_ref": "r", "available_at": "2023-01-01", "relation": "SUPPLIER",
             "counterparty_name": "Perfectly Ordinary Widgets"}]
    exposures, weak = threat.sanctions_exposures("co_c", "C", recs, DESIGNATIONS)
    threats, rej = threat.assess_threats("co_c", "C", exposures, [], weak_candidates=weak)
    assert threats == [] and rej == []     # no exposure, no false alarm


# ---------------------------------------------------------------- incumbent displacement

def test_recompete_alone_is_not_a_threat():
    exps = _incumbency()
    recs = [{"catalyst_kind": "recompete", "program_key": "prog:x", "available_at": "2024-01-01",
             "source_ref": "sam:rc"}]
    threats, rej = threat.assess_threats("co_sub", "Sub", exps, recs)
    assert threats == []
    assert rej and rej[0].reason_code == "RECOMPETE_NOT_A_THREAT"


def test_recompete_with_displacement_signal_is_a_threat():
    exps = _incumbency(amount=30_000_000)
    recs = [{"catalyst_kind": "recompete", "program_key": "prog:x", "available_at": "2024-01-01",
             "source_ref": "sam:rc", "displacement_signal": "set_aside_change", "evidence_strength": 4}]
    threats, rej = threat.assess_threats("co_sub", "Sub", exps, recs)
    assert len(threats) == 1
    t = threats[0]
    assert t.mechanism == "INCUMBENT_DISPLACEMENT"
    assert t.severity == "HIGH"          # $30M contract
    assert t.affected_value_category == "CONTRACT_POSITION"


def test_recompete_on_unheld_program_is_no_exposure():
    exps = _incumbency(program="prog:x")
    recs = [{"catalyst_kind": "recompete", "program_key": "prog:OTHER", "available_at": "2024-01-01",
             "source_ref": "s", "displacement_signal": "named_competitor"}]
    threats, rej = threat.assess_threats("co_sub", "Sub", exps, recs)
    assert threats == [] and rej[0].reason_code == "NO_EXPOSURE"


# ---------------------------------------------------------------- program contraction / cancellation

def test_program_cancellation_threat_and_severity_band():
    exps = _incumbency(program="prog:y", amount=8_000_000)
    # PROGRAM exposure exists (incumbency also builds a PROGRAM edge).
    recs = [{"catalyst_kind": "program_cancellation", "program_key": "prog:y",
             "available_at": "2024-06-01", "source_ref": "fr:cancel", "amount_delta_usd": 8_000_000}]
    threats, rej = threat.assess_threats("co_sub", "Sub", exps, recs)
    cancel = [t for t in threats if t.mechanism == "PROGRAM_CANCELLATION_OR_DELAY"]
    assert cancel and cancel[0].severity == "MODERATE"   # $8M band
    assert cancel[0].affected_value_category == "CONTINUITY"


# ---------------------------------------------------------------- severity vs confidence are distinct

def test_severity_and_confidence_are_orthogonal():
    # High-value program (severity HIGH) but only an INFERRED exposure with thin catalyst (confidence LOW).
    exp = Exposure(subject_ref="co_d", subject_name="D", relation_type="PROGRAM",
                   target_ref="prog:z", target_name="Z", join_method="inferred_strong_attribute",
                   link_class="INFERRED", confidence=0.6, available_at="2024-01-01",
                   meta={"amount_usd": 200_000_000})
    exp.id = threat.exposure_id("co_d", "PROGRAM", "prog:z")
    recs = [{"catalyst_kind": "funding_reduction", "program_key": "prog:z", "available_at": "2024-02-01",
             "source_ref": "b", "amount_delta_usd": 200_000_000, "evidence_strength": 1}]
    threats, _ = threat.assess_threats("co_d", "D", [exp], recs)
    assert len(threats) == 1
    assert threats[0].severity == "CRITICAL"   # magnitude band
    assert threats[0].confidence == "LOW"      # weak evidence
    assert threats[0].severity != threats[0].confidence  # never collapsed


# ---------------------------------------------------------------- regulatory / eligibility + duality

def test_regulatory_eligibility_threat_with_dual_opportunity():
    exps = threat.declared_exposures("co_e", "E", [
        {"relation": "CERTIFICATION", "target_ref": "cert:cmmc", "target_name": "CMMC L2",
         "available_at": "2024-01-01", "source_ref": "sam:cert"}])
    recs = [{"catalyst_kind": "regulatory_mandate", "target_ref": "cert:cmmc",
             "available_at": "2024-03-01", "source_ref": "fr:cmmc", "eligibility_gated": True,
             "catalyst_id": "cat_shared", "summary": "CMMC mandate"}]
    threats, rej = threat.assess_threats("co_e", "E", exps, recs)
    assert len(threats) == 1
    t = threats[0]
    assert t.mechanism == "ELIGIBILITY_OR_CERTIFICATION_RISK"
    assert t.affected_value_category == "ELIGIBILITY"
    # duality: an opportunity (compliance vendor) sharing the same catalyst gets cross-linked
    opps = [{"id": "cons_vendor", "catalyst_id": "cat_shared"}]
    assert threat.link_duality(threats, opps) == 1
    assert t.dual_opportunity_ref == "cons_vendor"


# ---------------------------------------------------------------- company threat surface

def test_company_threat_surface_groups_by_mechanism_and_severity():
    exps = _incumbency(amount=30_000_000)
    recs = [{"catalyst_kind": "recompete", "program_key": "prog:x", "available_at": "2024-01-01",
             "source_ref": "s", "displacement_signal": "protest", "evidence_strength": 4}]
    threats, _ = threat.assess_threats("co_sub", "Sub", exps, recs)
    surface = threat.company_threat_surface("co_sub", threats)
    assert surface["active_threat_count"] == 1
    assert surface["by_mechanism"]["INCUMBENT_DISPLACEMENT"] == 1
    assert surface["by_severity"]["HIGH"] == 1


# ---------------------------------------------------------------- outcome linkage

def test_threat_outcome_resolution_and_future_exclusion():
    obs = [threat.threat_outcome_observation("thr_1", "MATERIALIZED", "2025-01-01", "usa", "usa:award:x",
                                             evidence_strength=4)]
    resolved = threat.resolve_threat_outcome(obs, as_of="2025-06-01")
    assert resolved["label"] == "MATERIALIZED"
    # As of a date before the observation, it is UNKNOWN — never inferred false alarm.
    early = threat.resolve_threat_outcome(obs, as_of="2024-06-01")
    assert early["label"] == "UNKNOWN" and early["future_excluded_count"] == 1
    assert early["false_alarm_inferred_from_absence"] is False


def test_negative_threat_outcome_needs_source():
    with pytest.raises(ValueError):
        threat.threat_outcome_observation("t", "FALSE_ALARM", "2025-01-01", "src", "", evidence_strength=1)


# ---------------------------------------------------------------- temporal replay of the threat itself

def test_threat_absent_before_catalyst_available():
    exps = _incumbency(amount=30_000_000, as_of="2024-01-01")
    recs = [{"catalyst_kind": "recompete", "program_key": "prog:x", "available_at": "2024-12-01",
             "source_ref": "s", "displacement_signal": "named_competitor"}]
    # As of before the recompete is knowable, no threat exists.
    threats_before, _ = threat.assess_threats("co_sub", "Sub", exps, recs, as_of="2024-06-01")
    assert threats_before == []
    # Once the catalyst is available, the threat emerges.
    threats_after, _ = threat.assess_threats("co_sub", "Sub", exps, recs, as_of="2025-01-01")
    assert len(threats_after) == 1
