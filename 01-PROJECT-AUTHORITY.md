# Pyrnova project authority

_Status: current root project authority · Phase One Constitution locked · architecture reconciled 2026-09-19_

## Mission and current product

Pyrnova is an intelligence company building evidence-backed, historically auditable external intelligence for commercial decision-making.

Pyrnova is one company and one intelligence platform. **Core** is the shared data/infrastructure
substrate and **PyrAI** is the shared model-agnostic intelligence/orchestration layer. **Scout** (live
sensing), **Strike** (customer-specific judgement), **Vector** (consequence/scenario modelling), and
**Atlas** (structural intelligence) are distinct customer-facing products. They are complementary, not
mandatory sequential stages, and none owns Core or PyrAI. The locked boundaries are in
`docs/strategy/PLATFORM_PRODUCT_ARCHITECTURE.md` (D-067).

The current Phase 1 product is **Pyrnova**, a **decision-grade external-intelligence system for government contractors**. Its operating concept is **Material Changes**.

Pyrnova helps a government contractor identify which external developments matter, understand why they matter, verify the underlying evidence, and decide what to investigate or do next.

The overarching cross-phase product and commercial authority is:

`docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md`

The sole product and implementation authority within Phase 1 scope is:

`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`

That document controls the current category, ICP, customer order, commercial offer, Phase 1 acceptance,
validation, and explicit non-goals. The current offer maps primarily to Strike, supported by shared Core
foundations and bounded PyrAI capability. It is **Strike-led, not Strike-owned**: cross-product capability
may participate without moving shared truth into Strike or establishing separate commercial availability.
The offer remains Pyrnova / Strategic Change Pilot and is not automatically renamed or split into four
Phase 1 SKUs (D-068). Capture Radar and the earlier Business Opportunity Pipeline remain important
implementation and historical lineage, but they are not a competing Phase 1 product/category authority.

## Current commercial objective

Prove repeated customer-specific decision value with real design customers and convert that proof into durable recurring revenue.

**IronMountain Solutions is solely a non-customer, non-commercial operational-soak test Lens and is
explicitly not Customer #1** (D-065). Any Customer #1 designation and GO / NO-GO remains separately
authorized under CUSTOMER-001. The current commercial offer and production pricing are internal authority
and must not be published externally unless separately authorized.

The immediate execution workstream is defined only in `02-EXECUTION.md`.

## Phase 1 differentiated thesis

The differentiated loop is:

```text
SOURCE
-> EVIDENCE ARTIFACT
-> ASSERTION
-> ASSESSMENT
-> CUSTOMER CONSEQUENCE
-> MATERIAL CHANGE
-> INVESTIGATION / REVIEW
-> ACTION
-> OUTCOME
```

Pyrnova is not a generic procurement database, CRM, dashboard builder, generic research/chat product, or an AI wrapper around an incumbent. The customer value is selective interpretation of external change against the customer's real situation, with evidence, temporal truth, review, and later outcome learning.

The central commercial falsification question is whether Pyrnova can repeatedly tell a GovWin, GovTribe, or current-process customer something materially important their existing process did not adequately provide, early enough to change action.

## Authority hierarchy

Resolve conflicts in this order:

1. Current product / strategic authority.
2. Current milestone / work order.
3. Durable decisions.
4. Current state.
5. Architectural authority.
6. Roadmap.
7. Research.
8. Historical / superseded material.

`00-INDEX.md` and `AGENTS.md` define the repository navigation and mandatory reading order.

Research informs authority. It does not independently authorize implementation.

## Locked intelligence doctrine

The deterministic/evidentiary core is authoritative. Model output may assist extraction, synthesis, assessment, and explanation, but it does not become authoritative fact merely because a model produced it.

Preserve these distinctions:

- canonical intelligence truth versus presentation;
- source capture versus verification versus publication;
- source reliability versus claim credibility;
- claim credibility versus assessment confidence;
- assessment confidence versus event probability;
- evidence state versus claim state versus outcome state;
- observed fact versus inference versus assessment;
- global intelligence versus customer-specific relevance and private context;
- historical belief at time T versus evidence learned later.

Unknown remains unknown. Conflicting claims may coexist. Unresolved outcomes may remain unresolved. Later evidence must not silently rewrite earlier belief or retrospectively backfill a forecast.

Every customer-facing analytical conclusion must be traceable far enough to support audit and replay. AI/model participation must retain attribution sufficient to explain what came from source evidence, deterministic computation, human judgment, and model-assisted reasoning.

## Evidence and source doctrine

Preserve raw evidence with provenance and source-native identity. Archive scarce/live evidence once and replay it many times.

Live external calls are governed infrastructure. They must be intentional, budgeted where appropriate, observable, retry-safe, rate-limit-safe, and incapable of silently changing semantics when a source fails.

Current Live Operations doctrine is:

```text
BULK FIRST
-> DELTA SECOND
-> TARGETED LIVE LAST

ARCHIVE ONCE
-> REPLAY MANY
```

