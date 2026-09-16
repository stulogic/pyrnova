"""Minimal serious customer access: credentials, authenticated actor, tenant authorization (M22-F).

M22-A→E built the customer-facing intelligence product and an ``access_check`` authorization *seam*
(``OperatorConsole.access_check`` → ``PermissionError`` → HTTP 403), but authentication itself was
deliberately deferred (D-048/D-057/D-058): the seam was permissive (``None``) and the customer was chosen
from a request parameter / frontend dropdown. That is unsafe for a real design customer. M22-F attaches a
real authenticated identity to that seam, without building enterprise IAM.

The model is deliberately small (see ``docs/specs/M22F_MINIMAL_ACCESS_ONBOARDING.md``):

    presented credential  →  credential lookup  →  Actor  →  authorized customer scope

Doctrine honored:

* **Authentication identifies the actor; authorization defines the boundary.** An :class:`AuthContext`
  carries the authenticated actor and the single customer it is authorized for. Business handlers consume
  the context, never a bearer token or a request-controlled ``customer_id`` — so a later OIDC/SSO layer
  replaces only :func:`authenticate`, not the authorization spread through the product (§49).
* **The customer never chooses their own authority.** Tenant scope comes from the credential, never a
  dropdown or a request parameter. A forged ``customer_id`` cannot widen scope.
* **Tenant isolation fails closed.** No context ⇒ no access. A mismatch is a hard 403, never a fallback.
* **Secrets are handled professionally.** High-entropy CSPRNG tokens; only a salted one-way hash is
  persisted (never the plaintext secret); constant-time comparison; explicit revocation; never logged;
  never placed in the repository. The credential id is separate from the secret so a credential can be
  listed/revoked without ever exposing secret material.

Storage is the same append-only :class:`~pyrnova.state.StateStore` pattern as M22-B customer state (the
``credentials`` stream; production mirror ``credential`` in ``db/schema.sql``). Revocation is an
append-only closure record (last-write-wins per ``credential_id``), consistent with watchlist retirement —
security history is never destructively erased (§28/§53).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

# --- stream name (customer-private security state; never global intelligence) ------------------
STREAM_CREDENTIALS = "credentials"

# --- credential status ------------------------------------------------------------------------
STATUS_ACTIVE = "active"
STATUS_REVOKED = "revoked"

# --- actor roles ------------------------------------------------------------------------------
# A CUSTOMER credential is scoped to exactly one tenant (ordinary design-customer access). An OPERATOR
# credential is Pyrnova-internal: it may see the operator surfaces (all-customer listing, snapshot,
# fan-out, console) but is NOT a customer and carries no single-tenant scope. This keeps customer mode and
# operator mode explicitly separate (§11/§48) without an enterprise RBAC system.
ROLE_CUSTOMER = "customer"
ROLE_OPERATOR = "operator"
ROLES = (ROLE_CUSTOMER, ROLE_OPERATOR)

# Token hashing. The secret is a 256-bit CSPRNG token (see ``_new_secret``), NOT a low-entropy password,
# so a single salted SHA-256 is a sufficient and standard one-way representation (this is how mature API
# key systems store keys): there is no weak password to protect with a slow KDF, and a per-request slow
# KDF would be pointless latency (§30/§62/§68). No custom cryptography — stdlib primitives only (§63).
_HASH_ALGO = "sha256-salted"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_secret() -> str:
    """A URL-safe 256-bit CSPRNG secret (the un-persisted half of a credential)."""
    return secrets.token_urlsafe(32)


def _hash_secret(secret: str, salt: str) -> str:
    """One-way salted hash of a credential secret (hex). Never reversible to the plaintext secret."""
    return hashlib.sha256(salt.encode("utf-8") + secret.encode("utf-8")).hexdigest()


def parse_token(token: str) -> Optional[tuple[str, str]]:
    """Split a presented bearer token into ``(credential_id, secret)`` or ``None`` if malformed.

    The token embeds the credential id so authentication is an O(1) lookup of exactly one record — never
    a scan that hashes every stored credential. Format: ``<credential_id>.<secret>``.
    """
    if not token or not isinstance(token, str):
        return None
    credential_id, sep, secret = token.strip().partition(".")
    if not sep or not credential_id.startswith("cred_") or not secret:
        return None
    return credential_id, secret


@dataclass
class AuthContext:
    """The authenticated actor and the tenant scope it is authorized for.

    This is the ONLY thing business handlers should consume. It deliberately hides how the bearer token
    was validated so a future OIDC/SSO/SCIM layer can produce the same context without rewriting product
    authorization (§49). ``customer_id`` is empty for an operator actor (no single-tenant scope).
    """

    credential_id: str
    role: str
    customer_id: str = ""
    actor_label: str = ""

    @property
    def is_operator(self) -> bool:
        return self.role == ROLE_OPERATOR

    def authorized_for(self, customer_id: str) -> bool:
        """Whether this actor may touch ``customer_id``. Fails closed on any mismatch/empty scope.

        A customer actor is authorized for exactly its own tenant. An operator actor is Pyrnova-internal
        and may act across customers for operations/debugging (still an explicit, authenticated identity).
        """
        if self.is_operator:
            return True
        return bool(self.customer_id) and self.customer_id == customer_id


@dataclass
class Credential:
    """One persisted credential (append-only). Only a salted one-way hash of the secret is stored.

    A revocation appends a closure record with the SAME ``credential_id`` and ``status='revoked'``;
    last-write-wins per id, so history stays auditable and is never destructively erased (§28/§53).
    """

    credential_id: str
    role: str
    customer_id: str = ""
    actor_label: str = ""
    algo: str = _HASH_ALGO
    salt: str = ""
    secret_hash: str = ""
    status: str = STATUS_ACTIVE
    note: str = ""
    created_at: str = field(default_factory=_now)
    revoked_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.role = str(self.role or "").strip().lower()
        if self.role not in ROLES:
            raise ValueError(f"role must be one of {ROLES}")
        if self.role == ROLE_CUSTOMER and not str(self.customer_id).strip():
            raise ValueError("a customer credential requires a customer_id")

    def to_record(self) -> dict:
        return asdict(self)

    def public_metadata(self) -> dict:
        """Listing-safe view — identity/lifecycle only, NEVER secret material (salt/hash excluded, §25)."""
        return {
            "credential_id": self.credential_id,
            "role": self.role,
            "customer_id": self.customer_id,
            "actor_label": self.actor_label,
            "status": self.status,
            "created_at": self.created_at,
            "revoked_at": self.revoked_at,
            "note": self.note,
        }


def _record_to_credential(rec: dict) -> Credential:
    allowed = set(Credential.__dataclass_fields__)
    return Credential(**{k: v for k, v in rec.items() if k in allowed})


def _latest_by_id(store) -> dict[str, dict]:
    """Latest record per credential_id (append-only; a revocation closure supersedes the original)."""
    latest: dict[str, dict] = {}
    for r in store.read(STREAM_CREDENTIALS):
        cid = r.get("credential_id")
        if cid:
            latest[cid] = r  # last write wins
    return latest


# ------------------------------------------------------------------ provisioning (operator-facing)

def create_credential(store, *, customer_id: str = "", actor_label: str = "",
                      role: str = ROLE_CUSTOMER, note: str = "") -> tuple[dict, str]:
    """Provision a new credential. Returns ``(public_metadata, plaintext_token)``.

    The plaintext token is returned exactly once (it is NOT recoverable from storage — only its salted
    hash is persisted). A fresh secret is always generated: credential creation never silently reuses an
    existing secret (§27). Operator-facing (see ``pyrnova credential create``); the caller is responsible
    for delivering the token to the customer over a secure channel and must not log it (§30).
    """
    role = str(role or ROLE_CUSTOMER).strip().lower()
    credential_id = "cred_" + secrets.token_hex(8)
    secret = _new_secret()
    salt = secrets.token_hex(16)
    credential = Credential(
        credential_id=credential_id, role=role, customer_id=str(customer_id or "").strip(),
        actor_label=actor_label, salt=salt, secret_hash=_hash_secret(secret, salt), note=note)
    store.append(STREAM_CREDENTIALS, credential.to_record())
    token = f"{credential_id}.{secret}"
    return credential.public_metadata(), token


def revoke_credential(store, credential_id: str, *, note: str = "") -> dict:
    """Revoke a credential by appending a closure record (append-only; never a destructive delete).

    A revoked credential fails authentication immediately and cannot read or write. The original record
    and its hash remain for audit; only the status/lifecycle changes.
    """
    latest = _latest_by_id(store)
    rec = latest.get(credential_id)
    if rec is None:
        raise ValueError(f"credential not found: {credential_id}")
    if rec.get("status") == STATUS_REVOKED:
        return _record_to_credential(rec).public_metadata()
    closure = _record_to_credential(rec)
    closure.status = STATUS_REVOKED
    closure.revoked_at = _now()
    if note:
        closure.note = note
    store.append(STREAM_CREDENTIALS, closure.to_record())
    return closure.public_metadata()


def list_credentials(store, *, customer_id: Optional[str] = None,
                     include_revoked: bool = True) -> list[dict]:
    """List credential METADATA (never secrets). Optionally filter to one customer / active only."""
    out = []
    for rec in _latest_by_id(store).values():
        cred = _record_to_credential(rec)
        if customer_id is not None and cred.customer_id != customer_id:
            continue
        if not include_revoked and cred.status != STATUS_ACTIVE:
            continue
        out.append(cred.public_metadata())
    out.sort(key=lambda r: (r["role"], r["customer_id"], r["created_at"], r["credential_id"]))
    return out


def has_credentials(store) -> bool:
    """Whether any credential has ever been provisioned (used to decide the server's auth posture)."""
    for _ in store.read(STREAM_CREDENTIALS):
        return True
    return False


# ------------------------------------------------------------------ authentication (per request)

def authenticate(store, token: str) -> Optional[AuthContext]:
    """Validate a presented bearer token → :class:`AuthContext`, or ``None`` if it is not valid.

    Returns ``None`` (never raises, never leaks which half failed) for: a malformed token, an unknown
    credential id, a revoked/inactive credential, or a secret that does not match. Comparison is
    constant-time. This is the single point a later OIDC/SSO layer replaces.
    """
    parsed = parse_token(token)
    if parsed is None:
        return None
    credential_id, secret = parsed
    rec = _latest_by_id(store).get(credential_id)
    if rec is None:
        return None
    cred = _record_to_credential(rec)
    if cred.status != STATUS_ACTIVE or cred.revoked_at:
        return None
    expected = cred.secret_hash
    presented = _hash_secret(secret, cred.salt)
    if not hmac.compare_digest(expected, presented):
        return None
    # Named-user credentials obey ACCOUNT STATE: a customer whose managed lifecycle state denies normal
    # product access (suspended / expired / offboarded, or any pre-activation state) cannot authenticate.
    # An UNMANAGED account (no lifecycle record) is grandfathered as permitted. Operators are unaffected.
    # Fail closed on any error rather than granting a session.
    if cred.role == ROLE_CUSTOMER and cred.customer_id:
        try:
            from . import customer_lifecycle as _cl
            if not _cl.access_enabled(_cl.current_state(store, cred.customer_id)):
                return None
        except Exception:  # noqa: BLE001 — fail closed
            return None
    return AuthContext(credential_id=cred.credential_id, role=cred.role,
                       customer_id=cred.customer_id, actor_label=cred.actor_label)


# ------------------------------------------------------------------ request-scoped context (server)

# ThreadingHTTPServer serves each request on its own thread, so a thread-local cleanly carries the
# authenticated actor from the transport layer to the shared OperatorConsole's ``access_check`` without
# passing it through every method signature — one canonical, visible, testable pattern (§50). It is set
# per request and always cleared in a finally block; it defaults to None so the console fails closed.
_request_ctx = threading.local()


def set_request_context(ctx: Optional[AuthContext]) -> None:
    _request_ctx.value = ctx


def clear_request_context() -> None:
    _request_ctx.value = None


def current_context() -> Optional[AuthContext]:
    return getattr(_request_ctx, "value", None)


def request_access_check(customer_id: str) -> bool:
    """``access_check`` for the shared console: authorize against the current request's actor.

    Fails closed — no authenticated actor in scope ⇒ no access. This is defense-in-depth behind the
    transport-layer enforcement, so even a route that forgets to pass the right customer cannot leak.
    """
    ctx = current_context()
    return ctx is not None and ctx.authorized_for(customer_id)


__all__ = [
    "STREAM_CREDENTIALS", "STATUS_ACTIVE", "STATUS_REVOKED",
    "ROLE_CUSTOMER", "ROLE_OPERATOR", "ROLES",
    "AuthContext", "Credential", "parse_token",
    "create_credential", "revoke_credential", "list_credentials", "has_credentials",
    "authenticate",
    "set_request_context", "clear_request_context", "current_context", "request_access_check",
]
