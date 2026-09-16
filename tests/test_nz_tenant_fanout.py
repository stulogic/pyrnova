"""NZ tenant fan-out (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, NZ vertical, boundary A).

Proves the New Zealand national chain enters the SHARED per-tenant customer machinery without a country
fork and without importing US or AU semantics: an NZ NationalOpportunity projects into the shared
``opportunities`` stream, fans out deterministically to the NZ customer only, persists a customer-scoped
Material Change carrying NZ national truth (incl. Thin Prime access + NZD value), and honours AS-OF,
source-rights (UNKNOWN => DENY; GETS PROHIBITED), tenant isolation, idempotency, and
progression/reversal/cancellation propagation.
"""

from __future__ import annotations

import pytest

from pyrnova import customer_material_changes as cmc
from pyrnova.customer_material_changes import fan_out, _latest_versions
from pyrnova.customers import CustomerProfile, upsert_customer
from pyrnova.domains import get_domain
from pyrnova.domains.base import ProhibitedSourceIngestion
from pyrnova.domains.fanout import build_national_opportunity_record, national_value_block
from pyrnova.domains.pipeline import (
    ASOFViolation, NationalEvidence, NationalOpportunity, assess_access,
    derive_material_change_fixture,
)
from pyrnova.material_changes import build_material_changes
from pyrnova.state import StateStore

AS_OF = "2024-01-01"
EVAL = "eval-nz"
EVAL_REF = "co_eval_nz"


def _nz_opp_record(*, important_miss="PROGRESSION", lifecycle="EVALUATION", route="CLOSED",
                   access_class="THIN_PRIME", industrial="ECONOMIC_BENEFIT", mc_id="nz-mc-eval-001"):
    nz = get_domain("NZ")
    ev = NationalEvidence(
        "nz-ev-eval-001", "nz_mod", "2020-08-15", lifecycle, route,
        payload={"source_ref": "nz:nz_mod:EVAL-001", "archive_uri": "examples/nz_replay/eval_001.json"})
    mc = derive_material_change_fixture(nz, ev, as_of=AS_OF, important_miss_kind=important_miss, mc_id=mc_id)
    acc = assess_access(nz, access_class=access_class, industrial_position=industrial)
    opp = NationalOpportunity(mc, acc, EVAL)
    return nz, build_national_opportunity_record(
        nz, opp, evidence=[ev], subject_ref=EVAL_REF, subject_name="Evaluation Target NZ",
        title="NZ evaluation acquisition", as_of=AS_OF,
        value=national_value_block(120_000_000.0, "NZD"))


def _seed_eval_customer(store):
    upsert_customer(store, CustomerProfile(
        customer_id=EVAL, name="Evaluation Target NZ", entity_refs=[EVAL_REF],
        provenance="internal_evaluation", effective_from="2019-01-01T00:00:00+00:00",
        created_at="2019-01-01T00:00:00+00:00", updated_at="2019-01-01T00:00:00+00:00"))
    # A second tenant that must NOT receive the NZ record.
    upsert_customer(store, CustomerProfile(
        customer_id="other-nz", name="Other Tenant", entity_refs=["co_other_nz"],
        provenance="internal_evaluation", effective_from="2019-01-01T00:00:00+00:00",
        created_at="2019-01-01T00:00:00+00:00", updated_at="2019-01-01T00:00:00+00:00"))


def test_bridge_record_carries_nz_truth_without_us_or_au_assumptions():
    nz, rec = _nz_opp_record()
    nat = rec["meta"]["national"]
    assert nat["domain"] == "NZ"
    assert nat["route"] == "CLOSED" and nat["route_meaning"].startswith("Closed")
    assert nat["lifecycle_stage"] == "EVALUATION"
    assert nat["access_class"] == "THIN_PRIME"          # NZ-specific access class
    assert nat["industrial_position"] == "ECONOMIC_BENEFIT"
    assert nat["value_local"] == {"amount": 120_000_000.0, "currency": "NZD"}
    # No US semantic assumptions imported.
    assert rec["value_usd"] is None and rec["incumbent"] is None
    assert rec["customer_id"] == EVAL
    assert rec["meta"]["evidence_sources"] == ["nz_mod"]


