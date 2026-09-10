# Pyrnova current state

_Verified 2026-09-10 in `~/Documents/Pyrnova` on `main` (M22-F CLOSED — minimal customer access + seed-free
onboarding: credential/authenticated-actor/server-enforced tenant isolation; M22-E CLOSED — opportunity
Material Changes, the product is no longer threat-only; M22-D CLOSED — company/program investigation pages +
deterministic entity search; M22-C CLOSED — per-tenant persisted Material Change streams + production read
path; M22-B CLOSED — persisted customer intelligence + Material Change lifecycle; M22-A CLOSED — Material
Changes vertical slice; M2–M21 CLOSED). Core engineering & infrastructure doctrine codified (D-059). Full
suite **615 passed**._

> **M22-F minimal customer access + seed-free onboarding (2026-09-10, CLOSED).** Attaches a real
> authenticated identity to the previously-deferred (D-048/D-057/D-058) `access_check` seam — the smallest
> serious access model that closes the design-customer access P0, without enterprise IAM. Credential =
> `Authorization: Bearer <credential_id>.<secret>` (256-bit CSPRNG secret; only a salted one-way hash
> persisted, plaintext shown once; constant-time compare; append-only revocation closure) →
> `AuthContext` (actor ≠ tenant; customer-role scoped to one tenant, operator-role internal). Tenant
> isolation is SERVER-enforced and fails closed: the customer comes from the credential, never a request
> param/dropdown — a forged `?customer=` is a hard 403; customer enumeration is eliminated (a customer's
> `/api/customers` returns only itself; `/api/me` shows the org). `AccessPolicy` forces auth ON for any
> non-local bind / `PYRNOVA_REQUIRE_AUTH` / any provisioned credential; the operator surface + `/console`
> are local-bind only (404 remotely), production edge/TLS assumed in front. Frontend: Access gate,
> sessionStorage credential, `Pyrnova.authFetch`, the customer dropdown removed (authenticated org shown, no
> switching). Seed-free onboarding (`pyrnova/onboarding.py` + CLI `pyrnova customer|watch|credential`)
> reuses the M22-B customer/watchlist model + M22-D deterministic resolution + unchanged M22-C fan-out; a
> new watch never backdates relevance. Additive only; M22-A→E compatible. Full suite **615 passed** (was
> 571; +44). SSO/SAML/SCIM/MFA/RBAC/billing/audit-export/SOC-2 and production TLS explicitly DEFERRED
> (D-048); not claimed enterprise-grade. See D-061; `docs/specs/M22F_MINIMAL_ACCESS_ONBOARDING.md`.

> **M22-E opportunity Material Changes (2026-09-10, CLOSED).** The customer-facing product is no longer
> threat-only. WIRING/MATERIALIZATION only — no new opportunity engine: the read model and the M22-C
> fan-out already consumed an `opportunities` stream, but the demo seed produced only threats. M22-E
> materializes REAL opportunities through the SAME path as threats — the existing `detect_recompetes`
> engine (`pyrnova/engines/recompete.py`) over Torch's archived USAspending awards → 6 deterministic
> `recompete_expiry` opportunities (DIRECT_SUBJECT; $100M floor, 540-day window, pinned 2026-09-01 scan;
> byte-reproducible). Deterministic identity `opp_<hash(award_id, kind, subject_ref)>`. Fixed two defects:
> `_opportunity_change` now carries the canonical `subject_ref`/`subject_name` distinct from the tenant
> `customer_id` (so DIRECT_SUBJECT relevance + investigation links resolve), and opportunities are read
> from `mc_store` consistently with threats/fan-out. Observed vs assessed kept separate (known contract
> value OBSERVED, materiality UNKNOWN); temporal truth holds (hidden before scan date; expired → no active
> candidate); M22-B lifecycle + M22-C storage + M22-D investigation links reused unchanged; UNRESOLVED
> outcome first-class. DAP has no active recompete and honestly stays threat-only (proving isolation).
> Frontend added only value/deadline distinctions beside THREAT. §56 copy fix names the affected entity.
> Additive only; frozen components byte-identical. `tests/test_m22e_opportunity.py` (+14). See D-060,
> `docs/specs/M22E_OPPORTUNITY_MATERIAL_CHANGES.md`.

