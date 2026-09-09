# Pyrnova execution authority

_Current execution window: M21 CLOSED (raw adverse event + economic relationship diversity + observable
outcomes, 2026-09-09); M2–M20 closed; no milestone in progress — STOP and await next brief · updated
2026-09-09_

## Active work

### Milestone 21 — CLOSED 2026-09-09 (raw adverse event + economic relationship diversity + outcomes)

Spec `docs/specs/M21_RAW_TERMINATION_RELATIONSHIP_DIVERSITY.md`; evidence
`docs/replay/M21_RAW_TERMINATION_RELATIONSHIP_DIVERSITY.md`. Additive only — `scoring_v1`/`fit.py`/
`replay.py`/severity bands and frozen corpora (incl. `corpus_m20`) byte-identical. Phase 0 landed the
Product Language Authority (D-041) and strategic capability reconciliation + phase control (D-042; roadmap
areas 16–22). SEC ingestion hardened: configurable declared identity (never fabricated), authoritative
access order, discovery-vs-body separation, raw full-submission artifact, accession dedupe, safe 403.
Flagship: a real raw-archived USAspending **terminate-for-convenience** (PIID `36C25726N0240`, VA;
mod `P00002`, action_type `F`, −$3,908,263.25, 2026-08-31; D-043) → deterministic UEI `YR7CLZFGCM95`
exposure → HIGH-confidence `PROGRAM_CANCELLATION_OR_DELAY` → new `SUBSIDIARY_OF` economic relationship
(native-id parent hierarchy, child `YR7CLZFGCM95` → parent `KMSLVW1MZWU9`) → propagated threat
(HIGH→MEDIUM). `corpus_m21` (6 cases) → 80/80 pass; 55 direct / 19 propagated; 3 real relationship types;
20 negatives; 0 temporal leaks/explosions. Flagship later outcome honestly UNRESOLVED. ~16 keyless
USAspending calls (3 archival), 0 SEC/SAM. Full suite **482 passed**. No further M21 action.

### Milestone 20 — CLOSED 2026-09-09 (material adverse event + relationship-type diversity)

Spec `docs/specs/M20_GENERALIZED_ADVERSE_RELATIONSHIPS.md`; evidence
`docs/replay/M20_GENERALIZED_ADVERSE_RELATIONSHIPS.md`. A real SAIC SEC disclosure (10-K accession
`0001571123-26-000029`) reports $35M restructuring, impairment and exit costs → exact CIK deterministic
exposure → HIGH/HIGH `CORPORATE_RESTRUCTURING` → real deterministic `COMPANY_TO_PROGRAM` propagation to
active Army PIID `W31P4Q21F0095` (MODERATE/MEDIUM). Three adverse-event families and two real propagated
relationship types are now exercised. Relationship validity is enforced at catalyst time and full hop
provenance is retained. `corpus_m20` extends M19 → 74/74 pass; 51 direct / 17 propagated; 17 resolved
direct (precision 0.9412, N=17), 4 propagated (1.0, N=4 directional), 0 temporal leaks. One SEC raw
retrieval attempt returned 403 and was not retried; retained evidence is an attributable extract checked
against the archived SEC submissions identity snapshot. Full suite: 464 passed, 1 skipped. No further
M20 action.

### Milestone 19 — CLOSED 2026-09-09 (deterministic OBSERVED exposure + multi-family adverse events)

Spec `docs/specs/M19_DETERMINISTIC_EXPOSURE.md` (canonical); evidence
`docs/replay/M19_DETERMINISTIC_EXPOSURE.md`. Additive only: `scoring_v1`/`fit.py`/`replay.py`/frozen
corpora (incl. `corpus_m18`) byte-for-byte unchanged; additive edits to `adverse_events.py`/`threat.py`/
`propagation.py`/`ops.py`; new `corpus_m19.json`. Adds a **second OBSERVED adverse-event family** —
USAspending contract **deobligations** (`parse_usaspending_contract_modifications` → `contract_modification`
catalysts consumed by the existing `PROGRAM_CONTRACTION` engine), materially independent of BIS/Federal
Register export controls — and proves a **deterministic** OBSERVED exposure chain: a real deobligation
(mod **P00256, −$5,152,916.35, 2024-05-06**) on SAIC's exact PIID **47QFSA20F0057** (deterministic native-id
incumbency, SAIC UEI **MMLKPW9JLX64**) → **HIGH-confidence** PROGRAM_CONTRACTION → propagated one hop to
Torch on the SAME PIID. Deterministic authority (`exposure_join_class`) is durable on every threat and
every hop; deterministic identity alone is never a threat (materiality gate → `IMMATERIAL`, wrong-award →
`NO_EXPOSURE`, lapsed incumbency → `EXPOSURE_ENDED`). `summarize_m19` reports deterministic-vs-inferred +
multi-family selectivity; resolved propagated outcomes grew **1 → 4** with diversity. `corpus_m19`
(9 cases) extends `corpus_m18` → **66 cases all pass**; 46 direct / 16 propagated (no explosion), 2
adverse-event families, 10 OBSERVED / 36 MODELED direct, 2 REAL observed-deterministic-HIGH direct
threats, resolved outcomes 16 (precision 0.9333→**0.9375**, median lead 342.5 days). **3 live USAspending
calls** (archive-once); full suite **457 passed**. No further M19 action.

