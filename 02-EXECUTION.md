# Pyrnova execution authority

_Current execution window: M2 external closure gate (environment-blocked); M3–M9 closed; M10 active · updated 2026-09-09_

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

**2026-09-09 attempt:** the gate opened `2026-09-09T00:00:00Z`; a run attempted `2026-09-09T03:04:50Z`
could not begin because `SAM_API_KEY` is not provisioned in the execution environment (fresh clone; the
gitignored `.env` is absent). The adapter fails closed; no fresh retrieval, archive, or hash was
produced. M2 remains CONDITIONAL — an environment/provider prerequisite, not an implementation defect.
Rerun unchanged where `SAM_API_KEY` is available. See `06-HISTORY.md`.

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

### Milestone 8 — CLOSED

M8 passed acceptance on 2026-09-08: `pyrnova/company.py` (evidence-backed company profiles) and
`pyrnova/fit.py` (nine POSITIVE/NEGATIVE/UNKNOWN fit dimensions, structured blockers, capture posture
PRIME/SUPPORT/TEAM/DEFEND/NO_FIT). 48-case `corpus_m8.json` extends the frozen M7 corpus; a recovered
Operations Panel is stabilized. `scoring_v1` unchanged. See `docs/replay/M8_FIT_REPORT.md`.

### Milestone 9 — CLOSED

M9 replaces synthetic company-fit proof with real, evidence-backed company intelligence and
point-in-time fit calibration. Implemented offline-first per `docs/specs/M9_REAL_COMPANY_GROUNDING.md`:

- `pyrnova/grounding.py` — parses archived USAspending award bytes into temporally-provenanced facts
  and builds `profile_as_of(company, cutoff)` using only evidence knowable at the cutoff (capabilities,
  scale, vehicles, buyers all filtered point-in-time). Real Torch/MTSI evidence under
  `examples/real_evidence/`.
- `capabilities.py` gains specific real defense-services classes (additive; frozen corpora unchanged).
- `replay.py` adds a grounded-profile branch, a real/synthetic metrics split, and a hard
  temporal-leakage gate. CLI `profile`. `corpus_m9.json` extends frozen `corpus_m8.json` with 7 real
  fit cases.

Active constraints: NO future-knowledge profile construction — every profile fact is filtered
point-in-time and carries temporal provenance; real-profile metrics are reported separately from
synthetic (never blended); fit doctrine is unchanged (no broad-sector / agency-only / NAICS-only /
keyword-only / semantic-only match; unknown stays UNKNOWN; certifications/clearances/teaming are not
inferred); `scoring_v1` unchanged; frozen corpora byte-for-byte unchanged.

## Immediate sequence

1. M2 external gate remains open but environment-blocked (no `SAM_API_KEY` in this container). Rerun the
   unchanged sequence, without weakening it, where the key is provisioned; then record timestamp + hash.
2. M10 (active): broaden real grounding beyond USAspending prime history — SAM/SEC/official-capability
   evidence (certifications, clearances, vehicles), subaward/teaming evidence, real SUPPORT/TEAM
   exercise, `corpus_m10` with synthetic/real/multi-source metrics kept separate. See
   `docs/specs/M10_MULTI_SOURCE_INTELLIGENCE.md`.
3. Do not alter `scoring_v1` or begin M11 without M10 closing cleanly and all gates passing.

## Active constraints

- Preserve current M2/M3 behavior unless a reproducible defect requires a narrow repair.
- No scoring change for metric cosmetics or a single case.
- No frontend, source sprawl, commercial automation, or unrelated refactor.
- Keep `.env`, live archives, local state, customer data, and generated outputs out of Git.
- Use `~/Documents/Pyrnova` on `main` as the only working copy.
