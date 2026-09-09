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

## Milestone 7 — CLOSED 2026-09-08

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

## Milestone 8 — CLOSED 2026-09-08

- Stabilized the recovered internal Operations Panel (`pyrnova/ops.py`, `ops_server.py`, `ops_web/`):
  a local-only, loopback-only analyst view over append-only state. Made its tests sandbox-safe (the
  live-socket test skips when a bind is forbidden; a new handler-routing test covers the HTTP path
  without a port). Launch `python -m pyrnova.ops_server` → `http://127.0.0.1:8765`.
- Added `pyrnova/company.py`: evidence-backed company capability profiles (specific normalized
  capabilities, point-in-time capability/award filtering, deterministic id), distinct from `match.py`.
- Added `pyrnova/fit.py`: the capability-fit engine — nine POSITIVE/NEGATIVE/UNKNOWN fit dimensions,
  structured fatal/soft blockers, and capture posture PRIME/SUPPORT/TEAM/DEFEND/NO_FIT. Fit rests on
  explicit shared capability classes only (no sector/NAICS/keyword/semantic-only fit); unknown is never
  PRIME; fit confidence is separate from `scoring_v1`. A fit review queue (ACCEPT_FIT/REJECT_FIT/DEFER)
  reuses `StateStore`.
- Wired `run_fit_replay`/`run_fit_corpus`/`summarize_fit_results` and CLI `fit`/`fit-corpus`; mirrored
  `company_profile`, `fit_result`, and `fit_review` in `db/schema.sql`.
- Added `corpus_m8.json` (extends the frozen `corpus_m7.json`, 48 cases) with 5 fit cases / 12 graded
  fits across all five postures, multiple companies per consequence, and NO_FIT via broad-sector,
  eligibility, timing, and unknown/future-evidence-excluded companies. Fit precision 1.0, no-fit
  precision 1.0, false-match rate 0.0, posture precision 1.0, blocker accuracy 1.0 (small graded
  sample; warning surfaced). Under `scoring_v1`: FNR 0.0, no new false strike, no STRIKE explosion.
  Frozen M4–M7 baselines unchanged. Test suite grew to 218 passing (1 sandbox skip). No live API calls.
  Each coherent block (panel, company, fit engine) was committed and pushed to origin/main.

## Milestone 9 — IN PROGRESS 2026-09-08

- Grounded real company profiles in archived USAspending prime-award evidence (public domain, keyless):
  archived Torch Technologies and Modern Technology Solutions award history to `examples/real_evidence/`
  (4 live USAspending calls; no SAM).
- Added `pyrnova/grounding.py`: `parse_usaspending_awards` (temporally-provenanced facts) and
  `profile_as_of(company, cutoff)` — a strict no-future-knowledge profile where capabilities, scale,
  vehicles, and buyer agencies are all filtered `available_at <= cutoff`. `first_supportable_capability_date`
  answers "when did we first have evidence of X?" (Torch SETA 2018, HWIL 2021). CLI `profile`.
- Extended `capabilities.py` with specific defense-services classes (HWIL, SETA, missile defense, M&S,
  T&E, specialty engineering); additive, frozen M4–M8 corpora unchanged.
- Added a real/synthetic fit-metrics split and a hard temporal-leakage gate to `replay.py`.
- Added `corpus_m9.json` (extends frozen `corpus_m8.json`, 55 cases) with 7 real fit cases: PRIME
  (Torch Army SETA, MTSI MDA specialty, MTSI FAS), DEFEND (Torch incumbent recompete, real follow-on),
  SUPPORT (MTSI partial capability), NO_FIT (Torch vs radar hardware — broad-sector rejection; MTSI
  early-cutoff unknown), plus future-award leakage probes. Real-profile fit precision 1.0, no-fit
  precision 1.0, false-match rate 0.0, posture precision 1.0, temporal leakage violations 0 — reported
  SEPARATELY from synthetic M8 (12 fits, precision 1.0). Under `scoring_v1`: 55 cases, STRIKE precision
  0.9412, FNR 0.0, no STRIKE explosion. Frozen M4–M8 unchanged. Test suite grew to 248 passing (1
  sandbox skip). TEAM deferred for real profiles. Each block committed and pushed to origin/main.

