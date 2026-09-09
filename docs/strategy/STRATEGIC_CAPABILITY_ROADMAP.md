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

### 1. First-class threat intelligence — `RECORDED`

Threat becomes a first-class intelligence object, not merely "negative opportunity evidence." Model the
chain: **EXPOSURE → CATALYST → THREAT MECHANISM → AFFECTED ASSET / REVENUE / POSITION → PROBABILITY →
SEVERITY → TIME HORIZON → MITIGATION → EVIDENCE**. Threat classes to support: incumbent displacement,
budget reduction, cancellation, competitor encroachment, certification changes, sanctions/export
exposure, supply-chain dependency, input-cost shocks, customer concentration, geographic/facility
exposure, regulatory liability, technology substitution, buyer-priority changes, and funding moving
away from a company's capabilities. Discipline: a threat is only asserted from retained evidence with
explicit probability/severity/horizon; no unsupported alarm. Mirrors the opportunity path, reusing the
consequence engine (`catalysts.py`/mechanism taxonomy) rather than a parallel stack.

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

### 4. Company opportunity surface — `RECORDED`

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

### 10. Intelligence memory / thesis evolution — `RECORDED`

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

---

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
