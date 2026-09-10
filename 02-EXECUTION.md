# Pyrnova execution authority

_Current execution window: **M22-F CLOSED 2026-09-10** (minimal customer access + seed-free onboarding —
credential/authenticated-actor/server-enforced tenant isolation, operator-assisted onboarding without seed
edits); M22-E closed (opportunity Material Changes — the product is no longer threat-only); M22-D closed
(company/program investigation pages + deterministic entity search); M22-C closed (per-tenant persisted
Material Change streams + production read path); M22-B closed (persisted customer intelligence + Material
Change lifecycle); M22-A closed (Material Changes vertical slice); M2–M21 closed. Core engineering &
infrastructure doctrine codified (D-059). No milestone in progress — **STOP and await the next
milestone-opening brief** (expected: design-customer data-volume / live-operations readiness) before
beginning the next slice · updated 2026-09-10_

## Milestone 22-F — CLOSED 2026-09-10 (minimal customer access + seed-free onboarding)

**Authorized** by the M22-F work order; **CLOSED** 2026-09-10. Attaches a real authenticated identity to the
previously-deferred (D-048/D-057/D-058) `access_check` seam — the smallest serious access model that closes
the design-customer access P0, **without enterprise IAM**. **Authentication** (`pyrnova/access.py`): a
high-entropy bearer credential `Authorization: Bearer <credential_id>.<secret>` (256-bit CSPRNG secret;
public `cred_<hex>` id embedded → O(1) lookup); append-only `credentials` stream (PG mirror `credential`);
only a salted one-way hash persisted (plaintext shown once, unrecoverable); constant-time compare;
revocation = append-only closure that fails auth immediately. **Actor ≠ tenant** (`AuthContext`;
customer-role scoped to one tenant, operator-role internal) so a later OIDC/SSO layer replaces only
`authenticate()`. **Server-enforced tenant isolation, fail closed** (`ops_server.py`): the customer comes
from the credential, never a request param/dropdown — a forged `?customer=` is a hard 403; per-request
thread-local context + route levels (PUBLIC/CUSTOMER/GLOBAL/OPERATOR) + defense-in-depth `access_check`.
**Customer enumeration eliminated** — a customer's `/api/customers` returns only itself; the all-tenant
listing is operator-only. **Remote binding + operator separation**: `AccessPolicy` forces auth ON for any
non-local bind / `PYRNOVA_REQUIRE_AUTH` / any provisioned credential (local-no-credentials stays dev, never
silently for remote); the operator surface + `/console` are local-bind only (404 remotely), production edge/
TLS assumed in front. **Frontend**: Access gate (`ops_web/access.{js,css}`), sessionStorage credential,
`Pyrnova.authFetch` bearer wrapper (→ gate on 401), Sign Out; the customer **dropdown is removed** — the
authenticated org is shown, no tenant switching; overlay uses the authenticated customer; every boundary is
server-enforced. **Seed-free onboarding** (`pyrnova/onboarding.py` + CLI `pyrnova customer|watch|credential`)
reuses the M22-B customer/watchlist model + M22-D deterministic resolution (EXACT/PROBABLE-confirm/
AMBIGUOUS-never/UNRESOLVED-never-fabricate) + unchanged M22-C fan-out; a new watch never backdates relevance
(§52, tested). Additive only: `scoring_v1`/`fit.py`/`replay.py`/opportunity engine/severity bands and frozen
corpora byte-identical; M22-A→E read/API compatible. Full suite **615 passed** (was 571; +44 M22-F). Spec:
`docs/specs/M22F_MINIMAL_ACCESS_ONBOARDING.md`. See D-061. No further M22-F action.

## Milestone 22-E — CLOSED 2026-09-10 (opportunity Material Changes: product no longer threat-only)

