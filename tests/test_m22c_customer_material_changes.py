"""M22-C honesty gate: per-customer persisted Material Change streams + production read path.

Covers the M22-C acceptance priorities (see ``docs/specs/M22C_CUSTOMER_MATERIAL_CHANGE_STREAMS.md``):
deterministic idempotent fan-out; stable Material Change identity; STORAGE-level cross-customer isolation
(not just UI/relevance filtering); explicit first-seen semantics; temporal correctness (no future / no
retrospective leakage); append/version update semantics without lifecycle loss; outcome propagation without
rewriting the original assessment; rebuild preserving customer actions; the production-shaped read path;
and the invariant that customer fan-out/actions never touch or mutate global intelligence.

Uses the REAL M22-A/B archived-evidence demo fixture (Torch, DAP) plus small synthetic global records for
update/outcome/temporal cases — no fabrication of intelligence into the tracked corpus.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from pyrnova import customers as cust
from pyrnova import customer_material_changes as cmc
from pyrnova.customers import (
    CustomerProfile,
    WatchlistEntry,
    add_watch,
    record_review_action,
    upsert_customer,
)
from pyrnova.customer_material_changes import fan_out, rebuild_customer, version_history, _latest_versions
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"

GLOBAL_STREAMS = set(cust.GLOBAL_INTELLIGENCE_STREAMS)


def _load_seeder():
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seeded_customers(tmp_path) -> StateStore:
    store = StateStore(tmp_path / "customers")
    _load_seeder().seed(store)
    return store


def _threat(tid, *, subject_ref, severity="HIGH", confidence="HIGH", status="ACTIVE",
            observed="2026-03-01T00:00:00+00:00", outcome=None, program="PIID-777"):
    meta = {"event_type": "CONTRACT_TERMINATION", "event_time": observed, "agency": "VA",
            "affected_program": program, "catalyst_class": "OBSERVED",
            "evidence_sources": ["usaspending"]}
    if outcome is not None:
        meta["outcome"] = {"label": outcome}
    return {"id": tid, "subject_ref": subject_ref, "subject_name": "Target Co",
            "severity": severity, "confidence": confidence, "status": status,
            "evidence_ids": ["ev1"], "mechanism": "PROGRAM_CANCELLATION",
            "economic_effect": "loss", "available_at": observed, "first_observed_at": observed,
            "meta": meta}


def _synthetic_env(tmp_path, *, threats, watch_valid_from="2020-01-01T00:00:00+00:00",
                   watch_ref="co_target"):
    mc = StateStore(tmp_path / "mc")
    for t in threats:
        mc.append("threats", t)
    cstore = StateStore(tmp_path / "cust")
    upsert_customer(cstore, CustomerProfile(customer_id="w", name="Watcher",
                                            effective_from="2020-01-01T00:00:00+00:00",
                                            created_at="2020-01-01T00:00:00+00:00"))
    add_watch(cstore, WatchlistEntry(customer_id="w", object_type="ENTITY", ref=watch_ref,
                                     valid_from=watch_valid_from))
    cmc_store = StateStore(tmp_path / "cmc")
    return mc, cstore, cmc_store


# --- (1) fan-out materializes relevant changes; nothing for irrelevant customers ----------------

def test_fanout_inserts_relevant_and_nothing_for_irrelevant(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    report = fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    assert report["inserted"] > 0
    torch = _latest_versions(cmc_store, "torch")
    dap = _latest_versions(cmc_store, "dap")
    assert torch and dap
    # An unknown/irrelevant customer id has no rows written.
    assert _latest_versions(cmc_store, "nobody") == {}
    # Fan-out membership equals the on-the-fly read model relevant set (never diverges).
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "p", tmp_path / "o",
                              mc_store=mc, customer_store=cstore)
    onfly = {c["id"] for c in console.material_changes("torch")["material_changes"]}
    assert set(torch) == onfly


# --- (2) stable identity + idempotent fan-out ---------------------------------------------------

def test_identity_stable_and_fanout_idempotent(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    r1 = fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    rows_after_first = len(list(cmc_store.read(cmc.STREAM_CUSTOMER_MATERIAL_CHANGES)))
    ids1 = {(k, v["record_id"]) for k, v in _latest_versions(cmc_store, "torch").items()}
    # material_change_id IS the source intelligence id (the stable linkage M22-B review actions use).
    for mid, v in _latest_versions(cmc_store, "torch").items():
        assert v["material_change_id"] == mid
        assert v["content_version"] == 1
    # Re-running fan-out writes nothing new: every change is a suppressed duplicate.
    r2 = fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    assert r2["inserted"] == 0 and r2["updated"] == 0
    assert r2["duplicates_suppressed"] == r1["inserted"]
    assert len(list(cmc_store.read(cmc.STREAM_CUSTOMER_MATERIAL_CHANGES))) == rows_after_first
    ids2 = {(k, v["record_id"]) for k, v in _latest_versions(cmc_store, "torch").items()}
    assert ids1 == ids2  # identity did not churn on rebuild


# --- (3) STORAGE-level cross-customer isolation --------------------------------------------------

def test_storage_level_isolation_between_customers(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    torch_mids = set(_latest_versions(cmc_store, "torch"))
    dap_mids = set(_latest_versions(cmc_store, "dap"))
    assert torch_mids and dap_mids
    assert torch_mids.isdisjoint(dap_mids)
    # Every stored row is stamped with exactly one customer; a read for one never returns the other's.
    for row in cmc_store.read(cmc.STREAM_CUSTOMER_MATERIAL_CHANGES):
        assert row["customer_id"] in {"torch", "dap"}
    assert all(v["customer_id"] == "torch" for v in _latest_versions(cmc_store, "torch").values())
    assert all(v["customer_id"] == "dap" for v in _latest_versions(cmc_store, "dap").values())


def test_fanout_for_one_customer_never_writes_another(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store, customer_ids=["torch"])
    written_customers = {r["customer_id"] for r in cmc_store.read(cmc.STREAM_CUSTOMER_MATERIAL_CHANGES)}
    assert written_customers == {"torch"}  # DAP was not in the fan-out set → no DAP rows


def test_access_check_rejects_mismatched_customer(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "p", tmp_path / "o",
                              mc_store=mc, customer_store=cstore, cmc_store=cmc_store,
                              access_check=lambda cid: cid == "torch")
    assert console.material_changes("torch")["count"] > 0
    with pytest.raises(PermissionError):
        console.material_changes("dap")
    with pytest.raises(PermissionError):
        console.customer_material_change_versions("dap", "anything")


# --- (4) global intelligence is never touched or mutated by fan-out -----------------------------

def test_fanout_writes_only_customer_scoped_streams(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(tmp_path / "mc")
    for r in StateStore(STATE).read("threats"):
        mc.append("threats", r)
    for r in StateStore(STATE).read("propagated_threats"):
        mc.append("propagated_threats", r)
    before = (tmp_path / "mc" / "threats.jsonl").read_bytes()
    cmc_store = StateStore(tmp_path / "cmc")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    # The global stream is byte-identical: customer fan-out never mutates global truth.
    assert (tmp_path / "mc" / "threats.jsonl").read_bytes() == before
    written = {p.stem for p in (tmp_path / "cmc").glob("*.jsonl")}
    assert written <= {cmc.STREAM_CUSTOMER_MATERIAL_CHANGES, cmc.STREAM_FANOUT_RUNS}
    assert written.isdisjoint(GLOBAL_STREAMS)


# --- (5) first-seen semantics are explicit and distinct -----------------------------------------

def test_first_seen_three_distinct_times(tmp_path):
    mc, cstore, cmc_store = _synthetic_env(
        tmp_path, threats=[_threat("thr_a", subject_ref="co_target")])
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store, now="2026-04-01T00:00:00+00:00")
    v = _latest_versions(cmc_store, "w")["thr_a"]
    # intelligence knowable 2026-03-01; customer configured since 2020; delivered at fan-out 2026-04-01.
    assert v["intelligence_observed_at"].startswith("2026-03-01")
    assert v["delivered_at"] == "2026-04-01T00:00:00+00:00"
    # became relevant = max(observed, config effective) = 2026-03-01 (config predates the event).
    assert v["first_relevant_at"].startswith("2026-03-01")
    assert v["intelligence_observed_at"] != v["delivered_at"]


def test_first_relevant_respects_late_watch(tmp_path):
    # Intelligence knowable 2026-03-01, but the watch that makes it relevant only starts 2026-06-01.
    mc, cstore, cmc_store = _synthetic_env(
        tmp_path, threats=[_threat("thr_late", subject_ref="co_target")],
        watch_valid_from="2026-06-01T00:00:00+00:00")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store, now="2026-07-01T00:00:00+00:00")
    v = _latest_versions(cmc_store, "w")["thr_late"]
    # It could not have been relevant before the watch existed → first_relevant_at = 2026-06-01.
    assert v["first_relevant_at"].startswith("2026-06-01")


# --- (6) temporal: no future leakage; no retrospective watch leakage ----------------------------

def test_no_future_leakage_on_fanout(tmp_path):
    mc, cstore, cmc_store = _synthetic_env(
        tmp_path, threats=[_threat("thr_fut", subject_ref="co_target", observed="2026-03-01T00:00:00+00:00")])
    # Replaying as of a date BEFORE the intelligence was knowable materializes nothing.
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store, as_of="2026-01-01T00:00:00+00:00")
    assert _latest_versions(cmc_store, "w") == {}


def test_no_retrospective_watch_leakage_on_fanout(tmp_path):
    mc, cstore, cmc_store = _synthetic_env(
        tmp_path, threats=[_threat("thr_r", subject_ref="co_target")],
        watch_valid_from="2026-06-01T00:00:00+00:00")
    # As of 2026-04 the watch was not yet held → the change is not relevant → nothing materialized.
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store, as_of="2026-04-01T00:00:00+00:00")
    assert _latest_versions(cmc_store, "w") == {}


# --- (7) update semantics: new version, no duplicate, first-seen carried forward ----------------

def test_assessment_update_appends_version_without_losing_first_seen(tmp_path):
    mc, cstore, cmc_store = _synthetic_env(
        tmp_path, threats=[_threat("thr_u", subject_ref="co_target", severity="MODERATE")])
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store, now="2026-04-01T00:00:00+00:00")
    v1 = _latest_versions(cmc_store, "w")["thr_u"]
    assert v1["content_version"] == 1
    # Global intelligence evolves: severity escalates. Re-fan-out.
    mc.append("threats", _threat("thr_u", subject_ref="co_target", severity="CRITICAL"))
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store, now="2026-05-01T00:00:00+00:00")
    v2 = _latest_versions(cmc_store, "w")["thr_u"]
    assert v2["content_version"] == 2
    assert v2["change_kind"] == cmc.CHANGE_ASSESSMENT
    assert v2["assessment_snapshot"]["materiality"] == "CRITICAL"
    # First-seen fields are immutable across versions (no duplicate card, no lost delivery time).
    assert v2["delivered_at"] == v1["delivered_at"] == "2026-04-01T00:00:00+00:00"
    assert v2["first_relevant_at"] == v1["first_relevant_at"]
    hist = version_history(cmc_store, "w", "thr_u")
    assert [h["content_version"] for h in hist] == [1, 2]


def test_update_preserves_customer_review_lifecycle(tmp_path):
    mc, cstore, cmc_store = _synthetic_env(
        tmp_path, threats=[_threat("thr_lc", subject_ref="co_target", severity="MODERATE")])
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    record_review_action(cstore, customer_id="w", material_change_id="thr_lc", action_type="MONITOR")
    # Global assessment changes; re-fan-out appends a version.
    mc.append("threats", _threat("thr_lc", subject_ref="co_target", severity="CRITICAL"))
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    # The customer lifecycle (a SEPARATE stream keyed by the stable id) survives the derived-state update.
    assert cust.current_review_state(cstore, "w", "thr_lc") == "MONITORING"


# --- (8) outcome propagation without rewriting the original assessment --------------------------

def test_outcome_attaches_as_new_version_preserving_original_assessment(tmp_path):
    mc, cstore, cmc_store = _synthetic_env(
        tmp_path, threats=[_threat("thr_o", subject_ref="co_target", severity="HIGH")])
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    v1 = _latest_versions(cmc_store, "w")["thr_o"]
    assert v1["outcome_state"] == "UNKNOWN"
    # A later global outcome becomes known — same assessment, only the outcome moves.
    mc.append("threats", _threat("thr_o", subject_ref="co_target", severity="HIGH",
                                 outcome="RESOLVED_LOSS"))
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    v2 = _latest_versions(cmc_store, "w")["thr_o"]
    assert v2["content_version"] == 2
    assert v2["change_kind"] == cmc.CHANGE_OUTCOME
    assert v2["outcome_state"] == "RESOLVED_LOSS"
    # The ORIGINAL assessment version is retained unchanged — history is not flattened (§12).
    hist = version_history(cmc_store, "w", "thr_o")
    assert hist[0]["outcome_state"] == "UNKNOWN"
    assert hist[0]["assessment_snapshot"] == hist[1]["assessment_snapshot"]


# --- (9) rebuild preserves customer actions -----------------------------------------------------

def test_rebuild_preserves_customer_actions_and_is_idempotent(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    mid = next(iter(_latest_versions(cmc_store, "torch")))
    record_review_action(cstore, customer_id="torch", material_change_id=mid, action_type="DISMISS")
    rows_before = len(list(cmc_store.read(cmc.STREAM_CUSTOMER_MATERIAL_CHANGES)))
    rebuild_customer(mc_store=mc, customer_store=cstore, cmc_store=cmc_store, customer_id="torch")
    # Rebuild of unchanged derived state adds nothing, and never erases the customer action history.
    assert len(list(cmc_store.read(cmc.STREAM_CUSTOMER_MATERIAL_CHANGES))) == rows_before
    assert cust.current_review_state(cstore, "torch", mid) == "DISMISSED"


# --- (10) production-shaped read path serves the persisted customer-scoped state ----------------

def test_read_path_serves_persisted_first_seen(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "p", tmp_path / "o",
                              mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    view = console.material_changes("torch")
    assert view["materialized"] == view["count"] > 0
    for change in view["material_changes"]:
        fs = change["first_seen"]
        assert fs["status"] == "MATERIALIZED"
        assert fs["delivered_at"] and fs["intelligence_observed_at"] and fs["first_relevant_at"]
        assert fs["content_version"] >= 1


def test_read_path_without_cmc_store_is_backward_compatible(tmp_path):
    # No cmc_store → behaves exactly as M22-A/B (no first_seen block, no materialized count).
    cstore = _seeded_customers(tmp_path)
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "p", tmp_path / "o",
                              mc_store=StateStore(STATE), customer_store=cstore)
    view = console.material_changes("torch")
    assert view["materialized"] is None
    assert all("first_seen" not in c for c in view["material_changes"])


# --- (11) failure isolation: one bad customer does not corrupt others ----------------------------

def test_bad_customer_is_isolated_and_recorded(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    # "ghost" has no persisted profile → its context build fails; torch must still be materialized.
    report = fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store,
                     customer_ids=["ghost", "torch"])
    assert report["failure_count"] == 1
    assert report["failures"][0]["customer_id"] == "ghost"
    assert _latest_versions(cmc_store, "torch")  # unaffected
    assert _latest_versions(cmc_store, "ghost") == {}


# --- (12) observability report ------------------------------------------------------------------

def test_fanout_report_has_observability_counters(tmp_path):
    cstore = _seeded_customers(tmp_path)
    mc = StateStore(STATE)
    cmc_store = StateStore(tmp_path / "cmc")
    report = fan_out(mc_store=mc, customer_store=cstore, cmc_store=cmc_store)
    for key in ("global_items_evaluated", "inserted", "updated", "duplicates_suppressed",
                "relevant", "suppressed_irrelevant", "failures", "per_customer"):
        assert key in report
    assert report["global_items_evaluated"] > 0
    assert any(pc["customer_id"] == "torch" for pc in report["per_customer"])
    # The run is persisted for operational visibility.
    runs = list(cmc_store.read(cmc.STREAM_FANOUT_RUNS))
    assert runs and runs[-1]["run_id"] == report["run_id"]


# --- API: fan-out trigger + version-history endpoints (no socket) --------------------------------

def _call(console, method, path, body=None):
    import io
    from pyrnova.ops_server import make_handler
    handler_cls = make_handler(console)
    h = handler_cls.__new__(handler_cls)
    h.path = path
    raw = json.dumps(body or {}).encode()
    h.headers = {"Content-Length": str(len(raw))}
    h.rfile = io.BytesIO(raw)
    h.wfile = io.BytesIO()
    h.send_response = lambda *a, **k: None
    h.send_header = lambda *a, **k: None
    h.end_headers = lambda *a, **k: None
    status = {}
    orig = h.send_response
    h.send_response = lambda code, *a, **k: status.update(code=code)
    getattr(h, f"do_{method}")()
    return status.get("code"), json.loads(h.wfile.getvalue().decode() or "{}")


def test_api_fanout_and_versions_roundtrip(tmp_path):
    cstore = _seeded_customers(tmp_path)
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "p", tmp_path / "o",
                              mc_store=StateStore(STATE), customer_store=cstore,
                              cmc_store=StateStore(tmp_path / "cmc"))
    code, report = _call(console, "POST", "/api/fanout", {"customers": ["torch"]})
    assert code == 200 and report["inserted"] > 0
    view = console.material_changes("torch")
    mid = view["material_changes"][0]["id"]
    code, hist = _call(console, "GET", f"/api/material-changes/{mid}/versions?customer=torch")
    assert code == 200
    assert hist["versions"] and hist["versions"][0]["material_change_id"] == mid


def test_api_rejects_unauthorized_customer(tmp_path):
    cstore = _seeded_customers(tmp_path)
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "p", tmp_path / "o",
                              mc_store=StateStore(STATE), customer_store=cstore,
                              cmc_store=StateStore(tmp_path / "cmc"),
                              access_check=lambda cid: cid == "torch")
    code, out = _call(console, "GET", "/api/material-changes?customer=dap")
    assert code == 403 and "authorized" in out["error"]
