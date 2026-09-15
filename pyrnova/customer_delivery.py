"""B3.11 — Customer brief delivery contract.

A production-shaped, tenant-safe delivery path for customer briefs / Material Change notifications.
This is DELIBERATELY DECOUPLED from operator alerts (:mod:`pyrnova.alerts`): it reuses only the generic
email *transport seam* (``EmailTransport`` / ``TransportError`` / ``DisabledTransport``), never the alert
lifecycle, dedupe, or severity doctrine — customer-delivery correctness must not depend on operator-alert
implementation (B3.11 doctrine).

Guarantees implemented here:

* **Explicit tenant.** Every delivery names a customer id; reads are customer-scoped and a delivery for
  one tenant is never returned to another (``get_delivery`` / ``list_deliveries`` fail closed on mismatch).
* **Recipient authorization.** Recipients must be a subset of the customer's authorized recipient list;
  an unauthorized recipient is a hard refusal, never a silent drop.
* **Deterministic delivery id / dedupe.** ``delivery_id`` and the dedupe key are a pure function of
  (customer, artifact, content hash, recipients). Re-issuing the *same* brief to the *same* recipients is
  idempotent: an already-DELIVERED delivery is returned untouched — no duplicate mail on retries/restarts.
* **Delivery lifecycle / status.** PENDING → DELIVERED | FAILED | RIGHTS_BLOCKED, with attempt count,
  created/updated/delivered timestamps, and the last failure recorded durably.
* **Bounded retry + no silent loss.** A transport error is retried up to ``max_attempts`` within a call
  and, if still failing, recorded as FAILED (the delivery still exists and is inspectable); a later call
  with the same key RESUMES the same delivery rather than spawning a duplicate. Every attempt outcome is
  appended to an audit log; failures are additionally recorded in ``delivery_failures.jsonl``.
* **Rights-aware, fail closed.** When the rendered content carries source material whose customer display
  is BLOCKED, the delivery is refused (RIGHTS_BLOCKED) and never sent — restricted source expression is
  never transported.
* **No fabricated external delivery.** The default :class:`DisabledTransport` (no sending identity) raises
  a transport error, so a delivery with no real transport is recorded FAILED, NEVER DELIVERED. Real
  external delivery must be verified with genuine SMTP credentials; until then it is explicitly pending.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Generic transport seam only — no alert lifecycle is imported (B3.11 decoupling).
from .alerts import DisabledTransport, EmailTransport, TransportError

# Delivery lifecycle states.
PENDING = "PENDING"
DELIVERED = "DELIVERED"
FAILED = "FAILED"
RIGHTS_BLOCKED = "RIGHTS_BLOCKED"

# Rights display verdicts a customer brief can carry (mirrors sources.rights.gate_customer_display).
RIGHTS_ALLOWED = "ALLOWED"
RIGHTS_PARTIAL = "PARTIAL"
RIGHTS_BLOCKED_DISPLAY = "BLOCKED"


class DeliveryRefused(Exception):
    """A delivery was refused before any transport attempt (authorization / tenancy / input error)."""


def _now(now: Optional[datetime]) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()


def _norm_recipients(recipients) -> list[str]:
    seen: list[str] = []
    for r in recipients or ():
        r = str(r).strip().lower()
        if r and r not in seen:
            seen.append(r)
    return sorted(seen)


def _dedupe_key(customer_id: str, artifact_ref: str, content_sha256: str, recipients: list[str]) -> str:
    material = "\x1f".join([customer_id, artifact_ref, content_sha256, ",".join(recipients)])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass
class CustomerDelivery:
    delivery_id: str
    customer_id: str
    dedupe_key: str
    artifact_ref: str
    subject: str
    content_sha256: str
    recipients: list[str]
    rights_display: str
    status: str
    attempts: int
    created_at: str
    last_updated_at: str
    delivered_at: Optional[str] = None
    last_failure: Optional[str] = None
    transport: Optional[str] = None

    def to_record(self) -> dict:
        return asdict(self)


class CustomerDeliveryStore:
    """Append-only, tenant-partitioned durable store for customer deliveries.

    ``deliveries.jsonl`` holds the full append-only audit (latest record per delivery id wins);
    ``delivery_failures.jsonl`` additionally records every send that could not be delivered, so a failure
    is never lost even if a later record for the same delivery supersedes its state.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self) -> Path:
        return self.root / "deliveries.jsonl"

    def _failures_path(self) -> Path:
        return self.root / "delivery_failures.jsonl"

    def _all(self) -> dict[str, dict]:
        """Latest record per delivery id (append-only replay)."""
        out: dict[str, dict] = {}
        path = self._path()
        if not path.exists():
            return out
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                out[rec["delivery_id"]] = rec
        return out

    def _append(self, record: dict) -> None:
        with self._path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    def _append_failure(self, record: dict) -> None:
        with self._failures_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    # --- tenant-scoped reads (fail closed on mismatch) ------------------------------------------

    def get_delivery(self, customer_id: str, delivery_id: str) -> Optional[dict]:
        rec = self._all().get(delivery_id)
        if rec is None or rec.get("customer_id") != customer_id:
            return None  # cross-tenant read is indistinguishable from absent
        return rec

    def by_dedupe_key(self, customer_id: str, dedupe_key: str) -> Optional[dict]:
        for rec in self._all().values():
            if rec.get("customer_id") == customer_id and rec.get("dedupe_key") == dedupe_key:
                return rec
        return None

    def list_deliveries(self, customer_id: str) -> list[dict]:
        rows = [r for r in self._all().values() if r.get("customer_id") == customer_id]
        return sorted(rows, key=lambda r: (r.get("created_at") or "", r.get("delivery_id")))


