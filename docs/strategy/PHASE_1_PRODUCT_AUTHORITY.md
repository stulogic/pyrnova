# Pyrnova Phase 1 product and commercial authority

_Status: CANONICAL AND LOCKED · Phase One Constitution incorporated 2026-09-11 · architecture mapping reconciled 2026-09-19_

> **Authority level and scope.** This document is the sole product and implementation authority within
> Phase 1 scope. It incorporates the owner-approved Phase One Constitution, specializes
> `01-PROJECT-AUTHORITY.md` for Phase 1, and sits above the milestone work order. The overarching
> `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` separately governs cross-phase product and commercial
> strategy, and `docs/strategy/PLATFORM_PRODUCT_ARCHITECTURE.md` records the locked cross-phase Core,
> PyrAI, Scout, Strike, Vector and Atlas boundaries. This document may specialize those authorities for
> Phase 1, but may not erase, redefine, or supersede them outside Phase 1. It does **not** authorize
> implementation — `02-EXECUTION.md` alone authorizes active work.

Research informs this authority. Research does not override it. Roadmap material does not enter Phase 1 unless `02-EXECUTION.md` explicitly authorizes it under the phase-control rules below.

## 1. Locked Phase 1 product definition

**Product:** Pyrnova

**Category:** Decision-grade external-intelligence system for government contractors.

**Core job:** Pyrnova helps government contractors identify which external developments matter, understand why they matter, verify the evidence, and decide what to investigate or do next.

**Phase One operating concept:** Material Changes.

Pyrnova is an intelligence system. It is not:

- CRM;
- generic procurement search;
- GovWin with AI;
- generic company research;
- generic AI chat or research;
- a dashboard-builder product;
- an AlphaSense clone;
- a Dataminr clone;
- a Palantir clone;
- a general-purpose internal operating system.

The cross-phase architecture is broader: shared Core and PyrAI layers support Scout, Strike, Vector and
Atlas as distinct products. Phase 1 sales and category language nevertheless remain narrow until customer
evidence and owner authority authorize different packaging.

The dominant customer question is: **What materially changed since I last looked, why does it matter to us, what evidence supports it, and what should we investigate or do next?**

Material Changes is the dominant customer surface. Company and program investigation, evidence, search, review, and outcome history support that workflow. They are not separate products.

Within the locked cross-phase architecture, this current package maps primarily to **Strike**. Existing
source/archive/identity/temporal infrastructure maps to shared **Core** foundations, and bounded optional
model assistance is compatible with **PyrAI**. Existing event sensing, consequence/propagation, and
entity/relationship work may provide foundations for Scout, Vector, and Atlas respectively, but does not
establish those products as implemented standalone Phase 1 SKUs. The current offer remains branded
Pyrnova unless the owner separately authorizes a naming or packaging transition.

## 2. Canonical intelligence lineage

The canonical conceptual lineage is:

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

Existing Evidence Plane, Intelligence Plane, Compute Plane, and Delivery Plane architecture remains valid where compatible with this lineage.

The following are invariants:

- canonical intelligence truth is separate from presentation;
- capture is distinct from verification and publication;
- raw evidence is preserved with provenance;
- source reliability is distinct from claim credibility;
- claim credibility is distinct from assessment confidence;
- assessment confidence is distinct from event probability;
- evidence state is distinct from claim state and outcome state;
- conflicting claims may coexist;
- unknown never silently becomes zero;
- later evidence must not rewrite what was believed at an earlier point in time;
- no retrospective forecast backfill;
- unresolved may remain unresolved;
- customer-specific relevance is distinct from global intelligence;
- AI or model extraction and assessment must retain attribution sufficient for audit and replay;
- intelligence semantics must survive infrastructure changes.

Do not flatten these distinctions for implementation convenience.

## 3. Phase 1 ideal customer profile

Primary Phase 1 ICP: U.S. federal contractors at approximately **$50M-$300M annual revenue**, especially:

- defense;
- industrial;
- technology;
- engineering;
- infrastructure.

Strong target characteristics:

- lean BD, capture, or strategy teams;
- meaningful federal exposure;
- multiple active pursuits or programs;
- multiple adjacent capabilities;
- insufficient analyst capacity for continuous external monitoring;
- ideally already using GovWin, GovTribe, or a comparable procurement-intelligence process.

