"""AU tenant fan-out (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, boundary A).

Proves the Australian national chain enters the SHARED per-tenant customer machinery without a country
fork and without importing US semantics: an AU NationalOpportunity projects into the shared
``opportunities`` stream, fans out deterministically to the AU customer only, persists a customer-scoped
Material Change carrying AU national truth, and honours AS-OF, source-rights (UNKNOWN => DENY), tenant
isolation, idempotency, and progression/reversal/cancellation propagation.
"""

from __future__ import annotations

import pytest

from pyrnova import customer_material_changes as cmc
from pyrnova.customer_material_changes import fan_out, _latest_versions
from pyrnova.customers import CustomerProfile, upsert_customer
from pyrnova.decision_lead_time import TemporalAnchors
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
EVAL = "eval-au"
EVAL_REF = "co_eval_au"


def _au_opp_record(*, important_miss="PROGRESSION", lifecycle="EVALUATION", route="OPEN",
                   access_class="PANEL_MEMBER", industrial="AIC_ALIGNED", mc_id="au-mc-eval-001"):
    au = get_domain("AU")
    ev = NationalEvidence(
        "au-ev-eval-001", "au_austender", "2020-08-15", lifecycle, route,
        payload={"source_ref": "austender:CN-EVAL-001", "archive_uri": "examples/au/replay/eval_001.json"})
    mc = derive_material_change_fixture(au, ev, as_of=AS_OF, important_miss_kind=important_miss, mc_id=mc_id)
    acc = assess_access(au, access_class=access_class, industrial_position=industrial)
    opp = NationalOpportunity(mc, acc, EVAL)
    return au, build_national_opportunity_record(
        au, opp, evidence=[ev], subject_ref=EVAL_REF, subject_name="Evaluation Target AU",
        title="AU evaluation acquisition", as_of=AS_OF,
        value=national_value_block(250_000_000.0, "AUD"))


def _seed_eval_customer(store):
    upsert_customer(store, CustomerProfile(
        customer_id=EVAL, name="Evaluation Target AU", entity_refs=[EVAL_REF],
        provenance="internal_evaluation", effective_from="2019-01-01T00:00:00+00:00",
        created_at="2019-01-01T00:00:00+00:00", updated_at="2019-01-01T00:00:00+00:00"))
    # A second tenant that must NOT receive the AU record.
    upsert_customer(store, CustomerProfile(
        customer_id="other-au", name="Other Tenant", entity_refs=["co_other"],
        provenance="internal_evaluation", effective_from="2019-01-01T00:00:00+00:00",
        created_at="2019-01-01T00:00:00+00:00", updated_at="2019-01-01T00:00:00+00:00"))


def test_bridge_record_carries_au_truth_without_us_assumptions():
    au, rec = _au_opp_record()
    nat = rec["meta"]["national"]
    assert nat["domain"] == "AU"
    assert nat["route"] == "OPEN" and nat["route_meaning"].startswith("Open approach")
    assert nat["lifecycle_stage"] == "EVALUATION"
    assert nat["access_class"] == "PANEL_MEMBER"
    assert nat["industrial_position"] == "AIC_ALIGNED"
    assert nat["value_local"] == {"amount": 250_000_000.0, "currency": "AUD"}
    # No US semantic assumptions imported.
    assert rec["value_usd"] is None and rec["incumbent"] is None
    assert rec["customer_id"] == EVAL
    assert rec["meta"]["evidence_sources"] == ["au_austender"]


