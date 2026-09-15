# Operator Alerts + Independent Dead-Man / Liveness — Evidence

**Workstream:** OPERATOR-ALERTS-001 — Phase 1 Operational GO blocker.
**Branch:** `operator-alerts-001` (stacked on `backup-restore-001` @ `8275d91`, which is stacked on
`source-rights-001` @ `3732d86`). Not on `main`.
**Final acceptance state:** **OPERATOR ALERTS — IMPLEMENTED / AWAITING REAL DELIVERY VERIFICATION.**

No real operator email was delivered to a real inbox in this workstream (no verified sender domain /
provider credentials available), so per the acceptance rules this cannot be marked VERIFIED / CLOSED.
Everything short of real delivery — lifecycle, severity doctrine, dedupe, dead-man independence,
transport construction and transport-failure behaviour — is implemented and verified by isolated,
controlled-time tests.

## Recovered work state (Phase 0)

This session recovered **partial uncommitted work** (recovery state **B**): `pyrnova/alerts.py` (durable
lifecycle + severity + transport seam) and `pyrnova/heartbeat.py` (heartbeat writer/reader) existed as
untracked files in the `operator-alerts-001` worktree, with **no commits** beyond the branch base and no
tests, no watcher, and no evidence doc. `heartbeat.py` referenced a `pyrnova.watchdog` module that did not
yet exist. Work was continued from that state — the existing modules were kept as-is (only additive
evaluators appended to `alerts.py`) and the missing pieces were built.

## Architecture

```
PYRNOVA SERVICE  --HeartbeatWriter.beat()-->  var/heartbeat/<component>.json   (bounded progress record)
INDEPENDENT WATCHER (pyrnova.watchdog)         reads freshness with HeartbeatReader — never touches the
  run as a SEPARATE scheduled process          service loop, so it can detect TOTAL service death
      |  check_once()
      v
AlertManager (pyrnova.alerts)  --> AlertStore  var/alerts/{active.json, history.jsonl, delivery_failures.jsonl}
      |                                            durable, restart-safe, deduped lifecycle
      v
Notifier --> EmailTransport (SMTPEmailTransport | DisabledTransport)  --> operator inbox
```

- `pyrnova/alerts.py` — severity doctrine, durable OPEN/UPDATED/RESOLVED lifecycle, dedupe, email
  transport seam, bounded non-recursive delivery-failure handling, evidence sanitisation, and doctrine
  bridges (`evaluate_source_health`, `evaluate_cycle_health`, `evaluate_persistence`).
- `pyrnova/heartbeat.py` — service-side heartbeat writer + fail-closed freshness reader; maintenance marker.
- `pyrnova/watchdog.py` — the independent watcher: `check_once()` (pure, testable) + `python -m
  pyrnova.watchdog check` (one evaluation, exit 0 healthy / 2 dead-man CRITICAL) for an external timer.
- `pyrnova/config.py` — `AlertConfig` + `load_alert_config()`: all config/secrets external; SMTP password
  read from process env or the gitignored `.env`, never the tree.

## Severity doctrine

| Severity | Meaning | Emails operator? |
|---|---|---|
| `INFO` | routine operational state | **No** — durable logs/status only |
| `OPERATOR_ATTENTION` | actionable degradation needing awareness | Yes |
| `CRITICAL` | threatens trustworthy operation / availability / persistence / evidence integrity | Yes |

Only `OPERATOR_ATTENTION` and above reach an inbox (`_NOTIFY_MIN_RANK`). Deliberate `PAUSED`/`UNKNOWN`
source states and single-cycle blips stay `INFO` (logs-only) and never page.

## Lifecycle semantics

Stable identity `alert_key = "{class}:{subject}"`; per-incident `incident_id = "{key}#gen{N}"`.
Each alert carries schema version, severity, class, subject, first-opened & last-updated timestamps,
human summary, bounded sanitised evidence, resolution state/time, occurrence count, and delivery status.

- **OPEN** — first occurrence of a condition (or a new generation after a prior RESOLVED).
- **UPDATED** — a *meaningful* change (severity worsens, or the human summary changes → different
  fingerprint).
- **RESOLVED** — recovery; a later recurrence OPENs a new **generation** rather than mutating history.
- `history.jsonl` is an append-only audit of every transition.

## Deduplication

Fingerprint = `sha256(severity, class, summary)` — it deliberately **excludes** volatile evidence such as
age counters and timestamps, so a persistently-dead heartbeat or a repeating identical failure **dedupes**
(refreshes last-seen/occurrences, no email) instead of storming. A design bug was caught during this work
and fixed: the watchdog dead-man summary originally embedded the elapsed age, which changed every check and
produced spurious UPDATEDs — the age was moved to evidence-only so repeated STALE checks dedupe, while a
genuine `STALE → MISSING` worsening still yields an UPDATED.

## Dead-man independence

