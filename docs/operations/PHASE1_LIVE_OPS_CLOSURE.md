# Phase 1 Live Operations closure — engineering evidence and soak readiness

_Execution opened 2026-09-12 · authority: `02-EXECUTION.md` · operational acceptance pending_

This is an engineering/operations evidence record, not a Customer #1 decision and not a completed-soak
claim. Acceptance still requires seven consecutive calendar days containing at least five business days.

## Initial state

- Canonical checkout `/Users/stu/Documents/Pyrnova`, `main`; starting HEAD and `origin/main`
  `d8714b63c9e008f336c8d3f944fb2043bf4edd04`.
- Pre-existing untracked `.codex/config.toml` (documented intentional) and `.DS_Store`; not modified here.
- 620 collected tests. Restricted baseline: 619 passed, one loopback-bind skip, plus a cache-write warning.
- Python 3.9 venv; local JSONL and content-addressed archive; SAM key configured. SEC identity, PostgreSQL,
  and S3 were not configured.
- No repository-owned unattended service existed. The governed scheduler was a library/thin driver; the
  separate manual `capture-radar --live` path did not inherit scheduler controls.
- Persisted customer state contained Torch and DAP, not IronMountain Solutions. No approved IronMountain
  capability profile, watchlist/monitored-object set, or primary NAICS was present.

## Acceptance audit before changes

| Area | Before | Evidence / gap |
|---|---|---|
| Authorized evidence | PASS | Rights registry; SAM/USAspending live-proven; M13/M14 archives |
| Automatic acquisition | GAP | No daemon/service or supervisor definition |
| Cadence | PARTIAL | Registry guidance and scheduler intervals; no immutable soak plan |
| Checkpoints | PASS | Durable after archive; soak needed post-downstream advancement |
| Retries / rate limits | PARTIAL | Bounded metadata, budgets, throttle category, breaker; retry time did not drive next poll |
| Dedupe | PASS | Sanitized request fingerprint, archive hash, cache index |
| Idempotency | PASS customer-facing | Stable IDs and content-hash fan-out suppress unchanged cards |
| Restart/recovery | PARTIAL | Durable source control; no immutable run/cycle/intervention ledger |
| Health / freshness / degradation | PARTIAL | Raw counters existed; explicit state/attempt/stale/error semantics absent |
| Selectivity | PASS, bounded | M13: 0 STRIKE, 19 WATCH, 11 REJECT; continuous reports |
| Important Miss instrumentation | GAP | No structured trace from source through non-emission/delivery |
| Operational visibility | PARTIAL | Panel/source/fan-out reports; no soak heartbeat/manifest |
| Point-in-time / replay | PASS | Cutoff gates, frozen prospective calls, deterministic corpora |
| Tenant fan-out | PARTIAL | Isolation passed; live pipeline used display name instead of persisted tenant id |
| Realistic load | UNKNOWN | 75 is a test ceiling; actual IronMountain Lens absent |

## Refreshed real-source proof

One pre-budgeted keyless USAspending call on 2026-09-12 returned 10 IronMountain Solutions awards. The
first source object was award `W31P4Q21FB001`, internal id
`CONT_AWD_W31P4Q21FB001_9700_GS10F0390Y_4732`, recipient `IRONMOUNTAIN SOLUTIONS, LLC`, dated 2021-02-08
through 2026-09-07. Raw bytes are under `var/phase1_live_ops/baseline_2026-09-12/archive/`; SHA-256
`3c5a3fc2ee6c754ec2b3980925dd9326224596b7e43960fa70760f3e07bc3061` round-tripped exactly. Durable
state recorded one call, zero remaining of one, closed circuit, and checkpoint
`ironmountain:2026-09-12:page:1`. No retry, degradation, or intervention occurred. This is current
single-source evidence, not a soak or multi-source characterization.

## Minimal acceptance changes

- Source state now records latest cycle/network attempt/success/error and failed-cycle count.
- A retryable failed poll persists its bounded retry time; it becomes due after backoff instead of waiting
  the ordinary cadence. Existing breaker/budget controls remain authoritative.
