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

## Milestone 5 — IN PROGRESS 2026-09-08

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

## Repository authority normalization — 2026-09-08

- Declared `~/Documents/Pyrnova/main` the sole canonical working copy.
- Replaced overlapping authority/handover documents with the root `00`–`06` hierarchy.
- Preserved detailed specifications, research, replay evidence, historical handovers, and superseded
  authority in clearly scoped directories.
- Retained the existing source and test layout because structural churn was not justified.
