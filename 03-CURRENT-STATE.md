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

**Pre-release gate:** `PRELAUNCH-CONVERGENCE-001` is the mandatory pre-release work order
(`docs/specs/PRELAUNCH_CONVERGENCE_001.md`, D-066). Release is prohibited while any mandatory CLOSE item
is materially incomplete; the governing acceptance measure is customer usefulness, expressed through the
`SIGNAL → OPPORTUNITY → BUYER → INCUMBENT → ACCESS → CUSTOMER FIT → PURSUIT DECISION → MATERIAL CHANGE →
CUSTOMER ACTION → OUTCOME → LEARNING` decision chain (a refinement of the lineage above). Final Live Ops
acceptance is revised to require an immutable pinned release/worktree isolated from development.

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

### Internal evaluation estate (PRODUCT-DEMO-001, 2026-09-16)

The customer product can now be inspected under realistic data load via one **internal** evaluation Lens,
`eval-multinational` ("Pyrnova Internal Evaluation"): 31 opportunities across all five national domains
(CA 9, GB 8, US 6, NZ 5, AU 3), projected from accepted replay/fixture evidence through each country's own
existing `build_customer_proof.py` — one projection path, no demo-only product logic, no country UI fork.
It is not a real customer and holds no live production intelligence; two rights-denied cases stay blocked
and two US evidence records stay withheld, both reported. Launch and contents:
`examples/evaluation_estate/README.md`. Guarded by `tests/test_evaluation_estate.py`.

Two shared-kernel defects were fixed to make it visible: the customer product's opportunity **list** now
passes national acquisition truth through (it previously dropped it, so international rows rendered as
"Unknown"), and the local launch path now **imports** the committed demo intelligence into persisted state
instead of silently pointing the console at a different store — which had hidden any genuinely provisioned
global intelligence. Full suite at this close: **1054 passed, 2 skipped, 0 failed**.

## Customer #1

The fixed CUSTOMER-001 cohort is not changed or reconstructed by this execution. Owner clarification
(2026-09-12) designates **IRONMOUNTAIN SOLUTIONS, LLC** only as a **SOAK TEST LENS — NON-CUSTOMER /
NON-COMMERCIAL**. It is not Customer #1, a design customer, a cohort member, an outreach target, or a
substitute for MTSI. Its output is operational evidence only, not commercial validation or willingness to pay.

## Commercial state

Current offer: **PYRNOVA LIVE INTELLIGENCE** (owner-locked 2026-09-15; authority `04-DECISIONS.md` D-067,
`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` §5).

- $15,000 initial engagement;
- 60 days;
- one Customer Lens; bounded intelligence surface; up to 10 Named Users;
- 100% invoiced after signature; Net 15 default; activation normally after cleared payment;
- continuation $18,000 quarterly prepaid; annual option $72,000 prepaid;
- no free pilot; no default discount.

_Superseded (not current): the earlier $12,500 / $10,000-floor 10-week "Strategic Change Pilot" and the
obsolete $2,500 Intelligence Sprint._

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

The required audit and bounded engineering-gap implementation are integrated on canonical main:
durable retry scheduling, explicit health/acquisition-freshness state, customer-id-safe live pipeline
fan-out, Important Miss records, an immutable soak evidence harness, and a macOS supervision template.
A one-call current USAspending acceptance probe for IronMountain Solutions preserved 10 real records and
round-tripped its archive hash. Evidence: `docs/operations/PHASE1_LIVE_OPS_CLOSURE.md`.

The owner-unblock instruction now approves a non-commercial IronMountain test Lens. It is persisted as
`soak-ironmountain-solutions` through canonical onboarding, with six source-backed watches, literal
award-description capability keywords, and no unsupported NAICS/PSC or commercial preferences.
Foreground validation is separate from the official clock; supervision may start acceptance only after
preflight, real processing, and unchanged fan-out pass. Configuration/criteria are recorded in
`docs/operations/PHASE1_SOAK_UNBLOCK.md`; actual runtime start/status are authoritative in the gitignored
corrected evidence directory specified below.

The original foreground cycle acquired 14 USAspending records and 100 SAM records, but its historical
ledger incorrectly recorded zero. That failed evidence under `var/phase1_soak/evidence/` is preserved.
The narrowly scoped source-counter correction now wires the shared authoritative response parser,
represents unavailable counts explicitly, and rejects count/hash disagreement before checkpointing.
Separate retained-runner evidence verifies parsed/newly recorded counts of 14/100 without provider
calls or repairs. A retained start gate verifies current indexed/checkpointed HEALTHY/CURRENT evidence
while respecting cadence; supervised execution requires a passed gate matching the pinned commit/plan.
Actual corrected gate, service activation, official start, and elapsed-soak outcomes are authoritative
in `var/phase1_soak/evidence_source_counter_fix_2026-09-12/`. Neither automated tests nor a generated
plist constitutes unattended activation or operational acceptance. Details are recorded in
`docs/operations/PHASE1_SOAK_UNBLOCK.md`.

Operational acceptance requires the literal seven-calendar-day/five-business-day unattended evidence window;
the corrected runtime manifest/status determines whether that window has actually started.
No Customer #1 GO / NO-GO or commercial-readiness conclusion is established by this test Lens.

## Next decision

After Live Operations closure, the next authorized decision is:

**A separately authorized Customer #1 GO / NO-GO under CUSTOMER-001.**

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
