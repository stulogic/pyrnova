"""UK tenant fan-out (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, UK vertical, boundary C).

Proves the UK national chain enters the SHARED per-tenant customer machinery without a country fork and
without importing US/AU/NZ semantics: a UK NationalOpportunity projects into the shared ``opportunities``
stream, fans out deterministically to the UK customer only, persists a customer-scoped Material Change
carrying UK national truth (consequential-change state, evidenced SSCR/QDC, prime vs supply-chain access,
post-award marker, GBP value), and honours AS-OF, source-rights (UNKNOWN => DENY), tenant isolation,
idempotency, and progression / access-change / prime-change / post-award / closure propagation.
"""

from __future__ import annotations

import pytest

from pyrnova import customer_material_changes as cmc
from pyrnova.customer_material_changes import fan_out, _latest_versions
from pyrnova.customers import CustomerProfile, upsert_customer
from pyrnova.domains import get_domain
from pyrnova.domains.fanout import build_national_opportunity_record, national_value_block
from pyrnova.domains.pipeline import (
    ASOFViolation, NationalEvidence, NationalOpportunity, assess_access, derive_material_change_fixture,
)
from pyrnova.material_changes import build_material_changes
from pyrnova.state import StateStore

AS_OF = "2024-01-01"
EVAL = "eval-uk"
EVAL_REF = "co_eval_uk"


def _uk_opp_record(*, consequential="OPPORTUNITY_CREATED", lifecycle="TENDER", route="COMPETITIVE_FLEXIBLE",
                   access_class="OPEN_COMPETITION", industrial="UK_BUILD_WORKSHARE", sscr_qdc="UNKNOWN",
                   mc_id="gb-mc-eval-001"):
    uk = get_domain("GB")
    ev = NationalEvidence(
        "gb-ev-eval-001", "uk_contracts_finder", "2020-08-15", lifecycle, route,
        payload={"source_ref": "uk:uk_contracts_finder:EVAL-001", "archive_uri": "examples/uk_replay/eval_001.json"})
    mc = derive_material_change_fixture(uk, ev, as_of=AS_OF, mc_id=mc_id,
                                        consequential_change_kind=consequential, sscr_qdc=sscr_qdc)
    acc = assess_access(uk, access_class=access_class, industrial_position=industrial)
    opp = NationalOpportunity(mc, acc, EVAL)
    return uk, build_national_opportunity_record(
        uk, opp, evidence=[ev], subject_ref=EVAL_REF, subject_name="Evaluation Target UK",
        title="UK evaluation acquisition", as_of=AS_OF, value=national_value_block(500_000_000.0, "GBP"))


def _seed_eval_customer(store):
    upsert_customer(store, CustomerProfile(
        customer_id=EVAL, name="Evaluation Target UK", entity_refs=[EVAL_REF],
        provenance="internal_evaluation", effective_from="2019-01-01T00:00:00+00:00",
        created_at="2019-01-01T00:00:00+00:00", updated_at="2019-01-01T00:00:00+00:00"))
    upsert_customer(store, CustomerProfile(
        customer_id="other-uk", name="Other Tenant", entity_refs=["co_other_uk"],
        provenance="internal_evaluation", effective_from="2019-01-01T00:00:00+00:00",
        created_at="2019-01-01T00:00:00+00:00", updated_at="2019-01-01T00:00:00+00:00"))


def test_bridge_record_carries_uk_truth_without_foreign_assumptions():
    uk, rec = _uk_opp_record(access_class="SUPPLY_CHAIN", sscr_qdc="UNKNOWN")
    nat = rec["meta"]["national"]
    assert nat["domain"] == "GB"
    assert nat["route"] == "COMPETITIVE_FLEXIBLE"
    assert nat["access_class"] == "SUPPLY_CHAIN"
    assert nat["industrial_position"] == "UK_BUILD_WORKSHARE"
    assert nat["consequential_change_kind"] == "OPPORTUNITY_CREATED"
    assert nat["sscr_qdc"] == "UNKNOWN"
    assert nat["value_local"] == {"amount": 500_000_000.0, "currency": "GBP"}
    assert rec["value_usd"] is None and rec["incumbent"] is None  # no US assumptions
    assert rec["meta"]["evidence_sources"] == ["uk_contracts_finder"]


