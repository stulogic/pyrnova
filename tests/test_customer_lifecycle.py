"""Shared commercial customer lifecycle (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, boundary D).

Activation / suspension / expiry / offboarding WITHOUT inventing payment or legal state and without a
payment processor: activation never falsely implies payment; manual invoicing is first-class; named-user
credentials and the product surfaces obey account state; revocation stays fail closed; reactivation is
deterministic; audit is append-only; offboarding does not delete evidence.
"""

from __future__ import annotations

import pytest

from pyrnova import access
from pyrnova import customer_lifecycle as cl
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.customers import CustomerProfile, upsert_customer
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

CID = "acme"


def _store(tmp_path):
    return StateStore(tmp_path / "state")


# --- state machine ---------------------------------------------------------------------------------

def test_activation_never_falsely_implies_payment(tmp_path):
    s = _store(tmp_path)
    cl.set_state(s, CID, cl.CONTRACTED)
    # Cannot jump to ACTIVE without payment clearing.
    with pytest.raises(cl.LifecycleError):
        cl.set_state(s, CID, cl.ACTIVE)
    cl.set_state(s, CID, cl.PAYMENT_PENDING)
    with pytest.raises(cl.LifecycleError):
        cl.set_state(s, CID, cl.ACTIVE)  # still not cleared
    assert cl.payment_cleared(cl.current_state(s, CID)) is False
    # Manual invoice cleared (no processor) -> then activation is legitimate and implies payment.
    cl.set_state(s, CID, cl.PAYMENT_CLEARED, invoice_ref="INV-2026-014")
    assert cl.payment_cleared(cl.current_state(s, CID)) is True
    cl.set_state(s, CID, cl.ACTIVE)
    assert cl.access_enabled(cl.current_state(s, CID)) is True
    assert cl.payment_cleared(cl.current_state(s, CID)) is True


def test_internal_evaluation_is_access_enabled_but_never_paid(tmp_path):
    s = _store(tmp_path)
    cl.set_state(s, CID, cl.INTERNAL_EVALUATION)
    assert cl.access_enabled(cl.current_state(s, CID)) is True
    assert cl.payment_cleared(cl.current_state(s, CID)) is False  # no false payment for an eval lens


def test_suspend_expire_offboard_deny_access_and_reactivation_is_deterministic(tmp_path):
    s = _store(tmp_path)
    for st in (cl.CONTRACTED, cl.PAYMENT_PENDING, cl.PAYMENT_CLEARED, cl.ACTIVE, cl.SUSPENDED):
        cl.set_state(s, CID, st)
    assert cl.access_enabled(cl.SUSPENDED) is False
    # Deterministic reactivation restores access.
    cl.set_state(s, CID, cl.ACTIVE)
    assert cl.access_enabled(cl.current_state(s, CID)) is True
    cl.set_state(s, CID, cl.EXPIRED)
    assert cl.access_enabled(cl.EXPIRED) is False
    cl.set_state(s, CID, cl.OFFBOARDED)
    assert cl.access_enabled(cl.OFFBOARDED) is False
    # OFFBOARDED is terminal: no further transition.
    with pytest.raises(cl.LifecycleError):
        cl.set_state(s, CID, cl.ACTIVE)


def test_audit_trail_is_append_only(tmp_path):
    s = _store(tmp_path)
    cl.set_state(s, CID, cl.CONTRACTED, reason="signed", actor="ops-1")
    cl.set_state(s, CID, cl.PAYMENT_PENDING)
    hist = cl.history(s, CID)
    assert [h["to_state"] for h in hist] == [cl.CONTRACTED, cl.PAYMENT_PENDING]
    assert hist[0]["from_state"] is None and hist[0]["reason"] == "signed"
    # Re-reading yields the same immutable history (nothing overwritten).
    assert cl.history(s, CID) == hist


def test_unmanaged_account_is_grandfathered(tmp_path):
    s = _store(tmp_path)
    assert cl.current_state(s, CID) is None
    assert cl.access_enabled(None) is True  # legacy customers are not retroactively locked out


# --- credential + product-surface enforcement ------------------------------------------------------

def test_customer_credential_obeys_account_state(tmp_path):
    s = _store(tmp_path)
    _rec, token = access.create_credential(s, customer_id=CID, role=access.ROLE_CUSTOMER)
    cl.set_state(s, CID, cl.INTERNAL_EVALUATION)
    assert access.authenticate(s, token) is not None  # access-enabled state authenticates
    # Move through to ACTIVE then SUSPENDED — authentication must fail while suspended.
    for st in (cl.CONTRACTED, cl.PAYMENT_PENDING, cl.PAYMENT_CLEARED, cl.ACTIVE, cl.SUSPENDED):
        cl.set_state(s, CID, st)
    assert access.authenticate(s, token) is None  # named-user credential obeys account state
    cl.set_state(s, CID, cl.ACTIVE)
    assert access.authenticate(s, token) is not None  # reactivation restores the session


def test_offboarding_does_not_delete_evidence(tmp_path):
    s = _store(tmp_path)
    s.append("opportunities", {"id": "op1", "customer_id": CID, "state": "candidate",
                               "evidence": [{"id": "e1", "source_id": "usaspending"}]})
    cl.set_state(s, CID, cl.OFFBOARDED)
    # Offboarding changes access, not retention: the evidence record is still present.
    assert [r for r in s.read("opportunities") if r.get("customer_id") == CID]


def test_product_surface_denies_suspended_customer(tmp_path):
    s = _store(tmp_path)
    upsert_customer(s, CustomerProfile(customer_id=CID, name="Acme", entity_refs=["co_acme"]))
    console = OperatorConsole(s, tmp_path / "p", tmp_path / "o", mc_store=s,
                             customer_store=s, cmc_store=s,
                             delivery_store=CustomerDeliveryStore(tmp_path / "d"))
    # Managed + suspended: normal product access is denied (fail closed).
    for st in (cl.CONTRACTED, cl.PAYMENT_PENDING, cl.PAYMENT_CLEARED, cl.ACTIVE, cl.SUSPENDED):
        cl.set_state(s, CID, st)
    with pytest.raises(PermissionError):
        console.customer_lens(CID)
    # Reactivated: access restored.
    cl.set_state(s, CID, cl.ACTIVE)
    assert console.customer_lens(CID)["customer"]["id"] == CID


def test_operator_actor_bypasses_lifecycle_gate(tmp_path):
    s = _store(tmp_path)
    upsert_customer(s, CustomerProfile(customer_id=CID, name="Acme", entity_refs=["co_acme"]))
    console = OperatorConsole(s, tmp_path / "p", tmp_path / "o", mc_store=s,
                             customer_store=s, cmc_store=s,
                             delivery_store=CustomerDeliveryStore(tmp_path / "d"))
    for st in (cl.CONTRACTED, cl.PAYMENT_PENDING, cl.PAYMENT_CLEARED, cl.ACTIVE, cl.SUSPENDED):
        cl.set_state(s, CID, st)
    access.set_request_context(access.AuthContext(credential_id="c", role=access.ROLE_OPERATOR,
                                                  customer_id="", actor_label="ops"))
    try:
        # Operator admin inspection is not blocked by the account-lifecycle gate.
        assert console.customer_lens(CID)["customer"]["id"] == CID
    finally:
        access.clear_request_context()