## Repository authority normalization — 2026-09-08

- Declared `~/Documents/Pyrnova/main` the sole canonical working copy.
- Replaced overlapping authority/handover documents with the root `00`–`06` hierarchy.
- Preserved detailed specifications, research, replay evidence, historical handovers, and superseded
  authority in clearly scoped directories.
- Retained the existing source and test layout because structural churn was not justified.

## Milestone 2 — external SAM acceptance attempt 2026-09-09 (CONDITIONAL retained)

- The external SAM acceptance gate opened `2026-09-09T00:00:00Z`. An acceptance run was attempted at
  `2026-09-09T03:04:50Z` following the unchanged sequence in `02-EXECUTION.md`.
- Result: the gate could not begin. Step 1 (`SAM_API_KEY present: yes`) fails because no `SAM_API_KEY`
  is available in this execution environment — the key lives only in a repository-local, gitignored
  `.env` (mode 600) that is never present in a fresh clone/container. The environment variable is also
  unset. Verified: `has_sam == False`, and the SAM adapter fails closed with
  `RuntimeError("SAM_API_KEY is required for the SAM connector")` — there is no cache, fixture, saved
  record, or manual-payload path that could substitute for a genuinely fresh retrieval.
- Classification: **provider/runtime prerequisite failure, not an implementation failure.** No fresh
  SAM response, raw archive, or archive hash was produced (none could be, honestly). The frozen M2
  acceptance logic and gate were NOT modified or weakened.
- Disposition: M2 remains **CONDITIONAL PASS**. All implemented M2 behavior remains green (249 tests
  pass; SAM fail-closed verified). Closure is deferred to a run in an environment where `SAM_API_KEY`
  is provisioned. This does not undermine M10 safety (M10 grounding leans on keyless USAspending/SEC
  and archived SAM bytes), so milestone progression to M10 continues per authority.

## Milestone 2 — external SAM acceptance CLOSED 2026-09-09

- The external SAM acceptance gate (opened `2026-09-09T00:00:00Z`) was executed unchanged and
  unweakened in an environment where `SAM_API_KEY` is provisioned and `api.sam.gov` egress is available.
- **Fresh retrieval:** one genuinely fresh live SAM pull through the normal adapter path
  (`SamClient.search_observations` → `GET https://api.sam.gov/opportunities/v2/search`, ptype `o`) at
  `2026-09-09T07:11:39Z`, 10 real rows. Raw bytes archived to Tier B via the real `EvidenceArchive` at
  content hash `574813de00d1bc6f8703c075c601cb4fa48be401a94a1ceaa8c571c482350a08`. Verified: archive
  round-trip byte-identical, stored hash == content hash, endpoint identity recorded, request provenance
  carried **no** `api_key`, and the raw response contained no credential substring.
- **Full ingest (fresh pre-solicitation pull, `2026-09-09T07:14Z`, ptypes `r`/`p`/`s`, 150 notices):**
  stable `sam:notice:*` source/candidate identity; idempotent repeat ingest (duplicate candidates and
  identical-byte observations dedup); cross-source separation (SAM bytes retrievable only under
  `sam_opportunities`, not `usaspending`); evidence-level rules exercised (strength 5
  `direct_causal_program_evidence`); disposition deterministic across independent repeat runs; one
  live-derived human adjudication persisted (`stulogic`, WATCH → `human_watch`). No `api_key` in any
  stored observation provenance.
- **Regression:** 248 passed / 1 skipped; compilation clean (bytecode cache redirected around a sandbox
  restriction); diff integrity clean (no tracked-file change from the acceptance run); deterministic
  replay corpus reproduces the frozen `scoring_v1` baseline; live-ingest dedup contracts green.
- **Note (honesty):** the 48 STRIKEs in the 150-notice window come from broad capability matching of the
  Torch profile against an unfiltered live window; this is an ingest-integrity demonstration, not a
  precision claim — the frozen corpus baseline remains the precision authority.
- **Disposition:** M2 is **CLOSED**. This supersedes the 2026-09-09 environment-blocked CONDITIONAL
  record below.

## Milestone 10 — spec authored; execution blocked on environment (2026-09-09)

