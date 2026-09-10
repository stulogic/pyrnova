# Pyrnova strategic capability roadmap

_Status: strategic roadmap authority · created 2026-09-09 · updated 2026-09-09_

## Purpose and authority

This document is the durable record of strategically material capabilities identified for Pyrnova but
not yet built. It exists so that nothing strategically material silently falls out of planning.

**This file is strategic roadmap authority only.** It is *not* implementation authority. It does not
authorize work, does not override any completed milestone, and does not change the authority precedence
in `00-INDEX.md`. Active work is authorized solely by `02-EXECUTION.md`; detailed contracts live in
`docs/specs/`; prioritized near-term work lives in `05-BACKLOG.md`. This roadmap sits above the backlog
in time horizon and below every operating authority in precedence.

### Governance rule (binding)

> Strategic capabilities recorded here may be prioritized, deferred, researched, superseded, or
> explicitly rejected — but they must **not** be silently dropped from Pyrnova planning without owner
> direction or an explicit documented architectural decision (recorded in `04-DECISIONS.md`).

Every future milestone-planning cycle **must consult this roadmap** and account for the items below:
carry forward, promote to `05-BACKLOG.md`/`02-EXECUTION.md`, or record a supersession/rejection with a
reason. A capability's status is one of: `RECORDED` (captured, not yet scheduled), `RESEARCHING`,
`IN-BACKLOG`, `IN-PROGRESS`, `DELIVERED`, `SUPERSEDED`, or `REJECTED`. Status changes are logged in the
change table at the end of this file and, when they reflect a durable decision, in `04-DECISIONS.md`.

## Differentiated center (must be preserved)

Pyrnova is an **autonomous opportunity + threat + economic-consequence intelligence system**. Its
differentiated loop is and remains:

> CHANGE → ECONOMIC CONSEQUENCE → OPPORTUNITY / THREAT → WHO CAN CAPTURE / LOSE VALUE → EVIDENCE →
> ACTION → OUTCOME.

Every capability below must build on Pyrnova's attributable, time-bounded **evidence graph** and its
point-in-time truth discipline. None of them may turn Pyrnova into a generic search or chat product.
Enterprise-search, company/market intelligence, document intelligence, alerting, portfolio monitoring,
APIs, and proprietary datasets are all reachable *on top of* the evidence graph — they must not replace
it.

## Long-term architecture guardrail (AlphaSense-class)

Pyrnova should be architected so it can mature into a credible long-term competitor for high-value
enterprise intelligence workflows currently served by AlphaSense-class platforms **without a
fundamental redesign** of its data / evidence / graph architecture. This does *not* mean cloning
AlphaSense or pursuing feature parity. It means: every foundational choice (evidence schema,
provenance, temporal model, entity linking, source archival, graph state) should preserve optionality
for broad enterprise search, company intelligence, market intelligence, transcript/document
intelligence, alerts, portfolio monitoring, public APIs, proprietary datasets, and workflow embedding —
as extensions of the evidence graph, never as a replacement stack bolted on later.

---

## Capability areas

Each area records: what it is, why it matters, the discipline that keeps it *Pyrnova* rather than
speculation, and current status.

### 1. First-class threat intelligence — `DELIVERED` (M15, 2026-09-09)

Threat becomes a first-class intelligence object, not merely "negative opportunity evidence." Model the
chain: **EXPOSURE → CATALYST → THREAT MECHANISM → AFFECTED ASSET / REVENUE / POSITION → PROBABILITY →
SEVERITY → TIME HORIZON → MITIGATION → EVIDENCE**. Threat classes to support: incumbent displacement,
budget reduction, cancellation, competitor encroachment, certification changes, sanctions/export
exposure, supply-chain dependency, input-cost shocks, customer concentration, geographic/facility
exposure, regulatory liability, technology substitution, buyer-priority changes, and funding moving
away from a company's capabilities. Discipline: a threat is only asserted from retained evidence with
explicit probability/severity/horizon; no unsupported alarm. Mirrors the opportunity path, reusing the
consequence engine (`catalysts.py`/mechanism taxonomy) rather than a parallel stack.

