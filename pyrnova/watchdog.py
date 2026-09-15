"""Independent dead-man / liveness watcher.

This is a *separate* process from the Pyrnova service. It shares only the on-disk heartbeat record
(:mod:`pyrnova.heartbeat`) and the durable alert store (:mod:`pyrnova.alerts`). It never imports or drives
the service loop, so it can detect *total service death* — the case a monitor living inside that same loop
can never report because it dies with it.

Operational shape::

    PYRNOVA SERVICE  --beat()-->  var/heartbeat/<component>.json
    WATCHER (this)   --status()-> reads freshness, independently
                     --raise/resolve--> var/alerts/{active.json,history.jsonl,delivery_failures.jsonl}
                     --deliver--> configured operator email transport

Scheduling is external and deliberate (cron / launchd / systemd timer) so the watcher's own liveness does
not depend on the service. ``python -m pyrnova.watchdog check`` runs exactly one evaluation and exits with
a status code, which is the natural unit for a supervised timer. It is NEVER deployed into the running soak.

Behaviour (see docs/operations/OPERATOR_ALERTS_EVIDENCE.md):
- FRESH heartbeat            -> resolve any open dead-man incident (recovery -> RESOLVED);
- STALE / MISSING heartbeat  -> CRITICAL dead-man incident; identical repeats DEDUPE (no storm); a
                               meaningful change (STALE -> MISSING) is an UPDATED;
- MAINTENANCE (deliberate)   -> no false page; resolves any open incident with a maintenance note.
A restarted watcher re-reads the durable store, so an existing OPEN incident continues rather than reopening.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Optional

from .alerts import (AlertEvent, AlertManager, AlertStore, DEADMAN_CLASS, DisabledTransport, Notifier,
                     SMTPEmailTransport, Severity)
from .config import AlertConfig, load_alert_config
from .heartbeat import HeartbeatReader, Liveness


def build_transport(cfg: AlertConfig):
    """Return a real SMTP transport when a sending identity is configured, else an explicit DisabledTransport.

    A disabled transport still lets alerts open and persist durably; delivery is reported ``not_configured``
    rather than being silently treated as delivered. No credentials are read from the source tree.
    """
    if cfg.enabled and cfg.delivery_configured:
        return SMTPEmailTransport(
            host=cfg.smtp_host, port=cfg.smtp_port, username=cfg.smtp_username,
            password=cfg.smtp_password, use_tls=cfg.smtp_use_tls)
    reason = ("operator email transport disabled" if not cfg.enabled
              else "operator email transport not configured (missing host/sender/recipient)")
    return DisabledTransport(reason=reason)


def build_manager(cfg: AlertConfig) -> AlertManager:
    """Assemble the durable store + bounded-retry notifier from external configuration."""
    store = AlertStore(cfg.alert_state_dir)
    notifier = Notifier(transport=build_transport(cfg), sender=cfg.sender,
                        recipients=list(cfg.recipients), max_attempts=cfg.max_attempts)
    return AlertManager(store=store, notifier=notifier)


def check_once(reader: HeartbeatReader, manager: AlertManager, *, component: str,
               max_silence_seconds: float, now: Optional[datetime] = None) -> tuple[dict, AlertEvent]:
    """Run one independent liveness evaluation. Returns ``(liveness_status, alert_event)``.

    Deterministic under an injected ``now`` — the whole point for controlled-time tests.
    """
    status = reader.status(component, max_silence_seconds=max_silence_seconds, now=now)
    state = status["state"]
    subject = component

    if state in (Liveness.STALE.value, Liveness.MISSING.value):
        # The summary embeds the STATE (so STALE->MISSING is a meaningful UPDATED) and the fixed threshold,
        # but deliberately NOT the elapsed age — an ever-growing age counter must dedupe, not storm. The
        # live age is carried in evidence, which the fingerprint excludes.
        age = status.get("age_seconds")
        summary = (f"Live Ops heartbeat '{component}' {state} — service may be down "
                   f"(threshold {max_silence_seconds:.0f}s)")
        event = manager.raise_alert(
            alert_class=DEADMAN_CLASS, subject=subject, severity=Severity.CRITICAL, summary=summary,
            evidence={"liveness_state": state, "age_seconds": age,
                      "last_beat_at": status.get("last_beat_at"), "sequence": status.get("sequence"),
                      "max_silence_seconds": max_silence_seconds}, now=now)
        return status, event

    if state == Liveness.MAINTENANCE.value:
        # Deliberate downtime: never page. Clear any open incident so recovery is clean.
        event = manager.resolve(
            alert_class=DEADMAN_CLASS, subject=subject,
            summary=f"Live Ops '{component}' in deliberate maintenance — dead-man suppressed",
            evidence={"maintenance_reason": status.get("maintenance_reason", "")}, now=now)
        return status, event

    # FRESH -> healthy. Resolve any open dead-man incident; a no-op when nothing is open (no noise).
    event = manager.resolve(
        alert_class=DEADMAN_CLASS, subject=subject,
        summary=f"Live Ops heartbeat '{component}' fresh — service alive",
        evidence={"age_seconds": status.get("age_seconds"), "sequence": status.get("sequence")}, now=now)
    return status, event


def run_check(cfg: Optional[AlertConfig] = None) -> int:
    """CLI-facing single evaluation. Exit code: 0 healthy/maintenance/resolved, 2 dead-man CRITICAL open."""
    cfg = cfg or load_alert_config()
    reader = HeartbeatReader(cfg.heartbeat_dir)
    manager = build_manager(cfg)
    status, event = check_once(reader, manager, component=cfg.deadman_component,
                               max_silence_seconds=cfg.deadman_max_silence_seconds)
    delivery = manager.store.get(event.alert_key) or {}
    delivery_status = (delivery.get("delivery") or {}).get("status")
    print(f"[watchdog] component={cfg.deadman_component} liveness={status['state']} "
          f"transition={event.transition} notify={event.notify} delivery={delivery_status}")
    critical_open = status["state"] in (Liveness.STALE.value, Liveness.MISSING.value)
    return 2 if critical_open else 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pyrnova.watchdog",
        description="Independent Pyrnova dead-man / liveness watcher (run under an external timer).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="run one liveness evaluation and exit (0 healthy, 2 dead-man CRITICAL)")
    args = parser.parse_args(argv)
    if args.cmd == "check":
        return run_check()
    parser.error(f"unknown command {args.cmd!r}")
    return 2


if __name__ == "__main__":  # pragma: no cover - module entrypoint
    sys.exit(main())