Source health, freshness, degraded state, and unknown state must be explicit. Never imply current data when the system only has stale or failed acquisition.

## Product language authority

Customer-facing language is formal, precise, operational, and evidence-led. Prefer literal functional language describing information, state, evidence, consequence, uncertainty, and action.

Avoid slogans, clever headings, anthropomorphic AI language, generic startup claims, faux urgency, and unsupported certainty. Copy quality is part of feature acceptance.

Detailed voice/posture authority remains in `docs/strategy/CORPORATE_POSTURE_AND_BRAND.md` and D-041/D-054.

## Phase control and finishability

A missing capability may block current Phase 1 work only when needed for:

- correctness;
- safety;
- architectural integrity;
- current acceptance criteria;
- valid Customer #1 measurement.

Otherwise:

```text
DOCUMENT
-> ROADMAP
-> DEFER
```

Research curiosity, elegance, competitor parity, theoretical usefulness, another interesting source, or "while we are here" do not expand the phase.

Broad Phase 1 research is frozen except for a genuine Customer #1 blocker, an unsettled commercial decision that current authority cannot resolve, a correctness/security issue, or customer-driven expansion evidence.

## Engineering and infrastructure doctrine

Implementation must follow `docs/architecture/ENGINEERING_DOCTRINE.md` and `docs/architecture/INFRASTRUCTURE_DOCTRINE.md`.

Core rules include:

- one concept, one canonical implementation;
- reuse existing Pyrnova patterns unless a recorded reason justifies deviation;
- explicit state ownership and data flow;
- no silent semantic fallback;
- simplicity over speculative abstraction;
- consequence-proportional testing and observability;
- correct, clear, measurable behavior before optimization;
- infrastructure may change, intelligence semantics must not;
- migrations must preserve identity, provenance, temporal truth, customer isolation, and replay.

Start cheap and architect expensive. Do not create rewrite-at-scale assumptions or infrastructure theatre.

## Competitive doctrine

Pyrnova competes to create materially better customer decisions, not to reproduce incumbent feature lists.

The governing question for a major Phase 1 capability is:

> Why would a rational customer already paying for an incumbent switch budget, workflow, or attention to Pyrnova?

Durable advantage should compound from things competitors cannot cheaply reconstruct after the fact, especially point-in-time evidence history, customer-specific exposure history, rejection history, outcome calibration, rights-safe relationship history, and evidence/decision lineage.

AI, prompts, dashboards, generic graph visualization, generic RAG, generic search, and citations are useful capabilities but are not durable moats by themselves.

Full competitive authority remains in `docs/strategy/COMPETITIVE_DOCTRINE.md`.

## Lawful competitive intelligence and data autonomy

Competitive intelligence is conducted by lawful means only. Do not use unauthorized access, credential misuse, malware, bribery, deception to obtain protected information, inducement to breach confidentiality, trade-secret material, leaked code, or stolen databases.

Collection techniques with uncertain contractual, access-control, copyright, database-rights, or terms-of-service implications require legal review before operationalization.

Keep observation and implementation separable when clean-room discipline matters. Keep rented-data provenance separable so Pyrnova can understand what disappears if a vendor relationship ends.

Full doctrine remains in `docs/strategy/COMPETITIVE_INTELLIGENCE_AND_DATA_AUTONOMY.md`.

## Customer and data boundaries

Phase 1 should prefer a low-friction first-customer shape: bounded monitoring scope, few users, public/external intelligence, minimal customer-private data, no CUI, no classified information, no massive integration dependency, fixed term, and fixed price.

Do not accept bad revenue that requires bespoke analyst outsourcing, architecture forks, exclusivity, unsustainable discounting, endless free pilots, unsupported sensitive-data handling, or consulting disguised as product validation.

Customer-private configuration, relevance, review state, and contributed context must remain distinct from global intelligence truth.

## Current Phase 1 state

M21 and M22 are closed. Opportunity, Access, and Onboarding P0s are closed.

The sole primary remaining design-customer P0 is **Live Operations / Data Volume Readiness**. `02-EXECUTION.md` authorizes exactly one immediate workstream: **PHASE1-LIVE-OPS-CLOSURE**.

Do not invent further M22 lettered milestones to absorb new work. Do not broaden Pyrnova while closing Live Operations.

The next decision after Live Operations acceptance is **Customer #1 GO / NO-GO**.

## Deferred areas

Business Health is specification-complete but not launch-blocking and is not authorized while Live Operations or Customer #1 readiness needs work.

Broader threat-management products, physical threat intelligence, supply-chain threat, red/blue-team productization, social-engineering hardening, foreign-device risk, sector threat mapping, customizable dashboard/workspace building, broad ontology/graph-explorer experiences, complex compartmentation, and other long-term platform breadth remain roadmap-deferred unless customer evidence changes authority.

## Canonical working tree

The canonical local implementation tree is `/Users/stu/Documents/Pyrnova` on `main`; GitHub `origin/main` is repository authority. `/Users/stu/pyrnova` is not the authorized working tree.