**Delivered in M15** (`docs/specs/M15_THREAT_INTELLIGENCE.md`): first-class `Exposure`/`Threat`/
`ThreatRejection` objects; an evidence-safe exposure graph; seven threat mechanisms; severity/confidence
as orthogonal ordinals; first-class zero-threat; duality; a company threat surface; threat-outcome
linkage.

**Advanced in M16** (`docs/specs/M16_THREAT_CALIBRATION_PROPAGATION.md`): three more exposure families
(supplier/technology/geography, 10 mechanisms); a **real event-stream selectivity** proof (19,365 OFAC
designations → 0 threats for benign companies); **bounded cross-company propagation** (a small network
effect: direct + indirect threats + beneficiary opportunities, cycle-safe and degrading); and a
**calibration framework** (detection/exposure/outcome quality with denominators; unresolved never
false). Carried-forward M15 items (a) partially done — supplier/technology/geography exercised;
commodity-input & procurement-vehicle still open; (b) done at OFAC scale; (c) framework built, precision
still on 5 resolved outcomes (needs volume); (d) still open; (e) still open.

**Newly surfaced in M16** (`RECORDED`): (f) seed a **real propagation case from archived sub-award/
teaming edges** (M10 Torch sub-awards) rather than illustrative edges; (g) **wire selectivity into the
live scheduler/live_ops** so the funnel is measured continuously under budget; (h) **threat-relevant
source families** (BIS/export-controls, WARN notices, facility/closure data) — deferred in M16 (none
needed; never add a source for count) but the natural next exposure-evidence expansion.

**Advanced in M17** (`docs/specs/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md`): (f) **DONE** — a real
relationship graph is grounded from archived sub-awards (`relationships.ground_subaward_edges`; edge
strength mapped honestly to propagation behavior) and drives **two real, deterministic SAIC→Torch
propagation chains** (Prime-Award-ID-anchored; no explosion; confidence never increases). (g) **DONE at
the scheduler layer** — the selectivity funnel is persisted per source run in the durable source-state
doc (`record_selectivity_run`/`selectivity_report`); a live per-source-budget run of it remains open.
(c) advanced — resolved outcomes grew 5 → 12 (precision 0.9167 with denominator); still needs real
volume. (h) still open (no source added — none needed). **Newly surfaced in M17** (`RECORDED`): (i) a
**second real company relationship** for an independent real chain (M17's two chains share the SAIC↔Torch
pair — needs archived prime-side exposure for another real prime, or a distinct prime↔sub pair); (j) a
**company threat network view** was delivered (`ops.company_threat_network_view`) as an M17 foundation
for area 4 below. These sit below active authority until a justified milestone.

**Advanced in M18/M19** (`docs/specs/M18_INDEPENDENT_ADVERSE_EVENTS.md`,
`docs/specs/M19_DETERMINISTIC_EXPOSURE.md`): (i) **DONE** — two independent real chains (Parsons→Torch,
Intuitive→Torch, M18). (h) **advanced** — a first real adverse-event feed (Federal Register BIS/Commerce
export controls, M18) and now a **second family** (USAspending contract deobligations, M19), each an
OBSERVED catalyst; WARN/facility, enforcement, and SEC-disclosure families remain open (add only when they
materially improve evidence). **New in M19**: a **deterministic** OBSERVED exposure (exact PIID + recipient
UEI) carrying a **HIGH-confidence** direct threat propagated to a real subcontractor, with durable
deterministic-vs-inferred authority on every threat and a materiality/temporal-validity gate so an exact
identifier alone is never a threat. (c) advanced — resolved outcomes 12 → 16 (direct precision 0.9375),
resolved propagated 1 → 4; still needs real (non-probe) later outcomes at volume. Still open: a real
contract **termination** (vs a magnitude-modest deobligation) and relationship-TYPE diversity beyond
`SUBCONTRACTOR_OF`.

