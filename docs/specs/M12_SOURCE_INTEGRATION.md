# Milestone 12 — durable source integration: scheduler / jobs + operator controls

_Status: **CLOSED 2026-09-09** · authority: `01-PROJECT-AUTHORITY.md`, activated by `02-EXECUTION.md`._

## Core question

The durable source-state foundation (`sources/source_state.py`), the in-process `SourceControl`
(mode/budget/breaker/retry/metrics), the registry, and the exact-byte archive all existed **separately**.
M12 wires them into one runnable, **offline-default** job runner with operator controls and a source-health
view — closing the `SOURCE_INGESTION` doctrine gap (persistent budgets/cursors, request dedupe, cache
reuse, backoff, circuit breaking, resume, operator visibility) without touching `scoring_v1`, `fit.py`,
the adapters, or the frozen corpora.

## Design (`pyrnova/scheduler.py`, additive)

`SourceScheduler` composes `SourceStateStore` + `SourceControl` + registry + `EvidenceArchive`. It
performs **no HTTP of its own** and imports no adapter. `run_job(source_id, request, ...)` resolves one
point-in-time request in a strict, offline-safe order:

1. **operator paused** → `SKIPPED_PAUSED` (persisted operator control).
2. **request already indexed** (`request_fingerprint` seen in the durable dedupe/cache index) →
   `CACHE_HIT`, served from the archive, **no budget spent**.
3. **OFFLINE + fixture bytes** → `OFFLINE_REPLAY`: archive the bytes (Tier-B), index the fingerprint,
   count as a call avoided. **Never touches the network.**
4. **OFFLINE + nothing cached** → `SKIPPED_OFFLINE`.
5. **live mode + fetcher supplied** → `control.prepare()` reserves budget and checks the breaker, then
   the caller's `fetcher` runs → `LIVE_FETCH` (archived + indexed) | `SKIPPED_BUDGET` | `CIRCUIT_OPEN`
   | `ERROR` (failure recorded, backoff metadata returned).

**Offline is the structural default:** a run reaches the network only when a caller both opts a source
into a live mode *and* hands it a `fetcher`. No live call can happen by omission.

### Capabilities wired

| Capability | Mechanism |
|---|---|
| Budgets (durable) | `RequestBudget` hydrated from state; persists across restart within a `budget_epoch`; a new epoch resets the count |
| Dedupe | `request_fingerprint` (credential-safe) → cache index; equivalent request served from archive |
| Cache / archive | `EvidenceArchive.put` (exact-byte, immutable, dedup) + `record_request` index |
| Backoff | `control.record_failure` + `retry_metadata` (exponential + jitter, provider Retry-After honored) — the scheduler advises, the caller sleeps |
| Circuit breaker | `CircuitBreaker` state persisted; open circuit defers the next poll without calling the fetcher; `reset_breaker` operator control |
| Checkpoint / resume | `set_checkpoint` / `get_checkpoint` per source; a reborn scheduler resumes at the cursor |
| Source health | `health()` / `health_report()` — mode, budget remaining, circuit state, cache hits, calls avoided, checkpoint, last change, paused |
| Operator controls | `pause` / `resume`, `set_mode` / `clear_mode` (persisted override), `reset_breaker` |

### Operations Panel extension (lightweight, additive)

`OperatorConsole.__init__` takes an optional `source_state_dir`; `source_operations()` returns the
scheduler's `health_report()` (read-only) and is folded into the panel snapshot under
`source_operations`. With no directory configured it degrades to a well-formed empty report — no error.

## Invariants held

- `scoring_v1` and `fit.py` unchanged; `control.py`, `source_state.py`, and the adapters unchanged.
- Frozen M4–M11 corpora byte-for-byte unchanged.
- `ACCEPTANCE` mode never serves cached bytes (a fresh retrieval is required) —
  `test_acceptance_mode_never_serves_from_cache`.
- No live calls in the test suite; every path is offline (fixtures / injected fetchers).

## Acceptance (all hold)

1. Offline default: no fetch without an explicit live mode + fetcher. 2. Durable budget enforced across
restart; new epoch resets. 3. Dedupe/cache serves repeats from archive. 4. Backoff metadata on failure;
circuit opens after the threshold and defers the next poll. 5. Breaker reset control works. 6. Checkpoint
persists for resume. 7. Pause/resume and mode-override persist. 8. Health report aggregates sources.
9. Operations Panel surfaces durable source operations and degrades gracefully. 10. Full tests pass
(298 passed, 1 skipped). 11. Docs updated. 12. Pushed; `HEAD == origin/main`.

## Limitations (explicit)

- No adapter is auto-wired to a live endpoint here; adapters opt in by passing a `fetcher`. Real live
  ingestion still requires a separately justified LIVE-SAFE/ACCEPTANCE request and provisioned keys.
- The dedupe/cache index keys on the sanitized request fingerprint; a source that changes bytes under an
  identical request (Tier-A restatement) is captured by the archive's observation log, but the scheduler
  treats an identical fingerprint as a cache hit — freshness for Tier-A restatement is an adapter concern
  (pass `ACCEPTANCE` to force a fresh retrieval).
- Health is durable-state observability, not a live availability probe.
