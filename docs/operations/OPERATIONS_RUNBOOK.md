# Operations runbook

Status: local/controlled-operation runbook; production operation unverified  
Last reviewed: 2026-09-12

## When to use this

Use for local product operation, offline replay, explicit live-safe source jobs, customer onboarding,
source failure diagnosis, restart verification, and recovery planning. It does not authorize live calls,
deployment, spend, customer access, or a new milestone.

## Prerequisites

- canonical repository/worktree and current authority verified;
- Python 3.10+ environment with project dependencies;
- write access to configured state/archive/output directories;
- no secrets printed, copied, or committed;
- explicit authority for any fresh external call or remote bind;
- an approved customer/security posture before handling real customer data.

## Runtime locations

| Configuration | Default | Purpose |
|---|---|---|
| `PYRNOVA_STATE_DIR` | `./var/state` | append-only intelligence/customer/auth JSONL |
| `PYRNOVA_ARCHIVE_DIR` | `./var/archive` | local content-addressed raw evidence |
| `PYRNOVA_OUT_DIR` | `./out` | generated Markdown reports/briefs |
| `PYRNOVA_ARCHIVE_BACKEND` | `local` | `local` or optional `s3` archive |
| `SAM_API_KEY` | absent | SAM opportunity access |
| `PYRNOVA_SEC_USER_AGENT` / `PYRNOVA_SEC_CONTACT_EMAIL` | absent | declared SEC access identity |
| `PYRNOVA_REQUIRE_AUTH` | false | force auth even on local bind |

Source scheduler state uses a caller-selected directory through `SourceStateStore`; the product server
does not currently configure that directory into its `OperatorConsole`, so source-operations telemetry is
not automatically visible in the default server process.

## Routine local operation

### Verify the codebase

```bash
source .venv/bin/activate
python -m pytest
```

### Run a deterministic offline Capture Radar flow

```bash
python -m pyrnova.cli capture-radar \
  --profile examples/profiles/acme_c4isr.json \
  --fixtures
python -m pyrnova.cli scoreboard
```

This can append local state and output. Use a task-specific temporary `PYRNOVA_STATE_DIR`,
`PYRNOVA_ARCHIVE_DIR`, and `PYRNOVA_OUT_DIR` when a clean run is required.

### Start the customer product locally

```bash
python -m pyrnova.ops_server
```

- `/`: Material Changes customer UI.
- `/investigate`, `/company`, `/program`: investigation surfaces.
- `/console`: local-only internal Operator Console.

On startup the server runs customer fan-out. If configured state has no threats and tracked demo data
exists, it may use the demo intelligence store; if no persisted customers exist, it may seed tracked demo
customers. Confirm the data origin before treating the screen as current/live.

## Customer onboarding

```bash
pyrnova customer create --id <customer-slug> --name "<organization>" \
  --entity-ref <canonical-ref>
pyrnova watch add <customer-slug> <ref> --type ENTITY
pyrnova credential create --customer <customer-slug>
pyrnova customer show <customer-slug>
pyrnova fanout --customers <customer-slug>
```

Credential creation prints the token once. Transfer it only through the approved secure channel; do not
place it in URLs, logs, shell history captures, tickets, or Git. `--resolve` accepts EXACT automatically,
requires explicit confirmation for PROBABLE, and does not silently choose AMBIGUOUS/UNRESOLVED results.

To revoke:

```bash
pyrnova credential list --customer <customer-slug>
pyrnova credential revoke <credential-id> --note "<reason>"
```

Revocation appends history and should fail authentication immediately.

## Remote access boundary

```bash
python -m pyrnova.ops_server --host <approved-bind-address> --port 8765
```

Any non-local host forces authentication and hides the operator surface. This command alone is not a
production deployment: the built-in server has no TLS or hardened edge. Do not expose it publicly without
an approved reverse proxy/edge, TLS, firewall, monitoring, rate limits, process supervision, backup, and
security acceptance.

## Controlled source operation

There are two distinct live paths:

1. `capture-radar --live` is the original manual founder flow. It directly calls USAspending, optionally
   SAM, and Federal Register and does not provide the durable M12/M13 scheduler budget/cadence contract.
2. `SourceScheduler` + `LiveRunner` are the governed operational primitives. They require an explicitly
   constructed request, mode, budget epoch/max calls, archive, source-state directory, and fetcher. No
   platform is included; the Phase 1 local soak harness below composes these primitives.

Use the second path for controlled operational acceptance. A typical integration must:

- default to OFFLINE;
- set LIVE_SAFE or ACCEPTANCE explicitly;
- set a finite call budget and budget epoch;
- set a poll interval;
- reuse cached requests outside ACCEPTANCE;
- advance checkpoint only after safe processing;
- record call/record/selectivity metrics;
- stop on budget, pause, not-due, open circuit, or archive failure.

Do not use `capture-radar --live` as evidence that scheduler controls were exercised.

## Source health

Inspect the scheduler’s `health_report()` for each configured source:

- effective mode and pause reason;
- budget limit/remaining and calls made;
- cache hits/calls avoided;
- breaker state and next permitted poll;
- poll interval, last poll, next poll, and due state;
- last success/change;
- checkpoint and indexed requests;
- retryable/terminal errors and quota state.

Interpret conservatively:

- no state/observation means unobserved, not healthy;
- old success means only that a historical call succeeded;
- unknown quota remains unknown;
- fixture-only or archive-operational is not live-proven;
- a zero-record response may be legitimate and requires source-specific interpretation.

## Failure response