### Milestone 18 — CLOSED 2026-09-09 (independent relationship expansion + archived adverse catalysts)

Spec `docs/specs/M18_INDEPENDENT_ADVERSE_EVENTS.md` (canonical); evidence
`docs/replay/M18_INDEPENDENT_ADVERSE_EVENTS.md`. Additive only: `scoring_v1`/`fit.py`/`replay.py`/frozen
corpora (incl. `corpus_m17`) byte-for-byte unchanged; new `adverse_events.py`; additive edits to
`relationships.py`/`threat.py`/`propagation.py`/`threat_calibration.py`/`ops.py`. Proves a **REAL,
archived, OBSERVED adverse event → real catalyst → real exposure → an INDEPENDENT real relationship →
real propagated threat**: a Federal Register BIS Entity-List rule (FR 2026-17231, RIN 0694-AK49,
2026-08-24) propagates through **two independent real pairs — Parsons→Torch (MDA `HQ085821C0015`) and
Intuitive→Torch (Army `W31P4Q23FC001`), neither SAIC** — grounded 0-call from the authoritative sub-award
PRIME fields (`relationships.exposed_prime_awards_from_subawards`). Durable OBSERVED-vs-MODELED catalyst
authority on every threat; a real weak edge (NTSI) terminates; the same rule yields NO threat where there
is no evidenced exposure. `corpus_m18` (11 cases) extends `corpus_m17` → **57 cases all pass**; 41 direct
/ 12 propagated threats (max depth 2, no explosion), 11 independent company pairs, resolved outcomes
**12 → 15** (precision 0.9333, median lead 337 days), 13 negative cases. **1 live Federal Register call**;
full suite **445 passed**. No further M18 action.

### Milestone 17 — CLOSED 2026-09-09 (real relationship propagation + continuous threat operations)

Spec `docs/specs/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md` (canonical); evidence
`docs/replay/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md`. Additive only: `scoring_v1`/`fit.py`/`replay.py`/
frozen corpora (incl. `corpus_m16`) byte-for-byte unchanged; new `relationships.py`; additive edits to
`selectivity.py`/`scheduler.py`/`threat.py`/`threat_calibration.py`/`ops.py`. Grounds a REAL relationship
graph from archived sub-awards (22 real `SUBCONTRACTOR_OF` edges; strength mapped honestly:
program-anchored deterministic → CONFIRMED, repeat → INFERRED, single occurrence → weak/terminating);
proves **two real, deterministic SAIC→Torch propagation chains** (Prime-Award-ID-anchored; severity/
confidence degrade, never increase; no explosion); wires the selectivity funnel into normal scheduler
operation (`record_selectivity_run`/`selectivity_report`, persisted in the durable M12/M13 source-state
doc); measures **threat quality over time** (per-mechanism precision with denominators, source
contribution) from append-only predictions + later outcomes; adds a **company threat network view**.
`corpus_m17` (11 cases) extends `corpus_m16` → **46 cases all pass**; resolved outcomes **5 → 12**,
precision **0.9167 over 12**, median lead **336 days**. **0 live API calls**; full suite **428 passed**.
No further M17 action.

### Milestone 16 — CLOSED 2026-09-09 (threat calibration + exposure expansion + live selectivity)

Spec `docs/specs/M16_THREAT_CALIBRATION_PROPAGATION.md` (canonical); evidence
`docs/replay/M16_THREAT_CALIBRATION_PROPAGATION.md`. Additive only: `scoring_v1`/`fit.py`/`replay.py`/
frozen corpora (incl. `corpus_m15`) byte-for-byte unchanged; new `propagation.py`/`selectivity.py`/
`threat_calibration.py`; additive edits to `threat.py`/`ops.py`. Proves Pyrnova stays SELECTIVE on a real
19,365-event OFAC stream (0 threats for benign monitored companies), models three more exposure families
(supplier/technology/geography), propagates exposure safely across explicit company relationships
(bounded depth, degrading confidence, cycle-safe, duplicate-collapsing, beneficiary opportunities), and
calibrates historical warnings (precision with denominator; an unresolved threat is never a false alert).
`corpus_m16` (18 cases) extends `corpus_m15` → 35 cases all pass. **0 live API calls**; full suite **400
passed**. No further M16 action.