- Authored the full M10 architecture/semantics spec: `docs/specs/M10_MULTI_SOURCE_INTELLIGENCE.md`
  (source hierarchy, `SourceFact` evidence model, TEAM semantics, point-in-time gate, corpus/metrics
  plan, and a 21-point acceptance gate). Key architectural finding: `pyrnova/fit.py` already reads every
  field M10 needs (certifications, geography/facilities, partners→TEAM, sub-role history, vehicles), so
  M10 is additive grounding + data + metrics with `fit.py` and `scoring_v1` unchanged.
- **Blocker (environment, not implementation):** M10's defining gate requires new real multi-source
  evidence. In this execution environment the organization egress policy blocks all external data hosts
  — verified 403 CONNECT policy denials for `data.sec.gov` and `api.usaspending.gov` (proxy status;
  only Anthropic APIs and package registries are allowed) — and no `SAM_API_KEY` is provisioned. The
  one archived SAM record (`examples/observations/torch_sam_2026-09-08.json`) is a reduced opportunity
  notice (mostly null, "not a raw API snapshot"), not company-entity evidence, so it is not a second
  grounding source family. Archived USAspending bytes are `spending_by_award` only (no recipient
  business categories / set-asides / UEI / location), so real eligibility grounding is not derivable
  from disk either.
- **Decision:** per the operating rule for a milestone that cannot safely close — do not fabricate, do
  not weaken acceptance, do not build unvalidated multi-source scaffolding. M10 is NOT started for real
  grounding and NOT closed. Coherent completed work (M2 record, M9 closure reconciliation, M10 spec) is
  committed and pushed. Because M10 did not close, **M11 was not started** (M11 is strictly gated on a
  clean M10 close per the execution order).
- **To resume:** run from a session whose egress allows the keyless data hosts (SEC + USAspending
  sub-awards → second/third source family without SAM) and/or with `SAM_API_KEY` provisioned; then
  execute the spec end to end.
- **Environment unblocked 2026-09-09:** in the current session all three prerequisites are satisfied —
  `SAM_API_KEY` present, `api.usaspending.gov` POST → 200, `data.sec.gov` GET → 200 (with a descriptive
  User-Agent). The earlier 403/000 readings were method/header artifacts (usaspending needs POST; SEC
  needs a UA), not a standing egress policy block. M10 real multi-source grounding is now executable and
  is the active milestone; execution begins per `docs/specs/M10_MULTI_SOURCE_INTELLIGENCE.md` with its
  21-point gate unweakened.

## Branch/remote reality note (2026-09-09)

- The overnight "verified state" assumed `HEAD == origin/main` with M7–M9 on `origin/main`. On the
  actual remote, `origin/main` is at `ca47e28` (M6 closure). All M7–M9 work, the M2 acceptance record,
  and the M10 spec live on `origin/claude/nice-johnson-yk8avd` (this session's designated branch;
  pushing to `main` or opening a PR without explicit permission is disallowed by the session's operating
  rules). A human should merge `claude/nice-johnson-yk8avd` into `main` via PR to reconcile `origin/main`.

## M10 CLOSED (2026-09-09) — multi-source real-company intelligence

- **Closed offline from archived evidence, no live calls.** Real company profiles are grounded from
  ≥2 authoritative source families via `pyrnova/multisource.py` (`SourceFact` + point-in-time merger
  writing into existing `CompanyProfile` fields; higher-authority facts never overwritten by lower,
  conflicts recorded): SAIC (added public prime) = USAspending prime + SEC EDGAR submissions +
  USAspending recipient; Torch = USAspending prime + USAspending sub-awards + recipient. Parsers
  `grounding_sec.py`, `grounding_subawards.py`, `grounding_recipient.py` are self-contained and additive.
- **Corpus:** `corpus_m10.json` extends the frozen 55-case `corpus_m9.json` with 8 real multi-source
  fit cases (PRIME, TEAM via authoritative repeat sub-award edge, SUPPORT / false-tempting-TEAM,
  DEFEND, eligibility-blocked NO_FIT, broad-sector NO_FIT, future-evidence leakage, insufficient-evidence
  UNKNOWN). Cases are fit-probe cases (real grounding, constructed opportunity), evaluated only by the
  fit engine — not scoring cases.