> **M22-D company/program investigation + deterministic entity search (2026-09-10, CLOSED).** Completes the
> first investigation path beneath a Material Change: MATERIAL CHANGE → AFFECTED COMPANY/PROGRAM →
> INVESTIGATION PAGE and DETERMINISTIC SEARCH → ENTITY/PROGRAM RESOLUTION → PAGE. New
> `pyrnova/investigation.py`: an `IntelligenceEstate` computed read projection (same pattern as
> `build_material_changes` — not a second persisted truth system) built deterministically, point-in-time,
> from the existing global streams and reusing the shared `material_changes` normalizers so the
> investigation view never diverges from the feed; `search()` resolving in fixed order (exact identifier →
> exact name/alias → scored partial) to EXACT/PROBABLE/AMBIGUOUS/UNRESOLVED — exact identifiers by dictionary
> lookup, **never an LLM** (poison-tested); `company_intelligence()`/`program_intelligence()` page
> projections. Canonical identity reused, not re-invented: identifiers read from STRUCTURED provenance only
> (`co_uei_` ref shape; `SUBSIDIARY_OF` hop provenance; `uei:`/`cik:`/`cage:`/`lei:` tokens on a *direct*
> single-subject threat); missing identifiers stay missing; two same-named entities are surfaced as two
> (AMBIGUOUS), never merged; search reads/classifies and never writes a merge (reversible resolution).
> Pages are GLOBAL and carry no customer context by default; an authorized `customer` adds a
> separately-keyed `customer_context` overlay via the M22-C `access_check` seam (unauthorized → HTTP 403),
> never folding private relevance into global truth nor leaking across customers. Temporal truth: estate +
> sections reconstructed at `as_of`; relationship `valid_from`/`valid_to` respected; no future/outcome
> leakage. Sparse intelligence stated honestly (no UEI/CAGE/CIK, ownership unresolved); evidence referenced,
> never copied. `OperatorConsole` gained `search`/`company_intelligence`/`program_intelligence` + an
> `investigation` link block on every Material Change (affected company/program/related — no id copying).
> API adds `GET /api/search`, `GET /api/company?ref=`, `GET /api/program?key=`; restrained
> `investigation.{html,js,css}` (search + company + program, one asset trio routed by path) linked from the
> Material Changes masthead + per-card; CLI `pyrnova search`. **Additive only** —
> `scoring_v1`/`fit.py`/`replay.py`/severity bands and frozen corpora byte-identical; M22-A/B/C read/API
> compatible. Real-evidence demo (no live calls): `co_saic`/UEI `KMSLVW1MZWU9`/UEI `YR7CLZFGCM95`/PIID
> `47QFSA20F0057` resolve EXACT; `DAP Construction Management` resolves AMBIGUOUS across the real child and
> its native-id parent. Full suite **557 passed** (was 532; +25 in `tests/test_m22d_investigation.py`).
> Spec: `docs/specs/M22D_INVESTIGATION_SEARCH.md`. See D-058.

> **M22-C per-tenant persisted Material Change streams + production read path (2026-09-10, CLOSED).** Closes
> the M22-A/B storage seam: a relevant global change is now MATERIALIZED into durable, customer-scoped state
> and ordinary reads serve that state instead of re-projecting the shared global streams. New
> `pyrnova/customer_material_changes.py` (`CustomerMaterialChange` append-only VERSION;
> `fan_out`/`rebuild_customer`/`version_history`/`_latest_versions`; content-hash dedupe; customer-scoped
> JSONL streams `customer_material_changes`/`fanout_runs`; production mirror
> `customer_material_change`/`fanout_run` in `db/schema.sql`). Global truth stays global — fan-out writes
> ONLY the customer-scoped streams and never mutates the intelligence graph (the global `threats` stream is
> byte-identical after a run); a customer record stores REFERENCES (`source_refs`) + a compact
> `assessment_snapshot` + relevance basis + first-seen times, never authoritative prose. Identity is
> `(customer_id, material_change_id)` where `material_change_id` IS the source intelligence id (the M22-B
> review-action linkage unchanged); three distinct first-seen times
> (`intelligence_observed_at`/`first_relevant_at`/`delivered_at`) are never collapsed and immutable across
> versions. Fan-out is deterministic, idempotent, replayable, and point-in-time via the SAME
> `build_material_changes` read model (persisted set never diverges from the on-the-fly relevant set); an
> assessment change appends a new version and a later outcome appends an `outcome`-kind version preserving
> prior snapshots; rebuild is idempotent and never erases the separate customer review lifecycle;
> per-customer/per-item failure isolation with a structured report appended to `fanout_runs`. `OperatorConsole`
> gained an OPTIONAL `cmc_store` (first-seen overlay + `materialized` count; `None` ⇒ exactly M22-A/B, fully
> backward compatible) and an OPTIONAL `access_check` seam (HTTP 403; authentication deferred, D-048). The
> running product operates the persisted path: the server runs `fan_out()` at startup and `pyrnova fanout`
> is the continuous-operations CLI; API adds `POST /api/fanout` and
> `GET /api/material-changes/{id}/versions?customer=<id>`. **Additive only** —
> `scoring_v1`/`fit.py`/`replay.py`/severity bands and frozen corpora byte-identical; M22-A/B read/API
> compatible. Full suite **532 passed** (was 512; +20 in `tests/test_m22c_customer_material_changes.py`).
> Spec: `docs/specs/M22C_CUSTOMER_MATERIAL_CHANGE_STREAMS.md`. See D-057.

> **M22-B persisted customer intelligence + Material Change lifecycle (2026-09-10, CLOSED).** Removes the
> M22-A demo seam: customer configuration is PERSISTED (`pyrnova/customers.py` — `CustomerProfile`,
> `WatchlistEntry`, `ReviewAction`; append-only JSONL streams `customers`/`customer_watchlist`/
> `customer_review_actions`; production mirror in `db/schema.sql`) and drives the read path. Customer
> config/watchlists/relevance/review state are **customer-private** and never enter the global
> intelligence graph; the customer lifecycle (NEW/REVIEWED/MONITORING/INVESTIGATING/DISMISSED/RESOLVED) is
> an append-only per-`(customer, change)` overlay that never mutates the authoritative system assessment;
> tenancy is `customer_id`-keyed with cross-customer rejection; profile/watch temporal semantics
> (`effective_from`/`valid_from`/`valid_to`) prevent retrospective watchlist leakage; a resolution may
> link an existing outcome (`outcome_ref`, UNRESOLVED first-class); free-text watch refs are preserved
> unresolved. `OperatorConsole` reads persisted context + overlays review state; API + minimal frontend
> lifecycle actions added behind the unchanged M22-A view. Demo (Torch, DAP) seeded into persisted
> structures by a deterministic idempotent seed in `examples/` (`pyrnova seed-customers`), not runtime
> hard-coding. **Additive only** — `scoring_v1`/`fit.py`/`replay.py`/severity bands and frozen corpora
> byte-identical; M22-A read/API compatible. Full suite **510 passed** (was 492; +18 in
> `tests/test_m22b_customers.py`). Spec: `docs/specs/M22B_PERSISTED_CUSTOMER_LIFECYCLE.md`. See D-056.