**Authorized** by the M22-E work order (which first codified the binding engineering & infrastructure
doctrine, D-059); **CLOSED** 2026-09-10. A WIRING/MATERIALIZATION milestone — **not** a new opportunity
engine. Closes the design-customer readiness P0 that the customer-facing product was threat-only. Root
cause: the read model (`build_material_changes`) and the M22-C fan-out both already consumed an
`opportunities` stream, but the demo seed produced only threats — there was never any opportunity data to
show. M22-E materializes REAL, evidence-backed opportunities through the SAME deterministic, customer-
scoped, point-in-time, isolated path as threats. Authoritative source: the existing `detect_recompetes`
engine (`pyrnova/engines/recompete.py`) → existing `Opportunity` model → existing global `opportunities`
stream. Real evidence: Torch's own archived USAspending awards → 6 deterministic `recompete_expiry`
opportunities (DIRECT_SUBJECT; $100M floor, 540-day window, pinned 2026-09-01 scan). Deterministic
identity `opp_<hash(award_id, kind, subject_ref)>`. Two genuine defects fixed: `_opportunity_change` now
carries the canonical `subject_ref`/`subject_name` distinct from the tenant `customer_id` (DIRECT_SUBJECT
relevance + investigation links resolve), and opportunities are read from `mc_store` consistently with
threats/fan-out (one canonical pattern). Observed vs assessed kept separate (known contract value is
OBSERVED, materiality UNKNOWN); temporal truth holds (hidden before the scan date; expired → no active
candidate); M22-B lifecycle + M22-C storage reused unchanged; UNRESOLVED outcome first-class; investigation
links reach `co_torch` + the real PIID. Frontend added only value/deadline distinctions (already rendered
OPPORTUNITY). §56 copy fix names the affected entity. **Correction of a prior stale implication:**
opportunity/threat symmetry was NOT shipped to customers before M22-E — the machinery existed and the read
model supported it, but no opportunity was materialized into the product until now. Additive only; frozen
components byte-identical; threat/monitoring behavior unchanged. Full suite **571 passed** (was 557; +14).
See D-060, `docs/specs/M22E_OPPORTUNITY_MATERIAL_CHANGES.md`.

## Milestone 22-D — CLOSED 2026-09-10 (company/program investigation + deterministic entity search)

**Authorized** by the M22-D work order; **CLOSED** 2026-09-10. Completes the first investigation path
beneath a Material Change: MATERIAL CHANGE → AFFECTED COMPANY/PROGRAM → INVESTIGATION PAGE (related
intelligence, relationships, evidence, history, gaps) and DETERMINISTIC SEARCH → ENTITY/PROGRAM
RESOLUTION → INVESTIGATION PAGE. New `pyrnova/investigation.py`: an `IntelligenceEstate` read projection
built deterministically, point-in-time, from the existing global streams (`threats`/`propagated_threats`/
`opportunities`/`relationships`) reusing the shared `material_changes` normalizers so the investigation
view never diverges from the feed; `search()` resolving in fixed order (exact identifier → exact
name/alias → scored partial) to EXACT/PROBABLE/AMBIGUOUS/UNRESOLVED — exact identifiers by dictionary
lookup, **never an LLM** (verified by a poison test); `company_intelligence()`/`program_intelligence()`
page projections. Canonical identity reused, not re-invented (§10): identifiers read from structured
provenance only (`co_uei_` ref shape, `SUBSIDIARY_OF` hop provenance, and `uei:`/`cik:`/`cage:`/`lei:`
tokens on a *direct* single-subject threat); missing identifiers stay missing; `_merge_ident` never
overwrites an asserted value. Reversible resolution (§11): search reads/classifies, never writes a merge.
Global vs customer boundary (§12/§23): pages are global and carry no customer context by default; an
authorized `customer` adds a separately-keyed `customer_context` overlay via the M22-C `access_check`
seam (unauthorized → HTTP 403), never folding private relevance into global truth or leaking across
customers (direct negative tests). Temporal truth (§7/§19): estate + sections reconstructed at `as_of`;
relationship `valid_from`/`valid_to` respected; no future/outcome leakage. Read path: `OperatorConsole`
gained `search`/`company_intelligence`/`program_intelligence` + an `investigation` link block on every
Material Change (affected company/program/related entities — the customer never copies an identifier).
API: `GET /api/search`, `GET /api/company?ref=`, `GET /api/program?key=`. Frontend: restrained
`investigation.{html,js,css}` (search + company + program, one asset trio routed by path) linked from the
Material Changes masthead and per-card. CLI: `pyrnova search`. Additive only — `scoring_v1`/`fit.py`/
`replay.py`/severity bands and frozen corpora byte-identical; M22-A/B/C read/API behavior compatible.
Real-evidence demo (no live calls): `co_saic`/UEI `KMSLVW1MZWU9`/UEI `YR7CLZFGCM95`/PIID `47QFSA20F0057`
all resolve EXACT; `DAP Construction Management` resolves AMBIGUOUS across the real child and its native-id
parent (two Acmes → two Acmes). Full suite **557 passed** (was 532; +25 M22-D). Spec:
`docs/specs/M22D_INVESTIGATION_SEARCH.md`. See D-058. No further M22-D action.

