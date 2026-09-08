# Pyrnova execution authority

_Current execution window: M2 external closure gate, then M4 planning only · updated 2026-09-08_

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

## Immediate sequence

1. Complete and record the M2 live acceptance gate after the reset.
2. Re-run the M3 corpus and confirm the deterministic baseline remains unchanged.
3. Review the M4 authority stub in `docs/specs/M4_SOURCE_EXPANSION.md`.
4. Do not execute M4 until a separate implementation instruction authorizes it.

## Active constraints

- Preserve current M2/M3 behavior unless a reproducible defect requires a narrow repair.
- No scoring change for metric cosmetics or a single case.
- No frontend, source sprawl, commercial automation, or unrelated refactor.
- Keep `.env`, live archives, local state, customer data, and generated outputs out of Git.
- Use `~/Documents/Pyrnova` on `main` as the only working copy.