**Advanced in M20** (`docs/specs/M20_GENERALIZED_ADVERSE_RELATIONSHIPS.md`): a third observed family
(`sec_corporate_adverse_event`) and the first real non-subcontract propagation type
(`COMPANY_TO_PROGRAM`) are exercised end to end. Relationship validity is now enforced at catalyst time
and full edge provenance survives propagation. Still open: a raw-archived source-native contract
termination/WARN closure, customer/supplier/subsidiary relationship diversity, and real later propagated
outcomes at scale.

**Advanced in M21** (`docs/specs/M21_RAW_TERMINATION_RELATIONSHIP_DIVERSITY.md`): the raw-archived
source-native **contract termination** is DELIVERED (a real USAspending terminate-for-convenience
preserved as raw response bytes with sha256 provenance), and **`SUBSIDIARY_OF`** — the first economic
relationship type outside the government-program graph — is grounded from the authoritative recipient
hierarchy (native UEIs) and exercised in propagation. Still open: `CUSTOMER_OF`/`SUPPLIER_OF`/
`FACILITY_OF` diversity and real later propagated outcomes at scale (the M21 flagship outcome is honestly
unresolved — a days-old event).

### 2. Negative-space intelligence — `RECORDED`

Model expected evidence that **fails to appear**. Examples: authorization without appropriation;
appropriation without implementation; funding without market engagement; incumbent activity
disappearing before a recompete; expected hiring disappearing; an expected procurement stage not
occurring; missing supplier capacity before a mandate deadline. Discipline: **absence becomes evidence
only when a defensible expectation model exists** (a modeled prior for what *should* have appeared, by
when). Never treat silence as signal without that model. Depends on proprietary history (area 14) for
calibrated expectation baselines.

### 3. Capital-flow mapping — `RECORDED`

Trace the full path: **political intent → authorization → appropriation → agency/program → recipient →
prime → supplier/subcontractor → facility → workforce → local/sector economic effects.** Preserve
amount, probability, timing, and provenance at each hop. Extends existing capital-chain resolution
(`chains.py`, `precursors.py`) downstream past the prime into supplier/facility/workforce/local effects
and upstream to political intent. Discipline: every hop is evidence-backed with confidence and temporal
ordering; inferred hops are auditable, never silently asserted.

### 4. Company opportunity surface — `RECORDED` (M15 foundation: `company_threat_surface`)

Continuously model "everything in the observable economy becoming more or less favorable to this
company," combining opportunities, threats, buyers, capabilities, incumbencies, geography, partners,
competitors, vehicles, regulation, and capital movement into one per-company surface. Potentially a
primary enterprise product. Builds on `company.py`/`fit.py` grounding + the evidence graph; it composes
existing objects rather than introducing a new source of truth.

### 5. Competitor intent inference — `RECORDED`

Infer competitor positioning from observable evidence: hiring, awards, facilities, filings,
partnerships, acquisitions, patents, procurement behavior, capital investment. Discipline: **explicit
confidence, never unsupported certainty**; inferences are auditable and reviewable (reuse the M6 review
queue pattern). Distinguish observed fact from inference.

### 6. Buyer-intent models — `RECORDED`

Learn observable buyer behavior: typical path from funding to solicitation, seriousness of RFIs,
procurement timing, preferred acquisition patterns, common delays, program-office behavior, and
precursor combinations associated with eventual spend. Goal: probabilistic buyer behavior and timing
intelligence (additional lead time). Depends on proprietary history (area 14) for calibration; feeds
buyer-intent priors into precursor scoring without altering frozen `scoring_v1` until a justified
milestone evaluates it.

### 7. Relationship / team-formation intelligence — `RECORDED`