Primary falsification question:

> Can Pyrnova repeatedly tell a GovWin, GovTribe, or current-process customer something materially important their existing system did not adequately provide, early enough to change action?

The evidence standard is changed customer behavior, not feature parity.

## 4. Design-customer order

Owner clarification (2026-09-12): **IRONMOUNTAIN SOLUTIONS, LLC** is authorized solely as a
**SOAK TEST LENS — NON-CUSTOMER / NON-COMMERCIAL**. It is not Customer #1, a design customer, a member
of the fixed CUSTOMER-001 first-five cohort, an outreach target, or a substitute for MTSI. This execution
does not reconstruct or choose replacements in that fixed cohort.

The following earlier local target-order record is superseded where it treats IronMountain as a customer
or cohort member; retained only for authority-history provenance:

1. **IronMountain Solutions**
2. **Trideum**
3. **i3**
4. **Radiance Technologies**
5. **Avion Solutions**

Do not replace this order during ordinary implementation because another company appears interesting. A change requires owner direction or later customer evidence recorded through authority.

## 5. Locked commercial offer

### Strategic Change Pilot

- Duration: **10 weeks**
- List price: **$12,500**
- Absolute floor: **$10,000**
- Payment: **50% at signature, 50% at week 5**
- Included users: **up to 10**
- Monitored objects: **up to 75**

### Production pricing authority

- Target ACV: **$48,000**
- Floor: **$36,000**
- Stretch: **$72,000**
- Pilot-to-production conversion credit: **$6,250**

Do not publish launch pricing publicly on the website.

Any earlier authority describing a materially different pilot, including a **$15,000 prepaid 30-day pilot**, is superseded. Historical copies may remain only where clearly marked historical or superseded and must not be treated as current commercial authority.

## 6. Phase control and research freeze

New ideas do not automatically enter Phase 1.

A newly discovered capability changes current scope only when necessary for:

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

Broad Phase 1 research is frozen. It may reopen only for:

- a Customer #1 blocker;
- a commercial decision that genuinely cannot be settled from current authority;
- a correctness or security issue;
- a customer-driven expansion question.

Do not reopen category, ICP, broad competitive research, product architecture, or feature discovery merely because further research is possible.

## 7. Current implementation state

M21 and M22 remain closed. Do not reopen them unless a genuine correctness, safety, or acceptance defect is discovered.

Do not invent M22-G, M22-H, M22-I, M22-J, or similar containers for new work.

Closed design-customer P0 areas include:

- Opportunity;
- Access;
- Onboarding.

The sole primary remaining Phase 1 design-customer P0 is:

**LIVE OPERATIONS / DATA VOLUME READINESS**

The fundamental remaining question is no longer whether Pyrnova can represent this intelligence. It is:

> Can Pyrnova operate continuously on enough real external intelligence to repeatedly produce customer-specific decision value in a real paying organization?

## 8. Live Operations doctrine

The operating doctrine is:

```text
BULK FIRST
-> DELTA SECOND
-> TARGETED LIVE LAST

ARCHIVE ONCE
-> REPLAY MANY
```

Additional rules:

- materiality and decision value matter more than raw event volume;
- no silent source failure;
- customer-critical sources should normally refresh daily or better;
- decision-sensitive supported sources may operate approximately every 1-4 hours where justified;
- do not promise sub-minute realtime intelligence;
- explicit degraded, stale, and unknown states are preferable to pretending data is current.

## 9. Live Operations P0 acceptance

`PHASE1-LIVE-OPS-CLOSURE` must close, or prove already closed, all of the following:

- correct baseline creation;
- real authorized evidence;
- automatic acquisition;
- appropriate source cadence;
- durable checkpoints;
- retry handling;
- rate-limit handling;
- source health;
- freshness state;
- deduplication;
- idempotent downstream processing and fan-out;
- restart and recovery;
- selective Material Change generation;
- operational visibility;
- instrumentation capable of identifying important misses;
- safe handling of source degradation and failure;
- point-in-time and replay integrity.

Operational acceptance additionally requires **7 calendar days / 5 business days of unattended live operation**.

Passing unit, integration, replay, or acceptance tests does not satisfy the unattended live-operation gate by itself.

