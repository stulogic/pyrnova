"""Operator alerts — durable lifecycle, severity doctrine, dedupe, and an email transport seam.

Phase 1 operational blocker: make *important* operational failures explicit operator-attention events
while routine informational conditions stay logs-only. This module owns:

- a severity doctrine (:class:`Severity`): INFO (logs only, never emails), OPERATOR_ATTENTION (actionable
  degradation), CRITICAL (threatens trustworthy operation / availability);
- a durable, inspectable alert lifecycle (OPEN -> UPDATED -> RESOLVED) with stable identity, first-opened
  / last-updated timestamps, dedupe, and a new incident *generation* when a resolved condition recurs;
- an email transport *seam* suitable for real credentials later (:class:`SMTPEmailTransport`) plus a
  ``DisabledTransport`` that is explicit — a missing sending identity is never treated as a delivered mail;
- explicit, bounded, non-recursive delivery-failure handling: a failed send is recorded durably against
  the alert (the alert still exists and is inspectable) and never itself triggers another alert email.

It performs no HTTP on import and holds no product coupling beyond an optional health-evaluation helper
that reads :meth:`pyrnova.scheduler.SourceScheduler.health` rows. The running soak is never touched: this
is new code on an isolated branch; deploying it into a live service is a separate, deliberate act.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

SCHEMA_VERSION = "operator_alerts_v1"

# Evidence keys whose *values* must never be rendered into an operator email, even if a caller passes
# them. Diagnosis uses identifiers and references, not raw credentials or restricted payloads.
_REDACT_KEY_TOKENS = (
    "password", "passwd", "secret", "token", "authorization", "auth", "bearer",
    "api_key", "apikey", "access_key", "secret_key", "credential", "cookie", "session",
    "private", "payload_body", "raw_content", "content_body",
)
_MAX_EVIDENCE_STR = 300
_MAX_EVIDENCE_ITEMS = 25


class Severity(str, Enum):
    """Operator-facing severity. INFO stays in durable logs/status and never emails an operator."""

    INFO = "INFO"
    OPERATOR_ATTENTION = "OPERATOR_ATTENTION"
    CRITICAL = "CRITICAL"


# Only OPERATOR_ATTENTION and above reach an operator inbox. INFO is logs/status only (doctrine).
_SEVERITY_RANK = {Severity.INFO: 0, Severity.OPERATOR_ATTENTION: 1, Severity.CRITICAL: 2}
_NOTIFY_MIN_RANK = 1


class AlertState(str, Enum):
    OPEN = "OPEN"
    UPDATED = "UPDATED"
    RESOLVED = "RESOLVED"


def _coerce_severity(value: Any) -> Severity:
    if isinstance(value, Severity):
        return value
    return Severity(str(value))


def _now(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


# --------------------------------------------------------------------------- sanitisation


def _sanitize_evidence(value: Any, *, _depth: int = 0) -> Any:
    """Return a copy of ``value`` safe to place in an operator email.

    Drops any mapping key that looks like a credential/secret, truncates long strings, and bounds the
    breadth of collections so a single alert cannot dump restricted source content into a message.
    Identifiers and short references pass through for diagnosis.
    """
    if _depth > 4:
        return "…"
    if isinstance(value, dict):
        out: dict = {}
        for k, v in list(value.items())[:_MAX_EVIDENCE_ITEMS]:
            key = str(k)
            if any(tok in key.lower() for tok in _REDACT_KEY_TOKENS):
                out[key] = "[redacted]"
            else:
                out[key] = _sanitize_evidence(v, _depth=_depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_sanitize_evidence(v, _depth=_depth + 1) for v in list(value)[:_MAX_EVIDENCE_ITEMS]]
    if isinstance(value, str):
        return value if len(value) <= _MAX_EVIDENCE_STR else value[:_MAX_EVIDENCE_STR] + "…"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    text = str(value)
    return text if len(text) <= _MAX_EVIDENCE_STR else text[:_MAX_EVIDENCE_STR] + "…"


def _fingerprint(severity: Severity, alert_class: str, summary: str) -> str:
    """Stable identity of an alert's *meaning*.

    Deliberately excludes evidence (age counters, timestamps, etc.) so a persistently-dead heartbeat or a
    repeating identical failure dedupes instead of producing an email storm. A change in severity or in the
    human summary — i.e. a meaningful worsening/change — moves the fingerprint and yields an UPDATED event.
    """
    basis = json.dumps([severity.value, alert_class, summary], ensure_ascii=False)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- events


@dataclass
class AlertEvent:
    """The outcome of one lifecycle call. ``notify`` says whether an operator notification is warranted."""

    transition: str          # OPEN | UPDATED | RESOLVED | DEDUPED | NOOP
    alert: dict
    notify: bool

    @property
    def alert_key(self) -> str:
        return self.alert.get("alert_key", "")


# --------------------------------------------------------------------------- durable store


class AlertStore:
    """Durable, restart-safe alert lifecycle state.

    ``active.json`` holds the current alert per stable ``alert_key``; ``history.jsonl`` is the append-only
    audit of every transition; ``delivery_failures.jsonl`` records sends that could not be delivered. Every
    mutation re-reads ``active.json`` from disk so an independently-restarted watcher continues an existing
    incident (dedupe) rather than reopening it.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -- paths
    def _active_path(self) -> Path:
        return self.root / "active.json"

    def _history_path(self) -> Path:
        return self.root / "history.jsonl"

    def _delivery_failures_path(self) -> Path:
        return self.root / "delivery_failures.jsonl"

    # -- raw io
    def _load_active(self) -> dict:
        try:
            doc = json.loads(self._active_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return doc if isinstance(doc, dict) else {}

    def _save_active(self, doc: dict) -> None:
        fd, tmp = tempfile.mkstemp(dir=str(self.root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, sort_keys=True, indent=2)
            os.replace(tmp, self._active_path())
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _append(self, path: Path, record: dict) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    # -- introspection
    def active_alerts(self) -> list[dict]:
        return [dict(v) for v in self._load_active().values()]

    def get(self, alert_key: str) -> Optional[dict]:
        rec = self._load_active().get(alert_key)
        return dict(rec) if rec else None

    def history(self) -> list[dict]:
        path = self._history_path()
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    # -- lifecycle
    def open_or_update(self, *, alert_class: str, subject: str, severity: Any, summary: str,
                       evidence: Optional[dict] = None, now: Optional[datetime] = None) -> AlertEvent:
        """Open a new alert, meaningfully update an existing one, or dedupe an identical recurrence."""
        severity = _coerce_severity(severity)
        stamp = _now(now)
        key = f"{alert_class}:{subject}"
        fp = _fingerprint(severity, alert_class, summary)
        safe_evidence = _sanitize_evidence(evidence or {})
        active = self._load_active()
        current = active.get(key)

        if current is None or current.get("state") == AlertState.RESOLVED.value:
            generation = int(current.get("generation", 0)) + 1 if current else 1
            alert = {
                "schema_version": SCHEMA_VERSION,
                "alert_key": key,
                "incident_id": f"{key}#gen{generation}",
                "generation": generation,
                "alert_class": alert_class,
                "subject": subject,
                "severity": severity.value,
                "state": AlertState.OPEN.value,
                "summary": summary,
                "evidence": safe_evidence,
                "fingerprint": fp,
                "first_opened_at": _iso(stamp),
                "last_updated_at": _iso(stamp),
                "resolved_at": None,
                "occurrences": 1,
                "delivery": _initial_delivery(),
            }
            active[key] = alert
            self._save_active(active)
            self._record_history(alert, AlertState.OPEN)
            return AlertEvent(AlertState.OPEN.value, dict(alert),
                              notify=_SEVERITY_RANK[severity] >= _NOTIFY_MIN_RANK)

        # An active (unresolved) alert already exists for this identity.
        current["occurrences"] = int(current.get("occurrences", 1)) + 1
        current["last_updated_at"] = _iso(stamp)
        current["evidence"] = safe_evidence
        if current.get("fingerprint") == fp:
            # Identical meaning -> dedupe. Refresh last-seen/evidence, but do NOT notify (no email storm).
            active[key] = current
            self._save_active(active)
            return AlertEvent("DEDUPED", dict(current), notify=False)

        # Meaningful change (severity worsened, or summary changed) -> UPDATED notification.
        current["severity"] = severity.value
        current["summary"] = summary
        current["fingerprint"] = fp
        current["state"] = AlertState.UPDATED.value
        active[key] = current
        self._save_active(active)
        self._record_history(current, AlertState.UPDATED)
        return AlertEvent(AlertState.UPDATED.value, dict(current),
                          notify=_SEVERITY_RANK[severity] >= _NOTIFY_MIN_RANK)

    def resolve(self, *, alert_class: str, subject: str, summary: Optional[str] = None,
                evidence: Optional[dict] = None, now: Optional[datetime] = None) -> AlertEvent:
        """Resolve an active alert (recovery). A no-op when nothing is open for this identity."""
        stamp = _now(now)
        key = f"{alert_class}:{subject}"
        active = self._load_active()
        current = active.get(key)
        if current is None or current.get("state") == AlertState.RESOLVED.value:
            return AlertEvent("NOOP", current and dict(current) or {"alert_key": key}, notify=False)
        current["state"] = AlertState.RESOLVED.value
        current["resolved_at"] = _iso(stamp)
        current["last_updated_at"] = _iso(stamp)
        if summary:
            current["resolution_summary"] = summary
        if evidence:
            current["resolution_evidence"] = _sanitize_evidence(evidence)
        # Recovery of a condition that warranted attention is itself worth an operator RESOLVED note.
        severity = _coerce_severity(current.get("severity", Severity.INFO.value))
        active[key] = current
        self._save_active(active)
        self._record_history(current, AlertState.RESOLVED)
        return AlertEvent(AlertState.RESOLVED.value, dict(current),
                          notify=_SEVERITY_RANK[severity] >= _NOTIFY_MIN_RANK)

    def record_delivery(self, alert_key: str, result: dict) -> None:
        """Persist the outcome of a delivery attempt against the alert, and log any failure durably."""
        active = self._load_active()
        current = active.get(alert_key)
        if current is not None:
            current["delivery"] = result
            active[alert_key] = current
            self._save_active(active)
        if result.get("status") not in ("delivered", "suppressed"):
            self._append(self._delivery_failures_path(), {
                "logged_at": _iso(_now(None)),
                "alert_key": alert_key,
                "incident_id": (current or {}).get("incident_id"),
                "delivery": result,
            })

    def _record_history(self, alert: dict, state: AlertState) -> None:
        self._append(self._history_path(), {
            "logged_at": _iso(_now(None)),
            "transition": state.value,
            "alert_key": alert["alert_key"],
            "incident_id": alert["incident_id"],
            "generation": alert["generation"],
            "severity": alert["severity"],
            "alert_class": alert["alert_class"],
            "subject": alert["subject"],
            "summary": alert["summary"],
        })


def _initial_delivery() -> dict:
    return {"status": "pending", "attempts": 0, "last_error": None, "last_delivered_at": None}


# --------------------------------------------------------------------------- transport seam


class TransportError(RuntimeError):
    """A transport could not deliver a message. Bounded-retried by the notifier; never recurses."""


class EmailTransport(Protocol):
    def send(self, message: dict) -> None:  # pragma: no cover - protocol
        ...


@dataclass
class SMTPEmailTransport:
    """Production-capable SMTP transport. Credentials come from configuration, never the source tree.

    This is the real sending seam for later: give it real ``host``/credentials and a verified sender
    domain and it delivers. A transport error (connection, auth, refusal) is raised as
    :class:`TransportError` so the notifier records an explicit, inspectable delivery failure.
    """

    host: str
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    timeout: float = 30.0

    def send(self, message: dict) -> None:
        import smtplib
        from email.message import EmailMessage

        if not self.host:
            raise TransportError("no SMTP host configured")
        msg = EmailMessage()
        msg["From"] = message["from"]
        msg["To"] = ", ".join(message["to"])
        msg["Subject"] = message["subject"]
        msg.set_content(message["body"])
        try:
            if self.port == 465:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            with server:
                server.ehlo()
                if self.use_tls and self.port != 465:
                    server.starttls()
                    server.ehlo()
                if self.username:
                    server.login(self.username, self.password)
                server.send_message(msg)
        except (OSError, smtplib.SMTPException) as exc:
            # Never surface the credential-bearing exception verbatim; keep the transport error type.
            raise TransportError(f"SMTP delivery failed ({type(exc).__name__})") from None


@dataclass
class DisabledTransport:
    """Explicit 'no sending identity configured' transport.

    Alerts are still opened and persisted durably; delivery is reported as ``not_configured`` rather than
    silently treated as delivered. This is the safe default until real email credentials exist.
    """

    reason: str = "operator email transport not configured"

    def send(self, message: dict) -> None:
        raise TransportError(self.reason)


@dataclass
class RecordingTransport:
    """In-memory transport for deterministic tests. Optionally fails the first ``fail_times`` sends."""

    sent: list = field(default_factory=list)
    fail_times: int = 0
    _attempts: int = 0

    def send(self, message: dict) -> None:
        self._attempts += 1
        if self._attempts <= self.fail_times:
            raise TransportError(f"synthetic transport failure #{self._attempts}")
        self.sent.append(message)


# --------------------------------------------------------------------------- message construction


def build_email(alert: dict, transition: str, *, sender: str, recipients: list[str]) -> dict:
    """Construct a sanitised operator email. Contains identifiers + references, not raw restricted data."""
    sev = alert.get("severity", Severity.INFO.value)
    subject = f"[PYRNOVA {sev}] {transition}: {alert.get('summary', '')}"[:200]
    lines = [
        f"Severity:     {sev}",
        f"State:        {transition}",
        f"Alert class:  {alert.get('alert_class')}",
        f"Subject:      {alert.get('subject')}",
        f"Alert key:    {alert.get('alert_key')}",
        f"Incident id:  {alert.get('incident_id')} (generation {alert.get('generation')})",
        f"First opened: {alert.get('first_opened_at')}",
        f"Last updated: {alert.get('last_updated_at')}",
        f"Occurrences:  {alert.get('occurrences')}",
    ]
    if alert.get("resolved_at"):
        lines.append(f"Resolved at:  {alert.get('resolved_at')}")
    lines.append("")
    lines.append("Summary:")
    lines.append(f"  {alert.get('summary', '')}")
    evidence = alert.get("evidence") or {}
    if evidence:
        lines.append("")
        lines.append("Evidence (references only; restricted data is redacted):")
        lines.append(json.dumps(_sanitize_evidence(evidence), ensure_ascii=False, indent=2, sort_keys=True))
    return {"from": sender, "to": list(recipients), "subject": subject, "body": "\n".join(lines)}


# --------------------------------------------------------------------------- notifier


@dataclass
class Notifier:
    """Bounded-retry delivery over a transport. Never recurses on failure.

    A delivery failure returns an explicit result (``status='failed'``/``'not_configured'``) that the
    caller persists against the alert; it never itself raises another alert. When ``recipients`` or the
    transport are absent, delivery is reported as suppressed/not-configured rather than silently succeeding.
    """

    transport: Any
    sender: str
    recipients: list[str]
    max_attempts: int = 3

    @property
    def configured(self) -> bool:
        return bool(self.transport) and not isinstance(self.transport, DisabledTransport) \
            and bool(self.sender) and bool(self.recipients)

    def deliver(self, alert: dict, transition: str, *, now: Optional[datetime] = None) -> dict:
        stamp = _now(now)
        if not self.recipients or not self.sender:
            return {"status": "not_configured", "attempts": 0,
                    "last_error": "no operator recipient/sender configured", "last_delivered_at": None,
                    "last_attempt_at": _iso(stamp)}
        message = build_email(alert, transition, sender=self.sender, recipients=self.recipients)
        last_error: Optional[str] = None
        attempts = 0
        for attempts in range(1, max(1, self.max_attempts) + 1):
            try:
                self.transport.send(message)
                return {"status": "delivered", "attempts": attempts, "last_error": None,
                        "last_delivered_at": _iso(_now(None)), "last_attempt_at": _iso(_now(None))}
            except TransportError as exc:
                last_error = str(exc)
        status = "not_configured" if isinstance(self.transport, DisabledTransport) else "failed"
        return {"status": status, "attempts": attempts, "last_error": last_error,
                "last_delivered_at": None, "last_attempt_at": _iso(_now(None))}


# --------------------------------------------------------------------------- manager


@dataclass
class AlertManager:
    """Ties the durable store to the notifier: raise / resolve alerts and record delivery outcomes."""

    store: AlertStore
    notifier: Optional[Notifier] = None

    def raise_alert(self, *, alert_class: str, subject: str, severity: Any, summary: str,
                    evidence: Optional[dict] = None, now: Optional[datetime] = None) -> AlertEvent:
        event = self.store.open_or_update(alert_class=alert_class, subject=subject, severity=severity,
                                          summary=summary, evidence=evidence, now=now)
        self._maybe_notify(event, now=now)
        return event

    def resolve(self, *, alert_class: str, subject: str, summary: Optional[str] = None,
                evidence: Optional[dict] = None, now: Optional[datetime] = None) -> AlertEvent:
        event = self.store.resolve(alert_class=alert_class, subject=subject, summary=summary,
                                   evidence=evidence, now=now)
        self._maybe_notify(event, now=now)
        return event

    def _maybe_notify(self, event: AlertEvent, *, now: Optional[datetime]) -> None:
        if not event.notify:
            return
        if self.notifier is None:
            # No notifier at all still leaves the durable alert; record that delivery was not attempted.
            self.store.record_delivery(event.alert_key, {
                "status": "not_configured", "attempts": 0,
                "last_error": "no notifier configured", "last_delivered_at": None})
            return
        result = self.notifier.deliver(event.alert, event.transition, now=now)
        self.store.record_delivery(event.alert_key, result)


# --------------------------------------------------------------------------- Live Ops health bridge

# Alert classes used by the health bridge and the watchdog (stable identity across restarts).
SOURCE_HEALTH_CLASS = "source_health"
DEADMAN_CLASS = "deadman_liveness"
PERSISTENCE_CLASS = "state_persistence"
CYCLE_CLASS = "operational_cycle"


def evaluate_source_health(manager: AlertManager, rows: list[dict], *,
                           critical_failed_cycles: int = 5, now: Optional[datetime] = None) -> list[AlertEvent]:
    """Map :meth:`scheduler.health` rows onto the alert doctrine.

    HEALTHY / PAUSED / UNKNOWN are routine (INFO) — no operator email; a source returning to HEALTHY
    resolves any open source alert. DEGRADED (stale / last error) is OPERATOR_ATTENTION. FAILED (circuit
    open or repeated failed cycles) is OPERATOR_ATTENTION, escalating to CRITICAL once repeated cycle
    failures reach ``critical_failed_cycles`` with no recovery.
    """
    events: list[AlertEvent] = []
    for row in rows:
        sid = row.get("source_id", "?")
        state = row.get("operational_state")
        failed = int(row.get("consecutive_failed_cycles") or 0)
        if state == "FAILED":
            severity = Severity.CRITICAL if failed >= critical_failed_cycles else Severity.OPERATOR_ATTENTION
            summary = (f"Source '{sid}' repeated cycle failure with no recovery"
                       if severity is Severity.CRITICAL
                       else f"Source '{sid}' failing (circuit/retry exhaustion) — operator action required")
            events.append(manager.raise_alert(
                alert_class=SOURCE_HEALTH_CLASS, subject=sid, severity=severity, summary=summary,
                evidence={"operational_state": state, "consecutive_failed_cycles": failed,
                          "circuit_state": row.get("circuit_state"),
                          "last_error": row.get("last_error"),
                          "last_successful_acquisition_at": row.get("last_successful_acquisition_at")},
                now=now))
        elif state == "DEGRADED":
            events.append(manager.raise_alert(
                alert_class=SOURCE_HEALTH_CLASS, subject=sid, severity=Severity.OPERATOR_ATTENTION,
                summary=f"Source '{sid}' degraded (stale or recoverable errors) — needs operator awareness",
                evidence={"operational_state": state, "freshness_state": row.get("freshness_state"),
                          "last_error": row.get("last_error"),
                          "last_successful_acquisition_at": row.get("last_successful_acquisition_at")},
                now=now))
        elif state == "HEALTHY":
            events.append(manager.resolve(
                alert_class=SOURCE_HEALTH_CLASS, subject=sid,
                summary=f"Source '{sid}' recovered to HEALTHY",
                evidence={"last_successful_acquisition_at": row.get("last_successful_acquisition_at")},
                now=now))
        # PAUSED (deliberate) and UNKNOWN (no basis to alarm) are logs-only by doctrine.
    return events


def evaluate_cycle_health(manager: AlertManager, *, subject: str, consecutive_failed_cycles: int,
                          attention_threshold: int = 2, critical_threshold: int = 5,
                          last_error: Optional[str] = None, now: Optional[datetime] = None) -> AlertEvent:
    """Map the *operational cycle* (the loop itself, distinct from any one source) onto the doctrine.

    Zero failures resolves any open cycle alert (recovery). Reaching ``attention_threshold`` is
    OPERATOR_ATTENTION; ``critical_threshold`` escalates to CRITICAL. Repeated identical counts dedupe;
    crossing a threshold is a meaningful worsening (UPDATED).
    """
    failed = int(consecutive_failed_cycles or 0)
    if failed <= 0:
        return manager.resolve(alert_class=CYCLE_CLASS, subject=subject,
                               summary="Operational cycle recovered", now=now)
    if failed >= critical_threshold:
        severity = Severity.CRITICAL
        summary = f"Operational cycle '{subject}' failing repeatedly ({failed}x) — trustworthy operation at risk"
    elif failed >= attention_threshold:
        severity = Severity.OPERATOR_ATTENTION
        summary = f"Operational cycle '{subject}' failing ({failed}x) — operator awareness required"
    else:
        # A single blip is not operator-facing; stay logs-only (INFO, never emailed) and do not open noise.
        return manager.raise_alert(alert_class=CYCLE_CLASS, subject=subject, severity=Severity.INFO,
                                   summary=f"Operational cycle '{subject}' single failure", now=now,
                                   evidence={"consecutive_failed_cycles": failed, "last_error": last_error})
    return manager.raise_alert(alert_class=CYCLE_CLASS, subject=subject, severity=severity, summary=summary,
                               evidence={"consecutive_failed_cycles": failed, "last_error": last_error}, now=now)


def evaluate_persistence(manager: AlertManager, *, subject: str, ok: bool, detail: str = "",
                         now: Optional[datetime] = None) -> AlertEvent:
    """Durable persistence / state integrity. A failure threatens evidence integrity, so it is CRITICAL;
    a return to healthy resolves it. ``detail`` is a short reference, never raw restricted state."""
    if ok:
        return manager.resolve(alert_class=PERSISTENCE_CLASS, subject=subject,
                               summary="Durable persistence healthy", now=now)
    return manager.raise_alert(
        alert_class=PERSISTENCE_CLASS, subject=subject, severity=Severity.CRITICAL,
        summary=f"Durable persistence failure at '{subject}' — evidence integrity at risk",
        evidence={"detail": detail}, now=now)


__all__ = [
    "SCHEMA_VERSION", "Severity", "AlertState", "AlertEvent", "AlertStore",
    "TransportError", "EmailTransport", "SMTPEmailTransport", "DisabledTransport", "RecordingTransport",
    "build_email", "Notifier", "AlertManager",
    "evaluate_source_health", "evaluate_cycle_health", "evaluate_persistence",
    "SOURCE_HEALTH_CLASS", "DEADMAN_CLASS", "PERSISTENCE_CLASS", "CYCLE_CLASS",
]
