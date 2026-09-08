# Pyrnova execution authority

_Current execution window: M2 external closure gate; M4 closed; M5 in progress · updated 2026-09-08_

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

### Milestone 5 — in progress

M5 is cross-source intelligence and capital-chain resolution: connecting apparently separate source
signals into one economic story on evidence. Implemented offline-first per
`docs/specs/M5_CROSS_SOURCE_INTELLIGENCE.md`:

- `pyrnova/chains.py` resolves typed, temporal, evidence-backed relationships with a
  deterministic-program-key / native-identifier / conservative-inference hierarchy and explicit
  rejection of weak (agency/topic/chronology) matches.
- `pyrnova/transitions.py` derives opportunity evolution by replaying `scoring_v1` point-in-time.
- `Relationship` gains temporal/confidence fields and `OpportunityTransition` is added, both mirrored
  in `db/schema.sql`.
- `examples/replay/corpus_m5.json` extends the frozen `corpus_m4.json` with four reviewed chain cases;
  results are in `docs/replay/M5_CHAIN_RESOLUTION.md`. `scoring_v1` is unchanged.

Active constraint: chain resolution enriches evidence, timing, provenance, and explanation only. It
must not create a candidate, promote a disposition, or alter `scoring_v1`. Prefer deterministic and
native-identifier joins; never materialize a topic-, agency-name-, or chronology-only join.

## Immediate sequence

1. Complete and record the unchanged M2 live acceptance gate after the reset.
2. Re-run the frozen M3 corpus and confirm its deterministic baseline remains unchanged.
3. Expand new-source historical cases only as reviewed primary evidence becomes available; do not
   alter scoring or begin a later milestone without separate authority.

## Active constraints

- Preserve current M2/M3 behavior unless a reproducible defect requires a narrow repair.
- No scoring change for metric cosmetics or a single case.
- No frontend, source sprawl, commercial automation, or unrelated refactor.
- Keep `.env`, live archives, local state, customer data, and generated outputs out of Git.
- Use `~/Documents/Pyrnova` on `main` as the only working copy.
