# Pyrnova current state

_Verified 2026-09-08 in `~/Documents/Pyrnova` on `main`._

## Milestone status

- **M2: CONDITIONAL PASS / EXTERNAL SAM ACCEPTANCE PENDING.** All implemented behavior is green; a
  fresh post-quota-reset SAM call is the sole formal closure gate.
- **M3: CLOSED.** The formal acceptance review passed on 2026-09-08.
- **M4: CLOSED.** Offline-first source expansion passed its implementation and regression gates on
  2026-09-08; live connectivity checks remain operational freshness work, not closure evidence.
- **M5: IN PROGRESS.** Cross-source capital-chain resolution, opportunity evolution, and chain
  observability are implemented and offline-validated; acceptance is pending final review.

## Implemented and verified

- USAspending, SAM, and bounded Federal Register ingestion with raw evidence/provenance handling.
- Source-native deterministic identity/deduplication and stable candidate IDs.
- Five evidence levels; Federal Register context capped at levels 1–2 and unable to create candidates.
- Selectivity regression: 1 STRIKE / 57 WATCH / 43 REJECT from the prior 101-candidate Torch run.
- Durable human adjudication with reviewer, timestamp, reason, score, prior system disposition, and final
  decision.
- Strict point-in-time replay, future exclusion, deterministic result/report IDs, and persistent
  scoring/evidence/threshold/mechanism versions.
- Canonical M3 corpus: 20 cases, six mechanism families, positive/negative/partial/ambiguous outcomes.
- Automated classification, evidence, temporal, calibration, value, WATCH, failure-taxonomy,
  mechanism, and model-versus-human diagnostics.
- Full-corpus `scoring_v2_candidate` comparison completed and rejected; `scoring_v1` unchanged.
- 109 tests pass; compilation and diff-integrity checks pass.
- `SAM_API_KEY` loads from the repository-local, gitignored `.env`; file mode is `600`. The value is
  never documented or logged.
- Grants.gov Search2, focused SEC EDGAR submissions/companyfacts, and official agency procurement
  forecast CSV artifacts now have deterministic identity, exact-byte archival, offline fixtures,
  malformed/error handling, conservative normalization, and reusable source-call controls.
- M4 source expansion replays archived bytes through normalization, SEC CIK entity resolution,
  evidence, and partial program chains without creating candidates. Explicit joins support
  INTENT → AUTHORIZATION → FUNDING → PROGRAM → MARKET ENGAGEMENT → PROCUREMENT → AWARD → OUTCOME.
- The 23-case M4 corpus extends rather than edits the frozen M3 corpus. Under `scoring_v1`, it keeps
  STRIKE precision 0.6667, false-positive rate 0.3333, and false-negative rate 0.0; WATCH conversion
  is 0.8667 and median measurable lead time is 297.5 days. Each new source adds one WATCH in ablation,
  zero STRIKEs, and zero measured precision change.
- M5 cross-source resolution (`pyrnova/chains.py`, `pyrnova/transitions.py`) links source-native
  signals into typed, temporal, evidence-backed relationships (`AUTHORIZES`, `FUNDS`, `IMPLEMENTS`,
  `PRECEDES`, `CORROBORATES`, `CONTRADICTS`) via a deterministic-program-key / native-identifier /
  conservative-inference hierarchy; weak matches (agency-name-only, topic-only, chronology-only) are
  rejected and counted. Every relationship carries `first_observed_at`, so replay answers "when could
  we first have known this?". Opportunity transitions are derived by replaying `scoring_v1`
  point-in-time and never fabricate an unsupported promotion.
- `corpus_m5.json` extends the frozen `corpus_m4.json` with four reviewed chain cases. The M4 baseline
  is byte-for-byte unchanged. The M5 corpus (27 cases) shows STRIKE precision 0.75, WATCH conversion
  0.875, false-positive rate 0.25, false-negative rate 0.0, median lead time 297.5 days: one added
  hand-reviewed true-positive lifecycle STRIKE, no false positive, and no `scoring_v1` change. All
  seven chain-carrying cases resolve into seven deterministic cross-source relationships with one
  rejected weak join; the flagship Navy lifecycle chain spans forecast → solicitation → award over
  434 days and is promoted WATCH→STRIKE by the procurement solicitation. See
  `docs/replay/M5_CHAIN_RESOLUTION.md`.

## M3 baseline

- STRIKE precision: 0.6667
- WATCH conversion: 0.8571
- False-positive rate: 0.3333
- False-negative rate: 0.0
- Median measurable lead time: 306.5 days
- Human override rate: 0.15

## Known limitations

- M2 has no fresh post-reset SAM acceptance artifact yet.
- Only three known-outcome M3 cases are STRIKEs, so precision uncertainty remains wide.
- Binary metrics exclude PARTIAL and AMBIGUOUS cases.
- Value calibration has only two comparable cases and supports no general conclusion.
- Several official source sites restrict automated URL checks; canonical source/document identity is
  retained separately from current URL reachability.
- Local JSONL state and filesystem evidence archive are development implementations; production
  PostgreSQL/object storage remain deferred.
- Grants.gov replay evidence is still one reviewed historical case; SEC EDGAR one visible historical
  case; and procurement forecast one unresolved case. These prove conservative coverage, not broad
  predictive lift.
- Agency procurement forecasts are heterogeneous. M4 supports explicit official CSV artifacts, but
  each agency still requires a reviewed field mapping; PDF/HTML/spreadsheet variants are deferred.
- SEC filing metadata and filed capex facts are normalized; full-text semantic extraction of facility,
  supply-disruption, customer-concentration, and geographic-change claims remains human-supervised.
- No M4 live API calls were made. Current connectivity, provider quotas, and cadence remain unknown
  until a separately justified LIVE-SAFE or ACCEPTANCE request.
- The M5 chain corpus is four reviewed cases; every accepted join is deterministic. The conservative
  `inferred_strong_attribute` path is implemented and unit-tested but not yet exercised by a corpus
  case, and entity-level predicates (`AWARDED_TO`, `SUBSIDIARY_OF`, `LOCATED_AT`) plus explicit
  budget/appropriation precursor stages await reviewed primary evidence. No M5 live API calls were
  made.

## Exact next action

Run the unchanged M2 live acceptance sequence in `02-EXECUTION.md` at or after
`2026-09-09T00:00:00Z`, then record the acceptance timestamp and raw SAM archive hash here and in
`06-HISTORY.md`.
