# Pyrnova current state

_Verified repository authority state: 2026-09-11 · implementation baseline remains M22-F close_

## Phase 1 authority state

The **Pyrnova Phase One Constitution is complete and locked**.

Canonical Phase 1 product and commercial authority:

`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`

Broad Phase 1 research is **frozen** except for the narrow exceptions defined in that authority: a genuine Customer #1 blocker, an unsettled commercial decision that current authority cannot resolve, a correctness/security issue, or a customer-driven expansion question.

No broad product expansion is authorized.

## Current product

**Product:** Pyrnova

**Category:** Decision-grade external-intelligence system for government contractors.

**Phase One operating concept:** Material Changes.

Pyrnova helps government contractors identify which external developments matter, understand why they matter, verify the evidence, and decide what to investigate or do next.

The canonical intelligence lineage is:

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

Capture Radar and the Business Opportunity Pipeline are preserved as implementation and historical lineage. They do not override the current product/category authority.

## Milestone and P0 status

- M2-M21: **CLOSED**.
- M22-A Material Changes: **CLOSED**.
- M22-B persisted customer intelligence/lifecycle: **CLOSED**.
- M22-C per-tenant Material Change streams: **CLOSED**.
- M22-D investigation + deterministic entity search: **CLOSED**.
- M22-E opportunity Material Changes: **CLOSED**.
- M22-F minimal customer access + seed-free onboarding: **CLOSED**.

M21 and M22 stay closed unless a genuine correctness, safety, or acceptance defect is discovered.

Do not create new M22 lettered milestones merely to hold later work.

Closed design-customer P0 areas:

- Opportunity;
- Access;
- Onboarding.

Sole primary remaining Phase 1 design-customer P0:

**LIVE OPERATIONS / DATA VOLUME READINESS**

The remaining question is:

> Can Pyrnova operate continuously on enough real external intelligence to repeatedly produce customer-specific decision value in a real paying organization?

## Current implementation baseline

The last implementation close was **M22-F on 2026-09-10**. At that close, the repository recorded **615 passing tests**.

This 2026-09-11 authority synchronization is documentation-only. It does not claim a new implementation test count and does not reopen the M22-F acceptance result.

The verified implementation baseline includes:

- deterministic and evidence-backed Material Changes;
- persisted customer profiles and watchlists;
- customer review lifecycle separate from system assessment;
- durable per-tenant Material Change streams and version history;
- customer-specific fan-out using the existing global intelligence truth;
- company/program investigation pages;
- deterministic entity/program search with explicit ambiguous/unresolved states;
- real opportunity Material Changes using the existing opportunity engine;
- real credential-based customer access with server-enforced tenant isolation;
- seed-free operator onboarding;
- source scheduling/control, archive, checkpoint, retry/backoff, and earlier bounded live-operations primitives from M12/M13;
- point-in-time replay and future-data exclusion;
- append-only outcome/review history;
- explicit unknown/unresolved semantics.

Detailed implementation evidence remains in `04-DECISIONS.md`, `06-HISTORY.md`, `docs/specs/`, and `docs/replay/`.

## Customer #1

Current Customer #1 target:

**IronMountain Solutions**

Next targets, in order:

1. Trideum
2. i3
3. Radiance Technologies
4. Avion Solutions

The customer list is current authority. Do not swap targets during implementation merely because another prospect looks interesting.

## Commercial state

Current offer: **Strategic Change Pilot**.

- 10 weeks;
- $12,500 list price;
- $10,000 absolute floor;
- 50% at signature;
- 50% at week 5;
- up to 10 users;
- up to 75 monitored objects.

Production pricing authority:

- $48,000 target ACV;
- $36,000 floor;
- $72,000 stretch;
- $6,250 pilot-to-production conversion credit.

Launch pricing is not public website copy.

Earlier materially different pilot structures are superseded. Historical documents may preserve them only as clearly superseded provenance.

## Immediate execution state

One implementation workstream is authorized:

**PHASE1-LIVE-OPS-CLOSURE**

See `02-EXECUTION.md`.

