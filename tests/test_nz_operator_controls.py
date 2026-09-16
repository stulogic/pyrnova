"""NZ operator/domain controls (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, NZ vertical, boundary C).

Operator capability (no admin UI) to: inspect NZ source status (national activation × registry rights,
incl. GETS PROHIBITED and blocked live activation); provision the NZ evaluation lens from accepted replay
evidence and fan out; and inspect the lens's national opportunity / Important-Miss state — all fail closed.
Reuses the domain-neutral operator tooling built for AU (no NZ-specific operator fork).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.customer_material_changes import fan_out
from pyrnova.domains.operator import domain_source_status, lens_national_state
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

NZ_REPLAY = Path("examples/nz_replay")


def test_nz_source_status_crosses_activation_and_rights():
    status = domain_source_status("NZ")
    assert status["operational"] is True
    by_id = {s["id"]: s for s in status["sources"]}
    # GETS: hard-locked at the national layer; never live-activatable, never replay-derived.
    gets = by_id["nz_gets"]
    assert gets["national_activation"] == "PROHIBITED"
    assert gets["live_activatable"] is False and gets["replay_derived_permitted"] is False
    assert "PROHIBITED" in gets["blocked_live_activation"]
    # NZ MoD: lawful replay-derived use, but live activation blocked (rights approval pending).
    mod = by_id["nz_mod"]
    assert mod["national_activation"] == "FIXTURE_ONLY"
    assert mod["live_activatable"] is False
    assert mod["replay_derived_permitted"] is True
    assert "rights approval" in mod["blocked_live_activation"]
    # DECLARED civil / caution families: fail closed for both live and replay-derived use.
    for sid in ("nz_treasury", "nz_linz", "nz_greater_wellington", "nz_police", "nz_nzta"):
        s = by_id[sid]
        assert s["national_activation"] == "DECLARED"
        assert s["live_activatable"] is False and s["replay_derived_permitted"] is False
        assert s["blocked_live_activation"]
    # NZ Important Miss taxonomy is surfaced for the operator (incl. the NZ-specific Thin Prime shift).
    assert "ROUTE_CHANGE" in status["important_miss_taxonomy"]
    assert "THIN_PRIME_SHIFT" in status["important_miss_taxonomy"]


def _provisioned_console(tmp_path):
    spec = importlib.util.spec_from_file_location("nz_proof", NZ_REPLAY / "build_customer_proof.py")
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
    state = lens_national_state(console, "eval-nz", as_of="2024-01-01")
    assert state["count"] == 5
    routes = {o["route"] for o in state["opportunities"]}
    assert routes == {"OPEN", "CLOSED", "PANEL", "DIRECT_SOURCE"}
    # Important-Miss rollup is visible to the operator.
    assert state["important_miss"] == {"CANCELLATION": 1, "PROGRESSION": 2, "RE_SCOPE": 1, "ROUTE_CHANGE": 1}
    # The cancelled DIRECT_SOURCE case is downgraded in the shared state; national UNKNOWN preserved.
    ds = next(o for o in state["opportunities"] if o["route"] == "DIRECT_SOURCE")
    assert ds["shared_state"] == "cancelled"
    assert ds["access_class"] == "UNKNOWN"  # national UNKNOWN preserved, not guessed
    # A Thin Prime access position rides through the shared read model unflattened.
    closed = next(o for o in state["opportunities"] if o["route"] == "CLOSED")
    assert closed["access_class"] == "THIN_PRIME"
    assert closed["industrial_position"] == "ECONOMIC_BENEFIT"