| Symptom/action | Meaning | Operator response |
|---|---|---|
| `skipped_paused` | operator hold | Read pause reason; resume only after cause/authority clears. |
| `skipped_offline` | OFFLINE with no cache/fixture, or live requested without fetcher | Supply permitted archive/fixture or correct explicit live wiring. |
| `cache_hit` | equivalent sanitized request served from archive | Verify hash/content age meets the use; do not call it fresh acceptance. |
| `skipped_not_due` | cadence window still active | Wait until due; do not bypass for convenience. |
| `skipped_budget` | durable epoch budget exhausted | Stop. New epoch/limit needs operational authority, not a counter edit. |
| `circuit_open` | repeated failures/cooldown | Investigate provider/archive; wait for permitted poll or explicitly reset after remediation. |
| `error` from fetch | live request failed; budget was spent | Check category/status and retry metadata; do not loop manually. |
| `error` after fetch | archive/index failed after a spent call | Repair storage first; budget/failure state should prevent a retry storm. |
| fan-out failure | per-customer/item isolation recorded | Inspect `fanout_runs`; rerun after fixing the bad input. Global/other-customer state should remain intact. |
| 401/403/404 | unauthenticated / forbidden / surface hidden | Verify credential/role/tenant/bind posture; do not weaken access checks. |

## Restart and recovery

Source budgets, breaker, checkpoints, and request index survive a new `SourceScheduler` when the same
source-state directory and budget epoch are used. Customer/global JSONL state and archive survive process
restart when the same configured directories are used.

After restart:

1. confirm paths and permissions before starting;
2. read source health and active credential/customer metadata;
3. verify archive object referenced by the last indexed request is readable;
4. run one offline/cache job to prove dedupe and no external call;
5. run fan-out and confirm unchanged inputs produce duplicate suppression/no new versions;
6. inspect Material Changes for correct customer and origin;
7. only then consider an authorized live-safe job.

If JSONL has a malformed line, `StateStore.read` raises while loading the file. Preserve the file, copy it
to a task-specific recovery location, identify the first invalid record, and repair through an authorized
recovery procedure. Do not truncate or rewrite history in place.

## Idempotency expectations

- equal request fingerprint outside ACCEPTANCE → cache hit;
- equal raw bytes → same content SHA-256;
- unchanged customer relevance/assessment/outcome → fan-out writes no new version;
- repeated customer/watch creation should use explicit duplicate handling;
- outcome observation id prevents duplicate append;
- rebuild must preserve customer review history.

Idempotency is scoped to documented keys. It is not a multi-stream transaction guarantee.

## Monitoring and incident handling

Implemented observability consists of structured source health, live-run ledgers, operating-cost call
reports, fan-out run records, selectivity reports, scoreboard events, and operator read views. There is no
central alert transport or on-call integration.

For an incident:

1. stop new live calls or pause the affected source;
2. preserve state/archive/log evidence and record times/commit/config without secrets;
3. scope affected source, customer, stream, and time window;
4. determine whether raw evidence, normalized state, assessment, delivery, or access was affected;
5. fail closed—mark stale/degraded/unknown rather than present false freshness;
6. reproduce offline and add a regression test;
7. recover through append/rebuild or verified restore; do not rewrite history casually;
8. verify tenant isolation, hashes, temporal truth, and customer projections;
9. record residual risk and owner acceptance separately.

## Backup and restore

No repository-owned backup/restore implementation or successful restore drill exists. At minimum a future
procedure must cover state JSONL/source-state, raw archive and observation metadata, credentials/customer
state, generated output if required, encryption/access, retention, and restoration in a clean environment.
Verification must include archive hashes, customer isolation, current/as-of projections, credentials/
revocation, and replay. A backup is not accepted until a restore has been tested.

## Operational acceptance and soak

The executable Phase 1 soak contract, current engineering evidence, fail-closed plan template, and exact
freshness meanings are in `PHASE1_LIVE_OPS_CLOSURE.md`. Use
`python -m pyrnova.live_ops_acceptance preflight|foreground|start|run-once|serve`; the manual
`capture-radar --live` path is not unattended-soak evidence. Render
`ops/com.pyrnova.live-ops.plist.template` with explicit repository, plan, and evidence paths only after
preflight and one clean foreground cycle.

The `foreground` action records real processing and immediate unchanged fan-out under `foreground_*`
evidence without creating an official manifest. After it passes, loading the rendered launchd service
runs `serve`, whose `start` creates the immutable official acceptance timestamp. Do not call `start`
before foreground validation when establishing a new acceptance window. The copied plan paths are relative
to `var/phase1_soak/plan.json`. See `PHASE1_SOAK_UNBLOCK.md` for the source-backed non-commercial Lens.

Before calling the system unattended/production-ready, record dated evidence for a representative set of
sources and customers: scheduled cadence, restart, dedupe, budget rollover, throttle/service/archive fault,
stale/degraded display, fan-out/rebuild, access, data volume, resource use, alert delivery, backup/restore,
and multi-hour/day soak. Current M13 evidence is bounded and does not close this gate. The Phase 1 soak is
requires the owner-approved non-commercial IronMountain test Lens and complete monitored-object scope;
no placeholder, substitute customer, or commercial designation starts the acceptance clock. Alert delivery,
production backup/restore, public TLS, PostgreSQL/RLS, and S3 do not block this local soak unless runtime
preflight independently proves a current necessity.

## Manual-intervention boundaries

Operators may pause/resume/reset a remediated breaker, provision/revoke credentials, configure customers/
watches, fan out, adjudicate, record sourced outcomes, and export briefs. They may not lower scoring/
evidence thresholds, invent source state, backdate watches, rewrite predictions/outcomes, bypass tenant
checks, rotate credentials to evade source limits, or promote research/fixtures into production truth.
