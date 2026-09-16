"""CA tenant fan-out (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, CA vertical, boundary C).

Proves the Canadian national chain enters the SHARED per-tenant customer machinery without a country fork
and without importing US/AU/NZ/UK semantics: a CA NationalOpportunity projects into the shared
``opportunities`` stream, fans out deterministically to the Canadian customer only, persists a
customer-scoped Material Change carrying Canadian national truth (mechanism, QUALIFIED timing class,
evidenced ITB/VP, access vs Industrial Position, CAD value, bilingual provenance), and honours AS-OF,
source-rights (UNKNOWN => DENY), tenant isolation, idempotency, progression versioning, and
cancellation/reissue WITHOUT silent false continuity.
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
from pyrnova.material_changes import build_material_changes, CustomerContext
from pyrnova.state import StateStore

AS_OF = "2025-06-01"
EVAL = "eval-ca"
EVAL_REF = "co_eval_ca"


def _ca_opp_record(*, consequential="OPPORTUNITY_CREATED", lifecycle="SOLICITATION", route="OPEN_COMPETITIVE",
                   access_class="OPEN_COMPETITION", industrial="CANADIAN_SUPPLY_CHAIN",
                   mechanism="COMPETITIVE_OPEN", timing_class="EXACT", itb_vp="UNKNOWN",
                   language="en", translation=None, entity_key=None, mc_id="ca-mc-eval-001",
                   value_cad=500_000_000.0):
    ca = get_domain("CA")
    ev = NationalEvidence(
        "ca-ev-eval-001", "ca_canadabuys_dataset", "2020-08-15", lifecycle, route,
        language=language, translation=translation, entity_key=entity_key,
        payload={"source_ref": "ca:ca_canadabuys_dataset:EVAL-001",
                 "archive_uri": "examples/ca_replay/eval_001.json"})
    mc = derive_material_change_fixture(ca, ev, as_of=AS_OF, mc_id=mc_id,
                                        consequential_change_kind=consequential, mechanism=mechanism,
                                        timing_class=timing_class, itb_vp=itb_vp)
    acc = assess_access(ca, access_class=access_class, industrial_position=industrial)
    opp = NationalOpportunity(mc, acc, EVAL)
    return ca, build_national_opportunity_record(
        ca, opp, evidence=[ev], subject_ref=EVAL_REF, subject_name="Evaluation Target CA",
        title="CA evaluation acquisition", as_of=AS_OF,
        value=national_value_block(value_cad, "CAD") if value_cad else None)


def _seed_eval_customer(store):
    upsert_customer(store, CustomerProfile(
        customer_id=EVAL, name="Evaluation Target CA", entity_refs=[EVAL_REF],
        provenance="internal_evaluation", effective_from="2005-01-01T00:00:00+00:00",
        created_at="2005-01-01T00:00:00+00:00", updated_at="2005-01-01T00:00:00+00:00"))
    upsert_customer(store, CustomerProfile(
        customer_id="other-ca", name="Other Tenant", entity_refs=["co_other_ca"],
        provenance="internal_evaluation", effective_from="2005-01-01T00:00:00+00:00",
        created_at="2005-01-01T00:00:00+00:00", updated_at="2005-01-01T00:00:00+00:00"))


def test_bridge_record_carries_ca_truth_without_foreign_assumptions():
    ca, rec = _ca_opp_record(mechanism="FMS_GTG", route="FMS", access_class="GTG_CONSTRAINED",
                             timing_class="N_A", itb_vp="ITB_OBLIGATION_APPLIES", value_cad=None)
    nat = rec["meta"]["national"]
    assert nat["domain"] == "CA"
    assert nat["route"] == "FMS"
    assert nat["mechanism"] == "FMS_GTG"
    assert nat["timing_class"] == "N_A"          # open-market prime DLT N_A — never fabricated
    assert nat["itb_vp"] == "ITB_OBLIGATION_APPLIES"  # evidenced field; ITB applies to an FMS acquisition
    assert nat["access_class"] == "GTG_CONSTRAINED"
    assert nat["industrial_position"] == "CANADIAN_SUPPLY_CHAIN"
    assert rec["value_usd"] is None and rec["incumbent"] is None  # no US assumptions leaked
    assert rec["meta"]["evidence_sources"] == ["ca_canadabuys_dataset"]


def test_bilingual_evidence_rides_through_with_original_language_authority():
    ca, rec = _ca_opp_record(language="fr",
                             translation={"language": "en", "provenance": "machine", "derived": True},
                             entity_key="programme:eval")
    ev = rec["evidence"][0]
    assert ev["language"] == "fr"                       # original FR is authoritative
    assert ev["translation"]["derived"] is True         # translation is PYRNOVA DERIVED
    assert ev["entity_key"] == "programme:eval"


def test_ca_record_fans_out_to_ca_customer_only(tmp_path):
    store = StateStore(tmp_path / "state")
    _seed_eval_customer(store)
    _ca, rec = _ca_opp_record()
    store.append("opportunities", rec)

    report = fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    assert report["inserted"] == 1
    assert list(_latest_versions(store, EVAL)) == [rec["id"]]
    assert _latest_versions(store, "other-ca") == {}  # tenant isolation

    report2 = fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    assert report2["inserted"] == 0 and report2["duplicates_suppressed"] == 1  # idempotent


def test_read_model_projects_ca_national_truth():
    ca, rec = _ca_opp_record(consequential="SUPPLY_CHAIN_ACCESS_CHANGED", route="DIRECTED_OEM",
                             mechanism="DIRECTED_OEM", access_class="OEM_CONTROLLED",
                             industrial="DESIGN_AUTHORITY", timing_class="N_A")
    ctx = CustomerContext(customer_id=EVAL, name="Evaluation Target CA", entity_refs=[EVAL_REF])
    projected = build_material_changes(opportunities=[rec], context=ctx)
    assert len(projected) == 1
    p = projected[0]
    assert p["disposition"] == "OPPORTUNITY"  # supply-chain access change stays open (flagged review)
    assert p["national"]["mechanism"] == "DIRECTED_OEM"
    assert p["national"]["route_meaning"].startswith("Directed")


def test_source_rights_fail_closed_for_declared_ca_source():
    ca = get_domain("CA")
    ev = NationalEvidence("ca-ev-x", "ca_dcb", "2020-01-01", "FORECAST", "OPEN_COMPETITIVE")
    mc = derive_material_change_fixture(ca, ev, as_of=AS_OF, mc_id="ca-mc-x",
                                        consequential_change_kind="OPPORTUNITY_CREATED",
                                        mechanism="COMPETITIVE_OPEN")
    acc = assess_access(ca, access_class="OPEN_COMPETITION", industrial_position="UNKNOWN")
    with pytest.raises(PermissionError):
        build_national_opportunity_record(ca, NationalOpportunity(mc, acc, EVAL), evidence=[ev],
                                          subject_ref=EVAL_REF, subject_name="x", title="x", as_of=AS_OF)


def test_asof_integrity_refuses_future_evidence():
    ca = get_domain("CA")
    ev = NationalEvidence("ca-ev-future", "ca_canadabuys_dataset", "2026-06-01", "SOLICITATION",
                          "OPEN_COMPETITIVE", payload={"source_ref": "ca:ca_canadabuys_dataset:FUT"})
    mc = derive_material_change_fixture(ca, ev, as_of=None, mc_id="ca-mc-fut",
                                        consequential_change_kind="OPPORTUNITY_CREATED",
                                        mechanism="COMPETITIVE_OPEN")
    acc = assess_access(ca, access_class="OPEN_COMPETITION", industrial_position="UNKNOWN")
    with pytest.raises(ASOFViolation):
        build_national_opportunity_record(ca, NationalOpportunity(mc, acc, EVAL), evidence=[ev],
                                          subject_ref=EVAL_REF, subject_name="x", title="x", as_of=AS_OF)


def test_progression_versions_and_cancellation_downgrades(tmp_path):
    store = StateStore(tmp_path / "state")
    _seed_eval_customer(store)

    _ca, rec1 = _ca_opp_record(consequential="OPPORTUNITY_CREATED")
    store.append("opportunities", rec1)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v1 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v1["content_version"] == 1 and v1["disposition"] == "OPPORTUNITY"

    # A supply-chain access change on the same programme — new version, still monitored (open).
    _ca, rec2 = _ca_opp_record(consequential="SUPPLY_CHAIN_ACCESS_CHANGED")
    assert rec2["id"] == rec1["id"]
    store.append("opportunities", rec2)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v2 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v2["content_version"] == 2 and v2["disposition"] == "OPPORTUNITY"
    assert v2["change_kind"] == cmc.CHANGE_ASSESSMENT

    # Cancellation removes the opportunity.
    _ca, rec3 = _ca_opp_record(consequential="PROGRAMME_CANCELLED")
    store.append("opportunities", rec3)
    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    v3 = _latest_versions(store, EVAL)[rec1["id"]]
    assert v3["content_version"] == 3 and v3["disposition"] == "MONITORING"


def test_reissue_is_a_fresh_opportunity_not_silent_continuity(tmp_path):
    store = StateStore(tmp_path / "state")
    _seed_eval_customer(store)

    # Cancelled programme.
    _ca, cancelled = _ca_opp_record(consequential="PROGRAMME_CANCELLED", mc_id="ca-mc-msvs")
    store.append("opportunities", cancelled)
    # Reissue as a SUCCESSOR programme with its own identity (distinct mc_id / program_key).
    _ca, reissued = _ca_opp_record(consequential="PROGRAMME_REISSUED", mc_id="ca-mc-msvs-successor")
    store.append("opportunities", reissued)
    assert reissued["id"] != cancelled["id"]  # NO silent continuity — a fresh opportunity id
    assert reissued["program_key"] != cancelled["program_key"]

    fan_out(mc_store=store, customer_store=store, cmc_store=store)
    latest = _latest_versions(store, EVAL)
    assert latest[cancelled["id"]]["disposition"] == "MONITORING"   # cancelled downgraded
    assert latest[reissued["id"]]["disposition"] == "OPPORTUNITY"   # reissue is a fresh live candidate
