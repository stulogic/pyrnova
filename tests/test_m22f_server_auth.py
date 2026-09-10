"""M22-F HTTP access enforcement + tenant isolation (§31/§34 — the hard release blocker).

Drives the real request handler (no socket) with an explicit :class:`AccessPolicy` and credential store,
proving: authentication is required when enforced; a customer sees only its own tenant and cannot enumerate
or impersonate others; operator surfaces are separated and hidden on a remote bind; and a forged
``customer_id`` never bypasses the boundary.
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

from pyrnova import access
from pyrnova.ops import OperatorConsole
from pyrnova.ops_server import AccessPolicy, make_handler
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"


def _seeded(tmp_path) -> StateStore:
    """Persisted store seeded with the demo customers (torch, dap) + used as the credential store."""
    store = StateStore(tmp_path / "state")
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)
    return store


def _console(store: StateStore, tmp_path, *, enforced: bool) -> OperatorConsole:
    check = access.request_access_check if enforced else None
    return OperatorConsole(store, tmp_path / "p", tmp_path / "o",
                           mc_store=StateStore(STATE), customer_store=store,
                           cmc_store=StateStore(tmp_path / "cmc"), access_check=check)


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
    return status.get("code"), json.loads(h.wfile.getvalue().decode() or "{}")


def _enforced(tmp_path, host="0.0.0.0"):
    """An auth-enforced setup with a customer token (torch) and an operator token."""
    store = _seeded(tmp_path)
    _, torch_tok = access.create_credential(store, customer_id="torch", actor_label="torch-user")
    _, dap_tok = access.create_credential(store, customer_id="dap", actor_label="dap-user")
    _, op_tok = access.create_credential(store, role=access.ROLE_OPERATOR, actor_label="ops")
    policy = AccessPolicy.decide(host, store)
    console = _console(store, tmp_path, enforced=policy.require_auth)
    return store, policy, console, torch_tok, dap_tok, op_tok


# --- authentication required (§31.1-4) ----------------------------------------------------------

def test_missing_credential_is_401(tmp_path):
    store, policy, console, *_ = _enforced(tmp_path)
    assert policy.require_auth  # a non-local bind forces enforcement
    code, out = _call(console, policy, store, "GET", "/api/material-changes?customer=torch")
    assert code == 401


def test_invalid_and_revoked_credentials_are_401(tmp_path):
    store, policy, console, torch_tok, _dap, _op = _enforced(tmp_path)
    code, _ = _call(console, policy, store, "GET", "/api/material-changes?customer=torch",
                    token="cred_bogus.secret")
    assert code == 401
    access.revoke_credential(store, torch_tok.split(".")[0])
    code, _ = _call(console, policy, store, "GET", "/api/material-changes?customer=torch",
                    token=torch_tok)
    assert code == 401


def test_valid_credential_reads_own_tenant(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    code, out = _call(console, policy, store, "GET", "/api/material-changes?customer=torch",
                      token=torch_tok)
    assert code == 200 and out["customer"]["id"] == "torch"


# --- tenant isolation (§34 — hard blocker) ------------------------------------------------------

def test_customer_cannot_read_another_tenant(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    # Forged ?customer=dap with torch's credential → 403, never dap's data.
    code, out = _call(console, policy, store, "GET", "/api/material-changes?customer=dap",
                      token=torch_tok)
    assert code == 403


def test_forged_customer_defaults_to_own_scope(tmp_path):
    # A customer route with NO customer param resolves to the authenticated tenant, never a fallback tenant.
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    code, out = _call(console, policy, store, "GET", "/api/material-changes", token=torch_tok)
    assert code == 200 and out["customer"]["id"] == "torch"


def test_customer_cannot_alter_another_tenant_lifecycle(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    code, _ = _call(console, policy, store, "POST", "/api/material-changes/whatever/review",
                    token=torch_tok, body={"customer": "dap", "action_type": "DISMISS"})
    assert code == 403


def test_customer_cannot_read_another_tenant_watchlist(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    code, _ = _call(console, policy, store, "GET", "/api/customers/dap/watchlist", token=torch_tok)
    assert code == 403


def test_customer_cannot_mutate_another_tenant_watchlist(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    code, _ = _call(console, policy, store, "POST", "/api/customers/dap/watchlist",
                    token=torch_tok, body={"object_type": "ENTITY", "ref": "co_x"})
    assert code == 403


def test_investigation_overlay_respects_authenticated_customer(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    # Requesting dap's overlay on a global page with torch's token is refused (no cross-tenant overlay).
    code, _ = _call(console, policy, store, "GET", "/api/company?ref=co_torch&customer=dap",
                    token=torch_tok)
    assert code == 403
    # The global page WITHOUT an overlay is readable by any authenticated actor.
    code, out = _call(console, policy, store, "GET", "/api/company?ref=co_torch", token=torch_tok)
    assert code in (200, 404)  # 404 only if the ref is absent from the demo estate; never 401/403


# --- customer enumeration eliminated (§13/§31.10) -----------------------------------------------

def test_customer_cannot_enumerate_tenants(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    code, out = _call(console, policy, store, "GET", "/api/customers", token=torch_tok)
    assert code == 200
    ids = [c["id"] for c in out["customers"]]
    assert ids == ["torch"]      # only self — never the full tenant list


def test_operator_may_list_all_customers(tmp_path):
    store, policy, console, _t, _d, op_tok = _enforced(tmp_path, host="127.0.0.1")
    code, out = _call(console, policy, store, "GET", "/api/customers", token=op_tok)
    assert code == 200
    ids = {c["id"] for c in out["customers"]}
    assert {"torch", "dap"} <= ids


# --- operator surface separation (§11/§12) ------------------------------------------------------

def test_customer_cannot_reach_operator_surface(tmp_path):
    # Local bind: operator surfaces ARE exposed, so a customer credential is refused with 403 (not merely
    # hidden). Remote-bind hiding (404) is covered separately.
    store, policy, console, torch_tok, *_ = _enforced(tmp_path, host="127.0.0.1")
    for method, path, body in [("GET", "/api/snapshot", None),
                               ("POST", "/api/fanout", {}),
                               ("POST", "/api/customers", {"customer_id": "x", "name": "X"})]:
        code, _ = _call(console, policy, store, method, path, token=torch_tok, body=body)
        assert code == 403, f"{method} {path} should be operator-only"


def test_operator_surface_hidden_on_remote_bind(tmp_path):
    # Bound non-locally, operator surfaces are not exposed at all (§16) — even to an operator credential.
    store, policy, console, _t, _d, op_tok = _enforced(tmp_path, host="0.0.0.0")
    assert policy.expose_operator is False
    code, _ = _call(console, policy, store, "GET", "/api/snapshot", token=op_tok)
    assert code == 404
    code, _ = _call(console, policy, store, "GET", "/console", token=op_tok)
    assert code == 404


def test_operator_surface_available_on_local_bind(tmp_path):
    store = _seeded(tmp_path)
    _, op_tok = access.create_credential(store, role=access.ROLE_OPERATOR)
    policy = AccessPolicy.decide("127.0.0.1", store)   # local, but credentials exist ⇒ auth enforced
    assert policy.require_auth and policy.expose_operator
    console = _console(store, tmp_path, enforced=True)
    code, out = _call(console, policy, store, "GET", "/api/snapshot", token=op_tok)
    assert code == 200


# --- global intelligence requires authentication when enforced (§35, fail-closed) ---------------

def test_global_search_requires_authentication_but_not_a_tenant(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    code, _ = _call(console, policy, store, "GET", "/api/search?q=torch")
    assert code == 401                                   # anonymous global scraping is refused
    code, out = _call(console, policy, store, "GET", "/api/search?q=torch", token=torch_tok)
    assert code == 200                                   # any authenticated actor may search


# --- /api/me identity + posture -----------------------------------------------------------------

def test_me_reports_authenticated_identity(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    code, out = _call(console, policy, store, "GET", "/api/me", token=torch_tok)
    assert code == 200 and out["authenticated"] and out["require_auth"]
    assert out["customer"]["id"] == "torch" and out["customers"] is None   # no enumeration for a customer
    assert out["actor"]["role"] == "customer"


def test_me_unauthenticated_when_enforced(tmp_path):
    store, policy, console, *_ = _enforced(tmp_path)
    code, out = _call(console, policy, store, "GET", "/api/me")
    assert code == 200 and out["require_auth"] and not out["authenticated"]
    assert out["customer"] is None and out["customers"] is None


# --- token never echoed in responses (§30) ------------------------------------------------------

def test_token_never_echoed_in_error_body(tmp_path):
    store, policy, console, torch_tok, *_ = _enforced(tmp_path)
    code, out = _call(console, policy, store, "GET", "/api/material-changes?customer=dap",
                      token=torch_tok)
    assert code == 403
    secret = torch_tok.split(".", 1)[1]
    assert secret not in json.dumps(out)


# --- remote bind forces enforcement; local dev stays permissive (interlock, §16/§30) ------------

def test_policy_interlock(tmp_path):
    empty = StateStore(tmp_path / "empty")
    assert AccessPolicy.decide("0.0.0.0", empty).require_auth is True      # non-local ⇒ always enforced
    assert AccessPolicy.decide("127.0.0.1", empty).require_auth is False   # local, no creds ⇒ dev
    access.create_credential(empty, customer_id="torch")
    assert AccessPolicy.decide("127.0.0.1", empty).require_auth is True    # local + creds ⇒ enforced