## Milestone 22-C — CLOSED 2026-09-10 (per-tenant persisted Material Change streams + production read path)

**Authorized** by the M22-C work order; **CLOSED** 2026-09-10. Closes the M22-A/B storage seam: a relevant
global change is now MATERIALIZED into durable, per-customer state, and ordinary reads serve that state
instead of re-projecting the shared global streams. New `pyrnova/customer_material_changes.py`
(`CustomerMaterialChange` append-only VERSION; `fan_out`/`rebuild_customer`/`version_history`/
`_latest_versions`; content-hash dedupe; customer-scoped JSONL streams `customer_material_changes` and
`fanout_runs`; production mirror `customer_material_change`/`fanout_run` in `db/schema.sql`).
`SOURCE_KINDS = threat|propagated_threat|opportunity`; version `change_kind = initial|assessment|outcome`.
Truth-model (D-057): global truth stays global and is never duplicated as customer-owned truth nor mutated
by a customer (fan-out writes ONLY the customer-scoped streams; the global `threats` stream is byte-identical
after a run); a customer record stores REFERENCES (`source_refs`) + a compact `assessment_snapshot` +
relevance basis + first-seen times, never authoritative prose or copied evidence; identity is
`(customer_id, material_change_id)` where `material_change_id` IS the source intelligence id (the M22-B
review-action linkage unchanged), storage id `cmc_<hash(customer, change, version)>`; three distinct
first-seen times (`intelligence_observed_at` / `first_relevant_at` = max(observed, matching-config
effective_from) / `delivered_at`), never collapsed, immutable across versions; deterministic, idempotent,
replayable, point-in-time fan-out via the SAME `build_material_changes` read model (persisted set never
diverges from the on-the-fly relevant set); an assessment change appends a new version, a later outcome
appends an `outcome`-kind version preserving prior assessment snapshots; rebuild is idempotent and never
erases the separate customer review lifecycle; per-customer/per-item failure isolation with a structured
observability report appended to `fanout_runs`. Read path: `OperatorConsole` gained an OPTIONAL `cmc_store`
(first-seen overlay + `materialized` count; `None` ⇒ exactly M22-A/B, fully backward compatible) and an
OPTIONAL `access_check` seam (§15) surfacing `PermissionError` as HTTP 403 (authentication itself deferred,
D-048). The running product no longer needs the demo: the server runs `fan_out()` at startup and `pyrnova
fanout` is the continuous-operations CLI. API: `POST /api/fanout`, `GET /api/material-changes/{id}/versions
?customer=<id>`. Additive only — `scoring_v1`/`fit.py`/`replay.py`/severity bands and frozen corpora
byte-identical; M22-A/B read/API behavior compatible. Full suite **532 passed** (was 512; +20 M22-C). Spec:
`docs/specs/M22C_CUSTOMER_MATERIAL_CHANGE_STREAMS.md`. See D-057. No further M22-C action.

## Milestone 22-B — CLOSED 2026-09-10 (persisted customer intelligence + Material Change lifecycle)

