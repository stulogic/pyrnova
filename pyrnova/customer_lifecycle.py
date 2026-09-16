"""Shared commercial customer lifecycle (account state) — activation, suspension, expiry, offboarding.

Closes the previously identified US/shared customer-lifecycle gap WITHOUT inventing payment or legal
state and WITHOUT a payment processor. This is the ACCOUNT lifecycle (is this customer entitled to
normal product access, and has payment cleared?), kept strictly separate from:

* the per-Material-Change CUSTOMER REVIEW lifecycle (:mod:`pyrnova.customers`), and
* Pyrnova's SYSTEM intelligence assessment.

Doctrine:

* **Append-only + auditable.** Every transition is an immutable record (from → to → at → actor → reason);
  the current state is the fold over the log. History is never destructively overwritten.
* **Activation never falsely implies payment.** ACTIVE is reachable ONLY from PAYMENT_CLEARED (a fresh
  activation) or from SUSPENDED (deterministic reactivation of an already-paid account). You cannot jump
  to ACTIVE from PAYMENT_PENDING, so "the product is on" can never silently assert "they have paid".
* **Manual invoicing is first-class; no Stripe.** PAYMENT_CLEARED records an operator-attested manual
  cleared payment (optional ``invoice_ref``); no payment processor is required or implied. No legal
  seller/bank details are invented here — only the fact "an operator recorded payment as cleared".
* **Internal evaluation is distinct from paid ACTIVE.** INTERNAL_EVALUATION is access-enabled but NEVER
  implies payment or a commercial relationship (used by the international evaluation lenses).
* **Suspended/expired/offboarded cannot continue normal product access** (fail closed), and revocation of
  a credential remains independently fail closed (:mod:`pyrnova.access`).
* **Reactivation is deterministic.** SUSPENDED → ACTIVE restores access with no hidden re-derivation.
* **Offboarding does not delete evidence.** OFFBOARDED is a terminal access state; it changes access, not
  retention. Evidence/audit is retained unless a SEPARATE retention authority requires deletion.
* **Backward compatible.** An account with NO lifecycle record is UNMANAGED (legacy) and access is
  permitted, so introducing lifecycle never retroactively locks out existing customers; only an explicit
  managed state gates access.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

STREAM_CUSTOMER_LIFECYCLE = "customer_lifecycle"

# --- account states ----------------------------------------------------------------------------
PROSPECT = "PROSPECT"
INTERNAL_EVALUATION = "INTERNAL_EVALUATION"
CONTRACTED = "CONTRACTED"
PAYMENT_PENDING = "PAYMENT_PENDING"
PAYMENT_CLEARED = "PAYMENT_CLEARED"
ACTIVE = "ACTIVE"
SUSPENDED = "SUSPENDED"
EXPIRED = "EXPIRED"
OFFBOARDED = "OFFBOARDED"

STATES = (PROSPECT, INTERNAL_EVALUATION, CONTRACTED, PAYMENT_PENDING, PAYMENT_CLEARED,
          ACTIVE, SUSPENDED, EXPIRED, OFFBOARDED)

# States that permit normal customer product access. INTERNAL_EVALUATION is access-enabled but is NOT a
# paid state. An UNMANAGED account (no lifecycle record) is treated as access-permitted (see module doc).
ACCESS_ENABLED_STATES = frozenset({ACTIVE, INTERNAL_EVALUATION})
# States in which payment has genuinely cleared (never asserted from a non-payment path).
PAYMENT_CLEARED_STATES = frozenset({PAYMENT_CLEARED, ACTIVE})

# Deterministic allowed transitions. ACTIVE is reachable ONLY from PAYMENT_CLEARED or SUSPENDED, so
# activation cannot falsely imply payment. OFFBOARDED is terminal (access-wise) and reachable from any
# non-terminal state. EXPIRED re-enters the commercial flow via CONTRACTED (renewal).
_TRANSITIONS: dict[str, frozenset] = {
    PROSPECT: frozenset({INTERNAL_EVALUATION, CONTRACTED, OFFBOARDED}),
    INTERNAL_EVALUATION: frozenset({CONTRACTED, SUSPENDED, OFFBOARDED}),
    CONTRACTED: frozenset({PAYMENT_PENDING, OFFBOARDED}),
    PAYMENT_PENDING: frozenset({PAYMENT_CLEARED, OFFBOARDED}),
    PAYMENT_CLEARED: frozenset({ACTIVE, OFFBOARDED}),
    ACTIVE: frozenset({SUSPENDED, EXPIRED, OFFBOARDED}),
    SUSPENDED: frozenset({ACTIVE, EXPIRED, OFFBOARDED}),
    EXPIRED: frozenset({CONTRACTED, OFFBOARDED}),
    OFFBOARDED: frozenset(),  # terminal (access); evidence/audit retained
}
# The states a brand-new managed account may START in. OFFBOARDED is included so an operator can
# explicitly terminate access on a legacy/UNMANAGED account without first walking it through the flow.
_INITIAL_STATES = frozenset({PROSPECT, INTERNAL_EVALUATION, CONTRACTED, OFFBOARDED})


class LifecycleError(RuntimeError):
    """An illegal lifecycle transition (fail closed)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


