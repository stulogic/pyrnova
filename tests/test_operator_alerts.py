"""Operator alerts + independent dead-man watcher — isolated, controlled-time verification.

Every test uses tmp_path fixtures and injected ``now`` timestamps; nothing here touches the protected
live-ops soak, real SMTP, or any real inbox. Delivery is exercised through RecordingTransport /
DisabledTransport only. The ten representative conditions from the workstream spec are each covered and
named in the test docstrings.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pyrnova.alerts import (AlertManager, AlertState, AlertStore, DEADMAN_CLASS, DisabledTransport,
                            Notifier, RecordingTransport, Severity, build_email, evaluate_cycle_health,
                            evaluate_persistence, evaluate_source_health)
from pyrnova.config import AlertConfig
from pyrnova.heartbeat import HeartbeatReader, HeartbeatWriter, Liveness
from pyrnova.watchdog import build_transport, check_once

BASE = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _t(seconds: float) -> datetime:
    return BASE + timedelta(seconds=seconds)


def _manager(tmp_path, **notifier_kw):
    store = AlertStore(tmp_path / "alerts")
    notifier = None
    if notifier_kw:
        notifier = Notifier(sender="ops@pyrnova.example",
                            recipients=["operator@pyrnova.example"],
                            **notifier_kw)
    return AlertManager(store=store, notifier=notifier), store


# --------------------------------------------------------------------------- lifecycle: OPEN/UPDATED/RESOLVED


def test_open_update_resolve_lifecycle(tmp_path):
    """Condition 6 (update) + 7 (recovery): OPEN -> UPDATED -> RESOLVED with stable identity/generation."""
    mgr, store = _manager(tmp_path)
    open_ev = mgr.raise_alert(alert_class="source_health", subject="sam", severity=Severity.OPERATOR_ATTENTION,
                              summary="Source 'sam' degraded", now=_t(0))
    assert open_ev.transition == AlertState.OPEN.value
    assert open_ev.notify is True
    key = open_ev.alert_key

    # Meaningful worsening (severity up) -> UPDATED, new notify, same alert_key/generation.
    upd_ev = mgr.raise_alert(alert_class="source_health", subject="sam", severity=Severity.CRITICAL,
                             summary="Source 'sam' failing", now=_t(60))
    assert upd_ev.transition == AlertState.UPDATED.value
    assert upd_ev.notify is True
    assert upd_ev.alert_key == key
    assert store.get(key)["generation"] == 1
    assert store.get(key)["first_opened_at"] == open_ev.alert["first_opened_at"]

    # Recovery -> RESOLVED.
    res_ev = mgr.resolve(alert_class="source_health", subject="sam", summary="recovered", now=_t(120))
    assert res_ev.transition == AlertState.RESOLVED.value
    assert store.get(key)["state"] == AlertState.RESOLVED.value
    assert store.get(key)["resolved_at"] is not None

    # A later new incident OPENs a new generation, not a reopen of the resolved one.
    regen = mgr.raise_alert(alert_class="source_health", subject="sam", severity=Severity.OPERATOR_ATTENTION,
                            summary="Source 'sam' degraded again", now=_t(200))
    assert regen.transition == AlertState.OPEN.value
    assert store.get(key)["generation"] == 2

    transitions = [h["transition"] for h in store.history()]
    assert transitions == ["OPEN", "UPDATED", "RESOLVED", "OPEN"]


def test_dedupe_no_storm(tmp_path):
    """Condition 5 (dedupe): identical repeated conditions do not create new alerts or notifications."""
    mgr, store = _manager(tmp_path)
    first = mgr.raise_alert(alert_class=DEADMAN_CLASS, subject="live_ops", severity=Severity.CRITICAL,
                            summary="heartbeat STALE", now=_t(0))
    assert first.transition == AlertState.OPEN.value and first.notify is True
    for i in range(1, 6):
        ev = mgr.raise_alert(alert_class=DEADMAN_CLASS, subject="live_ops", severity=Severity.CRITICAL,
                             summary="heartbeat STALE", now=_t(i))
        assert ev.transition == "DEDUPED"
        assert ev.notify is False
    assert len(store.active_alerts()) == 1
    assert store.get(first.alert_key)["occurrences"] == 6
    # Only the single OPEN is in history — no storm.
    assert [h["transition"] for h in store.history()] == ["OPEN"]


def test_info_never_notifies(tmp_path):
    """Severity doctrine: INFO is durable but never emails an operator."""
    mgr, store = _manager(tmp_path, transport=RecordingTransport())
    ev = mgr.raise_alert(alert_class="operational_cycle", subject="loop", severity=Severity.INFO,
                         summary="single blip", now=_t(0))
    assert ev.notify is False
    assert mgr.notifier.transport.sent == []
    # ...but it is still recorded durably for inspection.
    assert store.get(ev.alert_key)["severity"] == "INFO"


# --------------------------------------------------------------------------- transport


def test_transport_delivers_and_records(tmp_path):
    """Happy-path delivery over the recording transport; delivery result persisted against the alert."""
    mgr, store = _manager(tmp_path, transport=RecordingTransport())
    ev = mgr.raise_alert(alert_class=DEADMAN_CLASS, subject="live_ops", severity=Severity.CRITICAL,
                         summary="down", now=_t(0))
    assert len(mgr.notifier.transport.sent) == 1
    assert store.get(ev.alert_key)["delivery"]["status"] == "delivered"


def test_transport_failure_is_durable_and_bounded(tmp_path):
    """Condition 8 (transport failure): bounded retries, explicit failure, durable failure log, no storm."""
    transport = RecordingTransport(fail_times=99)  # always fails
    mgr, store = _manager(tmp_path, transport=transport, max_attempts=3)
    ev = mgr.raise_alert(alert_class=DEADMAN_CLASS, subject="live_ops", severity=Severity.CRITICAL,
                         summary="down", now=_t(0))
    rec = store.get(ev.alert_key)
    assert rec["delivery"]["status"] == "failed"
    assert rec["delivery"]["attempts"] == 3          # bounded
    assert rec["delivery"]["last_error"]
    # The incident still exists and is inspectable even though delivery failed.
    assert rec["state"] == AlertState.OPEN.value
    # Failure recorded durably; a broken transport does not itself raise another alert (no recursion).
    failures = (store._delivery_failures_path()).read_text(encoding="utf-8").strip().splitlines()
    assert len(failures) == 1
    assert len(store.active_alerts()) == 1


def test_transport_recovers_after_retry(tmp_path):
    """Bounded retry succeeds on a later attempt within the same deliver() call."""
    transport = RecordingTransport(fail_times=2)
    mgr, store = _manager(tmp_path, transport=transport, max_attempts=3)
    ev = mgr.raise_alert(alert_class=DEADMAN_CLASS, subject="live_ops", severity=Severity.CRITICAL,
                         summary="down", now=_t(0))
    rec = store.get(ev.alert_key)
    assert rec["delivery"]["status"] == "delivered"
    assert rec["delivery"]["attempts"] == 3


def test_disabled_transport_is_explicit_not_silent(tmp_path):
    """A missing sending identity reports not_configured — never a silent 'delivered'."""
    store = AlertStore(tmp_path / "alerts")
    notifier = Notifier(transport=DisabledTransport(), sender="ops@pyrnova.example",
                        recipients=["operator@pyrnova.example"])
    mgr = AlertManager(store=store, notifier=notifier)
    ev = mgr.raise_alert(alert_class=DEADMAN_CLASS, subject="live_ops", severity=Severity.CRITICAL,
                         summary="down", now=_t(0))
    assert store.get(ev.alert_key)["delivery"]["status"] == "not_configured"


# --------------------------------------------------------------------------- security / privacy


def test_email_and_evidence_redact_secrets(tmp_path):
    """Operator emails/evidence must not leak secrets or dump restricted payloads."""
    mgr, store = _manager(tmp_path)
    ev = mgr.raise_alert(
        alert_class="source_health", subject="sam", severity=Severity.CRITICAL,
        summary="failing",
        evidence={"api_key": "SECRET-XYZ", "authorization": "Bearer abc",
                  "source_id": "sam", "raw_content": "x" * 5000, "note": "y" * 5000}, now=_t(0))
    stored = store.get(ev.alert_key)["evidence"]
    assert stored["api_key"] == "[redacted]"
    assert stored["authorization"] == "[redacted]"
    assert stored["raw_content"] == "[redacted]"       # key token 'raw_content'
    assert stored["source_id"] == "sam"                 # identifier passes through
    assert len(stored["note"]) <= 301                   # long value truncated
    email = build_email(store.get(ev.alert_key), "OPEN", sender="ops@pyrnova.example",
                        recipients=["operator@pyrnova.example"])
    assert "SECRET-XYZ" not in email["body"]
    assert "Bearer abc" not in email["body"]


# --------------------------------------------------------------------------- doctrine bridges


def test_evaluate_source_health_doctrine(tmp_path):
    """Condition 2 (unrecovered source degradation): DEGRADED/FAILED page; HEALTHY resolves; PAUSED silent."""
    mgr, store = _manager(tmp_path)
    rows = [
        {"source_id": "sam", "operational_state": "DEGRADED", "last_error": "timeout"},
        {"source_id": "usa", "operational_state": "FAILED", "consecutive_failed_cycles": 2},
        {"source_id": "fed", "operational_state": "FAILED", "consecutive_failed_cycles": 6},
        {"source_id": "sec", "operational_state": "PAUSED"},
    ]
    events = evaluate_source_health(mgr, rows, critical_failed_cycles=5, now=_t(0))
    by_subject = {e.alert["subject"]: e for e in events if e.alert.get("subject")}
    assert by_subject["sam"].alert["severity"] == "OPERATOR_ATTENTION"
    assert by_subject["usa"].alert["severity"] == "OPERATOR_ATTENTION"
    assert by_subject["fed"].alert["severity"] == "CRITICAL"       # escalation past threshold
    # PAUSED is deliberate -> no active alert opened for it.
    assert "sec" not in {a["subject"] for a in store.active_alerts()}

    # Recovery to HEALTHY resolves the open 'sam' alert.
    evaluate_source_health(mgr, [{"source_id": "sam", "operational_state": "HEALTHY",
                                  "last_successful_acquisition_at": "2026-01-01T12:05:00+00:00"}], now=_t(300))
    assert store.get("source_health:sam")["state"] == AlertState.RESOLVED.value


def test_evaluate_cycle_health(tmp_path):
    """Condition 1 (repeated operational cycle failure): attention then CRITICAL, then resolve at zero."""
    mgr, store = _manager(tmp_path)
    e1 = evaluate_cycle_health(mgr, subject="live_ops", consecutive_failed_cycles=2, now=_t(0))
    assert e1.alert["severity"] == "OPERATOR_ATTENTION"
    e2 = evaluate_cycle_health(mgr, subject="live_ops", consecutive_failed_cycles=5, now=_t(60))
    assert e2.alert["severity"] == "CRITICAL" and e2.transition == AlertState.UPDATED.value
    e3 = evaluate_cycle_health(mgr, subject="live_ops", consecutive_failed_cycles=0, now=_t(120))
    assert e3.transition == AlertState.RESOLVED.value


def test_evaluate_persistence_critical_and_recovery(tmp_path):
    """Condition 3 (durable persistence/state failure): CRITICAL on failure, resolve on recovery."""
    mgr, store = _manager(tmp_path)
    bad = evaluate_persistence(mgr, subject="var/state", ok=False, detail="write EIO", now=_t(0))
    assert bad.alert["severity"] == "CRITICAL"
    good = evaluate_persistence(mgr, subject="var/state", ok=True, now=_t(60))
    assert good.transition == AlertState.RESOLVED.value


# --------------------------------------------------------------------------- heartbeat + independent watcher


def test_heartbeat_fresh_stale_missing_maintenance(tmp_path):
    """Heartbeat freshness primitives: FRESH within threshold, STALE past it, MISSING absent, MAINTENANCE."""
    hb_dir = tmp_path / "hb"
    writer = HeartbeatWriter(hb_dir)
    reader = HeartbeatReader(hb_dir)

    # No record yet -> MISSING (fail closed).
    assert reader.status("live_ops", max_silence_seconds=300, now=_t(0))["state"] == Liveness.MISSING.value

    writer.beat("live_ops", now=_t(0))
    assert reader.status("live_ops", max_silence_seconds=300, now=_t(100))["state"] == Liveness.FRESH.value
    assert reader.status("live_ops", max_silence_seconds=300, now=_t(400))["state"] == Liveness.STALE.value

    # A corrupt record reads as MISSING, never as fresh.
    (hb_dir / "live_ops.json").write_text("{ not json", encoding="utf-8")
    assert reader.status("live_ops", max_silence_seconds=300, now=_t(0))["state"] == Liveness.MISSING.value

    writer.set_maintenance("live_ops", active=True, reason="planned", now=_t(0))
    assert reader.status("live_ops", max_silence_seconds=300, now=_t(9999))["state"] == Liveness.MAINTENANCE.value


def test_heartbeat_sequence_restart_safe(tmp_path):
    """A fresh writer continues the sequence rather than resetting it."""
    hb_dir = tmp_path / "hb"
    HeartbeatWriter(hb_dir).beat("live_ops", now=_t(0))
    HeartbeatWriter(hb_dir).beat("live_ops", now=_t(1))   # a *new* writer instance (restart)
    rec = HeartbeatReader(hb_dir).read("live_ops")
    assert rec["sequence"] == 2


def test_watchdog_deadman_expiry_and_recovery(tmp_path):
    """Condition 4 (dead-man expiry) + 10 (healthy no-alert) via the independent watcher."""
    hb_dir, reader = tmp_path / "hb", None
    writer = HeartbeatWriter(tmp_path / "hb")
    reader = HeartbeatReader(tmp_path / "hb")
    mgr, store = _manager(tmp_path, transport=RecordingTransport())

    writer.beat("live_ops", now=_t(0))

    # Healthy: FRESH -> NOOP, nothing opened, no email (condition 10).
    status, ev = check_once(reader, mgr, component="live_ops", max_silence_seconds=300, now=_t(100))
    assert status["state"] == Liveness.FRESH.value
    assert ev.transition == "NOOP"
    assert store.active_alerts() == []
    assert mgr.notifier.transport.sent == []

    # Silence past threshold: STALE -> CRITICAL OPEN + one email (condition 4).
    status, ev = check_once(reader, mgr, component="live_ops", max_silence_seconds=300, now=_t(400))
    assert status["state"] == Liveness.STALE.value
    assert ev.transition == AlertState.OPEN.value
    assert ev.alert["severity"] == "CRITICAL"
    assert len(mgr.notifier.transport.sent) == 1

    # Still expired: DEDUPE, no second email (no storm).
    status, ev = check_once(reader, mgr, component="live_ops", max_silence_seconds=300, now=_t(500))
    assert ev.transition == "DEDUPED"
    assert len(mgr.notifier.transport.sent) == 1

    # Service resumes -> FRESH -> RESOLVED.
    writer.beat("live_ops", now=_t(600))
    status, ev = check_once(reader, mgr, component="live_ops", max_silence_seconds=300, now=_t(620))
    assert status["state"] == Liveness.FRESH.value
    assert ev.transition == AlertState.RESOLVED.value
    assert store.get(ev.alert_key)["state"] == AlertState.RESOLVED.value


def test_watchdog_stale_to_missing_is_update(tmp_path):
    """Meaningful worsening: STALE heartbeat then a removed record (MISSING) yields an UPDATED, not a dup."""
    writer = HeartbeatWriter(tmp_path / "hb")
    reader = HeartbeatReader(tmp_path / "hb")
    mgr, store = _manager(tmp_path, transport=RecordingTransport())

    writer.beat("live_ops", now=_t(0))
    _, open_ev = check_once(reader, mgr, component="live_ops", max_silence_seconds=300, now=_t(400))
    assert open_ev.transition == AlertState.OPEN.value

    (tmp_path / "hb" / "live_ops.json").unlink()   # total disappearance -> MISSING
    _, upd = check_once(reader, mgr, component="live_ops", max_silence_seconds=300, now=_t(500))
    assert upd.transition == AlertState.UPDATED.value
    assert len(mgr.notifier.transport.sent) == 2    # worsening warrants a fresh notification


def test_watchdog_maintenance_no_false_page(tmp_path):
    """Deliberate maintenance must not raise a dead-man CRITICAL even long past the threshold."""
    writer = HeartbeatWriter(tmp_path / "hb")
    reader = HeartbeatReader(tmp_path / "hb")
    mgr, store = _manager(tmp_path, transport=RecordingTransport())
    writer.beat("live_ops", now=_t(0))
    writer.set_maintenance("live_ops", active=True, reason="deploy", now=_t(0))
    status, ev = check_once(reader, mgr, component="live_ops", max_silence_seconds=1, now=_t(9999))
    assert status["state"] == Liveness.MAINTENANCE.value
    assert mgr.notifier.transport.sent == []
    assert [a for a in store.active_alerts() if a["state"] != "RESOLVED"] == []


def test_watchdog_restart_continues_open_incident(tmp_path):
    """Condition 9 (watcher restart): a fresh watcher over the same durable store continues the OPEN
    incident (dedupe) instead of reopening it."""
    writer = HeartbeatWriter(tmp_path / "hb")
    reader = HeartbeatReader(tmp_path / "hb")
    writer.beat("live_ops", now=_t(0))

    # First watcher process opens the dead-man incident.
    mgr1, store1 = _manager(tmp_path, transport=RecordingTransport())
    _, ev1 = check_once(reader, mgr1, component="live_ops", max_silence_seconds=300, now=_t(400))
    assert ev1.transition == AlertState.OPEN.value
    first_opened = store1.get(ev1.alert_key)["first_opened_at"]

    # Watcher restarts: brand-new manager/store objects over the SAME directory.
    mgr2, store2 = _manager(tmp_path, transport=RecordingTransport())
    _, ev2 = check_once(reader, mgr2, component="live_ops", max_silence_seconds=300, now=_t(500))
    assert ev2.transition == "DEDUPED"                       # not reopened
    assert store2.get(ev2.alert_key)["first_opened_at"] == first_opened
    assert store2.get(ev2.alert_key)["generation"] == 1
    assert mgr2.notifier.transport.sent == []                # restart alone does not re-page


# --------------------------------------------------------------------------- config seam


def _cfg(**over) -> AlertConfig:
    base = dict(enabled=True, recipients=("operator@pyrnova.example",), sender="ops@pyrnova.example",
                smtp_host="smtp.example.com", smtp_port=587, smtp_username="u", smtp_password="p",
                smtp_use_tls=True, max_attempts=3, alert_state_dir="/tmp/x", heartbeat_dir="/tmp/y",
                deadman_component="live_ops", deadman_max_silence_seconds=900.0)
    base.update(over)
    return AlertConfig(**base)


def test_build_transport_disabled_when_no_identity(tmp_path):
    """Transport is DisabledTransport (explicit) unless a real host+sender+recipient exist and enabled."""
    from pyrnova.alerts import SMTPEmailTransport
    assert isinstance(build_transport(_cfg(smtp_host="")), DisabledTransport)
    assert isinstance(build_transport(_cfg(recipients=())), DisabledTransport)
    assert isinstance(build_transport(_cfg(enabled=False)), DisabledTransport)
    assert isinstance(build_transport(_cfg()), SMTPEmailTransport)