### Milestone 15 — CLOSED 2026-09-09 (first-class threat intelligence + exposure graph)

Spec `docs/specs/M15_THREAT_INTELLIGENCE.md` (canonical semantics); evidence
`docs/replay/M15_THREAT_INTELLIGENCE.md`. Additive only: `scoring_v1`/`fit.py`/`replay.py`/frozen M4–M11
corpora byte-for-byte unchanged (additive edits only to `models.py`/`ops.py`; new `pyrnova/threat.py`).
Threat is a first-class PEER of commercial consequence via `Exposure` + `Threat` + `ThreatRejection`,
with severity and confidence kept as orthogonal ordinals (no invented probability). **Seven** evidence-
safe mechanisms; sanctions linkage is deterministic-identifier-only (weak name matches rejected);
zero-threat is first-class; duality cross-links a threat and an opportunity sharing a catalyst without
duplicating facts; `company_threat_surface` and append-only threat-outcome linkage seed roadmap areas 4
and 10. `corpus_m15.json` extends the frozen lineage with 17 point-in-time threat cases (own replay);
one real evidence-backed threat (Torch, award `W31P4Q21F0038`); 2 dual-sided cases. Real OFAC linkage
proven on the 19,365 archived designations (guarded test). Operations Panel gained a thin read-only
threat view. No threat/temporal/secret leakage; full suite **373 passed**. No further M15 action.

### Milestone 14 — CLOSED 2026-09-09 (multi-source intelligence expansion + continuous operations)

Spec `docs/specs/M14_MULTI_SOURCE_EXPANSION.md`; manifest `docs/specs/SOURCE_MANIFEST.md` (machine-
readable `pyrnova/sources/registry.py`); evidence `docs/replay/M14_MULTISOURCE_EXPANSION.md`. Additive
only: `scoring_v1`/`fit.py`/frozen corpora byte-for-byte unchanged; the M12/M13 ingestion primitives
(`control.py`/`source_state.py`/`scheduler.py`/`live_ops.py`/`archive.py`) reused without redesign
(Workstream 2 finding). Broadened to **nine registered families across distinct economic domains**,
adding `sbir` (federal R&D precursor) and `sanctions_ofac` (sanctions/trade exposure). **Five families
operational on real bytes across five domains** (USAspending, SAM, SEC EDGAR, OFAC, Federal Register).
Two real cross-source chains proven (`chains.py`/`multisource.py`, no new join semantics): Chain A
SBIR→USAspending anchored on the real Torch UEI (2 cross-family accepted joins, 3 rejected weak joins,
confidence 0.60, ~6.8yr R&D→procurement lead time); Chain B SAIC SEC EDGAR + USAspending deterministic
entity merge (3 families). Three bounded live probes total (OFAC 200 → 19,365 real designations from one
bulk download; Federal Register 200; SBIR 403). Point-in-time truth, provenance, weak-join rejection
verified; no STRIKE explosion; no secret leakage; full suite 342 passed; Operations Panel functional
(thin family-mesh + chain readout). **Residual documented blocker:** `sbir` connectivity (HTTP 403,
provider maintenance) — adapter built and validated offline; retry one connectivity call when the
provider is available. Strategic roadmap items (broader source families, threat engine, etc.) remain in
`docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`. No further M14 action.

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

1. M2–M21 CLOSED — no milestone in progress; **STOP and await the next brief** (per the M21 work order,
   do not automatically begin M22).
2. Expected next direction (do not begin without explicit authority): customer-facing productization —
   Company Intelligence Dossier + Company Opportunity/Threat Surface + universal entity search + fast
   read-optimized delivery (roadmap areas 16–18). Source breadth, outcomes, calibration, and relationship
   coverage continue accumulating in parallel rather than blocking productization.
3. Documented residual (not a blocker to any closed milestone): retry one `sbir` connectivity call when
   the provider is out of maintenance to move it from `blocked` to `archive_operational`.
4. Other next-milestone candidates are recorded in `05-BACKLOG.md` and
   `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`. `scoring_v1`/`fit.py`/severity bands remain frozen
   absent a justified milestone.

## Active constraints

- Preserve current M2/M3 behavior unless a reproducible defect requires a narrow repair.
- No scoring change for metric cosmetics or a single case.
- No frontend, source sprawl, commercial automation, or unrelated refactor. New sources must pass the
  `M4_SOURCE_EXPANSION.md` test and honor `SOURCE_INGESTION.md`.
- Keep `.env`, live archives, local state, customer data, and generated outputs out of Git.
- Use `~/Documents/Pyrnova` on `main` as the only working copy.
