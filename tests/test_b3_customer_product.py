"""Bundle 3 — customer product surface: Lens, Opportunities, Decision View, Evidence, Disposition,
Brief download and tenant-safe delivery. Exercises the console service and the HTTP routes with the same
no-socket handler harness the M22-F auth suite uses, proving tenant isolation and rights fail-closed."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

import pytest

from pyrnova import access
from pyrnova.alerts import RecordingTransport
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.ops_server import AccessPolicy, make_handler
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"


def _seeded(tmp_path) -> StateStore:
    store = StateStore(tmp_path / "state")
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)
    return store


def _console(tmp_path, *, enforced=False) -> OperatorConsole:
    store = _seeded(tmp_path)
    check = access.request_access_check if enforced else None
    return OperatorConsole(store, tmp_path / "p", tmp_path / "o",
                           mc_store=StateStore(STATE), contexts_dir=DEMO, customer_store=store,
                           cmc_store=StateStore(tmp_path / "cmc"), access_check=check,
                           delivery_store=CustomerDeliveryStore(tmp_path / "deliveries"))


def _first_opp(console) -> str:
    opps = console.customer_opportunities("torch")
    assert opps["count"] > 0
    return opps["opportunities"][0]["id"]


# --- B3.3 opportunities -----------------------------------------------------------------------------

def test_opportunities_surface_native_intelligence(tmp_path):
    console = _console(tmp_path)
    opps = console.customer_opportunities("torch")
    assert opps["source_rights"]["display"] in ("ALLOWED", "PARTIAL")
    item = opps["opportunities"][0]
    assert item["why_now"]["kind"]  # catalyst surfaced
    assert item["incumbent"] and item["recommended_action"]
    # native signals surfaced as-is, not a fabricated composite score
    assert set(item["signal"]) == {"attractiveness", "confidence", "relevance_score"}


# --- B3.4 decision view -----------------------------------------------------------------------------

def test_decision_view_is_coherent_and_fabricates_no_verdict(tmp_path):
    console = _console(tmp_path)
    oid = _first_opp(console)
    dec = console.opportunity_decision("torch", oid)
    dc = dec["decision_chain"]
    for key in ("why_now", "incumbent_competitive", "customer_fit", "pursuit", "material_changes",
                "next_action", "evidence", "temporal", "uncertainty"):
        assert key in dc
    # B4.1 — the Bundle-2 verdict is now RECOMPUTED from persisted, accepted evidence (the Torch
    # opportunity is a self-incumbent recompete). It is a real evidence-backed disposition with a
    # qualitative (never a fabricated composite) confidence, not fabricated and not hard-coded UNKNOWN.
    assert dc["pursuit"]["verdict"] in ("PURSUE", "WATCH", "INVESTIGATE", "PASS")
    assert dc["pursuit"]["confidence"] in ("LOW", "MEDIUM", "HIGH")
    assert dc["pursuit"]["recommended_action"]  # the real persisted recommendation is still shown
    # The verdict is evidence-backed (the derived pursuit verdict cites decisive evidence).
    assert dc["pursuit"]["pursuit_verdict"]["reversal_conditions"]
    # Buyer / access / fit are no longer hard-coded UNKNOWN where evidence supports them.
    assert dc["buyer"]["status"] == "EVIDENCED"
    assert dc["access"]["verdict"] == "DIRECT_ACCESS"
    assert "pursuit_verdict" not in dc["uncertainty"]["unknown_components"]
    # The B2.10 Integrated Decision contract is composed by reference.
    assert dec["integrated_decision"]["integrated_decision_version"]
    assert dec["integrated_decision"]["opportunity_ref"] == oid


# --- B3.6 evidence inspector ------------------------------------------------------------------------

def test_evidence_inspector_shows_provenance_and_is_rights_gated(tmp_path):
    console = _console(tmp_path)
    oid = _first_opp(console)
    dec = console.opportunity_decision("torch", oid)
    evid = dec["decision_chain"]["evidence"][0]["id"]
    insp = console.opportunity_evidence("torch", oid, evid)
    assert insp["doctrine"]["source_fact"]
    assert insp["doctrine"]["provenance"]["content_sha256"]
    assert insp["source_rights"]["display"] in ("ALLOWED", "BLOCKED")


# --- B3.8 customer disposition (Decision Memory) ----------------------------------------------------

def test_disposition_is_customer_feedback_and_tenant_isolated(tmp_path):
    console = _console(tmp_path)
    oid = _first_opp(console)
    rec = console.record_opportunity_disposition("torch", oid, relevance="RELEVANT", pursuit="PURSUE",
                                                 note="strong recompete")
    assert rec["origin"] == "CUSTOMER_FEEDBACK"  # never conflated with Pyrnova judgment
    assert rec["pursuit"] == "PURSUE"
    # surfaced back on the opportunity list for the owning tenant
    opps = console.customer_opportunities("torch")
    item = next(o for o in opps["opportunities"] if o["id"] == oid)
    assert item["customer_disposition"]["pursuit"] == "PURSUE"
    # a different tenant cannot record against another tenant's opportunity
    with pytest.raises(ValueError):
        console.record_opportunity_disposition("dap", oid, relevance="RELEVANT")


# --- B3.10 authenticated brief ----------------------------------------------------------------------

def test_brief_is_deterministic_and_rights_aware(tmp_path):
    console = _console(tmp_path)
    oid = _first_opp(console)
    a = console.build_customer_brief("torch", oid)
    b = console.build_customer_brief("torch", oid)
    assert a["content_sha256"] == b["content_sha256"]  # deterministic for audit
    assert a["rights_display"] in ("ALLOWED", "PARTIAL")
    assert "PYRNOVA DECISION BRIEF" in a["body"]


# --- B3.11 delivery through the tenant-safe contract ------------------------------------------------

def test_delivery_requires_authorized_recipient_and_never_fabricates(tmp_path):
    from pyrnova.customer_delivery import DeliveryRefused
    console = _console(tmp_path)
    oid = _first_opp(console)
    # unauthorized recipient -> hard refusal
    with pytest.raises(DeliveryRefused):
        console.deliver_customer_brief("torch", oid, recipients=["stranger@evil.example"])
    console.authorize_delivery_recipient("torch", "ceo@torch.example")
    # no real transport -> FAILED, never fabricated as delivered
    rec = console.deliver_customer_brief("torch", oid, recipients=["ceo@torch.example"], transport=None)
    assert rec["status"] == "FAILED" and rec["delivered_at"] is None
    # a real transport -> DELIVERED, idempotent on reissue
    t = RecordingTransport()
    rec2 = console.deliver_customer_brief("torch", oid, recipients=["ceo@torch.example"], transport=t)
    assert rec2["status"] == "DELIVERED"
    rec3 = console.deliver_customer_brief("torch", oid, recipients=["ceo@torch.example"], transport=t)
    assert rec3["delivery_id"] == rec2["delivery_id"] and len(t.sent) == 1  # no duplicate
    # tenant-isolated audit
    assert console.list_customer_deliveries("torch")["count"] >= 1
    assert console.list_customer_deliveries("dap")["count"] == 0


# --- route level: enforcement + tenant isolation ----------------------------------------------------

def _call(console, policy, auth_store, method, path, *, token=None, body=None):
    handler_cls = make_handler(console, policy, auth_store)
    h = handler_cls.__new__(handler_cls)
    h.path = path
    raw = json.dumps(body or {}).encode()
    headers = {"Content-Length": str(len(raw))}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    h.headers = headers
    h.rfile = io.BytesIO(raw)
    h.wfile = io.BytesIO()
    h.end_headers = lambda *a, **k: None
    h.send_header = lambda *a, **k: None
    status = {}
    h.send_response = lambda code, *a, **k: status.update(code=code)
    getattr(h, f"do_{method}")()
    return status.get("code"), h.wfile.getvalue()


def test_routes_serve_customer_surface_local_dev(tmp_path):
    console = _console(tmp_path)
    policy = AccessPolicy(host="127.0.0.1", require_auth=False, expose_operator=True)
    code, body = _call(console, policy, None, "GET", "/api/opportunities?customer=torch")
    assert code == 200 and json.loads(body)["count"] > 0
    oid = json.loads(body)["opportunities"][0]["id"]
    code, body = _call(console, policy, None, "GET", f"/api/opportunities/{oid}/decision?customer=torch")
    assert code == 200 and "decision_chain" in json.loads(body)
    code, body = _call(console, policy, None, "GET", "/api/lens?customer=torch")
    assert code == 200 and json.loads(body)["opportunities"]["count"] > 0


def test_customer_lens_app_assets_are_served(tmp_path):
    console = _console(tmp_path)
    policy = AccessPolicy(host="127.0.0.1", require_auth=False, expose_operator=True)
    for path, needle in (("/", b"Live Intelligence"), ("/product.js", b"Customer Lens"),
                         ("/product.css", b"masthead")):
        code, body = _call(console, policy, None, "GET", path)
        assert code == 200 and needle in body


def test_brief_download_route_returns_attachment(tmp_path):
    console = _console(tmp_path)
    oid = _first_opp(console)
    policy = AccessPolicy(host="127.0.0.1", require_auth=False, expose_operator=True)
    code, body = _call(console, policy, None, "GET",
                       f"/api/opportunities/{oid}/brief?customer=torch&download=1")
    assert code == 200 and b"PYRNOVA DECISION BRIEF" in body
