"""M22-E honesty gate: opportunity Material Changes wired to the customer-facing product.

The customer-facing product was THREAT-ONLY not because the read model lacked opportunity support (it
always had it) but because the demo estate carried no opportunity data. M22-E materializes REAL,
evidence-backed opportunities through the SAME deterministic, customer-scoped, point-in-time, isolated
path as threats — no new engine, model, stream, or persistence.

Covers the M22-E acceptance priorities (see ``docs/specs/M22E_OPPORTUNITY_MATERIAL_CHANGES.md``):
opportunity → Material Change; deterministic identity; duplicate suppression; customer relevance vs
irrelevant-customer suppression; storage isolation; lifecycle across rebuild; observed vs assessed;
evidence refs; no future / no retrospective-watch leakage; historical (expired) opportunity not shown as
active; investigation links; outcome linkage; threat behavior unchanged.

Uses the REAL archived-evidence demo fixture (Torch recompetes over ``usaspending_torch.json``, DAP
threat-only) plus the real ``detect_recompetes`` engine — no fabricated opportunities.
"""

import importlib.util
import json
from datetime import date
from pathlib import Path

from pyrnova import customer_material_changes as cmc
from pyrnova.customer_material_changes import fan_out, rebuild_customer, _latest_versions
from pyrnova.customers import record_review_action
from pyrnova.engines.recompete import detect_recompetes
from pyrnova.material_changes import DISPOSITION_OPPORTUNITY, build_material_changes, CustomerContext
from pyrnova.normalize import normalize_award
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"


def _load_seeder():
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seeded_customers(tmp_path) -> StateStore:
    store = StateStore(tmp_path / "customers")
    _load_seeder().seed(store)
    return store


def _console(tmp_path, cstore, mc, cmc_store=None):
    return OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "p", tmp_path / "o",
                           mc_store=mc, customer_store=cstore, cmc_store=cmc_store)


