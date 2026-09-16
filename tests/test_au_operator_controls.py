"""AU operator/domain controls (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, boundary C).

Operator capability (no admin UI) to: inspect AU source status (national activation × registry rights,
incl. blocked live activation); provision the AU evaluation lens from accepted replay evidence and fan
out; and inspect the lens's national opportunity / Important-Miss state — all fail closed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.customer_material_changes import fan_out
from pyrnova.domains.operator import domain_source_status, lens_national_state
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

AU_REPLAY = Path("examples/au_replay")


def test_au_source_status_crosses_activation_and_rights():
    status = domain_source_status("AU")
    assert status["operational"] is True
    by_id = {s["id"]: s for s in status["sources"]}
    # AusTender: lawful replay-derived use, but live activation blocked (rights approval pending).
    aus = by_id["au_austender"]
    assert aus["national_activation"] == "FIXTURE_ONLY"
    assert aus["live_activatable"] is False
    assert aus["replay_derived_permitted"] is True
    assert "rights approval" in aus["blocked_live_activation"]
    # DECLARED sources: fail closed for both live and replay-derived use.
    iip = by_id["au_defence_iip"]
    assert iip["national_activation"] == "DECLARED"
    assert iip["live_activatable"] is False and iip["replay_derived_permitted"] is False
    assert iip["blocked_live_activation"]
    # Important Miss taxonomy is surfaced for the operator.
    assert "ROUTE_CHANGE" in status["important_miss_taxonomy"]


def _provisioned_console(tmp_path):
    spec = importlib.util.spec_from_file_location("au_proof", AU_REPLAY / "build_customer_proof.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store = StateStore(tmp_path / "state")
    module.seed(store)
    fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    console = OperatorConsole(store, tmp_path / "p", tmp_path / "o", mc_store=store,
                             customer_store=store, cmc_store=store,
                             delivery_store=CustomerDeliveryStore(tmp_path / "d"))
    return console


def test_operator_lens_national_state(tmp_path):
    console = _provisioned_console(tmp_path)
    state = lens_national_state(console, "eval-au", as_of="2024-01-01")
    assert state["count"] == 3
    routes = {o["route"] for o in state["opportunities"]}
    assert routes == {"OPEN", "LIMITED", "GTG"}
    # Important-Miss rollup is visible to the operator.
    assert state["important_miss"] == {"CANCELLATION": 1, "PROGRESSION": 1, "ROUTE_CHANGE": 1}
    # The cancelled GTG case is downgraded in the shared state.
    gtg = next(o for o in state["opportunities"] if o["route"] == "GTG")
    assert gtg["shared_state"] == "cancelled"
    assert gtg["access_class"] == "UNKNOWN"  # national UNKNOWN preserved, not guessed