- **Metrics (multisource_real bucket, directional, separate from M8 synthetic and M9 single-family
  real):** 8 graded fits, fit precision 1.0, no-fit precision 1.0, false-match rate 0.0, posture
  precision 1.0 (per-posture 1.0), blocker accuracy 1.0, capability coverage 0.875, buyer-history
  coverage 1.0, unknown rate 0.125, temporal_leakage_violations 0. Grounding: 8/8 multi-source, avg 2.5
  families/profile (max 3), eligibility coverage 0.5, subcontract coverage 0.625, 5 authoritative
  partner edges.
- **Frozen invariants:** `fit.py` and `scoring_v1` unchanged (scoring stability proven over the frozen
  M9 corpus: 55 cases, FNR 0.0, one inherited false strike, no STRIKE explosion). Frozen M4–M9 corpora
  byte-for-byte unchanged. Full suite: 272 passed, 1 skipped.
- **Acceptance:** all 21 gate points hold (see `docs/replay/M10_MULTISOURCE_CALIBRATION.md` and the
  updated `docs/specs/M10_MULTI_SOURCE_INTELLIGENCE.md`). M11 (production lifecycle + append-only outcome
  learning) is now unblocked.

## M11 CLOSED (2026-09-09) — production lifecycle + append-only outcome learning

- **`pyrnova/outcomes.py` (additive, no scoring change).** Twelve authoritative point-in-time outcome
  labels; `OutcomeObservation` is append-only, dated, sourced, idempotent. `resolve_outcome(as_of)`
  enforces strict future-outcome exclusion and resolves to UNKNOWN when nothing is knowable — loss is
  never inferred from absence (capture-negative/terminal labels require an explicit source_ref and
  evidence_strength >= 3, enforced in `__post_init__`).
- **Predictions preserved verbatim** in the learning ledger (`build_learning_record`); correctness is a
  calibration read only and never feeds scoring. **Challengers are evaluation-only** (`evaluate_challenger`
  hard-codes `promoted=False`, `production_scoring_version=scoring_v1`); `ACTIVE_SCORING_VERSION` unchanged.
- **`corpus_m11.json` extends frozen `corpus_m10.json`** with 13 outcome cases (all 12 labels + an
  absence-guard resolving UNKNOWN + a future-exclusion case). Metrics (directional): resolution rate
  0.8462, capture 4, win-rate-among-contested 0.6667, loss_inferred_from_absence 0,
  future_outcomes_excluded 1; sample challenger precision/recall 0.75/0.75, not promoted.
- **Frozen invariants:** scoring_v1 and fit.py unchanged; M4–M10 corpora byte-for-byte unchanged; M9
  canonical base still loads (55). Full suite: 284 passed, 1 skipped. No live calls. See
  `docs/specs/M11_OUTCOME_LEARNING.md`. Next: M12 durable-source integration.

## M12 CLOSED (2026-09-09) — durable source integration (scheduler / jobs)

- **`pyrnova/scheduler.py` (additive).** `SourceScheduler` composes the previously separate primitives —
  `SourceStateStore` (durable budget/breaker/checkpoint/dedupe), `SourceControl` (mode/budget/breaker/
  retry/metrics), the registry, and `EvidenceArchive` — into an offline-default `run_job`. Performs no
  HTTP and imports no adapter; a live call happens only when a caller opts a source into a live mode AND
  supplies a `fetcher`.
- **Capabilities wired:** durable budgets (persist across restart within a `budget_epoch`; new epoch
  resets), request dedupe + cache/archive reuse, exponential+jitter backoff metadata, persisted circuit
  breaker that defers the next poll when open, checkpoint/resume, source-health report, and persisted
  operator controls (pause/resume, mode override, breaker reset).
- **Operations Panel extension:** `OperatorConsole(source_state_dir=...).source_operations()` surfaces
  durable per-source health read-only and degrades to an empty well-formed report when unconfigured.
- **Invariants:** control.py, source_state.py, adapters, fit.py, and scoring_v1 unchanged; frozen M4–M11
  corpora byte-for-byte unchanged; ACCEPTANCE never serves cached bytes; no live calls in the suite.
  Full suite: 298 passed, 1 skipped. See `docs/specs/M12_SOURCE_INTEGRATION.md`.
