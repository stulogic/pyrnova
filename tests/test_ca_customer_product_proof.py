"""CA customer-product proof (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, CA vertical, boundary C).

Proves the Canadian national domain reaches the SAME tenant-isolated customer product the US, AU, NZ and UK
use — Customer Lens, Opportunity list, Decision View (CA mechanism / route / access incl. OEM-controlled and
nested strategic-source / Canadian Industrial Position / QUALIFIED timing class / evidenced ITB-VP /
bilingual provenance), Evidence Inspector, AS-OF, uncertainty, Decision Memory, and brief download — with a
real replay-backed proof and NO Canada frontend fork. Uses the accepted Canadian replay corpus via the
internal evaluation lens (no real customer, no commercial relationship).

Source honesty: the DCB-backed forecast case is honestly BLOCKED (DCB automation rights not presumed);
public availability is not production authorization.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyrnova.customer_material_changes import fan_out
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

CA_REPLAY = Path("examples/ca_replay")
AS_OF = "2025-06-01"
EVAL = "eval-ca"


def _proof_module():
    spec = importlib.util.spec_from_file_location("ca_build_proof", CA_REPLAY / "build_customer_proof.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _console(tmp_path):
    proof = _proof_module()
    store = StateStore(tmp_path / "state")
    report = proof.seed(store)
    fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    console = OperatorConsole(store, tmp_path / "p", tmp_path / "o",
                              mc_store=store, customer_store=store,
                              cmc_store=store, delivery_store=CustomerDeliveryStore(tmp_path / "d"))
    return console, report


def _opp_by_case(console, case_suffix):
    """Find an opportunity whose title carries the corpus case id suffix."""
    for o in console.customer_opportunities(EVAL, as_of=AS_OF)["opportunities"]:
        if o.get("title", "").endswith(case_suffix):
            dec = console.opportunity_decision(EVAL, o["id"], as_of=AS_OF)
            return o["id"], dec
    raise AssertionError(f"no CA opportunity for case {case_suffix}")


def test_source_honesty_blocks_dcb_source(tmp_path):
    _c, report = _console(tmp_path)
    # 15 rights-approved cases materialize; the DCB-backed forecast is honestly blocked.
    assert report["materialized"] == 15
    assert {b["source_id"] for b in report["blocked"]} == {"ca_dcb"}


def test_customer_lens_and_opportunity_list(tmp_path):
    console, _ = _console(tmp_path)
    lens = console.customer_lens(EVAL, as_of=AS_OF)
    assert lens["customer"]["id"] == EVAL
    assert lens["opportunities"]["count"] == 15
    opps = console.customer_opportunities(EVAL, as_of=AS_OF)
    assert opps["count"] == 15
    for item in opps["opportunities"]:
        assert item["value_usd"] is None and item["incumbent"] is None  # no US assumptions leaked


def test_decision_view_carries_ca_acquisition_truth(tmp_path):
    console, _ = _console(tmp_path)
    _oid, dec = _opp_by_case(console, "ca-gbad-open")
    nat = dec["decision_chain"]["national_acquisition"]
    assert nat["domain"] == "CA"
    assert nat["mechanism"] == "COMPETITIVE_OPEN"
    assert nat["route"] == "OPEN_COMPETITIVE"
    assert nat["access_class"] == "OPEN_COMPETITION"
    assert nat["timing_class"] == "EXACT"
    assert dec["decision_chain"]["temporal"]["as_of"] == AS_OF


def test_fms_is_commercially_relevant_without_open_prime_and_itb_applies(tmp_path):
    console, _ = _console(tmp_path)
    _oid, dec = _opp_by_case(console, "ca-himars-fms")
    nat = dec["decision_chain"]["national_acquisition"]
    assert nat["mechanism"] == "FMS_GTG" and nat["route"] == "FMS"
    assert nat["access_class"] == "GTG_CONSTRAINED"      # not open competition
    assert nat["timing_class"] == "N_A"                  # open-market prime DLT N_A, still relevant
    assert nat["itb_vp"] == "ITB_OBLIGATION_APPLIES"     # ITB applies even to an FMS acquisition


def test_strategic_source_access_is_not_open_prime(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_case(console, "ca-nss-strategic")
    nat = dec["decision_chain"]["national_acquisition"]
    assert nat["mechanism"] == "STRATEGIC_SOURCE"
    assert nat["access_class"] == "NESTED_SUBCOMPETITION"  # WHO CAN COMPETE, not open prime
    item = next(o for o in console.customer_opportunities(EVAL, as_of=AS_OF)["opportunities"] if o["id"] == oid)
    assert item["lifecycle_state"] == "reviewing"


def test_itb_does_not_imply_prime_access(tmp_path):
    console, _ = _console(tmp_path)
    _oid, dec = _opp_by_case(console, "ca-cmma-itbvp")
    nat = dec["decision_chain"]["national_acquisition"]
    # ITB/VP relevant, but the prime is OEM-controlled — ITB relevance != prime access.
    assert nat["itb_vp"] == "VALUE_PROPOSITION_RELEVANT"
    assert nat["access_class"] == "OEM_CONTROLLED"


def test_bounded_and_contaminated_timing_not_promoted_to_exact(tmp_path):
    console, _ = _console(tmp_path)
    _oid, tapv = _opp_by_case(console, "ca-tapv-bounded")
    assert tapv["decision_chain"]["national_acquisition"]["timing_class"] == "BOUNDED"
    _oid, lvm = _opp_by_case(console, "ca-lvm-contaminated")
    assert lvm["decision_chain"]["national_acquisition"]["timing_class"] == "CONTAMINATED"
    _oid, cc177 = _opp_by_case(console, "ca-cc177-bounded2006")
    assert cc177["decision_chain"]["national_acquisition"]["timing_class"] == "BOUNDED"  # not exact 6-day


def test_bilingual_evidence_inspector_shows_original_language_authority(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_case(console, "ca-victoria-bilingual")
    ev = dec["decision_chain"]["evidence"][0]
    inspected = console.opportunity_evidence(EVAL, oid, ev["id"], as_of=AS_OF)
    lang = inspected["doctrine"]["language"]
    assert lang["original_language"] == "fr"                 # French original is authoritative
    assert lang["original_is_authoritative"] is True
    assert lang["translation_is_derived"] is True            # translation is PYRNOVA DERIVED
    assert lang["entity_key"] == "programme:victoria-class-modernization"


def test_cancellation_downgrades_and_reissue_is_fresh(tmp_path):
    console, _ = _console(tmp_path)
    opps = console.customer_opportunities(EVAL, as_of=AS_OF)["opportunities"]
    cancelled = next(o for o in opps if o["title"].endswith("ca-msvs-cancelled"))
    reissued = next(o for o in opps if o["title"].endswith("ca-msvs-reissued"))
    assert cancelled["lifecycle_state"] == "cancelled"    # PROGRAMME_CANCELLED downgrades to MONITORING
    assert reissued["lifecycle_state"] == "candidate"     # PROGRAMME_REISSUED is a fresh live opportunity
    assert cancelled["id"] != reissued["id"]              # no silent false continuity


def test_asof_excludes_later_cases(tmp_path):
    console, _ = _console(tmp_path)
    # Only CC-177 (2006-06-01) is knowable at end of 2006; every other case is later.
    early = console.customer_opportunities(EVAL, as_of="2006-12-31")
    assert early["count"] == 1
    dec = console.opportunity_decision(EVAL, early["opportunities"][0]["id"], as_of="2006-12-31")
    assert dec["decision_chain"]["national_acquisition"]["mechanism"] == "DIRECTED_OEM"


def test_decision_memory_and_brief_download(tmp_path):
    console, _ = _console(tmp_path)
    oid, _dec = _opp_by_case(console, "ca-himars-fms")
    console.record_opportunity_disposition(EVAL, oid, relevance="RELEVANT", pursuit="PURSUE",
                                           reason="GOOD_LEAD", note="evaluation: FMS with ITB obligation")
    dec = console.opportunity_decision(EVAL, oid)
    assert dec["decision_chain"]["customer_disposition"]["pursuit"] == "PURSUE"

    brief = console.build_customer_brief(EVAL, oid, as_of=AS_OF)
    body = brief["body"]
    assert "NATIONAL DOMAIN: Canada (CA)" in body
    assert "Acquisition mechanism: FMS_GTG" in body
    assert "Timing class (no numeric DLT threshold): N_A" in body
    assert "ITB/VP status (EVIDENCED, not derived; ITB != prime access): ITB_OBLIGATION_APPLIES" in body
    assert brief["content_sha256"] and brief["filename"].endswith(".txt")

    # A bilingual brief states original-language authority is preserved.
    b_oid, _ = _opp_by_case(console, "ca-victoria-bilingual")
    b_body = console.build_customer_brief(EVAL, b_oid, as_of=AS_OF)["body"]
    assert "Bilingual evidence: original-language authority preserved" in b_body