> **Post-M21 authority synchronization (2026-09-09, documentation only).** A repository-governance sync
> recorded the post-M21 strategic direction: the Phase 1 federal-contractor wedge and Material-Changes
> product loop (`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`), explicit non-goals and finishability/moat
> authority (D-044…D-051), the 2026-09-09 red team review and strategic data research
> (`docs/research/`), roadmap Phase-1 disposition labels, and agent anti-drift rules (`AGENTS.md`).
> **No product code, tests, scoring, corpora, or runtime state changed;** the 482-test M21 state stands.
> M22 direction is set but implementation is not yet authorized (see `02-EXECUTION.md`).

> **M22-A Material Changes vertical slice (2026-09-09, IN PROGRESS — first product slice).** New
> customer-facing read path: `pyrnova/material_changes.py` (Material Changes read model + deterministic
> customer relevance + `CustomerContext`); `OperatorConsole.material_changes`/`.customers`;
> `/api/material-changes` + `/api/customers`; a customer-facing Material Changes frontend served at `/`
> (`pyrnova/ops_web/material.{html,css,js}`; Operator Console moved to `/console`). Demo fixture
> `examples/material_changes_demo/` (two isolated customers, generated from real archived M19/M21
> evidence). OBSERVED vs ASSESSED kept separate; point-in-time enforced; evidence referenced not
> duplicated; customer-isolated. **Additive only** — `scoring_v1`/`fit.py`/`replay.py`/severity bands and
> frozen corpora byte-identical. Full suite **492 passed** (was 482; +10 in `tests/test_material_changes.py`).
> Spec: `docs/specs/M22A_MATERIAL_CHANGES.md`. See D-055.

## Milestone status

- **M21: CLOSED 2026-09-09.** Raw authoritative adverse event + economic relationship diversity +
  observable outcomes. Additive only (`scoring_v1`/`fit.py`/`replay.py`/severity bands and frozen
  corpora incl. `corpus_m20` byte-for-byte unchanged; additive edits to `adverse_events.py`/
  `relationships.py`/`threat.py`/`ops.py`/`config.py`/`sources/sec_edgar.py`; new `corpus_m21.json`).
  **Phase 0** landed the Product Language Authority (D-041) and strategic capability reconciliation +
  phase-control rule (D-042; roadmap areas 16–22). **SEC hardening**: configurable declared identity
  (`config.sec_user_agent`, never fabricated), authoritative access order (`SEC_ACCESS_ORDER`),
  discovery-vs-body separation, `full_submission_url` raw artifact + `fetch_full_submission`, accession
  dedupe (amendments preserved), and safe 403 (terminal, one call, no retry loop). **Flagship**: a real
  USAspending **terminate-for-convenience** (PIID `36C25726N0240`, VA Kerrville VAMC boiler replacement;
  mod `P00002`, action_type `F`, −$3,908,263.25, 2026-08-31) preserved as **raw response bytes** with
  sha256 provenance — upgrading M20's curated-only SEC extract. Deterministic exposure by recipient UEI
  `YR7CLZFGCM95`; HIGH-confidence `PROGRAM_CANCELLATION_OR_DELAY` (severity LOW by frozen $ bands). New
  economic relation **`SUBSIDIARY_OF`** grounded from the authoritative recipient hierarchy (child UEI
  `YR7CLZFGCM95` → parent UEI `KMSLVW1MZWU9`, native ids; self-parent filtered) — the first propagation
  relation outside the government-program graph — propagates the threat up to the parent (confidence
  HIGH→MEDIUM, never increasing). `corpus_m21` (6 cases) extends `corpus_m20` → **80/80 pass**: 55 direct
  / 19 propagated, 3 real relationship types, 16 unique pairs, 20 negatives, deterministic resolved-direct
  precision 0.9412 (N=17), 0 temporal leaks/explosions. Flagship later outcome honestly **UNRESOLVED**
  (event days old; no defensible later evidence within budget). ~16 keyless public-domain USAspending
  calls (one-time acquisition, 3 archival), 0 SEC/SAM. Full suite **482 passed**. Spec/evidence:
  `docs/specs/M21_RAW_TERMINATION_RELATIONSHIP_DIVERSITY.md`,
  `docs/replay/M21_RAW_TERMINATION_RELATIONSHIP_DIVERSITY.md`.