Determine evidence-backed potential teams (e.g. A owns customer access, B supplies a missing
capability, C owns the required vehicle, D holds the incumbent position). Discipline: **do not invent
partnerships.** Explicitly distinguish an *existing* relationship (evidenced) from *potential strategic
complementarity* (inferred, confidence-scored). Extends entity predicates and TEAM posture already in
`fit.py`/graph.

### 8. Strategic scenario engine — `RECORDED`

Evidence-constrained what-if analysis: appropriation cut 20%, tariff expands, export restriction
broadens, program accelerates, regulation delayed, supplier exits market. Results traverse *known*
relationships in the evidence graph and explicitly state assumptions. Discipline: **must not become
generic LLM speculation** — every scenario result is constrained by, and cites, graph evidence and its
stated assumptions.

### 9. Contradiction detection — `RECORDED`

Detect disagreement among evidence sources (a filing says one thing, hiring suggests another, budget
says another, a procurement action contradicts guidance). Discipline: **preserve contradictions as
intelligence rather than silently resolving them.** Contradictions are retained, surfaced, and
provenance-linked, not auto-collapsed. Reinforces the "unknown stays unknown" doctrine.

### 10. Intelligence memory / thesis evolution — `RECORDED` (M15 foundation: append-only threat state + evolution cases)

Persist how an intelligence thesis evolves over time (weak WATCH → funding → buyer confirmation →
capability fit → PRIME → solicitation → award → observed outcome). Supports auditability, customer
explanation, historical calibration, and proof of lead time. Extends the append-only outcome-learning
lifecycle from M11 into a first-class, queryable thesis-history object.

### 11. Portfolio-level intelligence — `RECORDED`

Support "across all companies/assets I own or monitor, where are external events creating upside or
risk?" Users: PE, VC, lenders, holding companies, corporates, strategic investors, government
portfolios. Aggregates per-company surfaces (area 4) across a watched set; a strong enterprise wedge
beyond single-company Capture Radar. Builds on the same evidence graph and fit/threat objects.

### 12. Broad source expansion — `RECORDED` (partially in progress via milestone work)

Treat observation breadth as strategic infrastructure. Pyrnova eventually requires broad coverage
across: government procurement, spending, appropriations, legislation, regulation, grants, corporate
filings, company disclosures, labor, facilities, patents, trade, customs, sanctions, export controls,
energy, infrastructure, industrial policy, supply chains, critical minerals, logistics, recalls,
permits, state/local activity, commercial web change, and premium data where justified. Discipline:
**collect broadly, call sparingly, archive everything useful, replay many times**; every source still
passes the coverage/selectivity/provenance/replay/API-efficiency test in `M4_SOURCE_EXPANSION.md` and
the operating contract in `SOURCE_INGESTION.md`. Never add a source merely to raise the source count.
(M14 operationalizes a first broad multi-family expansion; the full breadth list remains roadmap.)

### 13. Customer-facing intelligence simplification — `RECORDED`

Internal machinery may be sophisticated; the customer experience must stay simple. Target: "Three
things changed overnight that materially affect you," with drill-down into evidence, mechanism, value,
confidence, timing, and recommended posture. Discipline: **do not expose internal complexity
unnecessarily.** A presentation/UX guardrail for all customer-facing surfaces; does not authorize a
frontend rebuild.

### 14. Proprietary history accumulation — `RECORDED` (ongoing operating discipline)

Treat every day of operation as creation of a proprietary asset. Preserve: raw historical
observations, source snapshots, entity evolution, graph states, rejected hypotheses, prediction states,
fit states, human adjudications, outcome states, thesis evolution, and timing/lead history. **Historical
state itself is a moat** (subject to the authority caveat: stored data is not itself proof of a moat;
the test is measurable predictive and commercial lift). This underpins areas 2, 6, and 10. Archive-first
ingestion and append-only outcome history already advance it; the roadmap requirement is to preserve
*all* the listed state classes durably, not only what current scoring consumes.

### 15. AlphaSense-class long-term architecture guardrail — `RECORDED`

