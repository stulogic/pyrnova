# Pyrnova execution authority

_Current execution window: M2 external closure gate; M3–M5 closed; M6 in progress · updated 2026-09-08_

## Active work

### Milestone 2 — conditional pass; external SAM acceptance pending

M2 functionality is complete. Formal closure requires one genuinely fresh SAM retrieval at or after
`2026-09-09T00:00:00Z` through the normal live adapter path. No cache, fixture, saved record, manual
payload, or fallback may count as success.

At the gate:

1. Verify only `SAM_API_KEY present: yes`; never expose the value.
2. Execute fresh retrieval and verify timestamp, adapter consumption, raw archival, matching hash,
   endpoint identity, sanitized request provenance, and absence of credential material.
3. Verify stable source/candidate identity, idempotent repeat ingest, and correct cross-source separation.
4. Verify evidence-level rules and explainable deterministic disposition.
5. Persist one live-derived human adjudication.
6. Run full tests, compilation, diff integrity, deterministic replay, and live-ingest dedup regression.
7. If every gate passes, mark M2 CLOSED in current state and history with timestamp and archive hash.

Do not weaken the gate. If SAM quota/service remains the only failure, preserve state and record the
exact external response.

### Milestone 3 — CLOSED

M3 passed closure review on 2026-09-08. Its corpus, metrics, versioning, challenger evaluation, and
known limitations are in `docs/replay/M3_BASELINE.md`. `scoring_v1` remains active.

### Milestone 4 — CLOSED

M4 passed offline implementation/replay acceptance on 2026-09-08. Active source expansion comprises
Grants.gov Search2, focused SEC EDGAR submissions/companyfacts, and explicitly configured official
agency procurement forecast artifacts. All default to archived responses/fixtures; source-call modes,
budgets, fingerprints, backoff metadata, breaker state, and metrics are explicit.

The 23-case M4 corpus adds one reviewed case per new source family without changing the 20-case M3
baseline. `scoring_v1` remains unchanged: no new STRIKEs, no precision regression, and each new source
adds one conservative WATCH in leave-one-source-out replay. See
`docs/replay/M4_SOURCE_CONTRIBUTION.md`.

### Milestone 5 — CLOSED

M5 passed acceptance on 2026-09-08. Cross-source capital-chain resolution (`pyrnova/chains.py`),
opportunity evolution (`pyrnova/transitions.py`), temporal `Relationship` fields, and
`OpportunityTransition` are implemented and offline-validated; the 27-case `corpus_m5.json` extends
the frozen `corpus_m4.json`. `scoring_v1` unchanged. See `docs/replay/M5_CHAIN_RESOLUTION.md`.

### Milestone 6 — in progress

M6 moves Pyrnova earlier in the capital lifecycle and calibrates inferred cross-source relationships
that cannot rely on deterministic identifiers. Implemented offline-first per
`docs/specs/M6_PRECURSOR_AND_INFERENCE.md`:

- `pyrnova/sources/appropriations.py` adds a budget/appropriation precursor source distinguishing
  INTENT / AUTHORIZATION / FUNDING and emitting authoritative structured identifiers (TAS, Federal
  Account, CFDA, program element) that crosswalk into existing chains.
- `pyrnova/chains.py` gains a weighted, explainable inference model (`score_inferred_join`) gated by
  an authoritative structured anchor, a `[0.45, 0.60)` deferral band, entity-level predicates
  (`AWARDED_TO`, `SUBSIDIARY_OF`, `LOCATED_AT`), and calibration outputs.
- `pyrnova/review_queue.py` (CLI `join-review`) persists human dispositions of deferred inferred
  joins as future calibration evidence.
- `examples/replay/corpus_m6.json` extends the frozen `corpus_m5.json` with eight reviewed cases;
  results are in `docs/replay/M6_INFERENCE_CALIBRATION.md`.

Active constraints: the inferred acceptance threshold stays frozen at 0.60 unless full-corpus
evidence justifies a change; inferred joins never independently drive a high-confidence STRIKE;
inference must remain explainable and evidence-anchored (no topic-only / agency-only / chronology-only
/ opaque-semantic joins); `scoring_v1` is unchanged; strict point-in-time replay is preserved.

## Immediate sequence

1. Complete and record the unchanged M2 live acceptance gate after the reset.
2. Accumulate additional reviewed inferred-join cases and at least one live-archived budget artifact
   before revisiting the 0.60 threshold; keep it frozen until the sample materially grows.
3. Do not alter scoring or begin a later milestone without separate authority.

## Active constraints

- Preserve current M2/M3 behavior unless a reproducible defect requires a narrow repair.
- No scoring change for metric cosmetics or a single case.
- No frontend, source sprawl, commercial automation, or unrelated refactor.
- Keep `.env`, live archives, local state, customer data, and generated outputs out of Git.
- Use `~/Documents/Pyrnova` on `main` as the only working copy.
