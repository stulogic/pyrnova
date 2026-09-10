# Pyrnova Phase 1 product authority

_Status: canonical current-product authority · effective 2026-09-09 · informed by the 2026-09-09 red
team review and strategic data research (`docs/research/`)_

> **Authority level.** This is the current product/strategic authority for the Phase 1 (M22+)
> productization phase. In the authority hierarchy (`00-INDEX.md`) it sits with `01-PROJECT-AUTHORITY.md`
> as current strategic authority, above the milestone work order. It does not override
> `01-PROJECT-AUTHORITY.md`'s locked doctrine; it specializes it for Phase 1. It does **not** authorize
> implementation — `02-EXECUTION.md` alone authorizes active work.

## Long-term thesis (architectural direction, NOT Phase 1 scope)

Pyrnova aims to become **a continuously updated, historically auditable model of what external change
means economically to a specific organization.** The broader system may eventually span policy, capital,
procurement, regulation, corporate activity, supply chains, physical events, markets, geopolitics,
facilities, dependencies, opportunities, threats, and outcomes.

This is long-term direction. It is preserved so foundational choices keep optionality (see
`STRATEGIC_CAPABILITY_ROADMAP.md`, areas 15–22). **It is not authority to build any of it in Phase 1.**

## Current differentiated thesis

Pyrnova's differentiated product is **not** broad data aggregation, generic company research, generic AI
search, a knowledge graph by itself, dashboards, alerts by themselves, procurement search alone, global
event detection, or generic supply-chain mapping.

The differentiated thesis is the loop:

> **external change → customer-specific consequence → opportunity / threat / monitoring → evidence →
> review / action → outcome → learning.**

Pyrnova determines: what materially changed; why it affects *this particular* organization; what
evidence supports the conclusion; what remains uncertain; what merits investigation; and what eventually
happened.

## Phase 1 customer wedge (locked)

- **Initial customer:** US federal contractors.
- **Primary sectors:** defense, industrial, technology, engineering, infrastructure.
- **Working ideal customer:** ≈ **$50M–$300M revenue**, with lean BD/capture/strategy capacity,
  meaningful federal program exposure, several capabilities, multiple programs/pursuits, and
  insufficient analyst bandwidth for continuous monitoring.

This is a **launch wedge**, not a permanent constraint. Do not hard-code the architecture so other
markets become impossible later (`STRATEGIC_CAPABILITY_ROADMAP.md`, area 15). This band refines and
supersedes the earlier "~$20M–$250M" figure in older README copy (D-045).

## Phase 1 dominant customer question

**"What materially changed since I last looked?"**

## Phase 1 commercial test (competitive)

The Phase 1 test is not "Can Pyrnova also do procurement intelligence?" It is: **can Pyrnova repeatedly
tell an existing GovWin/GovTribe/equivalent customer something materially important their workflow missed
— early and clearly enough to change what they do?** Prefer design customers who already use an
incumbent; the evidence standard is **displaced spend**, and the governing question for every major
capability is "why would a rational customer already paying the incumbent switch to Pyrnova?" A weak
answer means the capability is not finished. Full competitive doctrine, domination standard, incumbent
map, and displacement metrics: `docs/strategy/COMPETITIVE_DOCTRINE.md` (D-052).

## Phase 1 product surfaces

The Phase 1 product should support:

- **Material Changes** (the dominant surface)
- **Customer Intelligence Profile**
- **Opportunity Intelligence**
- **Threat Intelligence**
- **Evidence**
- **Company / Program Intelligence** (the dossier — a supporting investigation surface)
- **deterministic entity search**
- **watchlists**
- **review / adjudication**
- **outcome tracking**
- **explicit unknowns**
- **historical intelligence**

## Required Phase 1 loop

```
EVENT
  → AFFECTED ENTITY / PROGRAM
  → CUSTOMER RELATIONSHIP
  → CONSEQUENCE
  → OPPORTUNITY / THREAT
  → EVIDENCE
  → REVIEW / ACTION
  → OUTCOME
```

The graph should **primarily support this experience**, not dominate the interface. The dossier is a
supporting investigation surface; the graph is predominantly hidden from the primary Material-Changes
workflow (D-046).

## Relationship to Capture Radar

Capture Radar (pre-RFP / recompete intelligence) remains the delivery vehicle and the proven engine
(M2–M21). Phase 1 productization organizes that engine around the Material-Changes loop for the federal-
contractor wedge. This is an evolution of framing, not a repudiation: closed-milestone history stands
(`06-HISTORY.md`), and `scoring_v1`/`fit.py`/severity bands remain frozen.

## Phase 1 explicit non-goals (durable; deferred / customer-gated)

The following are **not** Phase 1 scope and must not be built merely because research shows eventual
usefulness. They are deferred or customer-gated unless later real Phase 1 customer evidence changes
authority (recorded via a decision in `04-DECISIONS.md`):

- Dataminr-equivalent global real-time event detection
- broad social-media ingestion
- commodities intelligence
- maritime intelligence
- aviation intelligence
- global multi-tier supply-chain reconstruction
- automated replacement-supplier claims
- comprehensive private-company universe
- complete beneficial ownership
- global facilities completeness
- strategic-intent prediction
- buyer-intent prediction
- advanced portfolio modelling
- state / local procurement
- complete financial terminal
- deep person intelligence
- unrestricted autonomous agents
- autonomous commercial action
- broad premium-feed integration
- unnecessary graph-database migration
- premature streaming infrastructure

Preserve future architectural compatibility for these (do not foreclose them); do not implement them.

## Finishability rule (binding)

A missing capability may block the current phase **only if**: correctness requires it; safety requires
it; architectural integrity requires it; existing acceptance criteria require it; or a real Phase 1
customer cannot receive the promised Phase 1 decision value without it.

The following do **not** qualify: research curiosity; architectural elegance; theoretical future
usefulness; competitor feature parity; "while we are here"; an interesting new dataset; or an agent
identifying another potentially useful relationship/event/source.

Default handling of anything that does not qualify: **DOCUMENT → ROADMAP → DEFER.** Expansion is pulled
by demonstrated user value, not pushed by architectural possibility. See D-047 (this hardens D-042).

## Defensibility / candidate moat

Pyrnova's candidate durable moat, in priority order:

1. historical "what could have been known then?" state;
2. customer-specific exposure / outcome history;
3. longitudinal outcome calibration;
4. rights-safe relationship history;
5. rejected-intelligence history;
6. customer-contributed context;
7. accumulated event/consequence performance;
8. evidence and decision lineage.

The following are **not** durable moats by themselves: AI, prompts, agents, dashboards, graph
visualization, natural-language search, company dossiers, alerts, RAG, citations, generic entity
resolution, generic knowledge graphs. (Consistent with `01-PROJECT-AUTHORITY.md`: stored data is not
itself proof of a moat; the test is measurable predictive and commercial lift.) See D-049.

## Binding architectural principles (Phase 1 preserves all)

Permanent canonical entity identity; all useful source-native identifiers; bitemporal semantics;
immutable provenance; assertions rather than flattened truth; temporal relationship validity;
observation vs. inference; confidence-aware intelligence; evidence lineage; evidence independence;
rights metadata; reversible entity resolution; events as first-class entities; facilities as first-class
entities; customer isolation; outcome/adjudication history; point-in-time replay; incremental read
projections; fast deterministic product rendering; **AI only after deterministic filtering**;
deterministic identity resolution where identifiers exist.

**PostgreSQL remains appropriate.** Do not introduce a specialist graph database merely because graph
semantics exist. Raw evidence remains separable from normalized facts and derived intelligence.
