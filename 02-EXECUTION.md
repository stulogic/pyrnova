# Pyrnova execution authority

_Current execution window: M2 external closure gate; M3–M7 closed; M8 in progress · updated 2026-09-08_

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

### Milestone 6 — CLOSED

M6 passed acceptance on 2026-09-08: an appropriations/budget precursor source (INTENT/AUTHORIZATION/
FUNDING), a weighted anchored inferred-join engine with a `[0.45, 0.60)` deferral band, a human review
queue, and entity predicates (`AWARDED_TO`, `SUBSIDIARY_OF`, `LOCATED_AT`). 35-case `corpus_m6.json`
extends the frozen M5 corpus; `scoring_v1` unchanged. See `docs/replay/M6_INFERENCE_CALIBRATION.md`.

### Milestone 7 — CLOSED

M7 passed acceptance on 2026-09-08: `pyrnova/catalysts.py` builds one `CapitalCatalyst` per resolved
program chain and 0..N `CommercialConsequence`s (7-family mechanism taxonomy, directness, participant
roles, structured falsification); `capabilities.py`/`value.py` supply specific capability classes and
KNOWN/ESTIMATED/BOUNDED/UNKNOWN value. 43-case `corpus_m7.json` extends the frozen M6 corpus;
`scoring_v1` unchanged. See `docs/replay/M7_CONSEQUENCE_REPORT.md`.

### Milestone 8 — in progress

M8 personalizes opportunities: which specific companies have a credible, evidence-backed path to
capture a commercial consequence. Implemented offline-first per `docs/specs/M8_CAPABILITY_FIT.md`:

- `pyrnova/company.py` — durable, source-linked company capability profiles (specific normalized
  capabilities, point-in-time capability/award filtering, deterministic id).
- `pyrnova/fit.py` — the capability-fit engine: nine explicit fit dimensions
  (POSITIVE/NEGATIVE/UNKNOWN), structured fatal/soft blockers, and capture posture
  PRIME/SUPPORT/TEAM/DEFEND/NO_FIT. Fit confidence is separate from `scoring_v1`. A fit review queue
  (ACCEPT_FIT/REJECT_FIT/DEFER) reuses `StateStore`.
- `pyrnova/replay.py` adds `run_fit_replay`/`run_fit_corpus`/`summarize_fit_results`; CLI
  `fit`/`fit-corpus`. `examples/replay/corpus_m8.json` extends frozen `corpus_m7.json` with 5 fit cases.
- `pyrnova/ops*.py` + `ops_web/` — a stabilized internal Operations Panel (`python -m pyrnova.ops_server`).

Active constraints: fit is explicit capability/evidence overlap only — no agency/NAICS/keyword/
semantic-similarity-only fit; unknown stays unknown and is never PRIME; fit confidence stays distinct
from opportunity quality, evidence confidence, and consequence confidence; strict point-in-time truth
(no future capability/award leakage); `scoring_v1` unchanged; frozen corpora byte-for-byte unchanged.

## Immediate sequence

1. Complete and record the unchanged M2 live acceptance gate after the reset.
2. Accumulate more reviewed fit cases (and the un-exercised mechanism families) before drawing general
   fit-precision conclusions.
3. Do not alter scoring or begin a later milestone without separate authority.

## Active constraints

- Preserve current M2/M3 behavior unless a reproducible defect requires a narrow repair.
- No scoring change for metric cosmetics or a single case.
- No frontend, source sprawl, commercial automation, or unrelated refactor.
- Keep `.env`, live archives, local state, customer data, and generated outputs out of Git.
- Use `~/Documents/Pyrnova` on `main` as the only working copy.
