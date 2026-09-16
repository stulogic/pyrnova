"""UK operator/domain controls (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, UK vertical, boundary D).

Operator capability (no admin UI) to: inspect UK source status (national activation × registry rights,
incl. blocked live activation and DECLARED families that fail closed); provision the UK evaluation lens from
accepted replay evidence and fan out; and inspect the lens's national opportunity / consequential-change /
Important-Miss state — all fail closed. Reuses the domain-neutral operator tooling (no UK operator fork).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.customer_material_changes import fan_out
from pyrnova.domains.operator import domain_source_status, lens_national_state
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

UK_REPLAY = Path("examples/uk_replay")


def test_uk_source_status_crosses_activation_and_rights():
    status = domain_source_status("GB")
    assert status["operational"] is True
    by_id = {s["id"]: s for s in status["sources"]}
    # OGL / structured procurement families: lawful replay-derived use, live activation blocked.
    for sid in ("uk_contracts_finder", "uk_gov_uk"):
        s = by_id[sid]
        assert s["national_activation"] == "FIXTURE_ONLY"
        assert s["live_activatable"] is False
        assert s["replay_derived_permitted"] is True
        assert s["blocked_live_activation"]
    # DECLARED families fail closed for both live and replay-derived use.
    for sid in ("uk_dsp", "uk_ssro", "uk_nao", "uk_vdr_attachments", "uk_supplier_material", "uk_archive_mirror"):
        s = by_id[sid]
        assert s["national_activation"] == "DECLARED"
        assert s["live_activatable"] is False and s["replay_derived_permitted"] is False
    # UK Important-Miss failure taxonomy is surfaced for the operator.
    assert "DIRECT_AWARD_AS_QDC" in status["important_miss_taxonomy"]
    assert "AWARD_AS_TERMINAL" in status["important_miss_taxonomy"]


def _provisioned_console(tmp_path):
    spec = importlib.util.spec_from_file_location("uk_proof", UK_REPLAY / "build_customer_proof.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store = StateStore(tmp_path / "state")
    module.seed(store)
    fan_out(mc_store=store, customer_store=store, cmc_store=store, as_of=None)
    console = OperatorConsole(store, tmp_path / "p", tmp_path / "o", mc_store=store,
                             customer_store=store, cmc_store=store,
                             delivery_store=CustomerDeliveryStore(tmp_path / "d"))
    return console


def test_operator_lens_national_state_rolls_up_consequential_change(tmp_path):
    console = _provisioned_console(tmp_path)
    state = lens_national_state(console, "eval-uk", as_of="2024-01-01")
    assert state["count"] == 8
    # Consequential-change rollup is visible to the operator (UK's state model, not just Important Miss).
    assert state["consequential_change"] == {
        "ACCESS_CHANGED": 1, "OPPORTUNITY_CLOSED": 1, "OPPORTUNITY_CREATED": 1, "OPPORTUNITY_EXPANDED": 2,
        "OPPORTUNITY_NARROWED": 1, "POST_AWARD_RISK_INCREASED": 1, "PRIME_POSITION_CHANGED": 1,
    }
    # The closed case is downgraded; the post-award case is still monitored (award not terminal).
    closed = next(o for o in state["opportunities"] if o["consequential_change_kind"] == "OPPORTUNITY_CLOSED")
    assert closed["shared_state"] == "cancelled"
    ajax = next(o for o in state["opportunities"] if o["consequential_change_kind"] == "POST_AWARD_RISK_INCREASED")
    assert ajax["shared_state"] == "reviewing" and ajax["post_award"] is True and ajax["sscr_qdc"] == "QDC_CONFIRMED"
