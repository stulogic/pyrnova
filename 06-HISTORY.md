# Pyrnova milestone history

## Foundation and commercial wedge

- Capture Radar kernel established with USAspending and SAM adapters, deterministic evidence archive,
  recompete and pre-solicitation engines, capability matching, human review, Signal Brief output, and
  append-only local state.
- Torch Technologies selected as the first real target; live evidence produced the initial outbound
  package. Historical commercial details remain in `docs/handovers/2026-09-08-M2-M3-HANDOVER.md`.

## Milestone 2 — functional pass; formal closure pending

- Added multi-source enrichment, five-level evidence strength, source-native identity/deduplication,
  sanitized SAM request provenance, raw response archival, deterministic disposition explanations,
  adjudication, and replay controls.
- Corrected expiry-driven selectivity noise from 47 STRIKEs to 1 STRIKE / 57 WATCH / 43 REJECT.
- Automated regression state: 52 tests passing.
- Formal state remains **CONDITIONAL PASS / EXTERNAL SAM ACCEPTANCE PENDING** until a fresh SAM response
  succeeds after `2026-09-09T00:00:00Z` and its archive hash/provenance gates pass.

## Milestone 3 — CLOSED 2026-09-08

- Built and quality-gated a 20-case historical corpus spanning six mechanism families.
- Added strict future exclusion, immutable scoring-policy identifiers, persistent deterministic replay
  results/reports, aggregate metrics, WATCH analysis, rejection taxonomy, mechanism diagnostics, and
  human-versus-model comparison.
- Established the `scoring_v1` baseline: STRIKE precision 0.6667, WATCH conversion 0.8571,
  false-positive rate 0.3333, false-negative rate 0.0, median lead time 306.5 days.
- Evaluated `scoring_v2_candidate` across the full corpus and rejected it as under-evidenced; no scoring
  change was made.

## Milestone 4 — CLOSED 2026-09-08

- Added offline-first Grants.gov Search2, focused SEC EDGAR submissions/companyfacts, and official
  agency procurement forecast ingestion with exact raw archival and deterministic identities.
- Added shared source modes, sanitized request fingerprints, per-source budgets/accounting, retry
  metadata, circuit state, and explicit unknown quota handling; no M4 live calls were made.
- Added deterministic SEC CIK resolution and explicit partial program chains spanning INTENT through
  OUTCOME without topic-inferred joins or new-source candidate creation.
- Extended the frozen M3 replay corpus to 23 reviewed M4 cases and added source-ablation measurement.
  STRIKE precision stayed 0.6667, false-positive rate 0.3333, false-negative rate 0.0, and no new
  STRIKEs appeared; each new source contributed one WATCH under ablation.
- Preserved `scoring_v1` and the frozen M2 SAM acceptance path.

## Milestone 5 — CLOSED 2026-09-08

- Added cross-source capital-chain resolution (`pyrnova/chains.py`): typed, temporal, evidence-backed
  relationships via a deterministic-program-key / native-identifier / conservative-inference
  hierarchy, with agency-name-only, topic-only, and chronology-only matches rejected and counted.
- Added opportunity evolution (`pyrnova/transitions.py`) derived by replaying `scoring_v1`
  point-in-time; it records disposition changes and their causing evidence without fabricating
  unsupported promotions.
- Extended `Relationship` with temporal/confidence/method provenance and added `OpportunityTransition`,
  mirrored in `db/schema.sql`.
- Added `corpus_m5.json` (extends the frozen `corpus_m4.json`) with four reviewed chain cases:
  a forecast→solicitation→award lifecycle (WATCH→STRIKE, 434-day lead), a grant→downstream-spend
  chain that stays WATCH, a rejected tempting false join, and an unresolved partial chain.
- Kept the M4 baseline byte-for-byte unchanged; the M5 corpus added one hand-reviewed true-positive
  STRIKE and no false positive, with `scoring_v1` unmodified. Test suite grew from 87 to 109.

## Milestone 6 — CLOSED 2026-09-08

- Added a budget/appropriation precursor source (`pyrnova/sources/appropriations.py`) distinguishing
  INTENT / AUTHORIZATION / FUNDING and emitting authoritative structured identifiers (TAS, Federal
  Account, CFDA, program element) that crosswalk into existing chains; offline-first, no live calls.
