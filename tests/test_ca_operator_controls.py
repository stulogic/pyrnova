"""CA operator/domain controls (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, CA vertical, boundary D).

Operator capability (no admin UI) to: inspect Canadian source status (national activation × registry rights,
incl. blocked live activation and DECLARED families that fail closed); provision the Canadian evaluation lens
from accepted replay evidence and fan out; and inspect the lens's national opportunity / consequential-change
state — all fail closed. Reuses the domain-neutral operator tooling (no CA operator fork) and the shared
`domains` CLI.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from pyrnova.cli import main
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.customer_material_changes import fan_out
from pyrnova.domains.operator import domain_source_status, lens_national_state
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

CA_REPLAY = Path("examples/ca_replay")

_DECLARED = ("ca_canadabuys_portal", "ca_dnd_web", "ca_canada_ca", "ca_dcb", "ca_parliament",
             "ca_thirdparty_mirror")


def test_ca_source_status_crosses_activation_and_rights():
    status = domain_source_status("CA")
    assert status["operational"] is True
    by_id = {s["id"]: s for s in status["sources"]}
    # CanadaBuys datasets: lawful replay-derived use, live activation blocked (licence not verified).
    ds = by_id["ca_canadabuys_dataset"]
    assert ds["national_activation"] == "FIXTURE_ONLY"
    assert ds["live_activatable"] is False
    assert ds["replay_derived_permitted"] is True
    assert ds["blocked_live_activation"]
    # DECLARED families fail closed for BOTH live and replay-derived use (UNKNOWN => DENY).
    for sid in _DECLARED:
        s = by_id[sid]
        assert s["national_activation"] == "DECLARED"
        assert s["live_activatable"] is False and s["replay_derived_permitted"] is False
    # CA Important-Miss failure taxonomy is surfaced for the operator.
    assert "RFP_AS_FIRST_MARKET_EVENT" in status["important_miss_taxonomy"]
    assert "RESURRECTED_2006_SIX_DAY_DLT" in status["important_miss_taxonomy"]


def test_domains_cli_surfaces_canada(capsys):
    assert main(["domains", "show", "CA"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["operational"] is True
    assert d["dlt_calibration"] is None                # NO Canadian numeric DLT threshold
    assert d["routes"]["FMS"] != d["routes"]["OPEN_COMPETITIVE"]
    assert "STRATEGIC_SOURCE" in d["mechanisms"]
    assert "CONTAMINATED" in d["timing_classes"]
    assert "ITB_OBLIGATION_APPLIES" in d["itb_vp_states"]
    assert d["evidence_languages"] == ["en", "fr"]

    assert main(["domains", "sources", "CA"]) == 0
    by_id = {s["id"]: s for s in json.loads(capsys.readouterr().out)["sources"]}
    assert by_id["ca_canadabuys_dataset"]["replay_derived_permitted"] is True
    assert by_id["ca_canadabuys_dataset"]["live_activatable"] is False
    assert by_id["ca_dcb"]["replay_derived_permitted"] is False


def _provisioned_console(tmp_path):
    spec = importlib.util.spec_from_file_location("ca_proof", CA_REPLAY / "build_customer_proof.py")
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
    state = lens_national_state(console, "eval-ca", as_of="2025-06-01")
    assert state["count"] == 15
    assert state["consequential_change"] == {
        "CAPABILITY_INSERTION_OPENED": 1, "ITB_VP_RELEVANCE_CHANGED": 1, "OPPORTUNITY_CREATED": 7,
        "OPPORTUNITY_EXPANDED": 2, "PROGRAMME_CANCELLED": 1, "PROGRAMME_REISSUED": 1,
        "QUALIFICATION_CHANGED": 1, "SUPPLY_CHAIN_ACCESS_CHANGED": 1,
    }
    cancelled = next(o for o in state["opportunities"]
                     if o["consequential_change_kind"] == "PROGRAMME_CANCELLED")
    assert cancelled["shared_state"] == "cancelled"
    reissued = next(o for o in state["opportunities"]
                    if o["consequential_change_kind"] == "PROGRAMME_REISSUED")
    assert reissued["shared_state"] == "candidate"  # reissue is a fresh live opportunity
