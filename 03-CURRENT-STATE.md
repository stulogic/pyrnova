# Pyrnova current state

_Verified 2026-09-08 in `~/Documents/Pyrnova` on `main`._

## Milestone status

- **M2: CONDITIONAL PASS / EXTERNAL SAM ACCEPTANCE PENDING.** All implemented behavior is green; a
  fresh post-quota-reset SAM call is the sole formal closure gate.
- **M3: CLOSED.** The formal acceptance review passed on 2026-09-08.
- **M4: CLOSED.** Offline-first source expansion passed its implementation and regression gates on
  2026-09-08; live connectivity checks remain operational freshness work, not closure evidence.
- **M5: CLOSED.** Cross-source capital-chain resolution, opportunity evolution, and chain
  observability passed acceptance on 2026-09-08. `scoring_v1` unchanged.
- **M6: CLOSED.** Budget/appropriation precursor coverage and inferred-relationship calibration passed
  acceptance on 2026-09-08; the weighted, explainable inference model, human review queue, and
  entity-level predicates are exercised by a reviewed corpus. `scoring_v1` unchanged.
- **M7: IN PROGRESS.** Capital catalysts and commercial consequences turn resolved capital chains into
  explicit, evidence-backed commercial consequences (mechanism, directness, participant roles,
  capability, value, falsifiers) without inventing generic business ideas.

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

## M6 precursor + inferred-join calibration

- **Appropriations / program-funding precursor source** (`pyrnova/sources/appropriations.py`,
  registry id `appropriations`): offline-first adapter over explicitly configured official budget
  artifacts, mirroring the acquisition-forecast contract (deterministic identity, `available_at`,
  exact-byte archival, sanitized request fingerprint, malformed handling). It distinguishes
  `INTENT` (budget request), `AUTHORIZATION` (enacted authority), and `FUNDING` (appropriated budget
  authority) and never collapses them. It emits the most authoritative structured identifier present
  (TAS → Federal Account → CFDA/assistance-listing → program element → budget line item) as
  `program_identifier`, retaining every raw id field. It cannot create a candidate or STRIKE.
- **Weighted, explainable inference model** (`pyrnova/chains.py:score_inferred_join`): replaces the
  M5 rubber-stamp inferred path with an additive factor model gated by an authoritative structured
  **anchor** (shared program identifier, matching entity UEI, or a specific program/solicitation
  number fragment). Without an anchor a pair is capped at 0.55, so agency + topic + chronology +
  name-similarity can never reach the frozen 0.60 acceptance threshold. Contradiction penalties
  (agency conflict, temporal impossibility, geography/funding divergence) subtract and can invalidate
  an anchored pair. Anchored pairs in `[0.45, 0.60)` are **deferred** to human review, not linked.
  Every factor, penalty, and anchor is retained on the relationship rationale. The canonical
  shared-identifier + agency case still lands at exactly 0.60, so all M5 behavior is preserved.
- **Human review queue** (`pyrnova/review_queue.py`, CLI `join-review`): deferred inferred joins are
  enqueued (idempotent per relationship id) with pre-review confidence and the prior automated
  recommendation; a reviewer records `ACCEPT_JOIN | REJECT_JOIN | WATCH` with reviewer, timestamp,
  and reason. `override_rate` reports how often reviewers disagree with the automated recommendation.
  This persisted history is future calibration evidence. State is durable append-only JSONL.
- **Entity-level predicates** (`pyrnova/chains.py:resolve_entity_relationships`): `AWARDED_TO`,
  `SUBSIDIARY_OF`, and `LOCATED_AT` are established only from authoritative structured fields
  (recipient/parent UEI, place of performance), never inferred from topic; each edge is
  evidence-backed, temporal, and deterministic (confidence 0.95).
