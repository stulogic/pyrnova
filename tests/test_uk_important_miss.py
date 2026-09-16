"""UK Important-Miss enforcement (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, UK vertical, boundary D).

Encodes UK-SPEC-001 v1.1 §10: the misclassifications the UK product must NEVER commit. Each test proves the
executable guardrail, not just that a label exists.
"""

from __future__ import annotations

import pytest

from pyrnova.domains import get_domain
from pyrnova.domains.fanout import _national_state
from pyrnova.domains.pipeline import (
    ASOFViolation, NationalEvidence, assess_access, derive_material_change_fixture,
)

UK = get_domain("GB")


def _mc(route, *, consequential=None, sscr_qdc="UNKNOWN", lifecycle="TENDER", stage_ok=True):
    ev = NationalEvidence("e", "uk_contracts_finder", "2020-01-01", lifecycle, route)
    return derive_material_change_fixture(UK, ev, as_of="2024-01-01", mc_id="gb-mc-im",
                                          consequential_change_kind=consequential, sscr_qdc=sscr_qdc)


# §10: direct award mistaken for QDC ----------------------------------------------------------------

def test_direct_award_never_derives_qdc():
    mc = _mc("DIRECT_AWARD", consequential="OPPORTUNITY_NARROWED")
    assert mc.sscr_qdc == "UNKNOWN"  # route DIRECT_AWARD does NOT set QDC


def test_single_source_never_derives_qdc():
    mc = _mc("SINGLE_SOURCE", consequential="OPPORTUNITY_NARROWED")
    assert mc.sscr_qdc == "UNKNOWN"  # single source does NOT automatically imply QDC


def test_qdc_value_must_be_a_reviewed_evidenced_value():
    with pytest.raises(ValueError):
        _mc("SINGLE_SOURCE", consequential="OPPORTUNITY_NARROWED", sscr_qdc="DERIVED_FROM_ROUTE")


# §10: award treated as terminal --------------------------------------------------------------------

def test_award_is_not_terminal_post_award_stays_monitored():
    # A post-award risk change must NOT map to a closed/cancelled disposition.
    assert _national_state(None, "POST_AWARD_RISK_INCREASED") == "reviewing"
    assert _national_state(None, "CAPABILITY_INSERTION_OPENED") == "candidate"


# §10: prime route mistaken for total market closure ------------------------------------------------

def test_prime_change_is_not_market_closure():
    # Prime position change is a review event, never an automatic closure.
    assert _national_state(None, "PRIME_POSITION_CHANGED") == "reviewing"
    assert _national_state(None, "OPPORTUNITY_CLOSED") == "cancelled"  # only explicit closure closes


# §10: industrial importance mistaken for Access (Industrial Position != Access) ---------------------

def test_access_and_industrial_position_are_separate_axes():
    # An Industrial Position value cannot be used as an Access class...
    with pytest.raises(ValueError):
        assess_access(UK, access_class="UK_BUILD_WORKSHARE", industrial_position="UK_PRIME")
    # ...and an Access value cannot be used as an Industrial Position.
    with pytest.raises(ValueError):
        assess_access(UK, access_class="PRIME", industrial_position="SUPPLY_CHAIN")
    # The legitimate pairing is accepted.
    acc = assess_access(UK, access_class="SUPPLY_CHAIN", industrial_position="UK_BUILD_WORKSHARE")
    assert acc.verdict == "SUPPLY_CHAIN" and acc.industrial_position == "UK_BUILD_WORKSHARE"


# §10: later webpage content projected backward (mutable GOV.UK) ------------------------------------

def test_mutable_page_cannot_be_back_projected():
    # Evidence dated after the point-in-time view is refused — a later page revision cannot leak backward.
    future = NationalEvidence("f", "uk_gov_uk", "2023-06-01", "TENDER", "OPEN")
    with pytest.raises(ASOFViolation):
        derive_material_change_fixture(UK, future, as_of="2022-01-01",
                                       consequential_change_kind="OPPORTUNITY_CREATED")


# §10: consequential-change / Important-Miss taxonomies are distinct and codified -------------------

def test_uk_taxonomies_are_distinct():
    # The failure taxonomy (§10) and the consequential-change state model (§2) are separate.
    assert "DIRECT_AWARD_AS_QDC" in UK.important_miss
    assert "AWARD_AS_TERMINAL" in UK.important_miss
    assert "OPPORTUNITY_CREATED" in UK.consequential_states
    assert set(UK.important_miss).isdisjoint(set(UK.consequential_states))