def deliver_customer_brief(
    store: CustomerDeliveryStore,
    *,
    customer_id: str,
    artifact_ref: str,
    subject: str,
    body: str,
    recipients,
    authorized_recipients,
    sender: str,
    transport: Optional[EmailTransport] = None,
    rights_display: str = RIGHTS_ALLOWED,
    content_sha256: Optional[str] = None,
    max_attempts: int = 3,
    now: Optional[datetime] = None,
) -> dict:
    """Deliver (or dedupe/resume) a customer brief under the full delivery contract.

    Returns the delivery record. Raises :class:`DeliveryRefused` for input/authorization/tenancy errors
    that occur BEFORE any durable delivery is created (a bad request must not create audit noise).
    """
    customer_id = (customer_id or "").strip()
    if not customer_id:
        raise DeliveryRefused("a delivery must name an explicit customer/tenant")
    if not artifact_ref:
        raise DeliveryRefused("a delivery must reference an explicit artifact")

    recipients = _norm_recipients(recipients)
    authorized = set(_norm_recipients(authorized_recipients))
    if not recipients:
        raise DeliveryRefused("no recipients specified")
    unauthorized = [r for r in recipients if r not in authorized]
    if unauthorized:
        # Hard refusal — never silently drop an unauthorized recipient, never partially deliver.
        raise DeliveryRefused(f"recipient(s) not authorized for tenant: {', '.join(unauthorized)}")

    body_bytes = body.encode("utf-8")
    content_sha256 = content_sha256 or hashlib.sha256(body_bytes).hexdigest()
    dedupe_key = _dedupe_key(customer_id, artifact_ref, content_sha256, recipients)
    delivery_id = f"cd_{dedupe_key[:20]}"
    ts = _now(now)

    existing = store.by_dedupe_key(customer_id, dedupe_key)
    if existing is not None and existing.get("status") == DELIVERED:
        return existing  # idempotent: the identical brief was already delivered — no duplicate mail
    attempts = int(existing.get("attempts", 0)) if existing else 0
    created_at = existing.get("created_at") if existing else ts

    delivery = CustomerDelivery(
        delivery_id=delivery_id, customer_id=customer_id, dedupe_key=dedupe_key,
        artifact_ref=artifact_ref, subject=subject[:200], content_sha256=content_sha256,
        recipients=recipients, rights_display=rights_display, status=PENDING,
        attempts=attempts, created_at=created_at, last_updated_at=ts,
    )

    # Rights fail-closed: restricted source expression is never transported to a customer.
    if rights_display == RIGHTS_BLOCKED_DISPLAY:
        delivery.status = RIGHTS_BLOCKED
        delivery.last_failure = "customer display is rights-blocked for this content"
        delivery.last_updated_at = _now(now)
        rec = delivery.to_record()
        store._append(rec)
        store._append_failure({"delivery_id": delivery_id, "customer_id": customer_id,
                               "reason": delivery.last_failure, "at": delivery.last_updated_at})
        return rec

    transport = transport if transport is not None else DisabledTransport()
    delivery.transport = type(transport).__name__
    message = {"from": sender, "to": recipients, "subject": delivery.subject, "body": body}

    last_error: Optional[str] = None
    for _ in range(max(1, max_attempts)):
        attempts += 1
        try:
            transport.send(message)
        except TransportError as exc:
            last_error = str(exc)
            continue
        # Delivered — record success (never fabricated: only a transport that did NOT raise reaches here).
        delivery.status = DELIVERED
        delivery.attempts = attempts
        delivery.delivered_at = _now(now)
        delivery.last_updated_at = delivery.delivered_at
        delivery.last_failure = None
        rec = delivery.to_record()
        store._append(rec)
        return rec

    # All attempts failed — durably recorded FAILED, never lost, never reported as delivered.
    delivery.status = FAILED
    delivery.attempts = attempts
    delivery.last_failure = last_error
    delivery.last_updated_at = _now(now)
    rec = delivery.to_record()
    store._append(rec)
    store._append_failure({"delivery_id": delivery_id, "customer_id": customer_id,
                           "reason": last_error, "attempts": attempts, "at": delivery.last_updated_at})
    return rec
