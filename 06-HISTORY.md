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

## Repository authority normalization — 2026-09-08

- Declared `~/Documents/Pyrnova/main` the sole canonical working copy.
- Replaced overlapping authority/handover documents with the root `00`–`06` hierarchy.
- Preserved detailed specifications, research, replay evidence, historical handovers, and superseded
  authority in clearly scoped directories.
- Retained the existing source and test layout because structural churn was not justified.
