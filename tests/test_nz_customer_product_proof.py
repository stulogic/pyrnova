"""NZ customer-product proof (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, NZ vertical, boundary B).

Proves the New Zealand national domain reaches the SAME tenant-isolated customer product the US and AU use —
Customer Lens, Opportunity list, Decision View (with NZ acquisition context: route, access incl. Thin Prime,
Industrial Position), Evidence Inspector (provenance), AS-OF, uncertainty, customer disposition / Decision
Memory, and brief download — with a real replay-backed proof and NO NZ frontend fork. Uses the accepted NZ
replay corpus via the internal evaluation lens (no real customer, no commercial relationship).

Source honesty: the non-Defence nz_treasury-backed civil case is honestly BLOCKED (source not rights-approved
for a derived customer projection); it never silently appears in the product — preserving the accepted
NZ non-Defence coverage limitation. GETS is never a source.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyrnova.customer_material_changes import fan_out
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

NZ_REPLAY = Path("examples/nz_replay")
AS_OF = "2024-01-01"
EVAL = "eval-nz"


def _proof_module():
    spec = importlib.util.spec_from_file_location("nz_build_proof", NZ_REPLAY / "build_customer_proof.py")
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


def _opp_by_route(console, route):
    for o in console.customer_opportunities(EVAL, as_of=AS_OF)["opportunities"]:
        dec = console.opportunity_decision(EVAL, o["id"], as_of=AS_OF)
        if dec["decision_chain"].get("national_acquisition", {}).get("route") == route:
            return o["id"], dec
    raise AssertionError(f"no NZ opportunity with route {route}")


def test_source_honesty_blocks_unapproved_nz_civil_source(tmp_path):
    _console_, report = _console(tmp_path)
    # 5 nz_mod-backed cases materialize; the non-Defence nz_treasury civil case is honestly blocked.
    assert report["materialized"] == 5
    blocked_sources = {b["source_id"] for b in report["blocked"]}
    assert blocked_sources == {"nz_treasury"}


def test_customer_lens_and_opportunity_list(tmp_path):
    console, _ = _console(tmp_path)
    lens = console.customer_lens(EVAL, as_of=AS_OF)
    assert lens["customer"]["id"] == EVAL
    assert lens["opportunities"]["count"] == 5
    assert lens["material_changes"]["count"] >= 5
    opps = console.customer_opportunities(EVAL, as_of=AS_OF)
    assert opps["count"] == 5
    # No US assumptions leaked into the shared list projection.
    for item in opps["opportunities"]:
        assert item["value_usd"] is None and item["incumbent"] is None


def test_decision_view_carries_nz_acquisition_truth_incl_thin_prime(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_route(console, "CLOSED")  # route-constrained + access-sensitive Thin Prime case
    dc = dec["decision_chain"]
    nat = dc["national_acquisition"]
    assert nat["domain"] == "NZ"
    assert nat["route"] == "CLOSED" and "Closed" in nat["route_meaning"]
    # Thin Prime is an ACCESS class; the Industrial Position is a DISTINCT axis (not the access class).
    assert nat["access_class"] == "THIN_PRIME"
    assert nat["industrial_position"] == "ECONOMIC_BENEFIT"
    assert nat["important_miss_kind"] == "ROUTE_CHANGE"
    assert any((c.get("national") or {}).get("route") == "CLOSED" for c in dc["material_changes"])
    assert dc["temporal"]["as_of"] == AS_OF
    assert "uncertainty" in dc
    assert dec["source_rights"]["display"] in ("ALLOWED", "PARTIAL")


def test_evidence_inspector_shows_provenance(tmp_path):
    console, _ = _console(tmp_path)
    oid, dec = _opp_by_route(console, "OPEN")
    ev = dec["decision_chain"]["evidence"][0]
    inspected = console.opportunity_evidence(EVAL, oid, ev["id"], as_of=AS_OF)
    assert inspected["doctrine"]["source_fact"] == "nz_mod"
    assert inspected["doctrine"]["provenance"]["source_ref"].startswith("nz:nz_mod:")
    assert "corpus.json" in (inspected["doctrine"]["provenance"]["archive_uri"] or "")


def test_asof_excludes_later_cases(tmp_path):
    console, _ = _console(tmp_path)
    # Only nz-mod-early-warning (2020-01-15) is knowable at end of 2020; the rest are later.
    early = console.customer_opportunities(EVAL, as_of="2020-12-31")
    assert early["count"] == 1
    routes = {console.opportunity_decision(EVAL, o["id"], as_of="2020-12-31")
              ["decision_chain"]["national_acquisition"]["route"]
              for o in early["opportunities"]}
    assert routes == {"OPEN"}


def test_cancellation_downgrades_to_monitoring(tmp_path):
    console, _ = _console(tmp_path)
    feed = console.material_changes(EVAL, as_of=AS_OF)["material_changes"]
    cancelled = [c for c in feed if (c.get("national") or {}).get("route") == "DIRECT_SOURCE"]
    assert cancelled and cancelled[0]["disposition"] == "MONITORING"  # cancelled => not a live opportunity


def test_customer_disposition_decision_memory_and_brief(tmp_path):
    console, _ = _console(tmp_path)
    oid, _dec = _opp_by_route(console, "CLOSED")
    console.record_opportunity_disposition(EVAL, oid, relevance="RELEVANT", pursuit="PURSUE",
                                           reason="GOOD_LEAD",
                                           note="evaluation: thin-prime access on a closed NZ approach")
    dec = console.opportunity_decision(EVAL, oid)
    assert dec["decision_chain"]["customer_disposition"]["pursuit"] == "PURSUE"

    # Brief download from the SHARED product renders NZ acquisition truth (no country brief fork).
    brief = console.build_customer_brief(EVAL, oid, as_of=AS_OF)
    body = brief["body"]
    assert "NATIONAL DOMAIN: New Zealand (NZ)" in body
    assert "Acquisition route: CLOSED" in body
    assert "Access position (PYRNOVA DERIVED): THIN_PRIME" in body
    assert "Industrial Position: ECONOMIC_BENEFIT" in body
    assert "NZD" in body
    assert brief["content_sha256"] and brief["filename"].endswith(".txt")
