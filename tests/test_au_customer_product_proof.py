"""AU customer-product proof (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, boundary B).

Proves the Australian national domain reaches the SAME tenant-isolated customer product the US uses —
Customer Lens, Opportunity list, Decision View (with AU acquisition context: route, access, Industrial
Position), Evidence Inspector (provenance), AS-OF, uncertainty, customer disposition / Decision Memory,
and brief download — with a real replay-backed proof and NO national frontend fork. Uses the accepted AU
replay corpus via the internal evaluation lens (no real customer, no commercial relationship).

Source honesty: the au_defence_iip-backed case is honestly BLOCKED (source not rights-approved for a
derived customer projection); it never silently appears in the product.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from pyrnova.customer_material_changes import fan_out
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

AU_REPLAY = Path("examples/au_replay")
AS_OF = "2024-01-01"
EVAL = "eval-au"


def _proof_module():
    spec = importlib.util.spec_from_file_location("au_build_proof", AU_REPLAY / "build_customer_proof.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _console(tmp_path):
    proof = _proof_module()
    store = StateStore(tmp_path / "state")
    report = proof.seed(store)
    # Materialize customer-scoped Material Change state through the shared fan-out.
    fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    console = OperatorConsole(store, tmp_path / "p", tmp_path / "o",
                              mc_store=store, customer_store=store,
                              cmc_store=store, delivery_store=CustomerDeliveryStore(tmp_path / "d"))
    return console, report


def _opp_by_route(console, route):
    for o in console.customer_opportunities(EVAL, as_of=AS_OF)["opportunities"]:
        dec = console.opportunity_decision(EVAL, o["id"], as_of=AS_OF)
        if dec["decision_chain"].get("national_acquisition", {}).get("route") == route:
            return o["id"], dec
    raise AssertionError(f"no AU opportunity with route {route}")


def test_source_honesty_blocks_unapproved_au_source(tmp_path):
    console, report = _console(tmp_path)
    # 3 austender-backed cases materialize; the au_defence_iip (FMS) case is honestly blocked.
    assert report["materialized"] == 3
    blocked_sources = {b["source_id"] for b in report["blocked"]}
    assert blocked_sources == {"au_defence_iip"}


def test_customer_lens_and_opportunity_list(tmp_path):
    console, _ = _console(tmp_path)
    lens = console.customer_lens(EVAL, as_of=AS_OF)
    assert lens["customer"]["id"] == EVAL
    assert lens["opportunities"]["count"] == 3
    assert lens["material_changes"]["count"] >= 3
    opps = console.customer_opportunities(EVAL, as_of=AS_OF)
    assert opps["count"] == 3
    # No US assumptions leaked into the shared list projection.
    for item in opps["opportunities"]:
        assert item["value_usd"] is None and item["incumbent"] is None


def test_decision_view_carries_au_acquisition_truth(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_route(console, "LIMITED")  # the access-sensitive strong case
    dc = dec["decision_chain"]
    nat = dc["national_acquisition"]
    assert nat["domain"] == "AU"
    assert nat["route"] == "LIMITED" and "Limited tender" in nat["route_meaning"]
    assert nat["access_class"] == "PANEL_MEMBER"
    assert nat["industrial_position"] == "SOVEREIGN_CAPABILITY"
    assert nat["important_miss_kind"] == "ROUTE_CHANGE"
    # National truth also rides on the related Material Change (shared feed, not a country fork).
    assert any((c.get("national") or {}).get("route") == "LIMITED" for c in dc["material_changes"])
    # AS-OF + uncertainty surfaces present.
    assert dc["temporal"]["as_of"] == AS_OF
    assert "uncertainty" in dc
    assert dec["source_rights"]["display"] in ("ALLOWED", "PARTIAL")


def test_evidence_inspector_shows_provenance(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_route(console, "OPEN")
    ev = dec["decision_chain"]["evidence"][0]
    inspected = console.opportunity_evidence(EVAL, oid, ev["id"], as_of=AS_OF)
    assert inspected["doctrine"]["source_fact"] == "au_austender"
    assert inspected["doctrine"]["provenance"]["source_ref"].startswith("austender:")
    assert "corpus.json" in (inspected["doctrine"]["provenance"]["archive_uri"] or "")


def test_asof_excludes_later_cases(tmp_path):
    console, _ = _console(tmp_path)
    # Only au-open-progression (2021-05-10) is knowable at end of 2021; route-change/cancellation are later.
    early = console.customer_opportunities(EVAL, as_of="2021-12-31")
    assert early["count"] == 1
    routes = {console.opportunity_decision(EVAL, o["id"], as_of="2021-12-31")
              ["decision_chain"]["national_acquisition"]["route"]
              for o in early["opportunities"]}
    assert routes == {"OPEN"}


def test_cancellation_downgrades_to_monitoring(tmp_path):
    console, _ = _console(tmp_path)
    feed = console.material_changes(EVAL, as_of=AS_OF)["material_changes"]
    gtg = [c for c in feed if (c.get("national") or {}).get("route") == "GTG"]
    assert gtg and gtg[0]["disposition"] == "MONITORING"  # cancelled => not a live opportunity


def test_customer_disposition_decision_memory_and_brief(tmp_path):
    console, _ = _console(tmp_path)
    oid, _dec = _opp_by_route(console, "LIMITED")
    # Record the eval lens's own disposition (Decision Memory), distinct from Pyrnova assessment.
    console.record_opportunity_disposition(EVAL, oid, relevance="RELEVANT", pursuit="PURSUE",
                                           reason="GOOD_LEAD",
                                           note="evaluation: sovereign-capability panel access")
    # Read at current time (the disposition is recorded now; a 2024 as-of would correctly exclude it).
    dec = console.opportunity_decision(EVAL, oid)
    assert dec["decision_chain"]["customer_disposition"]["pursuit"] == "PURSUE"

    # Brief download from the SHARED product renders AU acquisition truth (no country brief fork).
    brief = console.build_customer_brief(EVAL, oid, as_of=AS_OF)
    body = brief["body"]
    assert "NATIONAL DOMAIN: Australia (AU)" in body
    assert "Acquisition route: LIMITED" in body
    assert "Access position (PYRNOVA DERIVED): PANEL_MEMBER" in body
    assert "Industrial Position: SOVEREIGN_CAPABILITY" in body
    assert "AUD" in body
    assert brief["content_sha256"] and brief["filename"].endswith(".txt")
