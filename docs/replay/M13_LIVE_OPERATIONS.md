# M13 live-operations validation report

_Generated 2026-09-09 · canonical repo `~/Documents/Pyrnova` on `main`. Live evidence archived under
`/var/m13_live/` (gitignored); this report is the sanitized, committed record. Reproduce with the
harness described below — repeats make **zero** new external calls because the responses are archived._

This is a live-operation validation report; it does **not** replace or contaminate the frozen historical
replay corpora, which remain byte-for-byte unchanged.

## Source and budget

| | |
|---|---|
| Live source | `usaspending` — POST `/api/v2/search/spending_by_award/` (public, keyless) |
| Budget set **before** testing | 2 external calls (`budget_epoch = 2026-09-09`) |
| Poll cadence | 3600 s |
| Total live API calls made | **2** |
| Credential leakage | **none** (archived bytes + sanitized fingerprints scanned) |

## Process 1 — controlled live run (efficiency ledger)

| Step | Request | Action | Records | External call |
|---|---|---|---|---|
| 1 | Torch Technologies recipient history 2015–2023, 1 page ×25 | `live_fetch` | 25 | yes (1) |
| 2 | identical to step 1 | `cache_hit` | — | **no — served from archive** |
| 3 | NAICS 541715 market history 2022–2023, 1 page ×25 | `live_fetch` | 25 | yes (2) |
| 4 | distinct 3rd request (MTSI history) | `skipped_budget` | — | **no — budget exhausted** |

- requests_sent **2**, calls_avoided **1**, cache_hits **1**, records_returned **50**.
- budget_remaining **0 / 2**; checkpoints persisted (`torch:page:1`, then `naics541715:page:1`).

### Provenance (sanitized)

| Content SHA-256 | fetched_at | request fingerprint (sanitized) | archive round-trip |
|---|---|---|---|
| `a012fdb72cb4d830a4517ec4c20a1a69db40f36de6dfd609eccb6c96b0b5393f` | `2026-09-09T08:57:45.691211+00:00` | `89fbbd318c5ddbc0…` | ✅ |
| `363d6a6d477994440d66bb061cb2b8452a1289854727580744f8be6a378601da` | `2026-09-09T08:57:47.277674+00:00` | `5865a4c86af1b699…` | ✅ |

Each request fingerprint is an opaque SHA-256 over the sanitized request (no key material); source URL
and `fetched_at` are retained; both archived blobs round-tripped by content hash.

## Process 2 — genuine process restart (a second interpreter, same state dir)

Recovered from disk **before any request**: `budget_remaining 0 / limit 2`, `checkpoint
naics541715:page:1`, `indexed_requests 2`, `circuit_state closed`.

| Post-restart request | Action | External calls |
|---|---|---|
| Torch (step 1 repeat) | `cache_hit` | 0 |
| NAICS (step 3 repeat) | `cache_hit` | 0 |

- **Duplicate external calls after restart: 0** (the restart fetcher was wired to raise if invoked — it
  never was).
- Budget same-epoch remaining **0** (durable); a new epoch (`2026-09-10`) resets remaining to **2**.

## End-to-end propagation (live bytes → production pipeline)

50 live award rows fed through `pipeline.run` (NORMALIZE → DETECT → MATCH → REVIEW), no new network:

| Metric | Value |
|---|---|
| raw candidates / candidates | 30 / 30 |
| duplicate candidates | 0 |
| **STRIKE / WATCH / REJECT** | **0 / 19 / 11** |
| future_records_excluded (full-visibility run) | 0 |

Sample traced disposition: identity `usaspending:award:N0003019C0025`, catalyst `recompete_expiry`,
disposition `reviewing`, with archived evidence and event IDs. **No STRIKE explosion** — zero STRIKEs on
a broad live pull; conservative behaviour preserved. Zero opportunity is an acceptable, honest result;
no STRIKE was forced.

## Temporal truth (point-in-time leakage probe)

Re-running the same 50 rows at `replay_as_of = 2016-12-31`: **40 / 50 records excluded** as not knowable
at the cutoff → 0 candidates, 0 STRIKEs. `available_at <= evaluation time` is enforced; current ingestion
does not contaminate historical replay.

## Company-fit input from live evidence

A real `CompanyProfile` was grounded from the live Torch blob (point-in-time, `dominant_recipient_only`):
23 awards / 23 capability records, buyer agencies (Air Force, Army), specific capability classes
(hardware-in-the-loop simulation, specialty engineering, SETA), deterministic `company_id
co_9f62a44f1a4ce3ec3177`. The fit engine's input is reachable from live data; the full consequence→fit
chain remains corpus-validated (M5–M8).

## Fault / throttle behaviour (fault-injected — no provider hammering)

Covered by `tests/test_m13_live_ops.py`:

- 429 tagged `throttle` → `throttles` metric increments (untagged faults stay `service`).
- Circuit breaker opens after the failure threshold, **persists across a fresh scheduler**, and stops
  invoking the fetcher — no call storm; `reset_breaker` clears it.
- Archive failure after a live fetch: spent call counted, backoff engaged, no crash, no half-written
  index.
- Malformed live bytes archived exact-byte; the dedupe index is not corrupted (clean cache hit on repeat).
- Budget exhaustion never invokes the fetcher.

## Operating-cost telemetry (WS-H)

`operating_cost_report` over the run: total_calls_made **2**, total_calls_avoided **1**, cache_hit_rate
**0.333**, avoidance_rate **0.333**, budget 2 / 0. Free API → calls recorded, **no dollar cost invented**.
A day of this narrow operation costs on the order of the polls attempted; most repeat operations cost
**zero** external calls (dedupe/cache/offline replay win).

## Tests

Full suite **320 passed** (M12 handover baseline 298 + 22 M13 tests; the one previously environment-
skipped loopback test runs here). No network in the suite — every fetcher is injected.

## Reproduce

```
# Process 1 (makes ≤2 live calls; a re-run with the existing var/m13_live archive makes 0):
.venv/bin/python <harness p1>
# Process 2 (restart; 0 external calls):
.venv/bin/python <harness p2>
# Propagation + temporal probe + fit input (0 external calls — reads archived bytes):
.venv/bin/python <harness p3>
```

The harnesses live in the session scratchpad; all durable artifacts are under `/var/m13_live/`
(gitignored). Nothing here depends on re-issuing a live call.