def test_nz_record_fans_out_to_nz_customer_only_with_national_truth(tmp_path):
    store = StateStore(tmp_path / "state")
    _seed_eval_customer(store)
    _nz, rec = _nz_opp_record()
    store.append("opportunities", rec)

    report = fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    assert report["inserted"] == 1

    eval_rows = _latest_versions(store, EVAL)
    other_rows = _latest_versions(store, "other-nz")
    assert list(eval_rows) == [rec["id"]]          # NZ customer got it
    assert other_rows == {}                          # tenant isolation: nobody else did

    stored = eval_rows[rec["id"]]
    assert stored["national"]["domain"] == "NZ"
    assert stored["national"]["route"] == "CLOSED"
    assert stored["national"]["access_class"] == "THIN_PRIME"

    # Idempotent: re-running with unchanged truth writes nothing.
    report2 = fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    assert report2["inserted"] == 0 and report2["duplicates_suppressed"] == 1


def test_read_model_projects_nz_national_truth(tmp_path):
    nz, rec = _nz_opp_record(route="OPEN", important_miss="PROGRESSION", access_class="INCUMBENT",
                             industrial="SOVEREIGN_CAPABILITY")
    from pyrnova.material_changes import CustomerContext
    ctx = CustomerContext(customer_id=EVAL, name="Evaluation Target NZ", entity_refs=[EVAL_REF])
    projected = build_material_changes(opportunities=[rec], context=ctx)
    assert len(projected) == 1
    p = projected[0]
    assert p["disposition"] == "OPPORTUNITY"
    assert p["national"]["route_meaning"].startswith("Open")
    assert p["national"]["access_class"] == "INCUMBENT"


def test_source_rights_fail_closed_for_declared_and_prohibited():
    nz = get_domain("NZ")
    # A DECLARED NZ source (UNKNOWN => DENY) cannot back a projection.
    ev = NationalEvidence("nz-ev-x", "nz_treasury", "2020-01-01", "EVALUATION", "OPEN")
    mc = derive_material_change_fixture(nz, ev, as_of=AS_OF, mc_id="nz-mc-x")
    acc = assess_access(nz, access_class="PANEL_MEMBER", industrial_position="ECONOMIC_BENEFIT")
    with pytest.raises(PermissionError):
        build_national_opportunity_record(nz, NationalOpportunity(mc, acc, EVAL), evidence=[ev],
                                          subject_ref=EVAL_REF, subject_name="x", title="x", as_of=AS_OF)
    # GETS is a hard lock — the fixture/replay path itself refuses it.
    gets_ev = NationalEvidence("nz-ev-gets", "nz_gets", "2020-01-01", "AWARD", "OPEN")
    with pytest.raises(ProhibitedSourceIngestion):
        derive_material_change_fixture(nz, gets_ev, as_of=AS_OF, mc_id="nz-mc-gets")


def test_asof_integrity_refuses_future_evidence():
    nz = get_domain("NZ")
    ev = NationalEvidence("nz-ev-future", "nz_mod", "2025-06-01", "EVALUATION", "OPEN",
                          payload={"source_ref": "nz:nz_mod:FUT"})
    mc = derive_material_change_fixture(nz, ev, as_of=None, mc_id="nz-mc-fut")
    acc = assess_access(nz, access_class="PANEL_MEMBER", industrial_position="ECONOMIC_BENEFIT")
    with pytest.raises(ASOFViolation):
        build_national_opportunity_record(nz, NationalOpportunity(mc, acc, EVAL), evidence=[ev],
                                          subject_ref=EVAL_REF, subject_name="x", title="x",
                                          as_of="2024-01-01")


def test_progression_creates_new_version_and_cancellation_downgrades(tmp_path):
    store = StateStore(tmp_path / "state")
    _seed_eval_customer(store)

    # v1: live EVALUATION opportunity.
    _nz, rec1 = _nz_opp_record(lifecycle="EVALUATION", important_miss="PROGRESSION")
    store.append("opportunities", rec1)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v1 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v1["content_version"] == 1 and v1["disposition"] == "OPPORTUNITY"

    # Progression: same national material change advances to AWARD — new version.
    _nz, rec2 = _nz_opp_record(lifecycle="AWARD", important_miss="PROGRESSION")
    assert rec2["id"] == rec1["id"]  # stable identity across progression
    store.append("opportunities", rec2)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v2 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v2["content_version"] == 2
    assert v2["national"]["lifecycle_stage"] == "AWARD"
    assert v2["change_kind"] == cmc.CHANGE_ASSESSMENT

    # Reversal/cancellation: downgrades the opportunity to monitoring (closed pursuit).
    _nz, rec3 = _nz_opp_record(lifecycle="AWARD", important_miss="CANCELLATION")
    store.append("opportunities", rec3)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v3 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v3["content_version"] == 3
    assert v3["disposition"] == "MONITORING"  # cancelled => not a live opportunity