def test_uk_record_fans_out_to_uk_customer_only(tmp_path):
    store = StateStore(tmp_path / "state")
    _seed_eval_customer(store)
    _uk, rec = _uk_opp_record()
    store.append("opportunities", rec)

    report = fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    assert report["inserted"] == 1
    assert list(_latest_versions(store, EVAL)) == [rec["id"]]
    assert _latest_versions(store, "other-uk") == {}  # tenant isolation

    report2 = fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    assert report2["inserted"] == 0 and report2["duplicates_suppressed"] == 1  # idempotent


def test_read_model_projects_uk_national_truth():
    uk, rec = _uk_opp_record(consequential="ACCESS_CHANGED", route="FRAMEWORK_CALLOFF",
                             access_class="FRAMEWORK_SUPPLIER", industrial="UK_PRIME")
    from pyrnova.material_changes import CustomerContext
    ctx = CustomerContext(customer_id=EVAL, name="Evaluation Target UK", entity_refs=[EVAL_REF])
    projected = build_material_changes(opportunities=[rec], context=ctx)
    assert len(projected) == 1
    p = projected[0]
    assert p["disposition"] == "OPPORTUNITY"  # ACCESS_CHANGED stays open (flagged review), not closed
    assert p["national"]["access_class"] == "FRAMEWORK_SUPPLIER"
    assert p["national"]["route_meaning"].startswith("Call-off")


def test_source_rights_fail_closed_for_declared_uk_source():
    uk = get_domain("GB")
    ev = NationalEvidence("gb-ev-x", "uk_dsp", "2020-01-01", "TENDER", "OPEN")
    mc = derive_material_change_fixture(uk, ev, as_of=AS_OF, mc_id="gb-mc-x",
                                        consequential_change_kind="OPPORTUNITY_CREATED")
    acc = assess_access(uk, access_class="OPEN_COMPETITION", industrial_position="UK_PRIME")
    with pytest.raises(PermissionError):
        build_national_opportunity_record(uk, NationalOpportunity(mc, acc, EVAL), evidence=[ev],
                                          subject_ref=EVAL_REF, subject_name="x", title="x", as_of=AS_OF)


def test_asof_integrity_refuses_future_evidence():
    uk = get_domain("GB")
    ev = NationalEvidence("gb-ev-future", "uk_contracts_finder", "2025-06-01", "TENDER", "OPEN",
                          payload={"source_ref": "uk:uk_contracts_finder:FUT"})
    mc = derive_material_change_fixture(uk, ev, as_of=None, mc_id="gb-mc-fut",
                                        consequential_change_kind="OPPORTUNITY_CREATED")
    acc = assess_access(uk, access_class="OPEN_COMPETITION", industrial_position="UK_PRIME")
    with pytest.raises(ASOFViolation):
        build_national_opportunity_record(uk, NationalOpportunity(mc, acc, EVAL), evidence=[ev],
                                          subject_ref=EVAL_REF, subject_name="x", title="x", as_of="2024-01-01")


def test_progression_versions_and_closure_downgrades(tmp_path):
    store = StateStore(tmp_path / "state")
    _seed_eval_customer(store)

    _uk, rec1 = _uk_opp_record(lifecycle="TENDER", consequential="OPPORTUNITY_CREATED")
    store.append("opportunities", rec1)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v1 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v1["content_version"] == 1 and v1["disposition"] == "OPPORTUNITY"

    # Post-award risk on the same programme — new version, still monitored (award not terminal).
    _uk, rec2 = _uk_opp_record(lifecycle="POST_AWARD_CHANGE", consequential="POST_AWARD_RISK_INCREASED")
    assert rec2["id"] == rec1["id"]
    store.append("opportunities", rec2)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v2 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v2["content_version"] == 2 and v2["disposition"] == "OPPORTUNITY"  # not closed
    assert v2["national"]["post_award"] is True
    assert v2["change_kind"] == cmc.CHANGE_ASSESSMENT

    # Closure removes the opportunity.
    _uk, rec3 = _uk_opp_record(lifecycle="POST_AWARD_CHANGE", consequential="OPPORTUNITY_CLOSED")
    store.append("opportunities", rec3)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v3 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v3["content_version"] == 3 and v3["disposition"] == "MONITORING"