- **M20: CLOSED 2026-09-09.** Added a third observed family (`sec_corporate_adverse_event`) and a real
  non-subcontract propagation type (`COMPANY_TO_PROGRAM`). SAIC 10-K accession
  `0001571123-26-000029` reports $35M restructuring, impairment and exit costs → exact CIK
  deterministic exposure → HIGH/HIGH `CORPORATE_RESTRUCTURING` (observed/materialized) → active Army
  PIID `W31P4Q21F0095` via exact USAspending recipient-id/PIID evidence, degrading to MODERATE/MEDIUM.
  Propagation now enforces relationship `valid_from`/`valid_to` at catalyst time and retains complete
  source/join/validity/provenance per hop. `summarize_m20` reports relationship-type and severe-outcome
  selectivity. `corpus_m20` adds 8 cases → 74/74 pass: 51 direct / 17 propagated, 15 unique entity pairs,
  18 negatives, 17 resolved direct (precision 0.9412, N=17; median lead 337 days), 4 resolved propagated
  (precision 1.0, N=4 directional), zero temporal leaks/explosions/absence-derived false alerts. SEC raw
  filing retrieval: one attempted, HTTP 403, no retry; the retained attributable extract is identity-
  checked against the existing raw SEC submissions archive and explicitly is not called a raw body.
  Full suite **464 passed, 1 skipped**. Spec/evidence:
  `docs/specs/M20_GENERALIZED_ADVERSE_RELATIONSHIPS.md`,
  `docs/replay/M20_GENERALIZED_ADVERSE_RELATIONSHIPS.md`.

- **M19: CLOSED 2026-09-09.** Deterministic OBSERVED exposure + multi-family adverse-event validation.
  Additive only (`scoring_v1`/`fit.py`/`replay.py`/frozen corpora incl. `corpus_m18` byte-for-byte
  unchanged; additive edits to `adverse_events.py`/`threat.py`/`propagation.py`/`ops.py`; new
  `corpus_m19.json`). Proves a **REAL, archived, OBSERVED adverse event → DETERMINISTIC exposure →
  HIGH-confidence direct threat → real relationship → propagated threat**, and that this survives a
  **second adverse-event family**. **Second family** (`adverse_events.parse_usaspending_contract_modifications`):
  archived USAspending contract **deobligations** (negative `federal_action_obligation` on a specific PIID
  held by a specific recipient UEI) become OBSERVED `contract_modification` catalysts consumed by the
  existing `PROGRAM_CONTRACTION` engine — materially independent of the BIS/Federal Register export-control
  family. **Flagship deterministic chain**: a real deobligation (mod **P00256, −$5,152,916.35, 2024-05-06**)
  on SAIC's exact prime PIID **47QFSA20F0057** (SAIC UEI **MMLKPW9JLX64** is the recipient →
  `deterministic_native_id`/CONFIRMED incumbency) → **HIGH-confidence** PROGRAM_CONTRACTION (MODERATE
  severity = the >$5M magnitude) → propagated one hop to Torch on the SAME PIID via the real
  program-anchored edge (HIGH→MEDIUM, never increasing). **Deterministic authority** is durable on every
  threat (`threat.exposure_join_class ∈ {deterministic, inferred, candidate}`, retained across hops).
  **Deterministic identity is not a threat**: a materiality gate ($1M floor) rejects a routine −$31,616
  deobligation `IMMATERIAL`, a material deobligation on a different award the subject does not hold is
  `NO_EXPOSURE`, and a lapsed incumbency (`valid_to` < catalyst) is `EXPOSURE_ENDED` (temporal validity).
  `summarize_m19` reports deterministic-vs-inferred exposure/threat/outcome counts and multi-family
  selectivity; `propagated_outcome_calibration` grows resolved propagated **1 → 4** with outcome diversity
  (MATERIALIZED/MITIGATED/AVOIDED). `corpus_m19` (9 cases) extends `corpus_m18` → **66 cases all pass**.
  Merged metrics: **46 direct / 16 propagated** (no explosion, confidence never increases, max depth 2),
  **2 adverse-event families**, 7 observed-catalyst chains, **10 OBSERVED / 36 MODELED** direct, 79/13
  deterministic/inferred exposures, **2 REAL** observed-deterministic-HIGH direct threats, 14 unique pairs,
  16 negative cases; resolved outcomes **16** (precision **0.9375**, median lead **342.5 days**), resolved
  propagated **4** (precision 1.0), `false_alert_from_absence` 0. **3 live USAspending calls** (keyless,
  archived once); full suite **457 passed**. Spec `docs/specs/M19_DETERMINISTIC_EXPOSURE.md`; evidence
  `docs/replay/M19_DETERMINISTIC_EXPOSURE.md`.

