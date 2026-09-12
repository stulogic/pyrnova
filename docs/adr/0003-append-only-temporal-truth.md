# ADR-0003 — Append-only histories and cutoff reconstruction preserve temporal truth

Status: accepted  
Date: 2026-09-12 (retrospective record of implemented M3/M5/M11/M22 behavior)

## Context

Pyrnova must answer what was knowable at an earlier time and grade prospective calls without hindsight.
In-place mutation would erase the prior evidence, prediction, customer configuration, or assessment.

## Decision

Retain raw source states by content hash and observation; append predictions, reviews, outcomes, customer
profile/watch changes, and customer Material Change versions. Reconstruct at an explicit cutoff using
availability and validity fields. Later evidence/outcomes resolve or supersede through new records; they
do not rewrite the earlier call.

## Alternatives

- Keep only current rows: rejected because historical decisions become unreproducible.
- Backfill later facts into older predictions: rejected as temporal leakage.
- Infer negative outcomes from silence: rejected because missing remains unknown.

## Consequences

Replay and audit are possible and negative evidence remains honest. Readers must select current/as-of
versions correctly, and storage grows. Local JSONL lacks transactional/concurrency guarantees; a future
store must preserve ids, ordering, time, and append history.

## Related code

`pyrnova/archive.py`, `pyrnova/state.py`, `pyrnova/replay.py`, `pyrnova/outcomes.py`,
`pyrnova/customers.py`, `pyrnova/customer_material_changes.py`.

## Related authority

Project authority core doctrine; M3/M5/M11 and M22-B/C specifications; infrastructure doctrine §§26,
31–34.
