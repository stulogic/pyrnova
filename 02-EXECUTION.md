# Pyrnova execution authority

_Current execution window: M14 IN PROGRESS (multi-source intelligence expansion + continuous operations);
M2–M13 closed · updated 2026-09-09_

## Active work

### Milestone 14 — IN PROGRESS (multi-source intelligence expansion + continuous operations)

Spec: `docs/specs/M14_MULTI_SOURCE_EXPANSION.md`; manifest: `docs/specs/SOURCE_MANIFEST.md` (machine-
readable `pyrnova/sources/registry.py`). Additive only: `scoring_v1`/`fit.py`/frozen corpora unchanged;
the M12/M13 ingestion primitives (`control.py`/`source_state.py`/`scheduler.py`/`live_ops.py`/`archive.py`)
are reused without redesign (Workstream 2 finding). M14 broadens coverage to nine registered families
across distinct economic domains — adding `sbir` (federal R&D precursor) and `sanctions_ofac`
(sanctions/trade exposure) — proves cross-source intelligence chains (SBIR→USAspending by UEI; SEC+
USAspending company linkage) reusing `chains.py`/`multisource.py`, and enforces conservative per-source
live-call budgets (archive-first). Strategic roadmap: `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`.
Acceptance gate in the M14 spec; close only on honest breadth, otherwise document blockers and leave open.

### Milestone 13 — CLOSED 2026-09-09

Controlled live operations + end-to-end production validation. M2 verified CLOSED first (not inferred).
Additive only (`scoring_v1`/`fit.py`/`control.py`/`source_state.py`/adapters/frozen corpora unchanged):
poll cadence + live driver (`pyrnova/live_ops.py`) + Operations Panel call-cost view. A deliberately tiny
USAspending live run (2 calls, budget set first) proved only-needed calls, dedupe/cache avoidance, budget
enforcement, genuine-restart resume with 0 duplicate calls, end-to-end propagation (0 STRIKE / 19 WATCH /
11 REJECT — no explosion), strict temporal truth (40/50 excluded at a 2016 cutoff), zero credential
leakage, and fault-injected throttle/circuit/archive-failure recovery. Full suite 320 passed. See
`docs/specs/M13_LIVE_OPERATIONS.md` and `docs/replay/M13_LIVE_OPERATIONS.md`. No further M13 action.

### Milestone 2 — CLOSED 2026-09-09

The external SAM acceptance gate passed `2026-09-09T07:14Z`, executed unchanged and unweakened. Fresh
live retrieval at `2026-09-09T07:11:39Z` archived to Tier B at content hash
`574813de00d1bc6f8703c075c601cb4fa48be401a94a1ceaa8c571c482350a08`; all seven gate steps (key presence,
fresh retrieval + archival + matching hash + endpoint identity + sanitized provenance + no credential
material, stable identity + idempotent ingest + cross-source separation, evidence-level rules +
deterministic disposition, one persisted live adjudication, full regression) passed. Details in
`03-CURRENT-STATE.md` and `06-HISTORY.md`. No further M2 action.

### Milestone 10 — CLOSED 2026-09-09

M10 (multi-source company intelligence + subcontract/teaming resolution) passed its 21-point acceptance
gate offline on real archived evidence (`git` close commit `5a2e819`; see `03-CURRENT-STATE.md` and
`docs/replay/M10_MULTISOURCE_CALIBRATION.md`). `fit.py`/`scoring_v1` unchanged. No further M10 action.

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

1. M2–M13 CLOSED — no further action.
2. M14 (IN PROGRESS): execute `docs/specs/M14_MULTI_SOURCE_EXPANSION.md`. Reuse the M12/M13 ingestion
   primitives without redesign; add the `sbir` and `sanctions_ofac` families offline-first (archive-first,
   conservative live-call budgets); demonstrate ≥2 cross-source chains reusing `chains.py`/`multisource.py`;
   keep point-in-time truth, provenance, and weak-join rejection intact.
3. Do not alter `scoring_v1` or `fit.py` semantics (M14 is additive). Prefer bulk/archive over live calls;
   never spend SAM/authenticated quota on historical development.

## Active constraints

- Preserve current M2/M3 behavior unless a reproducible defect requires a narrow repair.
- No scoring change for metric cosmetics or a single case.
- No frontend, source sprawl, commercial automation, or unrelated refactor. New sources must pass the
  `M4_SOURCE_EXPANSION.md` test and honor `SOURCE_INGESTION.md`.
- Keep `.env`, live archives, local state, customer data, and generated outputs out of Git.
- Use `~/Documents/Pyrnova` on `main` as the only working copy.
