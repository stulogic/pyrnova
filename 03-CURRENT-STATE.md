# Pyrnova current state

_Verified 2026-09-09 in `~/Documents/Pyrnova` on `main` (M10 CLOSED; M2 external SAM gate closed)._

## Milestone status

- **M2: CLOSED 2026-09-09.** The external SAM acceptance gate passed at `2026-09-09T07:14Z`, executed
  unchanged and unweakened. Gate step 1 confirmed `SAM_API_KEY present: yes` (value never exposed). A
  genuinely fresh live SAM retrieval was performed through the normal adapter path at
  `2026-09-09T07:11:39Z` (`GET https://api.sam.gov/opportunities/v2/search`, ptype `o`), producing 10
  real rows archived to Tier B at content hash
  `574813de00d1bc6f8703c075c601cb4fa48be401a94a1ceaa8c571c482350a08`; the archive round-trip and content
  hash matched, request provenance contained no `api_key`, and the raw bytes contained no credential
  material. A second fresh pre-solicitation retrieval (`2026-09-09T07:14Z`, ptypes `r`/`p`/`s`, 150
  notices) exercised the full ingest: stable `sam:notice:*` identity, idempotent repeat ingest (dedup),
  cross-source separation (SAM bytes retrievable only under `sam_opportunities`), evidence-level rules
  (strength 5 `direct_causal_program_evidence` observed), deterministic disposition across repeat runs,
  and one persisted live-derived human adjudication (`stulogic`, WATCH → `human_watch`). Full suite: 248
  passed, 1 skipped; compilation clean; diff integrity clean (no tracked-file change); deterministic
  replay corpus reproduces the frozen `scoring_v1` baseline; live-ingest dedup regression green. See
  `06-HISTORY.md`.
- **M3: CLOSED.** The formal acceptance review passed on 2026-09-08.
- **M4: CLOSED.** Offline-first source expansion passed its implementation and regression gates on
  2026-09-08; live connectivity checks remain operational freshness work, not closure evidence.
- **M5: CLOSED.** Cross-source capital-chain resolution, opportunity evolution, and chain
  observability passed acceptance on 2026-09-08. `scoring_v1` unchanged.
- **M6: CLOSED.** Budget/appropriation precursor coverage and inferred-relationship calibration passed
  acceptance on 2026-09-08; the weighted, explainable inference model, human review queue, and
  entity-level predicates are exercised by a reviewed corpus. `scoring_v1` unchanged.
- **M7: CLOSED.** Capital catalysts and commercial consequences turn resolved capital chains into
  explicit, evidence-backed commercial consequences (mechanism, directness, participant roles,
  capability, value, falsifiers) without inventing generic business ideas. `scoring_v1` unchanged.
- **M8: CLOSED.** Capability fit + opportunity personalization: evidence-backed company profiles
  matched against commercial-consequence requirements produce an explainable capture posture
  (PRIME/SUPPORT/TEAM/DEFEND/NO_FIT) with fit dimensions, structured blockers, and point-in-time truth.
  A recovered internal Operations Panel is stabilized and sandbox-safe. `scoring_v1` unchanged.