See "Long-term architecture guardrail" above. Recorded explicitly as a capability-area obligation:
every foundational data/evidence/graph choice must preserve optionality for enterprise-class workflows
without a later fundamental redesign, while keeping Pyrnova's differentiated center intact.

### 16. Company Intelligence Dossier + Company Opportunity/Threat Surface — `RECORDED`

A per-entity dossier answering, from the evidence graph: what the company **is**, what it **does**, who
and what it **depends on**, what is **changing** around it, what **threatens** it, what **benefits** it,
what **may happen next**, and what **action / counterparties** are relevant. Includes profile-completeness
/ **intelligence-gap** measurement (what Pyrnova does not yet know about the entity) and rapid **on-demand
dossier creation** for entities not already stored. This is the presentation composition of area 4 (the
per-company surface) plus areas 1/3/5/10; it composes existing Threat/Exposure/Fit/Consequence/Relationship
objects and must not introduce a parallel source of truth. Expected first customer-facing product after M21.

### 17. Universal entity search + natural-language-assisted structured retrieval — `RECORDED`

Retrieve any entity deterministically by name, alias, CIK, UEI, CAGE, DUNS (where historically useful),
address, executive/person, program, contract/PIID, facility, geography, capability, or sector/industry.
Natural-language search operates as an **assisted structured retrieval / query-planning layer over the
same indexes** — never the only way to reach a deterministic entity, and never a substitute for
identifier lookup. Discipline: NL assistance plans queries against the evidence graph and read
projections; it does not invent entities or facts.

### 18. Read-optimized search/profile projections — `RECORDED` (M21 architectural guardrail)

Routine company lookup, identifier lookup, sector filtering, dossier opening, opportunity/threat lists,
relationship lists, and material-change views must render from **indexed, structured, read-optimized
projections** derived from the authoritative evidence graph — never from runtime graph reconstruction or
runtime LLM reasoning. Architecture: AUTHORITATIVE EVIDENCE / GRAPH → DERIVED READ PROJECTIONS → FAST
SEARCH / PROFILE DELIVERY. M21 builds no search layer but must not introduce structures that foreclose
this. Depends on **ingest-time classification** (sector/industry/capability/geography/event-family/
economic-mechanism/entity-type), computed durably at ingest, provenance- and confidence-aware,
multi-label, and temporally versionable — not recomputed per query.

### 19. Counterparty intelligence + multi-tier supply-chain reconstruction — `RECORDED`