- **M18: CLOSED 2026-09-09.** Independent relationship expansion + archived adverse catalysts. Additive
  only (`scoring_v1`/`fit.py`/`replay.py`/frozen corpora incl. `corpus_m17` byte-for-byte unchanged; new
  `adverse_events.py`; additive edits to `relationships.py`/`threat.py`/`propagation.py`/
  `threat_calibration.py`/`ops.py`). Proves a **REAL, archived, OBSERVED adverse event → real catalyst →
  real exposure → an INDEPENDENT real relationship → real propagated threat**. **Observed adverse-event
  family** (`adverse_events.parse_federal_register_adverse`): archived Federal Register BIS/Commerce
  export-control & Entity-List rules become first-class OBSERVED catalysts (source-native FR doc id, RIN,
  agency, publication date, archive hash, raw pointer); catalyst **authority** (OBSERVED vs MODELED/
  SYNTHETIC/PROBE) is durable on every `Threat.meta` and never relabels an old modeled fixture. **Two
  independent real chains** driven by the SAME real rule (FR 2026-17231, RIN 0694-AK49, 2026-08-24):
  Parsons→Torch (MDA `HQ085821C0015`) and Intuitive→Torch (Army `W31P4Q23FC001`) — **neither SAIC** —
  where the prime's incumbency is grounded 0-call from the authoritative sub-award PRIME fields
  (`relationships.exposed_prime_awards_from_subawards`) and the edge is program-anchored. Prime
  export-control exposure is INFERRED, so direct threats are MODERATE/MEDIUM and degrade to LOW/LOW one
  hop downstream (never increase). **Negative discipline**: the same rule yields NO threat with no
  evidenced exposure (`NO_EXPOSURE`); a real single-occurrence edge (NTSI) terminates; the 2026 rule is
  excluded at a 2026-01-01 cutoff. **Independence metric** (`relationships.independence_metrics`) +
  **direct-vs-propagated calibration** (`threat_calibration.propagated_outcome_calibration`). The new
  source feeds the SAME selectivity funnel; the Operations Panel gained a thin `adverse_catalyst_view`
  and catalyst authority in the network view. `corpus_m18` (11 cases) extends `corpus_m17` → **57 cases
  all pass**. Merged metrics: 41 direct / **12 propagated** across 12 chains (**3 observed-catalyst
  chains**, 11 unique company pairs, max depth 2, no explosion, confidence never increases, 1 cycle / 1
  duplicate / 1 weak termination), **5 OBSERVED / 36 MODELED** direct threats, **13 negative cases**;
  resolved outcomes **12 → 15**, confirmed precision **0.9333 over 15**, median lead **337 days**,
  `false_alert_from_absence` 0. **1 live Federal Register call** (keyless, archived once); full suite
  **445 passed**. Spec `docs/specs/M18_INDEPENDENT_ADVERSE_EVENTS.md`; evidence
  `docs/replay/M18_INDEPENDENT_ADVERSE_EVENTS.md`.

- **M17: CLOSED 2026-09-09.** Real relationship propagation + continuous threat operations. Additive only
  (`scoring_v1`/`fit.py`/`replay.py`/frozen corpora incl. `corpus_m16` byte-for-byte unchanged; new
  `relationships.py`; additive edits to `selectivity.py`/`scheduler.py`/`threat.py`/`threat_calibration.py`/
  `ops.py`). **Real relationship graph grounding** (`relationships.ground_subaward_edges`): archived
  USAspending sub-award bytes → 22 real `SUBCONTRACTOR_OF` edges (1 program-anchored deterministic, 11
  authoritative-repeat, 10 single-occurrence weak/terminating); a short local order number can never
  manufacture a false deterministic anchor. **Two real, deterministic propagation chains** — Torch is a
  repeat subcontractor to SAIC on the **same** prime awards SAIC holds (Prime-Award-ID matched): GSA
  `47QFSA20F0057` ($1.43B) → `PROGRAM_CONTRACTION` on SAIC → propagated one hop to Torch (HIGH/MEDIUM);
  Army `W31P4Q21F0095` ($825.8M) → `PROGRAM_CANCELLATION_OR_DELAY` → propagated to Torch. Severity/
  confidence degrade and never increase (proven per-threat); corpus edges are the same edges grounding
  derives from the archived bytes. **Continuous selectivity** (`selectivity.source_run_funnel` +
  `SourceScheduler.record_selectivity_run`/`selectivity_report`): the exposure→threat funnel persists per
  source run in the durable M12/M13 source-state doc (append-only, bounded, empty-safe) — not a second
  metrics store. **Threat quality over time** (`threat_calibration.threat_quality_over_time` +
  `threat.summarize_m17`): durable aggregates from append-only predictions + later outcomes (per-mechanism
  precision with denominators, source-family contribution, propagation quality). **Company threat network
  view** (`ops.company_threat_network_view`): direct + inbound-propagated + outbound-network threats for
  one company with relationship paths + outcome status. `corpus_m17` (11 new cases) extends `corpus_m16`
  → 35 → **46 cases all pass**. Merged metrics: 32 direct threats, **5 propagated across 4 chains (2
  real)**, 2 beneficiary opportunities, max depth 2 (no explosion), 0 cycles/duplicates; **resolved
  outcomes 5 → 12**, confirmed precision **0.9167 over 12** (one honest FALSE_ALARM), median lead **336
  days**, `false_alert_from_absence` 0. **0 live API calls**; full suite **428 passed**. Spec
  `docs/specs/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md`; evidence
  `docs/replay/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md`.

