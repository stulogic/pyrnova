"""M22-A honesty gate: Material Changes read model + customer relevance + read path.

Deterministic, point-in-time, customer-isolated projection over EXISTING intelligence. No fabrication:
the demo fixture is generated from real archived evidence by
``examples/material_changes_demo/build_seed.py``.
"""

import io
import json
from pathlib import Path

from pyrnova.material_changes import (
    CustomerContext,
    assess_relevance,
    build_material_changes,
)
from pyrnova.ops import OperatorConsole
from pyrnova.ops_server import make_handler
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"


def _demo_records():
    store = StateStore(STATE)
    return list(store.read("threats")), list(store.read("propagated_threats"))


def _ctx(name):
    return CustomerContext.from_dict(json.loads((DEMO / f"{name}.json").read_text()))


# --- relevance + isolation ---------------------------------------------------------------------

def test_relevance_is_deterministic_and_requires_a_structured_match():
    ctx = _ctx("torch")
    # A change on an unrelated entity/program/agency with no capability match is NOT relevant.
    unrelated = {"subject_ref": "co_unrelated", "affected_program": "ZZZ", "agency": "NASA",
                 "capability_classes": [], "path_refs": []}
    assert assess_relevance(unrelated, ctx) is None
    # A watched program alone is a structured, inspectable match.
    watched = {"subject_ref": "co_unrelated", "affected_program": "47QFSA20F0057", "agency": "NASA",
               "capability_classes": [], "path_refs": []}
    rel = assess_relevance(watched, ctx)
    assert rel and rel["basis"] == "WATCHED_PROGRAM" and "47QFSA20F0057" in rel["detail"]


def test_customer_isolation_real_fixture():
    threats, propagated = _demo_records()
    torch = build_material_changes(threats=threats, propagated_threats=propagated, context=_ctx("torch"))
    dap = build_material_changes(threats=threats, propagated_threats=propagated, context=_ctx("dap"))
    torch_subjects = {m["observed"]["affected_entity_ref"] for m in torch}
    dap_subjects = {m["observed"]["affected_entity_ref"] for m in dap}
    # Each customer sees only its own relevant changes; the two sets do not bleed into each other.
    assert "co_torch" in torch_subjects and "co_saic" in torch_subjects
    assert "co_dap_sub" in dap_subjects and "co_uei_KMSLVW1MZWU9" in dap_subjects
    assert torch_subjects.isdisjoint(dap_subjects)
    # DAP's terminated award never appears for Torch, and vice versa.
    assert not any(m["refs"]["program"] == "36C25726N0240" for m in torch)
    assert not any(m["refs"]["program"] == "47QFSA20F0057" for m in dap)


# --- observed vs assessed (must never flatten) --------------------------------------------------

def test_observed_and_assessment_are_separate_structured_blocks():
    threats, propagated = _demo_records()
    mc = build_material_changes(threats=threats, propagated_threats=propagated, context=_ctx("dap"))
    direct = next(m for m in mc if m["relevance"]["basis"] == "DIRECT_SUBJECT")
    assert set(direct) >= {"observed", "assessment"}
    # The observed event is a real OBSERVED catalyst; the assessment is explicitly Pyrnova's judgment.
    assert direct["observed"]["catalyst_class"] == "OBSERVED"
    assert direct["observed"]["event_type"] == "CONTRACT_TERMINATION"
    assert direct["assessment"]["is_assessment"] is True
    # Materiality (severity) and confidence are orthogonal fields, not one blended number.
    assert direct["assessment"]["materiality"] == "LOW"
    assert direct["assessment"]["confidence"] == "HIGH"
    assert direct["observed"].get("materiality") is None  # severity does not live in the observed block


# --- temporal truth ----------------------------------------------------------------------------

def test_point_in_time_hides_future_changes():
    threats, propagated = _demo_records()
    ctx = _ctx("dap")
    # The DAP termination is observable on 2026-08-31; an earlier cutoff must not reveal it.
    before = build_material_changes(threats=threats, propagated_threats=propagated, context=ctx,
                                    as_of="2026-08-01")
    after = build_material_changes(threats=threats, propagated_threats=propagated, context=ctx,
                                   as_of="2026-09-01")
    assert before == []
    assert any(m["observed"]["event_type"] == "CONTRACT_TERMINATION" for m in after)


# --- evidence: referenced, not duplicated; independence not overclaimed --------------------------

def test_evidence_is_referenced_not_duplicated_and_independence_is_conservative():
    threats, propagated = _demo_records()
    mc = build_material_changes(threats=threats, propagated_threats=propagated, context=_ctx("dap"))
    direct = next(m for m in mc if m["relevance"]["basis"] == "DIRECT_SUBJECT")
    ev = direct["evidence"]
    assert ev["evidence_ids"] and all(isinstance(x, str) for x in ev["evidence_ids"])  # ids, not bodies
    # All evidence is USAspending: one authoritative source => single-source, not independent corroboration.
    assert ev["independent_source_count"] == 1
    assert ev["single_source"] is True
    assert ev["raw_authoritative_bytes"] is True  # M21 termination is raw-archived bytes


# --- ordering + disposition filter -------------------------------------------------------------

def test_stable_ordering_direct_subject_before_watched_entity():
    threats, propagated = _demo_records()
    mc = build_material_changes(threats=threats, propagated_threats=propagated, context=_ctx("torch"))
    bases = [m["relevance"]["basis"] for m in mc]
    assert bases.index("DIRECT_SUBJECT") < bases.index("WATCHED_ENTITY")


def test_disposition_filter():
    threats, propagated = _demo_records()
    only_threats = build_material_changes(threats=threats, propagated_threats=propagated,
                                          context=_ctx("dap"), disposition="threat")
    assert only_threats and all(m["disposition"] == "THREAT" for m in only_threats)
    assert build_material_changes(threats=threats, propagated_threats=propagated,
                                  context=_ctx("dap"), disposition="OPPORTUNITY") == []


# --- console + read path -----------------------------------------------------------------------

def _console(tmp_path):
    store = StateStore(tmp_path / "state")
    return OperatorConsole(store, tmp_path / "profiles", tmp_path / "out",
                           mc_store=StateStore(STATE), contexts_dir=DEMO)


def test_console_material_changes_and_customers(tmp_path):
    console = _console(tmp_path)
    ids = {c["id"] for c in console.customers()}
    assert {"torch", "dap"} <= ids
    view = console.material_changes("torch")
    assert view["customer"]["id"] == "torch"
    assert view["count"] == len(view["material_changes"]) >= 2
    assert view["by_disposition"].get("THREAT")


def test_handler_routes_material_changes_without_a_socket(tmp_path):
    console = _console(tmp_path)
    handler_cls = make_handler(console)
    handler = handler_cls.__new__(handler_cls)
    handler.path = "/api/material-changes?customer=dap"
    handler.headers = {}
    handler.wfile = io.BytesIO()
    handler.send_response = lambda *a, **k: None
    handler.send_header = lambda *a, **k: None
    handler.end_headers = lambda *a, **k: None
    handler.do_GET()
    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert payload["customer"]["id"] == "dap"
    assert payload["material_changes"][0]["disposition"] == "THREAT"


def test_seed_fixture_is_present_and_real():
    # The demo fixture must exist (generated from real archived evidence) so the read path is populated.
    threats, propagated = _demo_records()
    assert threats and propagated
    dap = next(t for t in threats if t["mechanism"] == "PROGRAM_CANCELLATION_OR_DELAY")
    assert dap["meta"]["archive_hash"]  # raw-archived provenance carried through
    assert dap["meta"]["event_time"] == "2026-08-31"
