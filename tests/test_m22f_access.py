"""M22-F access core: credential lifecycle, authentication, tenant authorization, request context.

These tests pin the security invariants of :mod:`pyrnova.access` directly (§30/§31): high-entropy secrets,
no persisted plaintext, secure comparison, revocation, fail-closed authorization, actor≠tenant.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyrnova import access
from pyrnova.state import StateStore


def _store(tmp_path) -> StateStore:
    return StateStore(tmp_path / "state")


# --- credential creation + authentication -------------------------------------------------------

def test_create_and_authenticate_roundtrip(tmp_path):
    store = _store(tmp_path)
    meta, token = access.create_credential(store, customer_id="torch", actor_label="alice")
    assert meta["role"] == access.ROLE_CUSTOMER and meta["customer_id"] == "torch"
    assert meta["credential_id"].startswith("cred_")
    assert token.startswith(meta["credential_id"] + ".")
    ctx = access.authenticate(store, token)
    assert ctx is not None
    assert ctx.customer_id == "torch" and ctx.actor_label == "alice" and not ctx.is_operator


def test_invalid_missing_and_malformed_tokens_fail(tmp_path):
    store = _store(tmp_path)
    _, token = access.create_credential(store, customer_id="torch")
    assert access.authenticate(store, "") is None
    assert access.authenticate(store, "garbage") is None
    assert access.authenticate(store, "cred_deadbeef.wrongsecret") is None      # unknown id
    cid = token.split(".")[0]
    assert access.authenticate(store, f"{cid}.not-the-secret") is None          # right id, wrong secret
    assert access.authenticate(store, cid) is None                              # no secret half


def test_revoked_credential_fails_authentication(tmp_path):
    store = _store(tmp_path)
    meta, token = access.create_credential(store, customer_id="torch")
    assert access.authenticate(store, token) is not None
    access.revoke_credential(store, meta["credential_id"])
    assert access.authenticate(store, token) is None
    # Revocation is append-only: the original record is preserved for audit (never destructively deleted).
    rows = list(store.read(access.STREAM_CREDENTIALS))
    assert len(rows) == 2 and rows[-1]["status"] == access.STATUS_REVOKED and rows[-1]["revoked_at"]


def test_revoke_is_idempotent_and_unknown_rejected(tmp_path):
    store = _store(tmp_path)
    meta, _ = access.create_credential(store, customer_id="torch")
    access.revoke_credential(store, meta["credential_id"])
    # A second revoke does not error or add noise beyond the closure already written.
    again = access.revoke_credential(store, meta["credential_id"])
    assert again["status"] == access.STATUS_REVOKED
    with pytest.raises(ValueError):
        access.revoke_credential(store, "cred_nope")


# --- secret handling ----------------------------------------------------------------------------

def test_plaintext_secret_never_persisted(tmp_path):
    store = _store(tmp_path)
    _, token = access.create_credential(store, customer_id="torch")
    secret = token.split(".", 1)[1]
    blob = Path(store.root, "credentials.jsonl").read_text(encoding="utf-8")
    assert secret not in blob                       # only the salted hash is stored
    rec = json.loads(blob.splitlines()[0])
    assert rec["secret_hash"] and rec["secret_hash"] != secret and rec["salt"]


def test_listing_never_exposes_secret_material(tmp_path):
    store = _store(tmp_path)
    access.create_credential(store, customer_id="torch")
    access.create_credential(store, role=access.ROLE_OPERATOR)
    listed = access.list_credentials(store)
    assert len(listed) == 2
    for row in listed:
        assert "secret_hash" not in row and "salt" not in row and "algo" not in row
    assert access.list_credentials(store, customer_id="torch")[0]["customer_id"] == "torch"


def test_fresh_secret_every_creation(tmp_path):
    store = _store(tmp_path)
    _, t1 = access.create_credential(store, customer_id="torch")
    _, t2 = access.create_credential(store, customer_id="torch")
    assert t1 != t2 and t1.split(".")[0] != t2.split(".")[0]     # distinct id AND secret, never reused


# --- roles: actor authority is separate from tenant identity (§48) ------------------------------

def test_customer_actor_is_scoped_operator_is_not(tmp_path):
    store = _store(tmp_path)
    _, ctoken = access.create_credential(store, customer_id="torch")
    _, otoken = access.create_credential(store, role=access.ROLE_OPERATOR, actor_label="ops")
    cctx = access.authenticate(store, ctoken)
    octx = access.authenticate(store, otoken)
    assert cctx.authorized_for("torch") and not cctx.authorized_for("dap")
    assert octx.is_operator and octx.authorized_for("torch") and octx.authorized_for("anything")
    assert octx.customer_id == ""       # operator carries no single-tenant scope


def test_customer_credential_requires_customer_id(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        access.create_credential(store, role=access.ROLE_CUSTOMER, customer_id="")


# --- request-scoped context (fail closed) -------------------------------------------------------

def test_request_access_check_fails_closed_without_context(tmp_path):
    access.clear_request_context()
    assert access.current_context() is None
    assert access.request_access_check("torch") is False       # no actor ⇒ no access

    store = _store(tmp_path)
    _, token = access.create_credential(store, customer_id="torch")
    access.set_request_context(access.authenticate(store, token))
    try:
        assert access.request_access_check("torch") is True
        assert access.request_access_check("dap") is False     # scoped to own tenant only
    finally:
        access.clear_request_context()
    assert access.request_access_check("torch") is False       # cleared ⇒ fails closed again