- **M16: CLOSED 2026-09-09.** Threat calibration + exposure-family expansion + real-stream selectivity +
  cross-company propagation. Additive only (`scoring_v1`/`fit.py`/`replay.py`/frozen corpora incl.
  `corpus_m15` byte-for-byte unchanged; additive edits to `threat.py`/`ops.py`; new modules
  `propagation.py`, `selectivity.py`, `threat_calibration.py`). **Three new evidence-safe mechanisms**
  (SUPPLIER_DEPENDENCY_DISRUPTION, TECHNOLOGY_SUBSTITUTION, GEOGRAPHY_FACILITY_DISRUPTION — 10 total),
  each rejecting the un-exposed case (NO_DEPENDENCY / VAGUE_TREND_NOT_EVIDENCE /
  OUTSIDE_EXPOSURE_GEOGRAPHY). **Real event-stream selectivity** (`selectivity.run_selectivity`): the
  19,365 real archived OFAC designations × 4 monitored companies → 4 weak candidates, **0 accepted, 0
  threats** (emission_rate 0.0; guarded test). **Bounded cross-company propagation**
  (`propagation.propagate_threats`): explicit edges only, `max_depth` 2, confidence/severity degrade and
  never increase, deterministic cycle prevention, duplicate collapse, per-hop provenance, beneficiary
  (SUBSTITUTE_FOR/COMPETES_WITH) opportunities — never industry-adjacency. **Calibration**
  (`threat_calibration`): detection/exposure/outcome quality axes, precision reported only with its
  denominator, an unresolved threat never counted false (`false_alert_from_absence` = 0). `corpus_m16`
  (18 new cases) extends `corpus_m15` via chain-merge → 35 cases all pass, own point-in-time replay.
  Merged metrics: 22 direct threats, 3 propagated (2 cases, max depth 2 — no explosion), 2 beneficiary
  opportunities; calibration precision 1.0 over **5 resolved** TRUE_THREAT (directional), unresolved-rate
  0.77, median lead time 306 days. Operations Panel gained `threat_propagation_view()` +
  `selectivity_view()`. No threat/propagation explosion; no temporal/secret leakage; **0 live API calls**.
  Full suite: **400 passed**. Spec `docs/specs/M16_THREAT_CALIBRATION_PROPAGATION.md`; evidence
  `docs/replay/M16_THREAT_CALIBRATION_PROPAGATION.md`.

- **M15: CLOSED 2026-09-09.** First-class threat intelligence + exposure graph — threat as a durable
  PEER of commercial consequence, not a negated opportunity or a generic alarm. Additive only
  (`scoring_v1`/`fit.py`/`replay.py`/frozen M4–M11 corpora byte-for-byte unchanged; only `models.py` and
  `ops.py` gained additive edits; new `pyrnova/threat.py`). New objects: `Exposure` (WHO/WHAT is exposed
  to WHAT, with `join_method`/`link_class` so a weak fuzzy-name resemblance is a CANDIDATE, never a
  CONFIRMED exposure), `Threat` (severity and confidence as **orthogonal ordinals**, never one magic
  number; UNKNOWN valid; deterministic identity; `dual_opportunity_ref`), and `ThreatRejection`
  (zero-threat is first-class). Engine (`threat.py`) implements **seven** evidence-safe mechanisms —
  SANCTIONS_EXPOSURE, INCUMBENT_DISPLACEMENT, PROGRAM_CONTRACTION, PROGRAM_CANCELLATION_OR_DELAY,
  REGULATORY_COMPLIANCE_EXPOSURE, ELIGIBILITY_OR_CERTIFICATION_RISK, CUSTOMER_CONCENTRATION — plus
  duality (`link_duality`, shared `catalyst_id`, no duplicated facts), a `company_threat_surface`
  (foundation for roadmap area 4), and append-only threat-outcome linkage (future-excluded; an unresolved
  threat is never auto-labelled a false alarm). Severity is a magnitude band of a KNOWN dollar figure (no
  invented probabilities); confidence is an ordinal from exposure link-class + catalyst strength.
  `corpus_m15.json` extends the frozen lineage with **17 threat cases** (own point-in-time replay;
  `scoring_v1` untouched): sanctions confirmed/dual/weak-reject/unknown, real Torch incumbency (award
  `W31P4Q21F0038`, $623M, `examples/real_evidence/`), recompete-not-a-threat, program cancellation +
  contraction, regulatory compliance, eligibility+dual, customer concentration, zero-threat, future
  exclusion, severity/confidence split, threat evolution + outcome. Metrics (directional): 11 threats /
  4 zero-threat rejections, 6 mechanism families exercised, severity {CRITICAL 2, HIGH 7, MODERATE 2}
  distinct from confidence {HIGH 7, MEDIUM 3, LOW 1}, 2 dual-sided, 15 CONFIRMED / 4 INFERRED exposures,
  2 weak candidates rejected, false_exposure_rate 0.0, temporal_leakage_violations 0. Sanctions cases run
  REAL linkage semantics against the committed illustrative OFAC fixture; `tests/test_m15_real_ofac.py`
  (guarded) proves the same code on the **19,365 real archived SDN designations**. Operations Panel gained
  a thin read-only `threat_operations()` view. No STRIKE/threat explosion; no secret leakage; no temporal
  leakage. Full suite: **373 passed**. Spec `docs/specs/M15_THREAT_INTELLIGENCE.md`; evidence
  `docs/replay/M15_THREAT_INTELLIGENCE.md`.