The watcher is a separate process sharing only the on-disk heartbeat record and the durable alert store.
It never imports or drives the service loop, so it detects total service death (the case an in-loop monitor
cannot report because it dies with the loop). Scheduling is external and deliberate (cron / launchd /
systemd timer). Freshness reads are **fail-closed**: a missing or corrupt record reads as `MISSING`
(treated as expired), never as fresh. A `MAINTENANCE` marker suppresses false CRITICALs during deliberate
downtime. A restarted watcher re-reads `active.json` and **continues** an existing OPEN incident (dedupe)
rather than reopening it.

## Transport behaviour & failure handling

- `SMTPEmailTransport` is the real, production-capable sending seam (host + credentials + verified sender
  from config). `DisabledTransport` is the explicit default when no sending identity exists — alerts still
  persist durably and delivery is reported `not_configured`, **never** silently "delivered".
- Delivery uses **bounded retries** (`max_attempts`, default 3). A failure returns an explicit
  `status="failed"`/`"not_configured"` result that is persisted against the alert and appended to
  `delivery_failures.jsonl`. A broken transport **never itself raises another alert** (no recursion / no
  storm); the incident remains visible even if delivery fails.
- Operator emails/evidence are sanitised: keys matching credential tokens are `[redacted]`, long strings
  truncated, collections bounded — identifiers and references only, no secrets or raw restricted payloads.

## Configuration (all external; no secrets in tree)

`PYRNOVA_ALERT_ENABLED`, `PYRNOVA_ALERT_RECIPIENTS`, `PYRNOVA_ALERT_SENDER`, `PYRNOVA_ALERT_MAX_ATTEMPTS`,
`PYRNOVA_ALERT_STATE_DIR`, `PYRNOVA_SMTP_HOST/PORT/USERNAME/PASSWORD/USE_TLS`, `PYRNOVA_HEARTBEAT_DIR`,
`PYRNOVA_DEADMAN_COMPONENT`, `PYRNOVA_DEADMAN_MAX_SILENCE_SECONDS`. See `.env.example`. Missing production
credentials are explicit (`delivery_configured` is false → `DisabledTransport`).

## Focused tests — `tests/test_operator_alerts.py` (18 tests, all passing)

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_operator_alerts.py -q` → **18 passed**.
Deterministic (injected `now`), fully isolated (`tmp_path`), no real SMTP, no soak interaction.

Representative-condition coverage:

1. repeated operational cycle failure → `test_evaluate_cycle_health`
2. unrecovered source degradation → `test_evaluate_source_health_doctrine`
3. durable persistence / state failure → `test_evaluate_persistence_critical_and_recovery`
4. dead-man expiry → `test_watchdog_deadman_expiry_and_recovery`
5. alert deduplication → `test_dedupe_no_storm`, `test_watchdog_deadman_expiry_and_recovery`
6. alert update → `test_open_update_resolve_lifecycle`, `test_watchdog_stale_to_missing_is_update`
7. recovery / resolution → `test_open_update_resolve_lifecycle`, `test_watchdog_deadman_expiry_and_recovery`
8. notification transport failure → `test_transport_failure_is_durable_and_bounded`, `test_transport_recovers_after_retry`
9. watcher restart with existing OPEN incident → `test_watchdog_restart_continues_open_incident`
10. healthy / no-alert state → `test_watchdog_deadman_expiry_and_recovery` (FRESH → NOOP)

Plus: severity doctrine (`test_info_never_notifies`), explicit disabled transport
(`test_disabled_transport_is_explicit_not_silent`), secret redaction (`test_email_and_evidence_redact_secrets`),
heartbeat freshness/fail-closed/maintenance (`test_heartbeat_*`), maintenance no-false-page
(`test_watchdog_maintenance_no_false_page`), and the config transport seam (`test_build_transport_*`).

## Real-delivery status

**Not demonstrated.** Mock/recording transport success does **not** equal real delivery. To close to
VERIFIED: set a verified sender domain + real SMTP credentials in `.env`, deploy the watcher under an
external timer against a **non-soak** heartbeat, force an expiry, and confirm the email arrives in a real
operator inbox.

## Residual dependencies / not done (deliberately out of scope)

- Real operator email delivery to a real inbox (needs verified sender domain + provider credentials).
- Wiring `HeartbeatWriter.beat()` into the live service's per-cycle `status.json` write, and installing the
  watcher timer — a separate, deliberate deployment act. **Not deployed into the protected running soak.**
- No email domain purchased/configured; Customer #1, commercial authority, Live Ops architecture,
  SOURCE-RIGHTS and BACKUP/RESTORE all untouched.

## Soak protection

The protected live-ops soak was **not touched**: no restart/stop/reset/reseed/rebaseline, no config or
checkpoint changes, no alerting code deployed into it, nothing written to its evidence directory, and it
was never used as an alert test target. All testing used isolated `tmp_path` fixtures and injected time.