def test_au_record_fans_out_to_au_customer_only_with_national_truth(tmp_path):
    store = StateStore(tmp_path / "state")
    _seed_eval_customer(store)
    _au, rec = _au_opp_record()
    store.append("opportunities", rec)

    report = fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    assert report["inserted"] == 1  # exactly one customer-scoped record materialized

    eval_rows = _latest_versions(store, EVAL)
    other_rows = _latest_versions(store, "other-au")
    assert list(eval_rows) == [rec["id"]]          # AU customer got it
    assert other_rows == {}                          # tenant isolation: nobody else did

    stored = eval_rows[rec["id"]]
    assert stored["national"]["domain"] == "AU"
    assert stored["national"]["route"] == "OPEN"
    assert stored["national"]["industrial_position"] == "AIC_ALIGNED"

    # Idempotent: re-running with unchanged truth writes nothing.
    report2 = fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    assert report2["inserted"] == 0 and report2["duplicates_suppressed"] == 1


def test_read_model_projects_au_national_truth(tmp_path):
    au, rec = _au_opp_record()
    from pyrnova.material_changes import CustomerContext
    ctx = CustomerContext(customer_id=EVAL, name="Evaluation Target AU", entity_refs=[EVAL_REF])
    projected = build_material_changes(opportunities=[rec], context=ctx)
    assert len(projected) == 1
    p = projected[0]
    assert p["disposition"] == "OPPORTUNITY"
    assert p["national"]["route_meaning"].startswith("Open approach")
    assert p["national"]["access_class"] == "PANEL_MEMBER"


def test_source_rights_fail_closed_for_declared_and_prohibited():
    au = get_domain("AU")
    # A DECLARED national source (UNKNOWN => DENY) cannot back a projection.
    ev = NationalEvidence("au-ev-x", "au_defence_iip", "2020-01-01", "EVALUATION", "OPEN")
    mc = derive_material_change_fixture(au, ev, as_of=AS_OF, mc_id="au-mc-x")
    acc = assess_access(au, access_class="PANEL_MEMBER", industrial_position="AIC_ALIGNED")
    with pytest.raises(PermissionError):
        build_national_opportunity_record(au, NationalOpportunity(mc, acc, EVAL), evidence=[ev],
                                          subject_ref=EVAL_REF, subject_name="x", title="x", as_of=AS_OF)


def test_asof_integrity_refuses_future_evidence():
    au = get_domain("AU")
    ev = NationalEvidence("au-ev-future", "au_austender", "2025-06-01", "EVALUATION", "OPEN",
                          payload={"source_ref": "austender:CN-FUT"})
    mc = derive_material_change_fixture(au, ev, as_of=None, mc_id="au-mc-fut")
    acc = assess_access(au, access_class="PANEL_MEMBER", industrial_position="AIC_ALIGNED")
    with pytest.raises(ASOFViolation):
        build_national_opportunity_record(au, NationalOpportunity(mc, acc, EVAL), evidence=[ev],
                                          subject_ref=EVAL_REF, subject_name="x", title="x",
                                          as_of="2024-01-01")


def test_progression_creates_new_version_and_cancellation_downgrades(tmp_path):
    store = StateStore(tmp_path / "state")
    _seed_eval_customer(store)

    # v1: live EVALUATION opportunity.
    _au, rec1 = _au_opp_record(lifecycle="EVALUATION", important_miss="PROGRESSION")
    store.append("opportunities", rec1)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v1 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v1["content_version"] == 1 and v1["disposition"] == "OPPORTUNITY"

    # Progression: same national material change advances to CONTRACT — new version.
    _au, rec2 = _au_opp_record(lifecycle="CONTRACT", important_miss="PROGRESSION")
    assert rec2["id"] == rec1["id"]  # stable identity across progression
    store.append("opportunities", rec2)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v2 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v2["content_version"] == 2
    assert v2["national"]["lifecycle_stage"] == "CONTRACT"
    assert v2["change_kind"] == cmc.CHANGE_ASSESSMENT

    # Reversal/cancellation: downgrades the opportunity to monitoring (closed pursuit).
    _au, rec3 = _au_opp_record(lifecycle="CONTRACT", important_miss="CANCELLATION")
    store.append("opportunities", rec3)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v3 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v3["content_version"] == 3
    assert v3["disposition"] == "MONITORING"  # cancelled => not a live opportunity
