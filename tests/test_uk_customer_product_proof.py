"""UK customer-product proof (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, UK vertical, boundary C).

Proves the United Kingdom national domain reaches the SAME tenant-isolated customer product the US, AU and
NZ use — Customer Lens, Opportunity list, Decision View (UK route / competition / access incl. prime vs
supply-chain / UK Industrial Position / consequential-change state / evidenced SSCR-QDC / post-award),
Evidence Inspector provenance, AS-OF, uncertainty, Decision Memory, and brief download — with a real
replay-backed proof and NO UK frontend fork. Uses the accepted UK replay corpus via the internal
evaluation lens (no real customer, no commercial relationship).

Source honesty: the SSRO-backed QDC case is honestly BLOCKED (blanket automated/commercial reuse denied);
QDC evidence cannot be laundered in through a denied source.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyrnova.customer_material_changes import fan_out
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

UK_REPLAY = Path("examples/uk_replay")
AS_OF = "2024-01-01"
EVAL = "eval-uk"


def _proof_module():
    spec = importlib.util.spec_from_file_location("uk_build_proof", UK_REPLAY / "build_customer_proof.py")
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


def _opp_by_consequential(console, kind):
    for o in console.customer_opportunities(EVAL, as_of=AS_OF)["opportunities"]:
        dec = console.opportunity_decision(EVAL, o["id"], as_of=AS_OF)
        nat = dec["decision_chain"].get("national_acquisition", {})
        if nat.get("consequential_change_kind") == kind:
            return o["id"], dec
    raise AssertionError(f"no UK opportunity with consequential change {kind}")


def test_source_honesty_blocks_ssro_qdc_source(tmp_path):
    _c, report = _console(tmp_path)
    # 8 OGL-backed cases materialize; the SSRO-backed QDC case is honestly blocked.
    assert report["materialized"] == 8
    assert {b["source_id"] for b in report["blocked"]} == {"uk_ssro"}


def test_customer_lens_and_opportunity_list(tmp_path):
    console, _ = _console(tmp_path)
    lens = console.customer_lens(EVAL, as_of=AS_OF)
    assert lens["customer"]["id"] == EVAL
    assert lens["opportunities"]["count"] == 8
    opps = console.customer_opportunities(EVAL, as_of=AS_OF)
    assert opps["count"] == 8
    for item in opps["opportunities"]:
        assert item["value_usd"] is None and item["incumbent"] is None  # no US assumptions leaked


def test_decision_view_carries_uk_acquisition_truth(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_consequential(console, "OPPORTUNITY_CREATED")  # New Medium Helicopter
    nat = dec["decision_chain"]["national_acquisition"]
    assert nat["domain"] == "GB"
    assert nat["route"] == "COMPETITIVE_FLEXIBLE"
    assert nat["access_class"] == "OPEN_COMPETITION"
    assert nat["industrial_position"] == "UK_BUILD_WORKSHARE"
    assert nat["consequential_change_kind"] == "OPPORTUNITY_CREATED"
    assert nat["sscr_qdc"] == "UNKNOWN"
    assert dec["decision_chain"]["temporal"]["as_of"] == AS_OF


def test_prime_change_is_not_market_closure_supply_chain_access_remains(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_consequential(console, "PRIME_POSITION_CHANGED")  # Skynet SDW
    nat = dec["decision_chain"]["national_acquisition"]
    # Prime position changed, but supply-chain access remains — NOT total market closure.
    assert nat["access_class"] == "SUPPLY_CHAIN"
    # The opportunity stays OPEN (reviewing), not CLOSED.
    item = next(o for o in console.customer_opportunities(EVAL, as_of=AS_OF)["opportunities"] if o["id"] == oid)
    assert item["lifecycle_state"] == "reviewing"


def test_direct_award_does_not_imply_qdc(tmp_path):
    console, _ = _console(tmp_path)
    _oid, dec = _opp_by_consequential(console, "OPPORTUNITY_NARROWED")  # Project MACE direct award
    nat = dec["decision_chain"]["national_acquisition"]
    assert nat["route"] == "DIRECT_AWARD"
    assert nat["sscr_qdc"] == "UNKNOWN"  # direct award is NOT QDC — evidenced field stays UNKNOWN


def test_qdc_confirmed_only_from_contract_specific_evidence(tmp_path):
    console, _ = _console(tmp_path)
    _oid, dec = _opp_by_consequential(console, "POST_AWARD_RISK_INCREASED")  # Ajax
    nat = dec["decision_chain"]["national_acquisition"]
    assert nat["route"] == "SINGLE_SOURCE"
    assert nat["sscr_qdc"] == "QDC_CONFIRMED"  # rests on contract-specific evidence, not the route


def test_post_award_is_not_terminal(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_consequential(console, "POST_AWARD_RISK_INCREASED")  # Ajax
    nat = dec["decision_chain"]["national_acquisition"]
    assert nat["post_award"] is True
    # Award does not close monitoring: the opportunity remains live (reviewing), not cancelled.
    item = next(o for o in console.customer_opportunities(EVAL, as_of=AS_OF)["opportunities"] if o["id"] == oid)
    assert item["lifecycle_state"] == "reviewing"


def test_opportunity_closure_downgrades_to_monitoring(tmp_path):
    console, _ = _console(tmp_path)
    feed = console.material_changes(EVAL, as_of=AS_OF)["material_changes"]
    closed = [c for c in feed if (c.get("national") or {}).get("consequential_change_kind") == "OPPORTUNITY_CLOSED"]
    assert closed and closed[0]["disposition"] == "MONITORING"  # Warrior CSP cancellation removes opportunity


def test_evidence_inspector_shows_provenance(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_consequential(console, "OPPORTUNITY_CREATED")
    ev = dec["decision_chain"]["evidence"][0]
    inspected = console.opportunity_evidence(EVAL, oid, ev["id"], as_of=AS_OF)
    assert inspected["doctrine"]["source_fact"] == "uk_contracts_finder"
    assert inspected["doctrine"]["provenance"]["source_ref"].startswith("uk:uk_contracts_finder:")
    assert "corpus.json" in (inspected["doctrine"]["provenance"]["archive_uri"] or "")


def test_asof_excludes_later_cases(tmp_path):
    console, _ = _console(tmp_path)
    # Only FDIS (2020-09-01) is knowable at end of 2020; every other case is later.
    early = console.customer_opportunities(EVAL, as_of="2020-12-31")
    assert early["count"] == 1
    dec = console.opportunity_decision(EVAL, early["opportunities"][0]["id"], as_of="2020-12-31")
    assert dec["decision_chain"]["national_acquisition"]["route"] == "FRAMEWORK_CALLOFF"


def test_decision_memory_and_brief_download(tmp_path):
    console, _ = _console(tmp_path)
    oid, _dec = _opp_by_consequential(console, "OPPORTUNITY_CREATED")
    console.record_opportunity_disposition(EVAL, oid, relevance="RELEVANT", pursuit="PURSUE",
                                           reason="GOOD_LEAD", note="evaluation: NMH open competition window")
    dec = console.opportunity_decision(EVAL, oid)
    assert dec["decision_chain"]["customer_disposition"]["pursuit"] == "PURSUE"

    brief = console.build_customer_brief(EVAL, oid, as_of=AS_OF)
    body = brief["body"]
    assert "NATIONAL DOMAIN: United Kingdom (GB)" in body
    assert "Acquisition route: COMPETITIVE_FLEXIBLE" in body
    assert "Consequential change: OPPORTUNITY_CREATED" in body
    assert "SSCR/QDC status (EVIDENCED, not derived): UNKNOWN" in body
    assert "GBP" in body
    assert brief["content_sha256"] and brief["filename"].endswith(".txt")

    # A post-award brief states award is not terminal.
    pa_oid, _ = _opp_by_consequential(console, "POST_AWARD_RISK_INCREASED")
    pa_body = console.build_customer_brief(EVAL, pa_oid, as_of=AS_OF)["body"]
    assert "SSCR/QDC status (EVIDENCED, not derived): QDC_CONFIRMED" in pa_body
    assert "Post-award intelligence: award is NOT terminal" in pa_body