- **M10: CLOSED 2026-09-09.** Multi-source company intelligence + subcontract/teaming resolution.
  Real profiles are grounded from ≥2 authoritative source families offline from archived evidence:
  SAIC (added public prime) from USAspending prime + **SEC EDGAR** submissions + USAspending recipient;
  Torch from USAspending prime + **USAspending sub-awards** + recipient. `multisource.py` defines
  `SourceFact` + a point-in-time merger that writes into the existing `CompanyProfile` fields and never
  overwrites a higher-authority fact with a lower one (conflicts recorded, not silently resolved).
  `corpus_m10.json` extends frozen `corpus_m9.json` with 8 real multi-source fit cases exercising PRIME,
  TEAM (authoritative repeat sub-award partner edge), SUPPORT/**false-tempting-TEAM** (resolves to
  SUPPORT, never a manufactured TEAM), DEFEND, real-eligibility NO_FIT (`insufficient_certification`),
  broad-sector NO_FIT, a future-evidence leakage case, and an insufficient-evidence UNKNOWN.
  Multi-source-real fit metrics (separate bucket, directional): 8 graded fits, fit precision 1.0,
  no-fit precision 1.0, false-match rate 0.0, posture precision 1.0 (per-posture 1.0), blocker accuracy
  1.0, capability coverage 0.875, buyer-history coverage 1.0, unknown rate 0.125,
  **temporal_leakage_violations 0**. Grounding observability: 8/8 multi-source profiles, avg 2.5
  families/profile (max 3), eligibility coverage 0.5, subcontract coverage 0.625, 5 profiles with an
  authoritative partner edge. `fit.py` and `scoring_v1` unchanged; scoring stability proven over the
  frozen 55-case M9 corpus (FNR 0.0, one inherited false strike, no STRIKE explosion); frozen M4–M9
  corpora byte-for-byte unchanged. Full suite: 272 passed, 1 skipped. No live calls. See
  `docs/replay/M10_MULTISOURCE_CALIBRATION.md` and `06-HISTORY.md`.
- **M11: CLOSED 2026-09-09.** Production opportunity lifecycle + append-only outcome learning
  (`pyrnova/outcomes.py`). Twelve authoritative point-in-time outcome labels (WON, LOST, PARTICIPATED,
  NO_BID, AWARD_TO_OTHER, CANCELLED, EXPIRED, DELAYED, PARTIAL_CAPTURE, SUBCONTRACT_CAPTURE,
  INCUMBENT_RETENTION, UNKNOWN). Outcomes are recorded as dated, sourced, append-only
  `OutcomeObservation`s (idempotent); `resolve_outcome(..., as_of)` excludes future-dated observations
  and resolves to UNKNOWN when nothing is knowable — **loss is never inferred from absence** (capture-
  negative/terminal labels require an explicit `source_ref` and `evidence_strength >= 3`). The learning
  ledger snapshots each prediction **verbatim** (never mutated) and grades correctness as calibration
  only. Challenger predictors are **evaluation-only** (`promoted=False`, `production_scoring_version=
  scoring_v1`); `ACTIVE_SCORING_VERSION` stays `scoring_v1`. `corpus_m11.json` extends frozen
  `corpus_m10.json` with 13 outcome cases (all 12 labels + an absence-guard + a future-exclusion case):
  resolution rate 0.8462, capture 4, win-rate-among-contested 0.6667, `loss_inferred_from_absence` 0,
  `future_outcomes_excluded` 1; a sample challenger scores 0.75/0.75 and is not promoted. Frozen M4–M10
  corpora unchanged. Full suite: 284 passed, 1 skipped. No live calls. See
  `docs/specs/M11_OUTCOME_LEARNING.md`.
- **M9: CLOSED.** Real company grounding + production fit calibration: company profiles are built
  from real archived USAspending evidence (Torch Technologies, Modern Technology Solutions), filtered
  strictly point-in-time, then run through the fit engine against real historical opportunities.
  Real-profile metrics are reported separately from synthetic; temporal leakage is a hard gate.

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

## M8 capability fit + personalization

- **Company capability profile** (`pyrnova/company.py`, `CompanyProfile`): a durable, evidence-linked
  profile distinct from the customer relevance profile in `match.py`. Every capability is normalized
  via `capabilities.py` (specific labels only; broad labels rejected) and carries
  `source_id`/`source_ref`/`available_at` provenance. `build_profile`/`profile_from_dict` filter both
  capability evidence and contract history strictly point-in-time (`available_at <= as_of`), so future
  capability evidence and future awards cannot leak into an earlier fit. Deterministic `company_id`.
- **Capability-fit engine** (`pyrnova/fit.py`): given a `CommercialConsequence` and a `CompanyProfile`,
  decides whether the company has a credible, evidence-backed capture path. Fit is grounded in explicit
  capability-class overlap — the SAME normalizer extracts both the consequence's requirement and the
  company's capabilities — never agency-name-only, NAICS-only, keyword-only, or semantic-similarity-only.
  Nine fit dimensions (CAPABILITY_FIT, BUYER_RELEVANCE, GEOGRAPHY, CERTIFICATION, SECURITY, SCALE,
  TIMING, INCUMBENT_POSITION, TEAMING_POTENTIAL) each report POSITIVE / NEGATIVE / UNKNOWN, never a
  forced neutral. Structured `FitBlocker`s (fatal vs soft) falsify a fit with a reason.
- **Capture posture**: PRIME (full capability, eligible, credible scale, prior prime performance),
  SUPPORT (fits a subcontract/supplier or downstream role), TEAM (partial capability plus teaming
  partners), DEFEND (incumbent — retention not new capture), NO_FIT (evidence says no, or insufficient
  evidence marked `is_unknown`). Unknown is never PRIME. Fit confidence is kept strictly separate from
  `scoring_v1`, catalyst/consequence confidence, and opportunity attractiveness.
- **Human review**: a lightweight fit review queue (ACCEPT_FIT / REJECT_FIT / DEFER) reusing
  `StateStore`, retaining the automated posture and pre-review confidence as calibration evidence.
- **`corpus_m8.json`** extends the frozen `corpus_m7.json` with 5 fit cases (12 graded fits): an
  obvious PRIME, SUPPORT, TEAM, DEFEND, a broad-sector false match, a capability-match-but-eligibility
  failure, a timing-passed block, and unknown/future-evidence-excluded companies, with multiple
  companies evaluated against one consequence. Posture distribution PRIME 3 / SUPPORT 2 / TEAM 1 /
  DEFEND 1 / NO_FIT 5. Fit precision 1.0, no-fit precision 1.0, false-match rate 0.0, posture precision
  1.0 (per-posture 1.0), blocker accuracy 1.0, capability-match coverage 0.75, buyer-history coverage
  0.5833, unknown-rate 0.1667 — all on a deliberately small graded sample (warning surfaced). Under
  `scoring_v1` the 48-case M8 corpus keeps FNR 0.0 and a single inherited false strike (STRIKE precision
  0.9231), with no STRIKE explosion. Frozen M4–M7 baselines unchanged. No live API calls. See
  `docs/replay/M8_FIT_REPORT.md` and `docs/specs/M8_CAPABILITY_FIT.md`.
- **Operations Panel** (`pyrnova/ops.py`, `pyrnova/ops_server.py`, `pyrnova/ops_web/`): a stabilized,
  local-only internal analyst view over append-only state (target queue, source status, adjudication,
  PRIME/SUPPORT/TEAM/DEFEND posture, evidence links, notes/falsification, STRIKE promotion, Signal
  Brief export, outcome label). Launch `python -m pyrnova.ops_server` → `http://127.0.0.1:8765`. Tests
  are sandbox-safe (the live-socket path skips when a loopback bind is forbidden; a handler-routing test
  covers the HTTP path without a port). See `docs/OPERATOR_CONSOLE.md`.

## M9 real company grounding + fit calibration

- **Real evidence ingestion** (`pyrnova/grounding.py`): `parse_usaspending_awards` turns archived
  USAspending `spending_by_award` bytes into temporally-provenanced facts (contract history, capability
  records, scale, contract vehicles, buyer agencies). Real award history for **Torch Technologies** and
  **Modern Technology Solutions** is archived under `examples/real_evidence/` (public domain, keyless;
  archive once, replay many).
- **Point-in-time profiles** (`grounding.profile_as_of`): a `CompanyProfile` built from only evidence
  knowable at a historical cutoff. Capabilities, scale, vehicles, and buyer agencies are ALL filtered
  `available_at <= cutoff`, so a future mega-award or contract vehicle cannot leak backward.
  `first_supportable_capability_date` answers "when did we first have evidence of capability X?"
  (Torch SETA 2018-05-23, HWIL 2021-01-15). CLI `profile` renders a profile as of a date.
- **Real capability vocabulary**: `capabilities.py` gains specific defense-services classes
  (hardware-in-the-loop simulation, SETA, missile-defense engineering, modeling & simulation, test &
  evaluation, specialty engineering); additive only, so frozen M4–M8 corpora are byte-for-byte
  unchanged.
- **Hard temporal-leakage gate**: `run_fit_replay` verifies that future-dated award refs declared in a
  case's `leakage_probe` never appear in the as-of profile, and reports `temporal_leakage_violations`.
- **`corpus_m9.json`** extends the frozen `corpus_m8.json` (55 cases) with **7 real fit cases** built
  from archived evidence: PRIME (Torch Army SETA 2020, MTSI MDA specialty 2019, MTSI FAS 2021), DEFEND
  (Torch incumbent weapons-SETA recompete, backed by a real follow-on award), SUPPORT (MTSI partial
  capability on a HWIL+specialty requirement), NO_FIT (Torch vs radar hardware manufacturing — a real
  defense firm correctly rejected for broad-sector matching; MTSI early-2010 insufficient evidence).
  Two cases carry future-award leakage probes (MTSI 2024/2025, Torch 2021).
- **Real-profile calibration (separate from synthetic M8)**: 7 graded real fits — fit precision 1.0,
  no-fit precision 1.0, false-match rate 0.0, posture precision 1.0, **temporal leakage violations 0**,
  capability coverage 0.857, buyer-history coverage 0.714, unknown rate 0.143 (tiny sample; warning
  surfaced). Synthetic M8 metrics (12 graded fits, precision 1.0) are reported separately and never
  blended. Under `scoring_v1`: 55 cases, STRIKE precision 0.9412, WATCH conversion 0.8571, FPR 0.125,
  FNR 0.0, no STRIKE explosion (16 true / 1 inherited false). Frozen M4–M8 baselines unchanged. See
  `docs/replay/M9_REAL_PROFILE_CALIBRATION.md` and `docs/specs/M9_REAL_COMPANY_GROUNDING.md`.

## M3 baseline

- STRIKE precision: 0.6667
- WATCH conversion: 0.8571
- False-positive rate: 0.3333
- False-negative rate: 0.0
- Median measurable lead time: 306.5 days
- Human override rate: 0.15

## Known limitations

- M2 is closed against a fresh live SAM artifact (hash `574813de…`, `2026-09-09T07:11:39Z`). The 48
  STRIKEs seen in the 150-notice pre-solicitation ingest window reflect broad capability matching of the
  Torch profile against an unfiltered live window; that number is an ingest-integrity demonstration, not
  a precision measurement (the frozen `scoring_v1` corpus baseline remains the precision authority).
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
- M8 fit precision, no-fit precision, false-match rate, posture precision, and blocker accuracy are all
  measured on only 12 graded fits across 5 cases; the small-sample warning is surfaced, never hidden.
  Fit quality depends on structured source fields (NAICS/PSC/capability phrases, certifications,
  clearances, contract history); where those are absent the fit is correctly UNKNOWN/NO_FIT rather than
  guessed. Requirements (certifications, clearance, geography restriction, contract vehicle, incumbency,
  timing) are read only from explicit record fields. No M8 live API calls were made.
- The Operations Panel is internal-only, loopback-only tooling; source health means "an observation is
  persisted", not a live availability claim, and outcomes are operator-entered labels, not ground truth.
- **M9 real-profile limitations (explicit):** 2 real companies (Torch, MTSI); 7 graded real fits — all
  metrics are directional, not stable. Source coverage is USAspending prime-award history only: SAM
  entity/eligibility, SEC filings, and official capability statements were NOT ingested, so
  certifications, security clearances, contract-vehicle breadth, and teaming access are UNKNOWN (never
  inferred). Public award data cannot prove subcontract/support activity, so absence of a public award
  is not proof of non-participation (ambiguity preserved). TEAM posture is not exercised for real
  profiles because public award data does not reveal teaming agreements (synthetic M8 covers TEAM).
  USAspending publication lag means an award's real knowability is slightly after its start date, which
  is used as `available_at` (a small, documented generosity). 4 live USAspending calls were made
  (keyless, public domain, archived); no SAM calls.
- Earlier limitations (M2 fresh-SAM gate, sparse STRIKE sample, binary-metric exclusions, restricted
  URL checks, local JSONL/filesystem state, heterogeneous forecasts, SEC full-text, tiny inferred-join
  and consequence samples, two un-exercised mechanism families) still stand.

## M10 limitations (explicit)

- 3 real companies (Torch, MTSI, SAIC), 8 graded multi-source fits — all metrics are directional, not
  stable rates; the small-sample warning is surfaced, never hidden.
- The M10 opportunity records are constructed probes attached to real, point-in-time profiles; the
  grounding is real, the opportunity is illustrative. M10 cases are not `scoring_v1` cases (scoring
  stability is proven over the frozen M9 corpus).
- SAM entity certifications / vehicle eligibility were NOT ingested in this offline close; eligibility
  is grounded from USAspending recipient business categories only. SAM set-asides/vehicle eligibility
  remain documented-insufficient, not fabricated.
- TEAM/sub-award evidence is USAspending sub-awards only; a single occurrence is weak, so TEAM requires
  a repeat prime↔subrecipient relationship (or an archived official announcement, none ingested here).
- SEC grounding applies only to public primes (SAIC); Torch and MTSI are privately held (no SEC filings).

## Exact next action

M2 CLOSED (`2026-09-09T07:14Z`, hash `574813de…`). M10 CLOSED
(`docs/replay/M10_MULTISOURCE_CALIBRATION.md`). M11 CLOSED (`docs/specs/M11_OUTCOME_LEARNING.md`).

M12 (next): integrate durable `SourceState` (`pyrnova/sources/source_state.py`) with the adapters and a
scheduler/jobs layer — budgets, dedupe, cache, archive, backoff, circuit breaker, checkpoint/resume,
source-health, operator controls — plus a lightweight Operations Panel extension. Offline default; no
live calls without a separately justified acceptance request. `scoring_v1`/`fit.py` unchanged; frozen
corpora unchanged.
