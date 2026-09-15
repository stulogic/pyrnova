# Pyrnova — production security / control truth matrix (B4.7)

Truthful posture of launch-relevant controls. Status is one of **IMPLEMENTED** (code exists),
**TESTED** (automated regression covers it), **PRODUCTION-VERIFIED** (verified against real production
infrastructure), **NOT YET VERIFIED** (conservative — no evidence yet). Maturity is claimed only where
current evidence establishes it. This does not rewrite trust-pack claims beyond evidence.

| Control | Status | Evidence / notes |
|---|---|---|
| Authentication (bearer credential, revocation) | IMPLEMENTED + TESTED | `pyrnova/access.py`, `test_m22f_server_auth.py` (missing/invalid/revoked → 401). |
| Non-local bind forces auth (cannot be disabled remotely) | IMPLEMENTED + TESTED | `AccessPolicy.decide` interlock; `test_b4_security_posture.py`, `test_m22f_server_auth.py`. |
| Session restoration | IMPLEMENTED + TESTED | Bearer credential re-presented per request; validated each call (`access.request_access_check`). |
| Authorization / role separation (customer vs operator) | IMPLEMENTED + TESTED | `LEVEL_OPERATOR`/`LEVEL_PUBLIC`; operator routes require operator role. |
| Tenant isolation (application-layer, fail-closed) | IMPLEMENTED + TESTED | `test_m22f_server_auth.py`, `test_b3_*` cross-tenant assertions; forged `customer_id` cannot cross. **No DB RLS is claimed** (single-node JSONL). |
| `/console` + operator surfaces exposure | IMPLEMENTED + TESTED | Exposed only on a local bind; remote → 404 (`NotExposed`) and, if reached, operator credential required. `expose_operator = is_local`. |
| Secrets handling | IMPLEMENTED | All credentials from environment / gitignored `.env`; never baked into the tree (`config.py`, `_local_secret`). |
| Customer delivery credentials | IMPLEMENTED + TESTED | `config.build_customer_delivery_transport`; unconfigured → `DisabledTransport` (send recorded FAILED, never fabricated). Real SMTP transport: **NOT YET VERIFIED** (external credential dependency, B4.3). |
| Production debug state | IMPLEMENTED | No debug/verbose flag; no `PYRNOVA_DEBUG`. Handler returns sanitized 400/401/403/404; unexpected errors do not return a client-visible traceback. |
| Unsafe default configuration | IMPLEMENTED + TESTED | Fail-closed defaults: remote bind ⇒ auth on; delivery/alert transport ⇒ disabled (not silently "sent"); state read ⇒ fail-closed on corruption. |
| Logging / redaction | IMPLEMENTED (partial) | Operator alert emails carry identifiers/references, not raw restricted data (`alerts.build_email`); SMTP errors sanitized (transport type only). Centralized log aggregation/retention: **NOT YET VERIFIED**. |
| TLS / edge expectations | NOT YET VERIFIED | Design: Cloudflare terminates TLS at the edge; app binds `127.0.0.1` behind the tunnel (`ops/deploy/pyrnova-web.service.template`). No live edge verified in this environment. |
| Durable state safety (locking, fsync, torn-write recovery) | IMPLEMENTED + TESTED | `pyrnova/state.py`, `test_b4_durability.py` (process/thread contention, partial-write recovery, fail-closed corruption). |
| Backup destination / config | IMPLEMENTED + TESTED (local) | `pyrnova/backup.py`, `test_backup_restore.py`; snapshot coordinates with active writes (B4.4/B4.8). Off-host destination: **NOT YET VERIFIED** (infra/credential dependency). |
| Alert / watchdog wiring | IMPLEMENTED + TESTED | `pyrnova/alerts.py` + independent dead-man watcher; `test_operator_alerts.py`. Real external operator delivery: **NOT YET VERIFIED** (B4.9). |
| Immutable release / rollback | IMPLEMENTED + TESTED | `pyrnova/release.py`, `test_b4_release.py`; SHA-stamped, atomic, health-gated; rollback never touches state. |
| Error handling | IMPLEMENTED + TESTED | Typed exceptions → 400/401/403/404 with own-scope messages only (no cross-tenant data in errors). |
| Retention / deletion posture | NOT YET VERIFIED | Append-only history retained; formal retention/deletion policy not established. Conservative — not claimed. |
| Encryption at rest | NOT YET VERIFIED | Relies on host/volume encryption (deployment concern); application-level at-rest encryption not implemented. Not claimed. |
| Incident-response posture | NOT YET VERIFIED | No formal IR runbook beyond operator alerts. Conservative — not claimed. |
| Dependency / runtime configuration | IMPLEMENTED + TESTED | Pinned locks + fresh-install verification (B4.5), `test_b4_dependency_contract.py`. |

## Summary

Application-layer security (authN/authZ, tenant isolation, fail-closed posture, secrets hygiene, durable
state safety, immutable release) is IMPLEMENTED and TESTED. The **PRODUCTION-VERIFIED** column is
deliberately empty pending the final isolated Live Ops acceptance run against real edge/transport/off-host
infrastructure. Items marked NOT YET VERIFIED (TLS/edge, off-host backup, real customer/operator email,
retention/encryption/IR) are genuine external or infrastructure dependencies and are not claimed as
production-mature.