def _torch_opps(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    feed = _console(tmp_path, cstore, mc).material_changes("torch")["material_changes"]
    return [c for c in feed if c["disposition"] == DISPOSITION_OPPORTUNITY]


# --- (1) opportunity → Material Change ----------------------------------------------------------

def test_opportunities_surface_as_material_changes(tmp_path):
    opps = _torch_opps(tmp_path)
    assert opps, "the demo estate must materialize real opportunity Material Changes"
    for o in opps:
        assert o["kind"] == "opportunity"
        assert o["disposition"] == "OPPORTUNITY"


# --- (2) deterministic identity (§43) -----------------------------------------------------------

def test_opportunity_identity_is_deterministic_and_source_linked(tmp_path):
    opps = _torch_opps(tmp_path)
    ids = [o["id"] for o in opps]
    assert all(i.startswith("opp_") for i in ids)
    assert len(ids) == len(set(ids))  # no duplicate identity
    # Stable across a rebuild of the estate (the seed pins engine ids from source content).
    again = [o["id"] for o in _torch_opps(tmp_path)]
    assert set(ids) == set(again)


# --- (3) duplicate suppression via idempotent fan-out -------------------------------------------

def test_opportunity_fanout_is_idempotent(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    r1 = fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    opp_rows = [v for v in _latest_versions(cmc_store, "torch").values() if v["source_kind"] == "opportunity"]
    assert opp_rows, "opportunities must be materialized into customer-scoped storage"
    assert all(v["content_version"] == 1 for v in opp_rows)
    r2 = fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    assert r2["inserted"] == 0 and r2["updated"] == 0
    assert r2["duplicates_suppressed"] == r1["inserted"]


# --- (4)/(5) relevance for the right customer; suppression for the wrong one --------------------

def test_opportunity_relevance_and_irrelevant_customer_suppression(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    console = _console(tmp_path, cstore, mc)
    torch = console.material_changes("torch")["material_changes"]
    dap = console.material_changes("dap")["material_changes"]
    torch_opps = [c for c in torch if c["disposition"] == "OPPORTUNITY"]
    assert torch_opps
    # Torch is the incumbent → DIRECT_SUBJECT, resolving to the canonical entity (not the tenant id).
    for o in torch_opps:
        assert o["relevance"]["basis"] == "DIRECT_SUBJECT"
        assert o["refs"]["subject_ref"] == "co_torch"
    # DAP has no active recompete and shares none of Torch's opportunities.
    assert not [c for c in dap if c["disposition"] == "OPPORTUNITY"]


# --- (6) storage isolation ----------------------------------------------------------------------

def test_opportunity_storage_isolated_to_relevant_customer(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    dap_opps = [v for v in _latest_versions(cmc_store, "dap").values() if v["source_kind"] == "opportunity"]
    assert dap_opps == []
    for row in cmc_store.read(cmc.STREAM_CUSTOMER_MATERIAL_CHANGES):
        if row["source_kind"] == "opportunity":
            assert row["customer_id"] == "torch"


# --- (7) lifecycle survives rebuild -------------------------------------------------------------

def test_opportunity_review_lifecycle_survives_rebuild(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    opp_id = next(v["material_change_id"] for v in _latest_versions(cmc_store, "torch").values()
                  if v["source_kind"] == "opportunity")
    record_review_action(cstore, customer_id="torch", material_change_id=opp_id,
                          action_type="MONITOR", actor="tester")
    rebuild_customer(mc_store=mc, customer_store=cstore, cmc_store=cmc_store, customer_id="torch")
    console = _console(tmp_path, cstore, mc, cmc_store=cmc_store)
    change = next(c for c in console.material_changes("torch")["material_changes"] if c["id"] == opp_id)
    assert change["review"]["state"] == "MONITORING"  # customer action not erased by a derived rebuild


# --- (8) observed vs assessed kept separate -----------------------------------------------------

def test_observed_and_assessment_not_flattened(tmp_path):
    o = _torch_opps(tmp_path)[0]
    assert set(o["observed"]) & {"value_usd", "expected_action_at", "affected_entity"}
    assert o["observed"]["affected_entity"]  # a real incumbent name, not the tenant id
    assert o["assessment"]["is_assessment"] is True
    # The known contract value is an OBSERVED fact; it must not masquerade as an assessed severity.
    assert o["observed"]["value_usd"] and o["observed"]["value_usd"] > 0
    assert o["assessment"]["materiality"] == "UNKNOWN"


# --- (9) evidence referenced, not fabricated ----------------------------------------------------

def test_opportunity_evidence_references_real_archive(tmp_path):
    o = _torch_opps(tmp_path)[0]
    ev = o["evidence"]
    assert ev["evidence_count"] >= 1
    assert "usaspending" in ev["sources"]
    assert ev["archive_hash"] and ev["raw_authoritative_bytes"] is True


# --- (10) no future leakage ---------------------------------------------------------------------

def test_opportunity_not_visible_before_it_was_knowable(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    console = _console(tmp_path, cstore, mc)
    # The recompete became knowable at the pinned scan date (2026-09-01). A cutoff before that must hide it.
    early = console.material_changes("torch", as_of="2024-06-01")["material_changes"]
    assert not [c for c in early if c["disposition"] == "OPPORTUNITY"]


# --- (11) no retrospective-watch leakage --------------------------------------------------------

def test_first_relevant_never_precedes_observation(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    for v in _latest_versions(cmc_store, "torch").values():
        if v["source_kind"] == "opportunity":
            assert v["first_relevant_at"] >= v["intelligence_observed_at"]


# --- (12) a historical (expired) opportunity is not shown as active -----------------------------

def test_expired_award_yields_no_active_recompete():
    raw = json.loads((Path("examples/real_evidence/usaspending_torch.json")).read_text())
    awards = [normalize_award(r) for r in raw["results"]]
    # Scanned far in the future, every archived award has already expired → no active recompete candidate.
    assert detect_recompetes(awards, as_of=date(2035, 1, 1), window_days=540) == []


# --- (13) investigation links reach the canonical entity/program --------------------------------

def test_opportunity_investigation_links_resolve(tmp_path):
    o = _torch_opps(tmp_path)[0]
    inv = o["investigation"]
    assert inv["company"]["ref"] == "co_torch"
    assert inv["program"]["key"]  # the real PIID


# --- (14) outcome linkage: UNRESOLVED is valid, never forced ------------------------------------

def test_opportunity_outcome_unresolved_by_default(tmp_path):
    o = _torch_opps(tmp_path)[0]
    assert o["outcome_state"] == "UNKNOWN"  # no fabricated win/loss/conversion


# --- (15) threat behavior unchanged -------------------------------------------------------------

def test_threat_feed_unchanged_by_opportunity_wiring(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    console = _console(tmp_path, cstore, mc)
    dap = console.material_changes("dap")["material_changes"]
    assert dap and all(c["disposition"] in ("THREAT", "MONITORING") for c in dap)
    torch_threats = [c for c in console.material_changes("torch")["material_changes"]
                     if c["disposition"] == "THREAT"]
    assert torch_threats  # threats still present alongside the new opportunities
    # §56 copy fix: the affected entity is named, not the ambiguous "the subject's revenue".
    assert all("the subject's" not in (c["assessment"]["consequence"] or "") for c in torch_threats)
