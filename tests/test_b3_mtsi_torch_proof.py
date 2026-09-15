"""B3.15 — real MTSI / Torch product proof.

Proves the accepted Bundle-2 intelligence is usable THROUGH the Bundle-3 product against the two live
target lenses, using existing accepted data only (no invented facts). Records honestly what surfaces and
what remains UNKNOWN. In this environment the demo persists Torch opportunities (backed by real
usaspending evidence) while MTSI has a customer profile but no persisted opportunities — so the MTSI lens
is honestly EMPTY, not fabricated and not noisy. Cross-tenant isolation holds for both lenses."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"
PROFILES = Path("examples/profiles")


def _console(tmp_path):
    store = StateStore(tmp_path / "state")
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)  # torch + dap
    return OperatorConsole(store, PROFILES, tmp_path / "o", mc_store=StateStore(STATE),
                           contexts_dir=DEMO, customer_store=store,
                           cmc_store=StateStore(tmp_path / "cmc"),
                           delivery_store=CustomerDeliveryStore(tmp_path / "deliveries"))


def test_torch_lens_is_usable_and_coherent(tmp_path):
    console = _console(tmp_path)
    lens = console.customer_lens("torch")
    assert lens["customer"]["id"] == "torch"
    opps = console.customer_opportunities("torch")
    assert opps["count"] > 0  # not empty
    o = opps["opportunities"][0]
    # coherent: real intelligence surfaces (recompete catalyst, incumbent, recommended action)
    assert o["why_now"]["kind"] and o["incumbent"] and o["recommended_action"]
    dec = console.opportunity_decision("torch", o["id"])
    dc = dec["decision_chain"]
    # evidence is real (usaspending); B4.1 recomputes an evidence-backed pursuit verdict (self-incumbent
    # recompete) — a real disposition with qualitative confidence, not fabricated and not hard-coded UNKNOWN.
    assert any(e.get("source_id") == "usaspending" for e in dc["evidence"])
    assert dc["pursuit"]["verdict"] in ("PURSUE", "WATCH", "INVESTIGATE", "PASS")
    assert dc["pursuit"]["confidence"] in ("LOW", "MEDIUM", "HIGH") and dc["pursuit"]["recommended_action"]
    # brief representation is truthful (rights disposition present; verdict + confidence, no fabricated score)
    brief = console.build_customer_brief("torch", o["id"])
    assert brief["rights_display"] in ("ALLOWED", "PARTIAL")
    assert f"Verdict: {dc['pursuit']['verdict']} (confidence {dc['pursuit']['confidence']})" in brief["body"]


def test_mtsi_lens_surfaces_its_real_recompetes_tenant_isolated(tmp_path):
    # B4.2 — MTSI's empty lens was a fan-out gap, not a legitimate empty: the same real detect_recompetes
    # engine over the real archived usaspending_mtsi.json produces genuine MTSI recompete opportunities.
    console = _console(tmp_path)
    # Onboard MTSI from its accepted profile, carrying its canonical entity ref (no invented facts).
    console.create_customer(customer_id="mtsi", name="Modern Technology Solutions",
                            entity_refs=["co_mtsi"],
                            capabilities=["systems engineering", "modeling and simulation"],
                            agencies=["Missile Defense Agency", "Space Force", "General Services Administration"])
    lens = console.customer_lens("mtsi")
    assert lens["customer"]["id"] == "mtsi"
    opps = console.customer_opportunities("mtsi")
    # Real, persisted MTSI opportunities now surface (from usaspending_mtsi.json), never fabricated.
    assert opps["count"] > 0
    o = opps["opportunities"][0]
    assert o["incumbent"] and "MODERN TECHNOLOGY SOLUTIONS" in o["incumbent"].upper()
    # Evidence is the real MTSI archive, not Torch's (no cross-tenant copying).
    dec = console.opportunity_decision("mtsi", o["id"])
    ev = dec["decision_chain"]["evidence"]
    assert ev and all("usaspending_mtsi.json" in (e.get("archive_uri") or "")
                      for e in ev if e.get("archive_uri"))
    # MTSI never sees Torch's opportunities, and Torch never sees MTSI's (tenant isolation).
    torch_ids = {t["id"] for t in console.customer_opportunities("torch")["opportunities"]}
    mtsi_ids = {m["id"] for m in opps["opportunities"]}
    assert torch_ids and mtsi_ids and torch_ids.isdisjoint(mtsi_ids)