@dataclass
class LifecycleTransition:
    """One immutable account-lifecycle transition (append-only audit record)."""

    customer_id: str
    from_state: Optional[str]
    to_state: str
    actor: str = "operator"
    reason: str = ""
    invoice_ref: Optional[str] = None   # operator-attested manual invoice reference (no payment processor)
    note: str = ""
    at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not str(self.customer_id).strip():
            raise ValueError("customer_id is required")
        if self.to_state not in STATES:
            raise ValueError(f"to_state must be one of {STATES}, got {self.to_state!r}")
        if self.from_state is not None and self.from_state not in STATES:
            raise ValueError(f"from_state must be a known state or None, got {self.from_state!r}")
        _parse_dt(self.at)

    def to_record(self) -> dict:
        return asdict(self)


def _transitions_for(store, customer_id: str, *, as_of: Optional[str] = None) -> list[dict]:
    rows = [r for r in store.read(STREAM_CUSTOMER_LIFECYCLE) if r.get("customer_id") == customer_id]
    if as_of is not None:
        cutoff = _parse_dt(as_of)
        rows = [r for r in rows if _parse_dt(r.get("at") or r.get("_ts")) <= cutoff]
    rows.sort(key=lambda r: (r.get("at") or r.get("_ts") or "", r.get("_ts") or ""))
    return rows


def current_state(store, customer_id: str, *, as_of: Optional[str] = None) -> Optional[str]:
    """The account's current lifecycle state, or ``None`` if the account is UNMANAGED (no record)."""
    rows = _transitions_for(store, customer_id, as_of=as_of)
    return rows[-1]["to_state"] if rows else None


def history(store, customer_id: str, *, as_of: Optional[str] = None) -> list[dict]:
    """Full ordered lifecycle history (point-in-time reconstructable audit trail)."""
    return _transitions_for(store, customer_id, as_of=as_of)


def access_enabled(state: Optional[str]) -> bool:
    """Whether an account in ``state`` may have NORMAL product access.

    ``None`` (unmanaged/legacy) is permitted for backward compatibility; a managed account is permitted
    ONLY in an access-enabled state. Suspended/expired/offboarded and every pre-activation state deny.
    """
    if state is None:
        return True
    return state in ACCESS_ENABLED_STATES


def payment_cleared(state: Optional[str]) -> bool:
    """Whether payment has genuinely cleared for this state. Never true from a non-payment path."""
    return state in PAYMENT_CLEARED_STATES


def can_transition(from_state: Optional[str], to_state: str) -> bool:
    if from_state is None:
        return to_state in _INITIAL_STATES
    return to_state in _TRANSITIONS.get(from_state, frozenset())


def set_state(store, customer_id: str, to_state: str, *, actor: str = "operator", reason: str = "",
              invoice_ref: Optional[str] = None, note: str = "", at: Optional[str] = None) -> dict:
    """Record a lifecycle transition (append-only). Rejects an illegal transition (fail closed).

    ``PAYMENT_CLEARED`` records an operator-attested manual cleared payment (``invoice_ref`` optional);
    no payment processor is required or implied. ``ACTIVE`` is refused unless the account is at
    ``PAYMENT_CLEARED`` (fresh activation) or ``SUSPENDED`` (deterministic reactivation), so activation
    can never falsely imply payment.
    """
    to_state = str(to_state).strip().upper()
    if to_state not in STATES:
        raise LifecycleError(f"unknown lifecycle state: {to_state!r}")
    frm = current_state(store, customer_id)
    if frm == to_state:
        raise LifecycleError(f"account is already {to_state}")
    if not can_transition(frm, to_state):
        raise LifecycleError(
            f"illegal transition {frm or 'UNMANAGED'} -> {to_state} for customer {customer_id!r}")
    row = LifecycleTransition(customer_id=customer_id, from_state=frm, to_state=to_state,
                              actor=actor, reason=reason, invoice_ref=invoice_ref, note=note,
                              at=at or _now()).to_record()
    store.append(STREAM_CUSTOMER_LIFECYCLE, row)
    return {"customer_id": customer_id, "from_state": frm, "to_state": to_state,
            "access_enabled": access_enabled(to_state), "payment_cleared": payment_cleared(to_state),
            "at": row["at"]}


def status(store, customer_id: str, *, as_of: Optional[str] = None) -> dict:
    """A compact, inspectable account status (state + derived access/payment + allowed next states)."""
    state = current_state(store, customer_id, as_of=as_of)
    allowed_next = sorted(_TRANSITIONS.get(state, frozenset())) if state is not None \
        else sorted(_INITIAL_STATES)
    return {
        "customer_id": customer_id, "as_of": as_of,
        "state": state, "managed": state is not None,
        "access_enabled": access_enabled(state),
        "payment_cleared": payment_cleared(state),
        "allowed_next_states": allowed_next,
        "transitions": len(_transitions_for(store, customer_id, as_of=as_of)),
    }


__all__ = [
    "STREAM_CUSTOMER_LIFECYCLE", "STATES",
    "PROSPECT", "INTERNAL_EVALUATION", "CONTRACTED", "PAYMENT_PENDING", "PAYMENT_CLEARED",
    "ACTIVE", "SUSPENDED", "EXPIRED", "OFFBOARDED",
    "ACCESS_ENABLED_STATES", "PAYMENT_CLEARED_STATES",
    "LifecycleError", "LifecycleTransition",
    "current_state", "history", "access_enabled", "payment_cleared", "can_transition",
    "set_state", "status",
]