- **`corpus_m6.json`** extends the frozen `corpus_m5.json` with eight reviewed cases: two true
  inferred joins (shared assistance-listing identifier; matching recipient UEI), three tempting false
  joins (cross-agency shared identifier, temporal impossibility, agency-plus-topic only), one
  ambiguous deferral (number-fragment only), one appropriation→forecast→solicitation→award precursor
  chain, and one partial authorization-only chain. Under `scoring_v1` the 35-case M6 corpus keeps
  false-negative rate 0.0, adds one true-positive STRIKE (the appropriation-anchored Air Force radar
  lifecycle), and raises STRIKE precision to 0.80 with false-positive rate 0.1429 and WATCH
  conversion 0.8889. Chain observability: 2 accepted inferred joins (both true → inferred precision
  1.0, false-join rate 0.0), 1 deferred join, ≥4 rejected weak joins, all three entity predicates
  exercised. The appropriation-anchored chain gives a 1053-day lead time from appropriation to award
  (vs the M5 flagship's 434 days from forecast). The frozen 0.60 threshold was swept over the
  corpus's anchored candidates and left unchanged: too few reviewed examples to justify a move. No
  live API calls. See `docs/replay/M6_INFERENCE_CALIBRATION.md` and
  `docs/specs/M6_PRECURSOR_AND_INFERENCE.md`.

## M7 commercial-consequence engine

- **Capital catalysts** (`pyrnova/catalysts.py`, `CapitalCatalyst`): one catalyst per resolved program
  chain — connected program keys (native-id or accepted inferred crosswalk) collapse into a single
  catalyst with deterministic identity `cat_<hash(program_keys)>`, so a chain never yields duplicate
  catalysts. It references canonical signals/relationships, carries a catalyst confidence distinct from
  scoring, `first_observed_at`/`available_at`, contradiction status, and a small catalyst-type enum
  (BUDGET_APPROPRIATION / PROGRAM_ESTABLISHMENT / PROCUREMENT_LIFECYCLE / REGULATORY_MANDATE /
  CAPACITY_BUILDOUT / SUPPLY_DISRUPTION).
- **Commercial consequences** (`CommercialConsequence`, distinct from `Opportunity`/STRIKE): each
  describes one economically distinct behavior a catalyst is likely to cause, with mechanism,
  directness, participant roles, capability classes, timing, value, evidence, assumptions, falsifiers,
  a consequence confidence, and a *recommended* `screened_disposition`. A catalyst yields **0..N**
  consequences; zero is common and valid.
- **Mechanism taxonomy (v1, deterministic + explainable)**: DIRECT_PROCUREMENT, FUNDED_DOWNSTREAM_DEMAND,
  FORCED_COMPLIANCE_SPEND, CAPITAL_EXPANSION, SUPPLY_DISPLACEMENT, TECHNOLOGY_MIGRATION,
  INDUSTRIAL_CAPACITY_BUILDOUT. Classification comes from stage + record_kind + source + explicit
  structured flags (procurement language, funding type, regulatory obligation, capex/policy), never
  from topical similarity. A `_subsume` rule prevents double-counting the same money (an appropriation
  that funds an observed direct procurement is not also a separate downstream consequence).
- **Directness doctrine**: DIRECT (explicit buyer/spend path) → STRIKE-eligible; DOWNSTREAM (supported,
  one step removed) → WATCH; SECOND_ORDER (materially inferential) → held internal/WATCH pending
  corroboration. STRIKE requires DIRECT + a resolved BUYER/PRIME_RECIPIENT + a specific capability.
- **Participant roles** (`resolve_participants`): FUNDING_AUTHORITY, PROGRAM_OWNER, BUYER,
  PRIME_RECIPIENT, BENEFICIARY, REGULATED_ENTITY resolved from authoritative structured fields;
  SUPPLIER/SUBCONTRACTOR are never inferred without explicit evidence.
- **Capability classes** (`pyrnova/capabilities.py`): specific normalized labels from NAICS/PSC and
  curated phrases; overly broad labels (technology, consulting, services, manufacturing…) are rejected.
- **Value foundation** (`pyrnova/value.py`): KNOWN / ESTIMATED / BOUNDED / UNKNOWN with method, inputs,
  confidence, provenance, and range; never an unsupported precise amount. UNKNOWN is a valid result.
- **Negative commercial evidence**: structured `ConsequenceFalsifier`s (no_identifiable_buyer,
  funding_restricted_from_commercial_use, internal_self_performance, program_cancelled,
  speculative_second_order, …); fatal falsifiers reject the consequence with a reason rather than
  silently lowering a number.
- **`corpus_m7.json`** extends the frozen `corpus_m6.json` with eight consequence cases (direct STRIKE,
  downstream grant, multi-consequence CHIPS program, zero-consequence appropriation, internal
  self-performance kill, regulatory compliance, second-order capex, unknown-value direct procurement).
  Consequence engine over the 43-case M7 corpus: 29 catalysts (2 duplicate program keys collapsed),
  23 consequences, 6 zero-consequence catalysts, 4 multi-consequence cases, directness DIRECT 13 /
  DOWNSTREAM 7 / SECOND_ORDER 3, five mechanism families exercised, buyer resolution 0.5652, capability
  resolution 0.5217, value KNOWN 4 / BOUNDED 3 / UNKNOWN 16, 1 consequence rejected
  (internal_self_performance). Consequence precision 1.0 and false-consequence rate 0.0 graded over the
  eight cases that declare consequence-level ground truth (small-sample warning surfaced). Under
  `scoring_v1`: 43 cases, STRIKE precision 0.875, WATCH conversion 0.8571, FPR 0.125, FNR 0.0, no STRIKE
  explosion (7 true / 1 false). Frozen M4/M5/M6 baselines unchanged. No live API calls. See
  `docs/replay/M7_CONSEQUENCE_REPORT.md` and `docs/specs/M7_COMMERCIAL_CONSEQUENCE.md`.

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
- The M6 inferred-join corpus is deliberately small: only 2 accepted inferred joins and 5 anchored
  candidates total. Inferred precision (1.0) and false-join rate (0.0) are therefore directional, not
  stable rates; the summary emits an explicit small-sample warning that is never hidden. The 0.60
  threshold stays frozen until a materially larger reviewed set exists.
- The human override rate is a live metric over adjudicated reviews, not a corpus constant; it is
  meaningful only once several real reviews accumulate.
- The `appropriations` adapter parses explicitly configured official artifacts; it has no live
  discovery and, like agency forecasts, each artifact still needs a reviewed column/field mapping.
  Only synthetic offline fixtures have been exercised — no live budget artifact has been archived yet.
- Entity predicates are established only from structured UEI/place fields present on a record; entity
  resolution across name variants and unverified addresses remains out of scope.
- No M6 live API calls were made.
- M7 consequence precision (1.0) and false-consequence rate (0.0) are graded on only 8 cases with
  declared consequence-level ground truth; the small-sample warning is surfaced, never hidden. Two of
  the seven mechanism families (SUPPLY_DISPLACEMENT, TECHNOLOGY_MIGRATION) are implemented but not yet
  exercised by a reviewed corpus case. Capability/value extraction depends on structured NAICS/PSC and
  explicit amounts being present in a record; absent those, capability resolution and value are
  correctly UNKNOWN rather than guessed. Consequence generation is retrospective over a resolved chain;
  each consequence carries `first_supportable_at`, but per-cutoff consequence transitions are not yet
  woven into `derive_transitions`. No M7 live API calls were made.
- Earlier limitations (M2 fresh-SAM gate, sparse STRIKE sample, binary-metric exclusions, restricted
  URL checks, local JSONL/filesystem state, heterogeneous forecasts, SEC full-text, tiny inferred-join
  sample) still stand.

## Exact next action

Run the unchanged M2 live acceptance sequence in `02-EXECUTION.md` at or after
`2026-09-09T00:00:00Z`, then record the acceptance timestamp and raw SAM archive hash here and in
`06-HISTORY.md`. M6/M7 remain offline; accumulate additional reviewed consequence and inferred-join
cases (and exercise the SUPPLY_DISPLACEMENT / TECHNOLOGY_MIGRATION mechanisms) before drawing general
commercial-precision conclusions.