- **M14: CLOSED 2026-09-09.** Multi-source intelligence expansion + continuous operations. Five families
  now operational on real bytes across five distinct economic domains (USAspending, SAM, SEC EDGAR, OFAC,
  Federal Register); `sbir` adapter built + offline-validated but connectivity `blocked` (HTTP 403,
  provider maintenance) — the single documented residual, with a concrete retry path.
  Additive only — `scoring_v1`, `fit.py`, and frozen corpora byte-for-byte unchanged; the M12/M13
  ingestion primitives are reused without redesign (Workstream 2 finding). The source registry
  (`pyrnova/sources/registry.py`) became the durable manifest (family/signals/access/cadence/budget/
  reliability/status/priority/identifiers/links per source) and now declares **nine families across
  distinct economic domains**, adding `sbir` (federal R&D precursor) and `sanctions_ofac` (sanctions/
  trade exposure) as keyless, archive-first adapters (`pyrnova/sources/sbir.py`, `pyrnova/sources/ofac.py`).
  Two bounded connectivity probes (one per new source): `sanctions_ofac` → HTTP 200, one 5.68MB SDN bulk
  download → **19,365 real designations** parsed (archive-operational; bytes archived git-ignored,
  archive-once/replay-many); `sbir` → HTTP 403 (provider maintenance — status `blocked`, adapter validated
  offline). `pyrnova/cross_source.py` demonstrates two real cross-source
  chains reusing `chains.py`/`multisource.py`: **Chain A** SBIR→USAspending (Torch, anchored on the
  authoritative UEI `YA63J5PVEZE6` read from the recipient endpoint; 2 cross-family accepted joins,
  3 rejected weak joins, chain confidence 0.60, 2 independent sources, ~6.8-year R&D→procurement lead
  time), and **Chain B** SAIC SEC EDGAR + USAspending deterministic entity merge (3 families, 8 facts).
  The Operations Panel gained a thin family-mesh + cross-source-chains readout (unconfigured-branch
  contract preserved). Point-in-time truth, provenance, and weak-join rejection verified; no STRIKE
  explosion; no secret leakage. Spec `docs/specs/M14_MULTI_SOURCE_EXPANSION.md`, manifest
  `docs/specs/SOURCE_MANIFEST.md`, evidence `docs/replay/M14_MULTISOURCE_EXPANSION.md`. See the M14
  acceptance gate and closure decision in those docs and `06-HISTORY.md`.
- **M13: CLOSED 2026-09-09.** Controlled live operations + end-to-end production validation. M2 status
  was verified first (CLOSED, see below). Additive only — `scoring_v1`, `fit.py`, `control.py`,
  `source_state.py`, adapters, and frozen M4–M12 corpora all unchanged. The M12 scheduler gained poll
  cadence (`set_poll_interval`/`due`/`poll()`, `SKIPPED_NOT_DUE`; the gate governs only requests that
  would reach the network — a cache hit spends no poll), durable budget/`calls_made` in `health()`,
  throttle-tagged failures, and archive-failure resilience (a storage fault counts the spent call,
  engages backoff, never crashes/half-writes). `pyrnova/live_ops.py` adds the offline-safe live driver
  (`http_fetcher`, `LiveRunner` efficiency ledger, `operating_cost_report` — calls, never invented
  dollars); the Operations Panel folds in the call-cost view. **A deliberately tiny live run** against
  USAspending (public, keyless; budget of 2 calls set before testing) proved: 2 live calls archived with
  clean provenance and **zero credential leakage**; an identical repeat served from cache (call avoided);
  budget enforced (`SKIPPED_BUDGET`); **genuine process restart** recovered budget/checkpoint/circuit/
  dedupe and made **0 duplicate external calls** (new epoch resets); 50 live rows propagated
  source→normalize→detect→candidate→review with archived evidence IDs; selectivity **0 STRIKE / 19 WATCH
  / 11 REJECT** (no STRIKE explosion); temporal probe at a 2016 cutoff excluded 40/50 records (no
  leakage); a real `CompanyProfile` grounded from live bytes; throttle/circuit/archive-failure/malformed/
  budget faults covered by fault injection (no provider hammering). Full suite: 320 passed. See
  `docs/specs/M13_LIVE_OPERATIONS.md` and `docs/replay/M13_LIVE_OPERATIONS.md`.
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
- **M12: CLOSED 2026-09-09.** Durable source integration — scheduler/jobs (`pyrnova/scheduler.py`)
  composing `SourceStateStore` + `SourceControl` + registry + `EvidenceArchive` into an **offline-default**
  job runner. `run_job` resolves one point-in-time request through: operator-pause → durable
  dedupe/cache index (served from archive, no budget) → OFFLINE fixture replay (archived, no network) →
  OFFLINE skip → live authorize (budget reserve + circuit check) → fetch/archive/index. Live calls happen
  ONLY when a caller both opts a source into a live mode and supplies a `fetcher` — no network by
  omission. Durable budgets persist across restart within a `budget_epoch` (new epoch resets); backoff
  via `retry_metadata`; circuit breaker persisted and defers the next poll when open (`reset_breaker`
  control); checkpoint/resume per source; `health()`/`health_report()` operator view; operator controls
  pause/resume, mode override, breaker reset (all persisted). Lightweight Operations Panel extension:
  `OperatorConsole(source_state_dir=...).source_operations()` surfaces durable source health read-only and
  degrades gracefully when unconfigured. ACCEPTANCE never serves cached bytes. `control.py`,
  `source_state.py`, adapters, `fit.py`, and `scoring_v1` all unchanged; frozen M4–M11 corpora unchanged.
  Full suite: 298 passed, 1 skipped. No live calls. See `docs/specs/M12_SOURCE_INTEGRATION.md`.
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

