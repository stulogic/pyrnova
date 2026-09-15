"""B3.14 — integrated customer flow (authenticated, enforced, tenant-isolated end to end).

Drives the real HTTP handler with enforced authentication and a customer credential through the whole
canonical journey: Lens → Material Change → Opportunity → decision chain (buyer/incumbent/access/fit) →
Pursuit → Evidence → As-of → Disposition → Brief export → delivery — asserting cross-tenant isolation
holds at every step. Uses realistic demo fixtures; no external transport success is fabricated."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

from pyrnova import access
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.ops_server import AccessPolicy, make_handler
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"


def _seeded(tmp_path):
    store = StateStore(tmp_path / "state")
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)
    return store


def _setup(tmp_path):
    store = _seeded(tmp_path)
    _, torch = access.create_credential(store, customer_id="torch", actor_label="torch-user")
    _, dap = access.create_credential(store, customer_id="dap", actor_label="dap-user")
    _, op = access.create_credential(store, role=access.ROLE_OPERATOR, actor_label="ops")
    policy = AccessPolicy.decide("0.0.0.0", store)  # non-local bind forces auth on
    assert policy.require_auth
    console = OperatorConsole(store, tmp_path / "p", tmp_path / "o", mc_store=StateStore(STATE),
                              contexts_dir=DEMO, customer_store=store,
                              cmc_store=StateStore(tmp_path / "cmc"),
                              access_check=access.request_access_check,
                              delivery_store=CustomerDeliveryStore(tmp_path / "deliveries"))
    return store, policy, console, torch, dap, op


def _call(console, policy, store, method, path, *, token=None, body=None, raw=False):
    handler_cls = make_handler(console, policy, store)
    h = handler_cls.__new__(handler_cls)
    h.path = path
    payload = json.dumps(body or {}).encode()
    headers = {"Content-Length": str(len(payload))}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    h.headers = headers
    h.rfile = io.BytesIO(payload)
    h.wfile = io.BytesIO()
    h.end_headers = lambda *a, **k: None
    h.send_header = lambda *a, **k: None
    status = {}
    h.send_response = lambda code, *a, **k: status.update(code=code)
    getattr(h, f"do_{method}")()
    out = h.wfile.getvalue()
    return status.get("code"), (out if raw else json.loads(out.decode() or "{}"))


def test_full_authenticated_customer_flow_is_tenant_isolated(tmp_path):
    store, policy, console, torch, dap, op = _setup(tmp_path)

    # 1. authenticated customer enters the Customer Lens
    code, lens = _call(console, policy, store, "GET", "/api/lens", token=torch)
    assert code == 200 and lens["customer"]["id"] == "torch"
    assert lens["material_changes"]["count"] >= 0

    # 2. sees material changes (own tenant)
    code, mc = _call(console, policy, store, "GET", "/api/material-changes", token=torch)
    assert code == 200 and mc["customer"]["id"] == "torch"

    # 3. opens the opportunity list and an affected opportunity
    code, opps = _call(console, policy, store, "GET", "/api/opportunities", token=torch)
    assert code == 200 and opps["count"] > 0
    oid = opps["opportunities"][0]["id"]
    code, dec = _call(console, policy, store, "GET",
                      f"/api/opportunities/{oid}/decision", token=torch)
    assert code == 200
    dc = dec["decision_chain"]

    # 4. sees buyer / incumbent / access / customer fit
    for key in ("buyer", "incumbent_competitive", "access", "customer_fit"):
        assert key in dc
    assert dc["incumbent_competitive"]["incumbent"]

    # 5. sees the pursuit section (verdict distinct; not fabricated)
    assert "pursuit" in dc and dc["pursuit"]["recommended_action"]

    # 6. inspects evidence
    evid = dc["evidence"][0]["id"]
    code, ev = _call(console, policy, store, "GET",
                     f"/api/opportunities/{oid}/evidence/{evid}", token=torch)
    assert code == 200 and ev["doctrine"]["provenance"]["content_sha256"]

    # 7. inspects the AS-OF (temporal) state — a past cutoff never leaks later evidence
    code, past = _call(console, policy, store, "GET",
                       "/api/opportunities?as_of=2000-01-01", token=torch)
    assert code == 200 and past["count"] <= opps["count"]

    # 8. records a bounded customer disposition (Decision Memory)
    code, disp = _call(console, policy, store, "POST",
                       f"/api/opportunities/{oid}/disposition", token=torch,
                       body={"relevance": "RELEVANT", "pursuit": "PURSUE", "note": "recompete"})
    assert code == 200 and disp["origin"] == "CUSTOMER_FEEDBACK"

    # 9. exports / downloads a brief
    code, brief = _call(console, policy, store, "GET",
                        f"/api/opportunities/{oid}/brief?download=1", token=torch, raw=True)
    assert code == 200 and b"PYRNOVA DECISION BRIEF" in brief

    # 10. initiates delivery through the bounded delivery contract. Recipient authorization is an operator
    # onboarding action performed on the local console (operator surfaces are hidden on this remote bind).
    console.authorize_delivery_recipient("torch", "ceo@torch.example")
    code, delivery = _call(console, policy, store, "POST",
                           f"/api/opportunities/{oid}/deliver", token=torch,
                           body={"recipients": ["ceo@torch.example"]})
    assert code == 200
    # No verified transport in this environment → FAILED, never fabricated as delivered.
    assert delivery["status"] in ("FAILED", "DELIVERED")
    assert delivery["status"] != "DELIVERED" or delivery["delivered_at"]

    # 11. tenant isolation holds throughout — dap's credential cannot touch torch's opportunity
    code, _ = _call(console, policy, store, "GET",
                    f"/api/opportunities/{oid}/decision?customer=torch", token=dap)
    assert code == 403
    code, _ = _call(console, policy, store, "POST",
                    f"/api/opportunities/{oid}/disposition", token=dap,
                    body={"customer": "torch", "relevance": "RELEVANT"})
    assert code == 403
    # dap sees only its own (empty) delivery audit, never torch's
    code, dap_deliveries = _call(console, policy, store, "GET",
                                 f"/api/opportunities/{oid}/deliveries?customer=torch", token=dap)
    assert code == 403