- Refined the inferred-join path into a weighted, explainable model (`score_inferred_join`) gated by
  an authoritative structured anchor with contradiction penalties and a `[0.45, 0.60)` deferral band.
  The frozen 0.60 acceptance threshold was given teeth, not relaxed; the canonical case still scores
  exactly 0.60 and all M5 behavior is preserved.
- Added a human review queue (`pyrnova/review_queue.py`, CLI `join-review`) that persists reviewer
  dispositions of deferred inferred joins (ACCEPT_JOIN / REJECT_JOIN / WATCH) with prior automated
  state, and an override-rate metric, as future calibration evidence.
- Added entity-level predicates (`AWARDED_TO`, `SUBSIDIARY_OF`, `LOCATED_AT`) from authoritative
  structured fields only.
- Added `corpus_m6.json` (extends the frozen `corpus_m5.json`) with eight reviewed cases: two true
  inferred joins, three tempting false joins, one ambiguous deferral, one appropriation-anchored
  precursor lifecycle (1053-day lead, WATCH→STRIKE), and one partial authorization case. Under
  `scoring_v1`: false-negative rate 0.0, STRIKE precision 0.80, false-positive rate 0.1429, WATCH
  conversion 0.8889; inferred precision 1.0 and false-join rate 0.0 over 2 accepted inferred joins
  (small-sample warning surfaced). The 0.60 threshold was swept and left unchanged. Test suite grew
  from 109 to 146. No live API calls.

## Milestone 7 — IN PROGRESS 2026-09-08

- Added the commercial-consequence engine (`pyrnova/catalysts.py`): one `CapitalCatalyst` per resolved
  program chain (deterministic id, connected keys collapse) and 0..N `CommercialConsequence`s, with a
  deterministic 7-family mechanism taxonomy, directness (DIRECT/DOWNSTREAM/SECOND_ORDER), participant
  roles (FUNDING_AUTHORITY/PROGRAM_OWNER/BUYER/PRIME_RECIPIENT/BENEFICIARY/REGULATED_ENTITY), and
  structured negative-commercial falsification. STRIKE requires DIRECT + resolved buyer + capability;
  SECOND_ORDER stays internal/WATCH.
- Added `pyrnova/capabilities.py` (specific capability-class extraction, broad labels rejected) and
  `pyrnova/value.py` (KNOWN/ESTIMATED/BOUNDED/UNKNOWN with provenance; never an invented amount).
- Wired `run_consequence_replay`/`run_consequence_corpus`/`summarize_consequence_results` and CLI
  `consequences` / `consequence-corpus`; mirrored `capital_catalyst` and `commercial_consequence`
  tables in `db/schema.sql`.
- Added `corpus_m7.json` (extends the frozen `corpus_m6.json`, 43 cases) with eight consequence cases:
  a direct-procurement STRIKE, a downstream grant, a multi-consequence CHIPS program, a
  zero-consequence appropriation (no invented ideas), an internal-self-performance kill, a regulatory
  compliance case, a second-order capex case, and an unknown-value direct procurement. Consequence
  engine: 29 catalysts (2 keys collapsed), 23 consequences, 6 zero-consequence, 4 multi-consequence,
  five mechanism families, 1 rejected consequence; consequence precision 1.0 / false-consequence rate
  0.0 on the eight graded cases (small-sample warning surfaced). Under `scoring_v1`: 43 cases, STRIKE
  precision 0.875, WATCH conversion 0.8571, FPR 0.125, FNR 0.0, no STRIKE explosion. Frozen M4/M5/M6
  baselines unchanged. Test suite grew from 146 to 182 (tracked). No live API calls.

## Repository authority normalization — 2026-09-08

- Declared `~/Documents/Pyrnova/main` the sole canonical working copy.
- Replaced overlapping authority/handover documents with the root `00`–`06` hierarchy.
- Preserved detailed specifications, research, replay evidence, historical handovers, and superseded
  authority in clearly scoped directories.
- Retained the existing source and test layout because structural churn was not justified.