M21 CLOSED (`docs/specs/M21_RAW_TERMINATION_RELATIONSHIP_DIVERSITY.md`,
`docs/replay/M21_RAW_TERMINATION_RELATIONSHIP_DIVERSITY.md`) — Pyrnova now takes a REAL adverse event
preserved from **raw** authoritative source bytes (a USAspending contract termination), resolves the
exposed entity deterministically (recipient UEI), propagates across a **genuinely economic relationship
outside the government-program graph** (`SUBSIDIARY_OF`, native-id parent hierarchy), preserves temporal
truth/provenance, and records the later outcome honestly (UNRESOLVED — the event is days old). SEC
ingestion is hardened (declared identity, authoritative access order, accession dedupe, safe 403).
**No milestone in progress; STOP and await the next brief.** The expected next direction is the strategic
pivot to customer-facing productization (Company Intelligence Dossier + Opportunity/Threat Surface +
universal entity search + fast read-optimized delivery — roadmap areas 16–18); do not begin it without
explicit authority. `scoring_v1`/`fit.py`/severity bands remain frozen absent a justified milestone.
Highest-value continued accumulation (parallel, non-blocking): grow real later propagated outcomes
(re-award probe of the terminated requirement once time passes), and add `CUSTOMER_OF`/`SUPPLIER_OF`/
`FACILITY_OF` relationship types where authoritative evidence supports each.

### Prior next action (retained for continuity)

M19 CLOSED (`docs/specs/M19_DETERMINISTIC_EXPOSURE.md`, `docs/replay/M19_DETERMINISTIC_EXPOSURE.md`) —
Pyrnova now proves a REAL, archived, OBSERVED adverse event with a **deterministic** (exact PIID + UEI)
exposure carrying a **HIGH-confidence** direct threat, propagated through a real relationship, and shows
the behavior survives a **second adverse-event family** (USAspending contract deobligation) that stays
selective. Deterministic identity alone is never a threat (immaterial/wrong-award/lapsed rejections). No
milestone in progress; await the next brief. `scoring_v1`/`fit.py` remain frozen absent a justified
milestone. Highest-value next grounding (see M19 limitations / roadmap): a real contract **termination**
(vs a magnitude-modest deobligation) on a monitored incumbent, a third adverse-event family
(WARN/facility or enforcement), relationship-TYPE diversity beyond `SUBCONTRACTOR_OF`, and growing the
resolved propagated-outcome set with real (not directional-probe) later outcomes.

### Prior next action (retained for continuity)

M18 CLOSED (`docs/specs/M18_INDEPENDENT_ADVERSE_EVENTS.md`,
`docs/replay/M18_INDEPENDENT_ADVERSE_EVENTS.md`) — Pyrnova now takes a REAL, archived, OBSERVED adverse
event (a Federal Register BIS export-control rule) and propagates it through TWO real company
relationships INDEPENDENT of SAIC↔Torch (Parsons→Torch, Intuitive→Torch), preserving an auditable chain
from source event to propagated threat, with observed-vs-modeled catalyst authority durable at every hop
and no alarm explosion. No milestone in progress; await the next brief. `scoring_v1`/`fit.py` remain
frozen absent a justified milestone. Highest-value next grounding (see M18 limitations / roadmap): a
*deterministic* observed exposure (a real counterparty of a BIS-listed entity, or a program-specific
cancellation/modification notice tied to a PIID), a second adverse-event family (WARN/facility or
program-cancellation), relationship-TYPE diversity beyond `SUBCONTRACTOR_OF`, and growing the resolved
propagated-outcome set beyond 1.

### Prior next action (retained for continuity)

M17 CLOSED (`docs/specs/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md`,
`docs/replay/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md`) — Pyrnova now follows a REAL economic relationship
graph (grounded from archived sub-awards), propagates threats across two real deterministic SAIC→Torch
chains without an alarm explosion, measures the selectivity funnel continuously as part of source
operation, and calibrates threat quality over time (resolved outcomes 5 → 12, precision 0.9167 with
denominator). No milestone in progress; await the next brief. `scoring_v1`/`fit.py` remain frozen absent
a justified milestone. See the M17 spec's limitations: one real company relationship (SAIC↔Torch)
grounds both chains; a second real company pair and real adverse-event feeds (BIS/WARN/enforcement) are
the highest-value next grounding (recorded in `05-BACKLOG.md` / roadmap).

### Prior next action (retained for continuity)

M15 CLOSED (`docs/specs/M15_THREAT_INTELLIGENCE.md`, `docs/replay/M15_THREAT_INTELLIGENCE.md`) — threat
is first-class, exposure is explicitly modelled, and both peer commercial consequence. No milestone in
progress; await the next brief. Roadmap area 1 is DELIVERED; areas 4 (company threat/opportunity surface)
and 10 (thesis evolution) now have M15 foundations (`company_threat_surface`, append-only threat state)
ready to build on when authorised. `scoring_v1`/`fit.py` remain frozen absent a justified milestone.

### Prior next action (retained for continuity)

M13 CLOSED (`docs/specs/M13_LIVE_OPERATIONS.md`, `docs/replay/M13_LIVE_OPERATIONS.md`). M2 CLOSED
(`2026-09-09T07:14Z`, hash `574813de…`). M10–M12 CLOSED. Controlled live USAspending operation is proven
end-to-end: only-needed external calls, restart/failure survival, no STRIKE explosion, strict temporal
truth, zero secret leakage, `scoring_v1` frozen.

Recommended next milestone (**M14 — multi-source continuous operation + operating-cost characterization**):
extend the M13 live proof from one source/one scenario to a small *scheduled loop* over 2–3 keyless
sources (add SEC EDGAR, then SAM now that M2 is closed) under a real per-source daily budget, and measure
a genuine day of operation (calls/source/day, new-records/call, calls-avoided/day) rather than a single
representative slice. No milestone is currently in progress; await the next brief. Live ingestion beyond
the archived M13 evidence still requires a separately justified LIVE-SAFE/ACCEPTANCE request and
provisioned keys — do not initiate without one.