- Health exposes HEALTHY/DEGRADED/FAILED/PAUSED/UNKNOWN plus CURRENT/STALE/UNKNOWN acquisition freshness.
- `pipeline.run(customer_id=...)` preserves the real tenant key; omitted calls keep legacy behavior.
- Important Miss records are deterministic/idempotent across coverage, identity, relationship,
  materiality, consequence, timing, and delivery, retaining evidence/acquisition/assessment/relevance refs.
- `SoakHarness` fails closed on criteria, commit, rights/status, credentials, customer/profile/watch scope,
  cadence/budgets, and the 75-object test ceiling. It composes the existing archive, scheduler, pipeline,
  fan-out, and StateStore; source checkpoints advance only after downstream/fan-out success.
- The immutable manifest, append-only cycle/intervention ledgers, current status file, and
  `ops/com.pyrnova.live-ops.plist.template` provide bounded evidence and macOS restart supervision without
  adding a platform or a dependency.

## Freshness semantics

`last_cycle_at` is scheduler evaluation; `last_network_attempt_at` is fetcher invocation;
`last_successful_acquisition_at` is successful archived HTTP acquisition. Acquisition is `CURRENT` until
two configured intervals (minimum five-minute grace) after success, then `STALE`; it is `UNKNOWN` without
success/cadence. `last_detected_change` remains content-change telemetry. Evidence-native time and Material
Change observation/delivery/version time remain separate. `DEGRADED` means current error or staleness;
`FAILED` means open circuit or three failed cycles. External outage is acceptable when represented honestly.

## Representative capacity and idempotency probe

A local acceptance probe exercised the current 75-monitored-object operating envelope against 100
global opportunity records. Five records were relevant. The first fanout inserted all five in 0.004078
seconds; an immediate replay inserted none and suppressed five duplicates in 0.002764 seconds. Both
runs completed with zero failures. The resulting temporary JSONL state was 64,882 bytes. This is a
bounded functional/load probe, not evidence of sustained production throughput or a completed soak.

## Soak procedure and current status

Final pre-commit verification on 2026-09-12 passed all 630 collected tests with no skips. The
launchd template passed `plutil` validation, changed Python modules compiled successfully, and the
patch passed `git diff --check`.

Copy `ops/phase1_soak_plan.example.json` into gitignored `var/phase1_soak/plan.json` only after the
owner-approved IronMountain customer, watchlist, capability profile, monitored-object count, and NAICS are
present. Replace every `SET_` placeholder and pin the verified post-change commit.

```bash
.venv/bin/python -m pyrnova.live_ops_acceptance preflight --plan var/phase1_soak/plan.json --repo .
.venv/bin/python -m pyrnova.live_ops_acceptance start --plan var/phase1_soak/plan.json --repo .
.venv/bin/python -m pyrnova.live_ops_acceptance run-once --plan var/phase1_soak/plan.json --repo .
```

Render the launchd template only after one clean foreground cycle. Observation may read logs/health,
review intelligence, and capture evidence. Manual ordinary ingestion, checkpoint editing, output repair,
threshold changes, or unlogged code changes invalidate the soak. Any acceptance-critical code change
restarts the complete window.

Record and inspect reviewer-discovered misses without editing JSONL directly:

```bash
.venv/bin/python -m pyrnova.live_ops_acceptance record-miss --state-dir var/state \
  --miss-class identity --source-id sam_opportunities --source-ref SOURCE_NATIVE_ID \
  --customer-id ironmountain --reviewer REVIEWER --relevance-state NOT_EMITTED
.venv/bin/python -m pyrnova.live_ops_acceptance list-misses --state-dir var/state
```

**SOAK BLOCKED.** The approved IronMountain Lens is absent and the example plan intentionally contains
fail-closed placeholders. Substituting Torch/DAP or inventing the customer configuration would test a
different question. Operational acceptance is pending before start; no soak time has elapsed.