The workstream must first determine which Live Operations requirements are already satisfied, then implement only genuine gaps. It has two separate acceptance gates:

1. **ENGINEERING ACCEPTANCE**
2. **OPERATIONAL SOAK ACCEPTANCE**

Passing automated tests does not satisfy the second gate.

Operational acceptance requires **7 calendar days / 5 business days of unattended live operation** on real authorized external intelligence.

## Live Operations acceptance focus

The workstream must close or prove closed:

- correct baseline creation;
- real authorized evidence;
- automatic acquisition;
- appropriate cadence;
- durable checkpoints;
- retries;
- rate-limit handling;
- source health;
- freshness state;
- deduplication;
- idempotent downstream processing/fan-out;
- restart/recovery;
- selective Material Change generation;
- operational visibility;
- instrumentation for important misses;
- safe source degradation/failure;
- point-in-time/replay integrity.

Normal first-login expectation is approximately **3-10 genuine active Material Changes**, a small MONITOR set where appropriate, and historical context visibly separated from new/live changes.

During the first 10 business days, the system should normally produce at least **3 genuine Material Changes** if the environment supports them. This is not a quota. Never manufacture volume.

### Live Operations closure execution state (2026-09-12)

The required audit and bounded engineering-gap implementation are complete on the current working branch:
durable retry scheduling, explicit health/acquisition-freshness state, customer-id-safe live pipeline
fan-out, Important Miss records, an immutable soak evidence harness, and a macOS supervision template.
A one-call current USAspending acceptance probe for IronMountain Solutions preserved 10 real records and
round-tripped its archive hash. Evidence: `docs/operations/PHASE1_LIVE_OPS_CLOSURE.md`.

**Operational soak has not started.** It is blocked because persisted customer state has no owner-approved
IronMountain Solutions Lens, watchlist/monitored-object set, capability profile, or primary NAICS. The
repository intentionally does not infer this customer-private configuration from public award records.
The example plan fails closed until those inputs and the final verified commit are supplied.

Engineering implementation is therefore **conditional / soak pending**, operational acceptance remains
**blocked before start**, and Customer #1 GO / NO-GO remains out of scope until the literal soak completes.

## Next decision

After Live Operations closure, the next authorized decision is:

**Customer #1 GO / NO-GO: IronMountain Solutions**

There is no authorized broad product-expansion decision before that gate.

## Deferred / non-blocking

Business Health remains specification-complete, implementation-not-started, and non-launch-blocking. It may be implemented pre-launch only if true spare capacity exists and it cannot delay Live Operations, Customer #1, pilot validation, or core Material Changes.

The following remain roadmap-deferred unless customer evidence changes authority:

- broader digital threat assessment;
- physical threat intelligence;
- supply-chain threat;
- authorized red-team intelligence;
- blue-team intelligence;
- social-engineering hardening;
- foreign-device risk;
- sector threat mapping;
- mature decision-driven intelligence workflows;
- customizable dashboard/workspace builder;
- large ontology/graph-explorer experiences;
- complex compartmentation.

## Preserved constraints

- intelligence truth remains separate from presentation;
- raw evidence and provenance remain durable;
- observed, asserted, assessed, and outcome state remain distinct;
- later evidence does not rewrite earlier belief;
- no retrospective forecast backfill;
- customer relevance remains distinct from global intelligence;
- unknown never silently becomes zero;
- unresolved may remain unresolved;
- AI/model involvement remains attributable enough for audit/replay;
- customer-private data stays separate from global intelligence truth;
- infrastructure changes must preserve intelligence semantics.

## Historical detail

Detailed closed-milestone chronology is intentionally not duplicated here. Use:

- `06-HISTORY.md` for chronology;
- `04-DECISIONS.md` for durable decisions;
- `docs/specs/` for milestone acceptance and implementation contracts;
- `docs/replay/` for replay/acceptance evidence;
- `docs/archive/` and `docs/handovers/` only as historical/superseded provenance.

Old "next action" sections preserved in historical documents do not override this current state.