Expected customer experience:

- the first meaningful customer login should normally contain approximately **3-10 genuine active Material Changes**;
- a small MONITOR set may appear where appropriate;
- historical context must be clearly separated from genuinely new or live changes;
- during the first 10 business days, the system should normally produce at least **3 genuine Material Changes** if the external environment supports them.

Never manufacture intelligence volume to hit a numerical target. Zero genuine changes is preferable to fabricated or weak intelligence.

## 10. Validation doctrine and expansion gate

Do not substantially broaden Pyrnova until customer evidence supports it.

The expansion gate remains:

- at least **5 real design customers**;
- at least **3 willing to continue paying or convert**;
- repeated net-new material intelligence;
- measurable customer action;
- low severe false-positive rate;
- acceptable high-severity miss rate;
- voluntary repeat use;
- opportunity and threat both producing value;
- onboarding not requiring bespoke analyst work;
- positive gross-margin trajectory;
- incumbent differentiation demonstrated;
- at least one customer requesting broader scope because the current product works.

Expansion is pulled by customers, not pushed by architecture.

## 11. Deferred and non-blocking work

### Business Health

Business Health is:

- **SPECIFICATION COMPLETE**
- **IMPLEMENTATION NOT STARTED**
- **DESIRABLE PRE-LAUNCH ONLY IF TRUE SPARE CAPACITY EXISTS**
- **NOT LAUNCH-BLOCKING**
- **EARLY POST-LAUNCH OTHERWISE**

It must not delay Customer #1, Live Operations, pilot validation, or core Material Changes.

Longer-term roadmap areas remain deferred unless customer evidence changes priority:

- broader digital threat assessment;
- physical threat intelligence;
- supply-chain threat;
- authorized red-team intelligence;
- blue-team intelligence;
- social-engineering hardening;
- foreign-device risk;
- sector threat mapping;
- mature decision-driven intelligence workflows;
- customizable dashboard or workspace builder;
- large ontology or graph-explorer experiences;
- complex compartmentation.

Do not accidentally promote these into Phase 1 P0.

## 12. Bad-revenue guardrails

Reject Phase 1 commercial arrangements that require:

- bespoke analyst outsourcing;
- endless free pilots;
- customer control over the general roadmap;
- architecture forks;
- unsupported CUI or high-sensitivity work;
- exclusivity;
- massive custom integrations;
- unsustainable discounts;
- consulting masquerading as product validation.

Preferred first-customer shape:

- few users;
- no integration dependency;
- no CUI;
- no classified information;
- minimal customer-private data;
- public and external intelligence;
- bounded monitoring scope;
- fixed term;
- fixed price.

## 13. Authority hierarchy

The effective repository authority order is:

1. **Owner Decisions / Phase One Constitution**
2. **Cross-Phase Product / Commercial Authority**
3. **Phase 1 Product / Implementation Authority**
4. **Execution / State / Milestone / Evidence**
5. **Architectural Authority**
6. **Roadmap**
7. **Research**
8. **Historical / Superseded**

`00-INDEX.md` and `AGENTS.md` provide the navigation and anti-drift reading order.

Research informs authority. Research does not silently override authority.

## 14. Existing durable doctrine preserved

The Constitution narrows and synchronizes current authority. It does not erase compatible prior doctrine. In particular, preserve:

- deterministic identity and evidence handling;
- point-in-time truth and replay;
- append-only review and outcome history;
- global-intelligence versus customer-private boundaries;
- Product Language Authority;
- finishability and anti-scope-drift rules;
- engineering and infrastructure doctrine;
- lawful competitive-intelligence and data-autonomy rules;
- competitive differentiation against incumbent workflows;
- archive-once, replay-many source discipline.

Where an older document conflicts with this Constitution within Phase 1 scope, this document controls.
It does not redefine the cross-phase authority outside that scope.

## 15. Immediate authorized work

The single immediate implementation workstream is **`PHASE1-LIVE-OPS-CLOSURE`**, as defined in `02-EXECUTION.md`.

No broad product expansion is authorized. The formal decision after Live Operations closure is
**Customer #1 GO / NO-GO** under CUSTOMER-001, separately authorized. IronMountain soak evidence is not
commercial validation or a Customer #1 designation.