Reconstruct supplier/customer/prime/subcontractor/parent/subsidiary/facility relationships into a
multi-tier economic dependency graph, and support supplier/customer/prime/substitution matching,
strategic dependency mapping, and dynamic commercial substitution. Extends areas 3 and 7 and the M15–M21
relationship families (`SUBCONTRACTOR_OF`, `COMPANY_TO_PROGRAM`, and M21's `SUBSIDIARY_OF`/`PARENT_OF`)
downstream/upstream. Discipline: every tier is evidence-backed with directionality, native identifiers,
confidence, and CONFIRMED/INFERRED distinction; a relationship is never inferred from name/industry
resemblance.

### 20. Economic blast-radius propagation + customer exposure fingerprints — `RECORDED` (M16–M21 foundation)

Given a real external event, propagate the economic consequence across evidenced relationships to compute
the affected set (the "blast radius") and per-customer economic-exposure fingerprints (which watched
entities are exposed, via which mechanism, to what magnitude, with what confidence and temporal validity).
Directly extends the bounded, degrading, cycle-safe propagation delivered in M16–M21. Discipline:
propagation traverses only evidenced edges valid at event time; confidence never increases; severity is
never mechanically inflated by graph distance or identity.

### 21. Standing intelligence requirements + event-triggered escalation + decay/anomaly — `RECORDED`

Standing per-customer intelligence requirements that watch the evidence stream, escalate on triggering
events, and apply **opportunity/threat decay** over time; plus **market anomaly detection** over the
observed stream. Extends the M12–M17 scheduler/selectivity/calibration operations and the append-only
outcome history. Discipline: escalation and anomaly are evidence-triggered, not model speculation; decay
is a documented function of time/evidence, not silent forgetting. **No autonomous action on threats** (a
roadmap boundary; decision-support options only, evidence-grounded).

### 22. Calibrated forecasting — `RECORDED`

Calibrated probability/timing forecasts (buyer behavior, lead time, materialization likelihood) **only
where empirical evidence supports them** and only after full-corpus evaluation, never altering frozen
`scoring_v1` without a justified milestone. Depends on proprietary history (area 14) and the resolved
outcome set reaching non-directional volume (M15–M21 grew resolved outcomes but samples remain small).
Discipline: no invented probability; a forecast is published only beside its calibration denominator.

### Combined-depth doctrine (binding on planning)

Pyrnova combines broad research depth with its own economic intelligence layer. The target is not merely
"find information about Company X" but "determine what Company X is, what it does, who and what it depends
on, what is changing around it, what threatens it, what benefits it, what may happen next, and what action
or counterparties may be relevant." Broad research depth serves the economic intelligence graph; it never
replaces it, and never turns Pyrnova into a generic search or chat product.

### Phase-control rule (binding on planning)

New capabilities discovered during development do not expand the current phase unless required for
correctness, safety, architectural integrity, or an existing acceptance criterion. Otherwise:
document → roadmap → defer. See D-042.

---

## Phase 1 disposition (2026-09-09)

The `RECORDED`/`DELIVERED` status above is the capability's build state. This table adds each area's
**Phase 1 disposition** so a future agent cannot mistake a longer-horizon capability for current scope.
Labels: **NEXT** (the expected next productization phase, still gated by `02-EXECUTION.md`), **LATER**
(sequenced after Phase 1), **CUSTOMER-GATED** (only if demonstrated Phase 1 customer value pulls it),
**DEFERRED** (explicit Phase 1 non-goal, D-048), **ONGOING** (operating discipline). Nothing here
authorizes implementation (D-042, D-047).

| Area | Capability | Phase 1 disposition |
|---|---|---|
| 1 | First-class threat intelligence | DELIVERED (M15–M21); Threat Intelligence surface is a Phase 1 product surface |
| 2 | Negative-space intelligence | LATER |
| 3 | Capital-flow mapping | LATER (downstream supplier/facility/workforce hops CUSTOMER-GATED) |
| 4 | Company opportunity/threat surface | **NEXT** (Opportunity/Threat Intelligence surfaces) |
| 5 | Competitor intent inference | DEFERRED (strategic-intent prediction) |
| 6 | Buyer-intent models | DEFERRED (buyer-intent prediction) |
| 7 | Relationship / team-formation intelligence | LATER |
| 8 | Strategic scenario engine | LATER |
| 9 | Contradiction detection | LATER (supports "explicit unknowns"; CUSTOMER-GATED depth) |
| 10 | Intelligence memory / thesis evolution | **NEXT** foundation (historical intelligence; candidate moat, D-049) |
| 11 | Portfolio-level intelligence | DEFERRED (advanced portfolio modelling) |
| 12 | Broad source expansion | CUSTOMER-GATED — global event detection, commodities, maritime, aviation, broad social-media, state/local procurement, broad premium feeds are **DEFERRED** Phase 1 non-goals (D-048); pull sources by demonstrated value only |
| 13 | Customer-facing simplification | **NEXT** — Material Changes as dominant UX (D-046) |
| 14 | Proprietary history accumulation | ONGOING (top candidate moat, D-049) |
| 15 | AlphaSense-class architecture guardrail | ONGOING (preserve optionality; do not build breadth) |
| 16 | Company Intelligence Dossier + surface | **NEXT** — dossier is a *supporting* surface; graph mostly hidden (D-046) |
| 17 | Universal entity search + NL-assisted retrieval | **NEXT** — deterministic entity search is Phase 1; NL is assisted retrieval only, never the only path |
| 18 | Read-optimized projections + ingest-time classification | **NEXT** (fast deterministic rendering; AI after deterministic filtering) |
| 19 | Counterparty + multi-tier supply-chain reconstruction | DEFERRED — global multi-tier reconstruction and automated replacement-supplier claims are Phase 1 non-goals (D-048); conservative, evidence-qualified only |
| 20 | Blast-radius propagation + exposure fingerprints | LATER (M16–M21 foundation exists; customer-specific exposure history is a candidate moat) |
| 21 | Standing requirements + escalation + decay/anomaly | LATER; **no autonomous action** (DEFERRED non-goal) |
| 22 | Calibrated forecasting | LATER / CUSTOMER-GATED (only with calibration denominators; never invented probability) |

Additional durable Phase 1 non-goals not mapped to a single area (DEFERRED, D-048): comprehensive
private-company universe, complete beneficial ownership, global facilities completeness, complete
financial terminal, deep person intelligence, unrestricted autonomous agents, autonomous commercial
action, unnecessary graph-database migration, premature streaming infrastructure.

## Relationship to current authority

- Does not override `01-PROJECT-AUTHORITY.md`, `02-EXECUTION.md`, `03-CURRENT-STATE.md`,
  `04-DECISIONS.md`, `docs/specs/`, or any closed milestone.
- Sits alongside `05-BACKLOG.md`: the backlog holds prioritized near-term work; this roadmap holds the
  longer-horizon strategic capability set that milestone planning must not lose sight of.
- The locked doctrine in `01-PROJECT-AUTHORITY.md` (evidence-first, point-in-time truth, human-gated,
  scarce-call ingestion, Capture Radar as the active wedge, first $100k objective) governs *how* any of
  these capabilities may eventually be built.

## Change log

| Date       | Area(s) | Change                                              | Reference |
|------------|---------|-----------------------------------------------------|-----------|
| 2026-09-09 | 1–15    | Roadmap created; all 15 areas recorded (`RECORDED`) | Phase 0   |
| 2026-09-09 | 1       | Area 1 → `DELIVERED` (M15); 5 follow-on threat capabilities carried forward (`RECORDED`) | M15 |
| 2026-09-09 | 4, 10   | Noted M15 foundations (`company_threat_surface`; append-only threat state + evolution) | M15 |
| 2026-09-09 | 1       | M16 advanced area 1 (3 more families, live selectivity, propagation, calibration); 3 new follow-ons (f,g,h) recorded | M16 |
| 2026-09-09 | 1, 4    | M17 advanced area 1 (real relationship graph + 2 real propagation chains (f DONE), scheduler selectivity (g), calibration 5→12); company threat network view (area-4 foundation); follow-ons (i,j) recorded | M17 |
| 2026-09-09 | 1, 3    | M20 added SEC corporate adverse events, real company-to-program propagation, and catalyst-time edge validity | M20 |
| 2026-09-09 | 16–22   | M21 Phase 0 recorded areas 16–22 (dossier/surface, universal + NL-assisted search, read projections, counterparty/multi-tier supply chain, blast-radius + exposure fingerprints, standing requirements/decay/anomaly, calibrated forecasting) + combined-depth and phase-control doctrine | D-042 |
| 2026-09-09 | 1, 3, 19 | M21 added a raw-archived source-native contract **termination** and the `SUBSIDIARY_OF` economic relationship type (parent-hierarchy native ids); relationship-type diversity beyond `SUBCONTRACTOR_OF`/`COMPANY_TO_PROGRAM` | M21 |
| 2026-09-09 | 1–22 | Post-M21 authority sync: added **Phase 1 disposition** labels (NEXT/LATER/CUSTOMER-GATED/DEFERRED/ONGOING) so roadmap items cannot be mistaken for current scope; marked broad event/supply-chain/commodities/maritime/aviation/private-company/premium/autonomous items DEFERRED (D-048) | D-048, red team review |
