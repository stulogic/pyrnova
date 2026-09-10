"""M22-B honesty gate: persisted customer intelligence + tenancy + Material Change lifecycle.

Covers the M22-B acceptance priorities (see ``docs/specs/M22B_PERSISTED_CUSTOMER_LIFECYCLE.md``):
persistence survives restart; watchlists drive deterministic relevance; customer isolation and
private-context non-interference; lifecycle persists and never rewrites system assessment; review history
is reconstructable; outcome linkage is preserved; no future-event or retrospective-watchlist leakage; demo
data seeds the persisted structures rather than being runtime hard-coding; M22-A behavior is compatible.

Uses the REAL M22-A archived-evidence fixture (threats / propagated_threats) — no fabrication.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from pyrnova import customers as cust
from pyrnova.customers import (
    CustomerProfile,
    WatchlistEntry,
    add_watch,
    build_context,
    get_customer,
    list_customers,
    record_review_action,
    retire_watch,
    upsert_customer,
)
from pyrnova.material_changes import build_material_changes
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"


def _demo_records():
    store = StateStore(STATE)
    return list(store.read("threats")), list(store.read("propagated_threats"))


def _load_seeder():
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seeded_store(tmp_path) -> StateStore:
    store = StateStore(tmp_path / "customers")
    _load_seeder().seed(store)
    return store


# --- (1) persisted customer survives a restart / read cycle ------------------------------------

def test_persisted_customer_survives_restart(tmp_path):
    root = tmp_path / "cust"
    store = StateStore(root)
    upsert_customer(store, CustomerProfile(customer_id="acme", name="Acme Corp",
                                           entity_refs=["co_acme"], capabilities=["software"]))
    add_watch(store, WatchlistEntry(customer_id="acme", object_type="PROGRAM", ref="W31P4Q21F0095"))
    # A genuinely fresh store object at the same root (simulates a process restart).
    reloaded = StateStore(root)
    profile = get_customer(reloaded, "acme")
    assert profile is not None and profile.name == "Acme Corp"
    ctx = build_context(reloaded, "acme")
    assert ctx.entity_refs == ["co_acme"]
    assert "W31P4Q21F0095" in ctx.watched_programs


# --- (2) persisted watchlist drives deterministic relevance ------------------------------------

def test_watchlist_drives_relevance_and_retire_removes_it(tmp_path):
    threats, propagated = _demo_records()
    # A minimal customer whose ONLY relevance channel to the SAIC change is a single entity watch (no
    # entity_refs, no agencies, no program watch) so the effect of that one watch is isolated.
    store = StateStore(tmp_path / "c")
    upsert_customer(store, CustomerProfile(customer_id="w1", name="Watcher One"))
    watch = add_watch(store, WatchlistEntry(customer_id="w1", object_type="ENTITY", ref="co_saic"))
    ctx = build_context(store, "w1")
    changes = build_material_changes(threats=threats, propagated_threats=propagated, context=ctx)
    bases = {c["relevance"]["basis"] for c in changes}
    # The watch alone made the SAIC change (and the threat propagating THROUGH SAIC) relevant.
    assert changes and bases == {"WATCHED_ENTITY"}
    assert "co_saic" in {c["observed"]["affected_entity_ref"] for c in changes}

    # Retire the watch → with no remaining relevance channel, the change disappears entirely.
    retire_watch(store, "w1", watch["id"])
    changes2 = build_material_changes(threats=threats, propagated_threats=propagated,
                                      context=build_context(store, "w1"))
    assert changes2 == []


# --- (3) two customers remain isolated ---------------------------------------------------------

def test_two_customers_isolated(tmp_path):
    threats, propagated = _demo_records()
    store = _seeded_store(tmp_path)
    torch = build_material_changes(threats=threats, propagated_threats=propagated,
                                   context=build_context(store, "torch"))
    dap = build_material_changes(threats=threats, propagated_threats=propagated,
                                 context=build_context(store, "dap"))
    torch_subjects = {m["observed"]["affected_entity_ref"] for m in torch}
    dap_subjects = {m["observed"]["affected_entity_ref"] for m in dap}
    assert torch_subjects and dap_subjects
    assert torch_subjects.isdisjoint(dap_subjects)
    assert not any(m["refs"]["program"] == "36C25726N0240" for m in torch)
    assert not any(m["refs"]["program"] == "47QFSA20F0057" for m in dap)


# --- (4) one customer's private context never affects another -----------------------------------

def test_private_context_does_not_leak_between_customers(tmp_path):
    threats, propagated = _demo_records()
    store = _seeded_store(tmp_path)
    dap_before = build_material_changes(threats=threats, propagated_threats=propagated,
                                        context=build_context(store, "dap"))
    # Torch adds a private program watch. This is torch-private; DAP must be completely unaffected.
    add_watch(store, WatchlistEntry(customer_id="torch", object_type="PROGRAM", ref="ZZ-PRIVATE-1"))
    dap_after = build_material_changes(threats=threats, propagated_threats=propagated,
                                       context=build_context(store, "dap"))
    assert dap_before == dap_after
    # And torch's own configuration did change (the private write took effect for torch only).
    assert "ZZ-PRIVATE-1" in build_context(store, "torch").watched_programs
    assert "ZZ-PRIVATE-1" not in build_context(store, "dap").watched_programs


# --- (5,6) lifecycle persists; system assessment stays intact -----------------------------------

def test_lifecycle_persists_and_does_not_alter_system_assessment(tmp_path):
    threats, propagated = _demo_records()
    cstore = _seeded_store(tmp_path)
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "prof", tmp_path / "out",
                              mc_store=StateStore(STATE), customer_store=cstore)
    view = console.material_changes("dap")
    change = view["material_changes"][0]
    change_id = change["id"]
    assessment_before = json.loads(json.dumps(change["assessment"]))
    threats_bytes_before = (STATE / "threats.jsonl").read_bytes()

    console.record_customer_review("dap", change_id, action_type="DISMISS",
                                   actor="analyst_1", reason="accepted risk")

    # Restart: a fresh console over the same customer store still sees the DISMISSED state.
    console2 = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "prof", tmp_path / "out",
                               mc_store=StateStore(STATE), customer_store=StateStore(tmp_path / "customers"))
    view2 = console2.material_changes("dap")
    same = next(c for c in view2["material_changes"] if c["id"] == change_id)
    assert same["review"]["state"] == "DISMISSED"
    # The customer dismissal did NOT rewrite Pyrnova's system assessment or the authoritative stream.
    assert same["assessment"] == assessment_before
    assert (STATE / "threats.jsonl").read_bytes() == threats_bytes_before


# --- (6b) global vs customer-private boundary ---------------------------------------------------

def test_customer_private_writes_never_touch_global_intelligence_streams(tmp_path):
    threats, propagated = _demo_records()
    store = _seeded_store(tmp_path)
    # Exercise every customer-private write path.
    add_watch(store, WatchlistEntry(customer_id="torch", object_type="ENTITY", ref="co_new"))
    ctx = build_context(store, "torch")
    changes = build_material_changes(threats=threats, propagated_threats=propagated, context=ctx)
    record_review_action(store, customer_id="torch", material_change_id=changes[0]["id"],
                         action_type="MONITOR")
    written = {p.stem for p in (tmp_path / "customers").glob("*.jsonl")}
    assert written <= {cust.STREAM_CUSTOMERS, cust.STREAM_WATCHLIST, cust.STREAM_REVIEW_ACTIONS}
    assert written.isdisjoint(set(cust.GLOBAL_INTELLIGENCE_STREAMS))


# --- (7) historical review/action state is reconstructable -------------------------------------

def test_review_history_is_point_in_time_reconstructable(tmp_path):
    store = _seeded_store(tmp_path)
    mid = "thr_demo_change"
    record_review_action(store, customer_id="torch", material_change_id=mid,
                         action_type="MARK_REVIEWED", at="2026-01-10T00:00:00+00:00")
    record_review_action(store, customer_id="torch", material_change_id=mid,
                         action_type="MONITOR", at="2026-02-10T00:00:00+00:00")
    record_review_action(store, customer_id="torch", material_change_id=mid,
                         action_type="DISMISS", at="2026-03-10T00:00:00+00:00")
    assert cust.current_review_state(store, "torch", mid) == "DISMISSED"
    # As of mid-February only the first two actions had happened.
    assert cust.current_review_state(store, "torch", mid, as_of="2026-02-15T00:00:00+00:00") == "MONITORING"
    hist = cust.review_history(store, "torch", mid, as_of="2026-02-15T00:00:00+00:00")
    assert [h["action_type"] for h in hist] == ["MARK_REVIEWED", "MONITOR"]
    assert hist[0]["from_state"] == "NEW" and hist[1]["from_state"] == "REVIEWED"


# --- (8) outcome linkage is preserved; UNRESOLVED is first-class --------------------------------

def test_outcome_linkage_preserved_and_unresolved_first_class(tmp_path):
    store = _seeded_store(tmp_path)
    mid = "thr_outcome_change"
    # A review action with no outcome is valid and honest — UNRESOLVED stays first-class.
    r1 = record_review_action(store, customer_id="torch", material_change_id=mid, action_type="MONITOR")
    assert r1["action"]["outcome_ref"] is None
    # A resolution can link to an existing Pyrnova outcome id, preserving the lineage.
    r2 = record_review_action(store, customer_id="torch", material_change_id=mid, action_type="RESOLVE",
                              outcome_ref="outc_abc123", reason="program restored")
    assert r2["to_state"] == "RESOLVED"
    hist = cust.review_history(store, "torch", mid)
    assert hist[-1]["outcome_ref"] == "outc_abc123"


# --- (9) no future-event leakage (persisted path) ----------------------------------------------

def test_no_future_event_leakage_on_persisted_path(tmp_path):
    threats, propagated = _demo_records()
    store = _seeded_store(tmp_path)
    ctx = build_context(store, "dap", as_of="2026-08-01")
    before = build_material_changes(threats=threats, propagated_threats=propagated, context=ctx,
                                    as_of="2026-08-01")
    ctx2 = build_context(store, "dap", as_of="2026-09-01")
    after = build_material_changes(threats=threats, propagated_threats=propagated, context=ctx2,
                                   as_of="2026-09-01")
    assert before == []
    assert any(m["observed"]["event_type"] == "CONTRACT_TERMINATION" for m in after)


# --- (10) no retrospective watchlist leakage ---------------------------------------------------

def test_no_retrospective_watchlist_leakage(tmp_path):
    store = _seeded_store(tmp_path)
    # A watch added with a 2026 valid_from must not appear when replaying customer state as of 2021.
    add_watch(store, WatchlistEntry(customer_id="torch", object_type="ENTITY", ref="co_late_watch",
                                    valid_from="2026-05-01T00:00:00+00:00"))
    past = build_context(store, "torch", as_of="2021-01-01T00:00:00+00:00")
    present = build_context(store, "torch", as_of="2026-06-01T00:00:00+00:00")
    assert "co_late_watch" not in past.watched_entity_refs
    assert "co_late_watch" in present.watched_entity_refs


# --- (11) demo fixtures are not production hard-coding ------------------------------------------

def test_demo_seeds_persisted_structures(tmp_path):
    store = _seeded_store(tmp_path)
    ids = {c["id"] for c in list_customers(store)}
    assert {"torch", "dap"} <= ids
    # Re-running the seed is idempotent (no duplicate customer versions, stable watch ids).
    before = len(list(store.read(cust.STREAM_CUSTOMERS)))
    _load_seeder().seed(store)
    assert len(list(store.read(cust.STREAM_CUSTOMERS))) == before


def test_runtime_package_does_not_hardcode_demo_customers():
    # The demo customer identities must live in examples/, never in the pyrnova runtime package.
    import subprocess
    hits = subprocess.run(
        ["grep", "-rniE", "torch technologies|dap construction|47QFSA20F0057|36C25726N0240",
         "pyrnova"],
        capture_output=True, text=True).stdout
    assert hits.strip() == "", f"runtime package references demo specifics:\n{hits}"


# --- (12) M22-A read behavior remains compatible ------------------------------------------------

def test_persisted_path_matches_demo_json_relevance(tmp_path):
    threats, propagated = _demo_records()
    store = _seeded_store(tmp_path)
    # Persisted context and the committed M22-A demo JSON context must select the same relevant changes.
    from pyrnova.material_changes import CustomerContext
    demo_ctx = CustomerContext.from_dict(json.loads((DEMO / "torch.json").read_text()))
    persisted = build_material_changes(threats=threats, propagated_threats=propagated,
                                       context=build_context(store, "torch"))
    demo = build_material_changes(threats=threats, propagated_threats=propagated, context=demo_ctx)
    assert {c["id"] for c in persisted} == {c["id"] for c in demo}


def test_console_material_changes_carries_review_overlay(tmp_path):
    cstore = _seeded_store(tmp_path)
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "prof", tmp_path / "out",
                              mc_store=StateStore(STATE), customer_store=cstore)
    view = console.material_changes("torch")
    assert view["count"] >= 2
    assert all("review" in c and c["review"]["state"] == "NEW" for c in view["material_changes"])
    assert "by_review_state" in view and view["by_review_state"].get("NEW") == view["count"]


# --- tenancy: cross-customer access is rejected -------------------------------------------------

def test_cross_customer_review_action_rejected(tmp_path):
    cstore = _seeded_store(tmp_path)
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "prof", tmp_path / "out",
                              mc_store=StateStore(STATE), customer_store=cstore)
    dap_change = console.material_changes("dap")["material_changes"][0]["id"]
    # Torch must not be able to act on a Material Change that belongs to DAP.
    with pytest.raises(ValueError, match="cross-customer"):
        console.record_customer_review("torch", dap_change, action_type="DISMISS")


def test_cross_customer_watch_retire_rejected(tmp_path):
    store = _seeded_store(tmp_path)
    torch_watch = cust.list_watches(store, "torch")[0]["id"]
    with pytest.raises(ValueError, match="cross-customer"):
        retire_watch(store, "dap", torch_watch)


# --- honesty: a free-text watch ref is not silently canonicalized ------------------------------

def test_free_text_watch_ref_is_marked_unresolved(tmp_path):
    store = StateStore(tmp_path / "c")
    upsert_customer(store, CustomerProfile(customer_id="c1", name="C1"))
    resolved = add_watch(store, WatchlistEntry(customer_id="c1", object_type="ENTITY", ref="co_real"))
    freetext = add_watch(store, WatchlistEntry(customer_id="c1", object_type="ENTITY",
                                               ref="Some Company We Typed In"))
    assert resolved["resolved"] is True
    assert freetext["resolved"] is False and freetext["resolution_note"]


# --- API: handler routing for the new write endpoints (no socket) -------------------------------

def _handler(console):
    from pyrnova.ops_server import make_handler
    return make_handler(console)


def _call(console, method, path, body=None):
    import io
    handler_cls = _handler(console)
    h = handler_cls.__new__(handler_cls)
    h.path = path
    raw = json.dumps(body or {}).encode()
    h.headers = {"Content-Length": str(len(raw))}
    h.rfile = io.BytesIO(raw)
    h.wfile = io.BytesIO()
    h.send_response = lambda *a, **k: None
    h.send_header = lambda *a, **k: None
    h.end_headers = lambda *a, **k: None
    getattr(h, f"do_{method}")()
    return json.loads(h.wfile.getvalue().decode() or "{}")


def test_api_review_action_roundtrip(tmp_path):
    cstore = _seeded_store(tmp_path)
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "prof", tmp_path / "out",
                              mc_store=StateStore(STATE), customer_store=cstore)
    change_id = console.material_changes("dap")["material_changes"][0]["id"]
    out = _call(console, "POST", f"/api/material-changes/{change_id}/review",
                {"customer": "dap", "action_type": "MARK_REVIEWED"})
    assert out["to_state"] == "REVIEWED"
    # The state is visible through the read API and its review-history endpoint.
    hist = _call(console, "GET", f"/api/material-changes/{change_id}/review-history?customer=dap")
    assert hist["current_state"] == "REVIEWED"
    view = _call(console, "GET", "/api/material-changes?customer=dap")
    same = next(c for c in view["material_changes"] if c["id"] == change_id)
    assert same["review"]["state"] == "REVIEWED"


def test_api_customer_and_watch_crud(tmp_path):
    console = OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "prof", tmp_path / "out",
                              mc_store=StateStore(STATE), customer_store=StateStore(tmp_path / "c"))
    _call(console, "POST", "/api/customers", {"customer_id": "acme", "name": "Acme",
                                              "capabilities": ["software"]})
    _call(console, "POST", "/api/customers/acme/watchlist",
          {"object_type": "PROGRAM", "ref": "W31P4Q21F0095"})
    profile = _call(console, "GET", "/api/customers/acme")
    assert profile["name"] == "Acme"
    assert any(w["ref"] == "W31P4Q21F0095" for w in profile["watchlist"])
    listing = _call(console, "GET", "/api/customers")
    assert any(c["id"] == "acme" for c in listing["customers"])


def test_invalid_watch_and_action_are_rejected(tmp_path):
    store = StateStore(tmp_path / "c")
    with pytest.raises(ValueError):
        WatchlistEntry(customer_id="c1", object_type="NONSENSE", ref="x")
    with pytest.raises(ValueError):
        WatchlistEntry(customer_id="c1", object_type="ENTITY", ref="")
    with pytest.raises(ValueError):
        cust.ReviewAction(customer_id="c1", material_change_id="m", action_type="FLY",
                          from_state="NEW", to_state="NEW")