**Authorized** by the M22-B work order; **CLOSED** 2026-09-10. Removes the M22-A demo seam: customer
configuration is now PERSISTED and drives the read path. New `pyrnova/customers.py` (`CustomerProfile`,
`WatchlistEntry`, `ReviewAction`; append-only JSONL streams `customers`/`customer_watchlist`/
`customer_review_actions`; production mirror in `db/schema.sql`). Truth-model boundaries (D-056): global
vs customer-private (customer config/watchlists/relevance/review state never enter the global intelligence
graph); system assessment ≠ customer review state (append-only per-`(customer, change)` lifecycle
NEW/REVIEWED/MONITORING/INVESTIGATING/DISMISSED/RESOLVED never mutates the authoritative threat);
`customer_id`-keyed tenancy with cross-customer rejection; temporal config (`effective_from`/`valid_from`/
`valid_to`) with no retrospective watchlist leakage; outcome lineage via optional `outcome_ref`
(UNRESOLVED first-class); free-text refs preserved unresolved. Read path (`OperatorConsole`), API
(`/api/customers…`, `/api/material-changes/{id}/review[-history]`), and minimal frontend lifecycle actions
added behind the unchanged M22-A view. Demo (Torch, DAP) seeded into persisted structures by a
deterministic, idempotent seed in `examples/` (`pyrnova seed-customers`) — never hard-coded into runtime.
Additive only — `scoring_v1`/`fit.py`/`replay.py`/severity bands and frozen corpora byte-identical; M22-A
read/API behavior compatible. Full suite **510 passed** (was 492; +18 M22-B). Spec:
`docs/specs/M22B_PERSISTED_CUSTOMER_LIFECYCLE.md`. See D-056. No further M22-B action.

## Milestone 22-A — CLOSED 2026-09-09 (Material Changes vertical slice)

**Authorized** by the M22-A work order. First customer-facing productization slice: existing Pyrnova
intelligence → customer relevance → Material Change read projection → read API → Material Changes
frontend view. Bounded to one vertical slice; **not** all of M22. Additive only — `scoring_v1`/`fit.py`/
`replay.py`/severity bands and frozen corpora unchanged; no engine dispositions altered. Spec:
`docs/specs/M22A_MATERIAL_CHANGES.md`. Governed by `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` and D-041.
Deterministic relevance only (no LLM relevance agent); observed-vs-assessed preserved end to end;
point-in-time truth (`available_at <= as_of`) enforced in the read path; demo uses real archived evidence
(M21 termination, M19 SAIC→Torch), no fabrication, no unnecessary live calls. See D-055.

## M22 direction (Phase 1 productization) — direction set, NOT yet authorized

The next phase is **customer-facing Phase 1 productization** for the federal-contractor wedge, governed
by `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` (customer ≈ $50M–$300M defense/industrial/technology/
engineering/infrastructure; dominant question "What materially changed since I last looked?"; Material
Changes as dominant UX; dossier/search supporting; graph mostly hidden; explicit non-goals durable;
finishability rule binding). Direction is authoritative (D-046, D-051); **this does not authorize
implementation.** Do not begin M22 build until this document opens the milestone with acceptance
criteria. Before any M22 work, complete the `AGENTS.md` start-of-work check.

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

1. M2–M21, M22-A, M22-B, M22-C, and **M22-D CLOSED** — no milestone in progress; **STOP and await the next
   brief** (per the M22-D work order, do not automatically begin the next M22 slice).
2. **M22 productization in progress across bounded slices:** M22-A (Material Changes read model), M22-B
   (persisted customer intelligence + Material Change lifecycle), M22-C (per-tenant persisted Material
   Change streams + production read path), and M22-D (company/program investigation pages + deterministic
   entity search) are closed. Candidate next slices (each needs a milestone-opening brief before build):
   broad natural-language search on the M22-D deterministic substrate (NATURAL LANGUAGE → STRUCTURED QUERY
   → DETERMINISTIC RETRIEVAL); customer-contributed private context (documents/notes) on the ready
   private/global boundary; authentication attached to the existing `access_check`/`actor`/`customer_id`
   seam; first-class evidence-lineage independence. Explicit Phase 1 non-goals (D-048) stay
   deferred/customer-gated. Source breadth, outcomes, calibration, and relationship coverage keep
   accumulating in parallel.
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
