# Milestone 13 — controlled live operations + end-to-end production validation

_Status: **CLOSED 2026-09-09** · authority: `01-PROJECT-AUTHORITY.md`, activated by `02-EXECUTION.md`._

## Core question

Can Pyrnova stay running against real sources and convert genuinely new observations into evidence-backed
intelligence **without** duplicate API traffic, future-data leakage, stale-state corruption, a noisy
opportunity explosion, lost provenance, broken recovery, uncontrolled cost, or secret leakage?

M13 is operational proof, not feature work. It adds the smallest surface needed to *drive and measure*
the M12 durable scheduler against a real source, then validates the end-to-end path with a tiny,
conservative number of representative live calls and heavy reuse of archived evidence.

## First action — M2 status (verified, not inferred)

M2 is **CLOSED** (`2026-09-09T07:14Z`), confirmed from `03-CURRENT-STATE.md`, `02-EXECUTION.md`, and
`06-HISTORY.md` (§"Milestone 2 — external SAM acceptance CLOSED 2026-09-09", superseding the earlier
env-blocked CONDITIONAL), commit `5fd4191`, fresh SAM archive hash
`574813de00d1bc6f8703c075c601cb4fa48be401a94a1ceaa8c571c482350a08`, sanitized provenance. No re-attempt
was required; the frozen acceptance logic was not touched.

## Design (additive only)

`scoring_v1`, `fit.py`, `control.py`, `source_state.py`, the adapters, and the frozen M4–M12 corpora are
all **unchanged**. M13 adds:

### `pyrnova/scheduler.py` — poll cadence (the one genuine M12 gap)

M12 had failure-driven `next_permitted_poll` but no *cadence*. M13 adds, additively (`run_job` untouched,
so nothing that does not opt in changes behaviour):

- `set_poll_interval` / `get_poll_interval`, `mark_polled`, `next_poll_due` / `next_poll_at`,
  `due` / `due_sources`, and a cadence-aware `poll()` wrapper (new action `SKIPPED_NOT_DUE`).
- The cadence gate governs **only requests that would actually reach the network**. A dedupe/cache hit or
  an OFFLINE replay is never deferred by the poll window — a cache hit spends no poll.
- `health()` now reports `poll_interval_seconds`, `next_poll_at`, `due`, the **durable** budget
  ceiling/remaining, and the **durable** `calls_made` (epoch-independent operator truth).
- A fetcher may tag its exception with `failure_category` (e.g. `"throttle"` for HTTP 429) so
  throttle/quota metrics are honest; untagged faults stay `"service"`.
- The archive+index step in both the OFFLINE-replay and live paths is now guarded: a storage fault after
  a successful live fetch counts the spent call, engages backoff/circuit (no retry storm), and returns an
  `ERROR` result instead of crashing a long-running loop or half-writing state.

### `pyrnova/live_ops.py` — offline-safe live driver (new)

- `http_fetcher(request) -> bytes`: the real GET/POST-JSON fetcher the scheduler calls only when a source
  is opted into a live mode. It sends exactly what the request dict carries — **no credential is injected
  here** — returns raw bytes for exact-byte archival, and tags 429 as throttle.
- `LiveRunner`: a recording wrapper over `scheduler.poll` capturing the per-request efficiency ledger
  (attempted / sent / cache-hit / avoided / records returned / new-vs-unchanged).
- `operating_cost_report`: rolls durable per-source counters into a call-cost view (calls made/avoided,
  cache-hit rate, optional calls/day projection). **Calls only — never invented dollars.**

### `pyrnova/ops.py` — Operations Panel (thin)

`source_operations()` folds in `operating_cost_report`; launch unchanged (`python -m pyrnova.ops_server`,
loopback only).

## Live-source strategy

One narrow scenario, one source: **USAspending** (`spending_by_award`, public, keyless). A conservative
budget of **2 external calls** was set *before* any live testing. SAM (now that M2 is closed) and other
adapters were deliberately not driven live — a tiny representative sample plus aggressive archived-data
reuse is the M13 doctrine.

## Acceptance evidence

See `docs/replay/M13_LIVE_OPERATIONS.md` for the full ledger. Summary:

- **Live calls: 2** (USAspending, keyless, archived, both round-trips verified). **0 credential leakage**
  (archived bytes and sanitized fingerprints scanned).
- **Efficiency:** 1 identical repeat served from cache (call avoided); overall avoidance rate 0.333;
  budget enforced (a 3rd distinct request → `SKIPPED_BUDGET`, no call).
- **Restart/resume (genuine second process):** budget (0/2), checkpoint, circuit, and dedupe index all
  recovered from disk; both post-restart requests served from cache — **0 duplicate external calls**; new
  budget epoch resets the count.
- **End-to-end propagation:** 50 live award rows → normalize → detect → 30 candidates → match → review,
  with real evidence/event IDs archived per disposition.
- **Selectivity — no STRIKE explosion:** 30 candidates → **0 STRIKE / 19 WATCH / 11 REJECT**, 0
  duplicates on a broad live pull.
- **Temporal truth:** at a 2016-12-31 cutoff, **40 / 50** records excluded as not-yet-knowable → 0
  candidates. `available_at <= evaluation time` holds; no historical-replay contamination.
- **Fault behaviour (fault-injected, no provider hammering):** throttle categorization, circuit-breaker
  open + persistence across restart (no call storm), archive-failure resilience, malformed-payload
  resilience, budget no-storm — all covered by tests.
- `scoring_v1` unchanged; frozen corpora byte-for-byte unchanged; full suite **320 passed**.

## Invariants held

- Offline is the structural default; no live call without an explicit live mode **and** a fetcher.
- `ACCEPTANCE` still never serves cached bytes. No test makes a network call (all fetchers injected).
- Live evidence archives and local state live under `/var/` (gitignored) — no real evidence is committed.

## Limitations (explicit)

- One live source (USAspending), 2 calls — directional operational proof, not a broad load characterization.
- USAspending is retention-tier A (restated data); the dedupe index keys on the sanitized request
  fingerprint, so an identical request is a cache hit — freshness for a Tier-A restatement is an adapter
  concern (`ACCEPTANCE` forces a fresh retrieval). This is the documented M12 boundary, unchanged.
- The live award slice is recompete/award-only; the full chain → catalyst → consequence → fit trace
  remains corpus-validated (M5–M8). M13 shows the fit **input** (a real `CompanyProfile`) is reachable
  from live bytes; it does not force a live STRIKE.
- Throttle/timeout/provider-error/archive-failure are exercised by fault injection, not by deliberately
  stressing a real provider.
- Health is durable-state observability, not a live availability probe.
