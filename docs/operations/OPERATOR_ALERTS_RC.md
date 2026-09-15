# Operator alerts — release wiring verification (B4.9)

The alerting capability + independent dead-man watcher are accepted and NOT redesigned. This maps each
release-wiring requirement to its verifying evidence.

| Requirement | Status | Evidence |
|---|---|---|
| Live Ops heartbeat | IMPLEMENTED + TESTED | `pyrnova/heartbeat.py`; `test_operator_alerts.py::test_heartbeat_fresh_stale_missing_maintenance`, `::test_heartbeat_sequence_restart_safe`. |
| Independent dead-man watcher | IMPLEMENTED + TESTED | `pyrnova/watchdog.py` (separate process/reader from the heartbeat writer); `::test_watchdog_deadman_expiry_and_recovery`. |
| INFO / OPERATOR_ATTENTION / CRITICAL doctrine | IMPLEMENTED + TESTED | `Severity` + `_SEVERITY_RANK`; INFO never emails (`::test_info_never_notifies`, B4.9 `::test_severity_doctrine_end_to_end_via_build_manager`). |
| Transport failure visibility | IMPLEMENTED + TESTED | `Notifier.deliver` returns explicit `failed`/`not_configured` (never silent success); `::test_transport_failure_is_durable_and_bounded`, `::test_disabled_transport_is_explicit_not_silent`. |
| Recurrence / recovery | IMPLEMENTED + TESTED | dedupe (no storm) + resolve; `::test_dedupe_no_storm`, `::test_transport_recovers_after_retry`, `::test_watchdog_stale_to_missing_is_update`. |
| Restart behavior | IMPLEMENTED + TESTED | `::test_heartbeat_sequence_restart_safe`, `::test_watchdog_restart_continues_open_incident`. |
| Redaction | IMPLEMENTED + TESTED | `build_email` carries identifiers/references, not raw restricted data; SMTP errors sanitized. `::test_email_and_evidence_redact_secrets`. |
| Production configuration path | IMPLEMENTED + TESTED | `config.load_alert_config` + `watchdog.build_transport` → real `SMTPEmailTransport` when configured, else explicit `DisabledTransport`; B4.9 `::test_build_transport_is_real_smtp_when_configured`. Credentials from env / gitignored `.env` only. |
| Decoupled from customer email delivery | IMPLEMENTED + TESTED | Distinct factories/config (`watchdog.build_transport` vs `config.build_customer_delivery_transport`); alert recipients are config-sourced, customer-delivery recipients are operator-authorized. B4.9 `::test_operator_alerts_decoupled_from_customer_delivery`. |

## Remaining EXTERNAL dependency

Real external operator-delivery verification (an actual email landing in an operator inbox via a real SMTP
endpoint) is distinct from implementation and remains an explicit credential/infra dependency — the same
SMTP endpoint dependency as B4.3, not manufactured here. All internal wiring is complete and tested.
