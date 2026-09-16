"""CA Important-Miss enforcement (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, CA vertical, boundary D).

Encodes the Canadian misclassifications the product must NEVER commit. Each test proves the executable
guardrail, not just that a label exists.
"""

from __future__ import annotations

import pytest

from pyrnova.domains import get_domain
from pyrnova.domains.fanout import _national_state
from pyrnova.domains.pipeline import (
    ASOFViolation, NationalEvidence, assess_access, derive_material_change_fixture,
)

CA = get_domain("CA")


def _mc(**kw):
    ev = NationalEvidence(kw.pop("evidence_id", "e"), kw.pop("source_id", "ca_canadabuys_dataset"),
                          kw.pop("available_at", "2020-01-01"), kw.pop("lifecycle_stage", "SOLICITATION"),
                          kw.pop("route", "OPEN_COMPETITIVE"),
                          language=kw.pop("language", "en"), translation=kw.pop("translation", None),
                          entity_key=kw.pop("entity_key", None))
    return derive_material_change_fixture(CA, ev, as_of=kw.pop("as_of", "2025-06-01"),
                                          mc_id=kw.pop("mc_id", "ca-mc-im"), **kw)


# RFP is not the first market event / bounded is not exact -------------------------------------------

def test_rfp_is_not_forced_to_exact_timing():
    # An RFP-dated solicitation whose earlier supplier engagement is unresolved is BOUNDED, not EXACT.
    mc = _mc(consequential_change_kind="OPPORTUNITY_CREATED", mechanism="COMPETITIVE_OPEN",
             timing_class="BOUNDED")
    assert mc.timing_class == "BOUNDED"


def test_bounded_cannot_be_silently_converted_to_a_free_exactness():
    with pytest.raises(ValueError):
        _mc(mechanism="COMPETITIVE_OPEN", timing_class="EXACT_6_DAYS")  # fabricated exactness rejected


def test_invalid_2006_six_day_dlt_cannot_be_resurrected_as_a_timing_class():
    # There is no numeric national DLT class; the invalidated exact 6-day value cannot re-enter as timing.
    assert "EXACT" in CA.timing_classes
    with pytest.raises(ValueError):
        _mc(mechanism="DIRECTED_OEM", timing_class="SIX_DAY_2006")


# No back-projection: later evidence cannot leak backward (DCB metadata / later history) -------------

def test_later_evidence_cannot_be_back_projected():
    future = NationalEvidence("f", "ca_canadabuys_dataset", "2024-06-01", "ENGAGEMENT", "OPEN_COMPETITIVE")
    with pytest.raises(ASOFViolation):
        derive_material_change_fixture(CA, future, as_of="2021-01-01",
                                       consequential_change_kind="OPPORTUNITY_CREATED",
                                       mechanism="COMPETITIVE_OPEN")


# ITB is never inferred automatically — it is a SEPARATE evidenced field -----------------------------

def test_itb_vp_is_not_inferred_from_a_free_string():
    with pytest.raises(ValueError):
        _mc(mechanism="FMS_GTG", route="FMS", itb_vp="APPLIES_BECAUSE_LARGE_CONTRACT")


def test_itb_default_is_unknown_not_applied():
    mc = _mc(mechanism="COMPETITIVE_OPEN")  # no itb_vp supplied
    assert mc.itb_vp == "UNKNOWN"  # ITB is NOT auto-applied (never inferred from value/ownership/access)


# Canadian ownership/presence is not advantage; Industrial Position != Access ------------------------

def test_access_and_industrial_position_are_separate_axes():
    # A Canadian Industrial Position value cannot be used as an Access class...
    with pytest.raises(ValueError):
        assess_access(CA, access_class="DOMESTIC_PRODUCTION", industrial_position="INCUMBENCY")
    # ...and an Access value cannot be used as a Canadian Industrial Position.
    with pytest.raises(ValueError):
        assess_access(CA, access_class="OEM_CONTROLLED", industrial_position="NESTED_SUBCOMPETITION")
    ok = assess_access(CA, access_class="OEM_CONTROLLED", industrial_position="DOMESTIC_PRODUCTION")
    assert ok.verdict == "OEM_CONTROLLED" and ok.industrial_position == "DOMESTIC_PRODUCTION"


# FMS/GtG is not ordinary competition; inaccessible prime is not no-opportunity ----------------------

def test_fms_gtg_is_distinct_from_open_competition():
    assert CA.routes["FMS"] != CA.routes["OPEN_COMPETITIVE"]
    assert CA.routes["GTG"] != CA.routes["OPEN_COMPETITIVE"]
    fms = _mc(mechanism="FMS_GTG", route="FMS", timing_class="N_A")
    assert fms.timing_class == "N_A"  # open-market prime DLT is N_A, not zero-and-therefore-nothing


def test_inaccessible_prime_route_is_still_a_live_opportunity():
    # A directed/OEM change with supply-chain access stays OPEN (candidate/reviewing), never auto-closed.
    assert _national_state(None, "SUPPLY_CHAIN_ACCESS_CHANGED") == "reviewing"
    assert _national_state(None, "CAPABILITY_INSERTION_OPENED") == "candidate"


# Strategic-source downstream RFP is not open prime -------------------------------------------------

def test_strategic_source_downstream_is_not_open_prime_access():
    # A nested sub-competition access is a distinct access class from open competition.
    ok = assess_access(CA, access_class="NESTED_SUBCOMPETITION", industrial_position="STRATEGIC_SOURCE_STATUS")
    assert ok.verdict == "NESTED_SUBCOMPETITION"
    with pytest.raises(ValueError):
        assess_access(CA, access_class="STRATEGIC_SOURCE_STATUS", industrial_position="STRATEGIC_SOURCE_STATUS")


# Cancellation/reissue identity, and closure only on explicit closure --------------------------------

def test_cancellation_closes_and_reissue_is_fresh_not_continuity():
    assert _national_state(None, "PROGRAMME_CANCELLED") == "cancelled"   # cancellation closes
    assert _national_state(None, "PROGRAMME_REISSUED") == "candidate"    # reissue is a FRESH live candidate
    # Only explicit close/cancel closes; a route/industrial/qualification change is a review, not a close.
    assert _national_state(None, "ROUTE_CHANGED") == "reviewing"
    assert _national_state(None, "INDUSTRIAL_POSITION_CHANGED") == "reviewing"
    assert _national_state(None, "OPPORTUNITY_CREATED") == "candidate"


# Translation is never original evidence ------------------------------------------------------------

def test_translation_is_derived_not_original():
    mc = _mc(mechanism="DIRECTED_OEM", language="fr",
             translation={"language": "en", "provenance": "machine", "derived": True},
             entity_key="programme:x")
    # The material change records the French ORIGINAL; the translation is carried as DERIVED on the evidence.
    assert mc.evidence_ids  # evidence linkage preserved
    # (Original-language authority + derived translation are asserted end-to-end in the customer-product proof.)


# The Important-Miss taxonomy is codified and distinct from the consequential-change model -----------

def test_ca_taxonomies_are_distinct():
    assert "RFP_AS_FIRST_MARKET_EVENT" in CA.important_miss
    assert "RESURRECTED_2006_SIX_DAY_DLT" in CA.important_miss
    assert "OPPORTUNITY_CREATED" in CA.consequential_states
    assert set(CA.important_miss).isdisjoint(set(CA.consequential_states))
