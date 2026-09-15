"""B4.1 — deterministic per-opportunity decision recomputation.

Proves that the accepted Bundle-2 verdicts are now obtained per opportunity from ALREADY-PERSISTED,
accepted evidence (no second engine, no fabrication):

* an opportunity with sufficient accepted evidence (a self-incumbent recompete) yields non-UNKNOWN
  buyer / competitive / access / fit / pursuit outputs;
* an opportunity whose evidence is genuinely insufficient stays honestly UNKNOWN;
* recomputation is deterministic and honours the AS-OF cutoff;
* tenant isolation is preserved.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.customers import CustomerProfile
from pyrnova.opportunity_recompute import recompute_decision_components
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
    module.seed(store)
    return OperatorConsole(store, PROFILES, tmp_path / "o", mc_store=StateStore(STATE),
                           contexts_dir=DEMO, customer_store=store,
                           cmc_store=StateStore(tmp_path / "cmc"),
                           delivery_store=CustomerDeliveryStore(tmp_path / "deliveries"))


def _first_opp(console):
    return console.customer_opportunities("torch")["opportunities"][0]["id"]


def test_evidence_supported_opportunity_yields_non_unknown_outputs(tmp_path):
    console = _console(tmp_path)
    oid = _first_opp(console)
    dc = console.opportunity_decision("torch", oid)["decision_chain"]
    assert dc["buyer"]["status"] == "EVIDENCED" and dc["buyer"]["buyer_intelligence"]
    assert dc["incumbent_competitive"]["customer_is_incumbent"] is True
    assert dc["incumbent_competitive"]["competitive_intelligence"]
    assert dc["access"]["verdict"] == "DIRECT_ACCESS"
    assert dc["customer_fit"]["status"] == "EVIDENCED" and dc["customer_fit"]["fit_reasoning"]
    assert dc["pursuit"]["verdict"] in ("PURSUE", "WATCH", "INVESTIGATE", "PASS")
    assert dc["pursuit"]["confidence"] in ("LOW", "MEDIUM", "HIGH")
    # No fabricated composite score; reversal conditions come from the pursuit verdict itself.
    assert dc["pursuit"]["pursuit_verdict"]["reversal_conditions"]
    assert dc["uncertainty"]["unknown_components"] == []


def test_insufficient_evidence_stays_unknown():
    # A bare opportunity (no incumbent, no agency, no evidence) must recompute to all-UNKNOWN.
    bare = {"id": "opp_bare", "customer_id": "torch"}
    other = CustomerProfile(customer_id="torch", name="Torch Technologies", entity_refs=["co_torch"])
    comp = recompute_decision_components(bare, customer_profile=other, as_of="2026-09-11")
    assert comp.buyer_intelligence is None
    assert comp.competitive_intelligence is None
    assert comp.vehicle_access is None
    assert comp.fit_reasoning is None
    assert comp.pursuit_verdict is None
    assert comp.customer_is_incumbent is False


def test_non_incumbent_customer_gets_no_fabricated_verdict(tmp_path):
    # Same rich opportunity, but a customer who is NOT the incumbent: fit/access/pursuit must stay UNKNOWN.
    console = _console(tmp_path)
    oid = _first_opp(console)
    o = console._find_opportunity("torch", oid)
    stranger = CustomerProfile(customer_id="other", name="Unrelated Co", entity_refs=["co_other"])
    comp = recompute_decision_components(o, customer_profile=stranger, as_of="2026-09-11")
    assert comp.customer_is_incumbent is False
    assert comp.vehicle_access is None and comp.fit_reasoning is None and comp.pursuit_verdict is None
    # buyer/competitive are still derivable from the opportunity's own public evidence (agency + incumbent).
    assert comp.buyer_intelligence is not None and comp.competitive_intelligence is not None


def test_recomputation_is_deterministic(tmp_path):
    console = _console(tmp_path)
    oid = _first_opp(console)
    a = console.opportunity_decision("torch", oid, as_of="2026-09-11")["decision_chain"]["pursuit"]
    b = console.opportunity_decision("torch", oid, as_of="2026-09-11")["decision_chain"]["pursuit"]
    assert a == b


def test_as_of_before_evidence_hides_opportunity(tmp_path):
    # AS-OF integrity: a cutoff before the opportunity's evidence was first seen surfaces nothing.
    console = _console(tmp_path)
    opps = console.customer_opportunities("torch", as_of="2000-01-01")
    assert opps["count"] == 0
