# Pyrnova execution authority

_Execution-window disposition · updated 2026-09-14_

## DISPOSITION — PHASE1-LIVE-OPS-CLOSURE broad implementation workstream: SUPERSEDED / RETIRED

The broad **PHASE1-LIVE-OPS-CLOSURE** implementation workstream is **no longer active**. Its engineering objective is met and its coding phase is retired. Do **not** reopen it, relaunch it, or start another broad Live Ops coding session on the basis of anything below. Nothing in the historical body of this document is a live instruction to begin coding.

**Recorded states (authoritative):**

- **LIVE OPS ENGINEERING ACCEPTANCE — PASS** — 657 passed, 0 failed, 0 skipped; no remaining substantive engineering gap; no files changed during the verification pass.
- **PHASE1-LIVE-OPS-CLOSURE — BROAD IMPLEMENTATION SUPERSEDED / RETIRED** — permanent name, not reused; the historical body below is preserved as provenance.
- **PHASE1 LIVE OPS ACCEPTANCE — SOAK IN PROGRESS / PINNED EVIDENCE** — this residual state is a **read-only acceptance activity, not a coding workstream**.
- **CUSTOMER #1 — PENDING SUCCESSFUL SOAK** — no GO / NO-GO until the evidence is reviewed on/after 2026-09-19T20:03:50Z.

**The running soak is read-only acceptance evidence.** The canonical soak runs from pinned commit `e7cb2c98c3594166cbcb4d5691c0f370d4c5eb57`; protected evidence is `var/phase1_soak/evidence_source_counter_fix_2026-09-12`. Do **not** restart, reset, reseed, rebaseline, reconfigure, deploy into, rewrite, or otherwise alter the pinned runtime or its evidence. If a verified correctness defect is later discovered that would make the acceptance run invalid: **STOP AND REPORT** — do not correct or restart it automatically.

**Exact next Live Ops action (the only one):**

```text
WAIT UNTIL ON/AFTER 2026-09-19T20:03:50Z
-> REVIEW PROTECTED SOAK EVIDENCE (var/phase1_soak/evidence_source_counter_fix_2026-09-12)
-> CLASSIFY PASS / FAIL / INVALID
```

Separate work items — **do not absorb into Live Ops**: Operator Alerts; Backup + Isolated Restore; SOURCE-RIGHTS-001 administrative closure; AS-OF / THEN-NOW; Website GO; production-access preparation.

---

_Historical provenance follows. When opened on 2026-09-11 this document authorized one immediate implementation workstream (no product expansion, new milestone family, or redesign). That authorization is spent; the text is retained only to record what the retired workstream required._

Current product and commercial authority: `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`.

## Current status

- Phase One Constitution: **COMPLETE AND LOCKED**.
- M21: **CLOSED**.
- M22-A through M22-F: **CLOSED**.
- Opportunity P0: **CLOSED**.
- Access P0: **CLOSED**.
- Onboarding P0: **CLOSED**.
- Sole primary remaining design-customer P0: **LIVE OPERATIONS / DATA VOLUME READINESS**.
- Operational-soak test Lens: **IRONMOUNTAIN SOLUTIONS, LLC — SOAK TEST LENS — NON-CUSTOMER / NON-COMMERCIAL** (owner clarification 2026-09-12).
- The fixed CUSTOMER-001 cohort is not altered or reconstructed by this work; IronMountain is not Customer #1, a cohort member, or a substitute for MTSI.
- Broad Phase 1 research: **FROZEN** except under the explicit exceptions in product authority.
- Broad product expansion: **NOT AUTHORIZED**.

Do not reopen M21/M22 unless a genuine correctness, safety, or acceptance defect is discovered. Do not create M22-G, M22-H, M22-I, M22-J, or similar containers for this work.

## Immediate workstream

# PHASE1-LIVE-OPS-CLOSURE

### Objective

Determine, with real operational evidence, whether the existing Pyrnova implementation can run continuously on sufficient authorized external intelligence to produce selective, customer-specific Material Changes reliably enough to begin Customer #1.

The workstream must distinguish what already works from genuine gaps. Implement only the missing requirements needed to close the acceptance criteria below.

### Required sequence

1. Inspect the current implementation against every locked Live Operations P0 criterion.
2. Mark each criterion **PROVEN**, **PARTIAL**, **MISSING**, or **BLOCKED**, with repository evidence.
3. Reuse current M12-M22 primitives wherever they already satisfy the requirement.
4. Implement only missing correctness or operability requirements.
5. Preserve current intelligence semantics, provenance, temporal truth, customer isolation, Material Change identity, and replay behavior.
6. Produce automated evidence for the engineering gate.
7. Prepare and run the unattended live-operation acceptance period.
8. Evaluate misses, source failures, stale/degraded states, and customer-value output from the soak period.
9. Return the supervised soak as STARTED or BLOCKED, then stop. The literal elapsed operational gate and a separately authorized Customer #1 decision remain outstanding.

The current owner-unblock execution ends at that soak-start handoff. It does not authorize outreach, a Customer #1 decision, or unrelated product expansion.

## Scope

The workstream may address only what is needed to prove or close:

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

Do not use Live Ops as a pretext to add new product categories, broad source families, customer workflow systems, dashboards, or speculative architecture.

## Live Operations doctrine

```text
BULK FIRST
-> DELTA SECOND
-> TARGETED LIVE LAST

ARCHIVE ONCE
-> REPLAY MANY
```

Materiality and decision value matter more than raw event volume.

Customer-critical sources should normally refresh daily or better. Decision-sensitive supported sources may operate approximately every 1-4 hours where justified by source behavior and customer consequence.

Do not promise sub-minute realtime intelligence.

No silent source failure. A source that is stale, degraded, unavailable, rate-limited, or unknown must surface that state rather than appearing current.

## Acceptance gate 1: ENGINEERING ACCEPTANCE

Engineering acceptance is satisfied only when repository evidence demonstrates the system can correctly perform the required operational behavior before the long soak begins.

At minimum, prove:

- baseline creation is deterministic and correct;
- live acquisition uses authorized sources and preserves raw evidence/provenance;
- scheduled or repeated acquisition respects configured cadence;
- checkpoints survive restart;
- retries are bounded and do not hammer providers;
- rate limits/backoff are explicit and recoverable;
- source health and freshness are observable;
- duplicate acquisitions and duplicate downstream outputs are controlled;
- fan-out and downstream processing are idempotent;
- restart/recovery does not corrupt or duplicate intelligence state;
- Material Change generation remains selective;
- operational metrics make source behavior and important failure modes visible;
- degraded/failed sources fail honestly and safely;
- point-in-time and replay behavior excludes future knowledge;
- existing M21/M22 semantics and customer isolation remain intact.

Tests should be proportional to operational risk and should include fault injection where it materially improves confidence.

Passing ENGINEERING ACCEPTANCE does **not** close the workstream.

## Acceptance gate 2: OPERATIONAL SOAK ACCEPTANCE

Operational soak is a separate gate and cannot be satisfied by unit, integration, replay, or synthetic tests alone.

Required unattended period:

**7 calendar days / 5 business days of unattended live operation.**

The soak must use real authorized external intelligence and preserve enough operational evidence to answer:

- Did each customer-critical source run at an appropriate cadence?
- Were failures, throttles, stale periods, and recoveries visible?
- Did restarts or ordinary operational interruptions create duplicates or gaps?
- Did customer-specific fan-out remain correct and isolated?
- Did Pyrnova produce genuine Material Changes selectively rather than a volume flood?
- Could important misses be identified and investigated from instrumentation?
- Did the system ever imply current data when a source was actually stale or failed?
- Did temporal/replay integrity remain intact?
- Did the resulting intelligence look usable for Customer #1 without bespoke analyst outsourcing?

### Customer-value expectations

For a meaningful first customer login, the normal target is approximately **3-10 genuine active Material Changes**, with a small MONITOR set where appropriate and historical context clearly separated from genuinely new/live changes.

During the first 10 business days, Pyrnova should normally produce at least **3 genuine Material Changes** if the external environment supports them.

These are operating expectations, not quotas. Never manufacture or weaken intelligence to hit them.

## Miss instrumentation

Live Operations closure requires an explicit way to identify and examine important misses. It is not sufficient to count emitted changes while having no visibility into material source events the system failed to elevate.

The implementation may use the simplest compatible mechanism that permits a reviewer to trace:

```text
source evidence
-> ingestion/acquisition state
-> assertions/assessment path
-> customer relevance
-> emitted or non-emitted Material Change
```

Do not create a second intelligence model or a new analytics platform to satisfy this requirement.

## Customer #1 go/no-go

After both gates pass, a separately authorized formal Customer #1 readiness decision must follow CUSTOMER-001. The IronMountain operational-soak test Lens is non-customer/non-commercial evidence only.

A **GO** requires, at minimum:

- ENGINEERING ACCEPTANCE passed;
- OPERATIONAL SOAK ACCEPTANCE passed;
- no unresolved correctness, provenance, temporal, tenant-isolation, or source-integrity defect that would make the pilot misleading;
- enough genuine customer-relevant intelligence to justify starting the pilot without manufacturing volume;
- an operable monitoring scope consistent with the Strategic Change Pilot;
- no requirement for CUI, classified information, massive integrations, or bespoke analyst outsourcing.

A **NO-GO** must identify the minimum blocking defects and keep fixes bounded to those defects. It does not reopen broad product research.

## Explicit non-goals for this workstream

Do not:

- redesign Pyrnova;
- reopen the category or ICP;
- change the Strategic Change Pilot or production pricing;
- create new broad research tasks;
- implement Business Health;
- build customizable dashboard/workspace systems;
- implement broad digital or physical threat-management functionality;
- add CUI or classified support;
- add generic CRM functionality;
- create speculative abstractions;
- rename established intelligence concepts casually;
- invent milestone numbering;
- weaken provenance or temporal semantics;
- convert unknowns into inferred facts;
- expand source breadth merely because another source is interesting.

## Preserved implementation authority

All closed M21 and M22 implementation remains valid. Relevant detailed acceptance history remains in:

- `04-DECISIONS.md`;
- `06-HISTORY.md`;
- `docs/specs/M21_RAW_TERMINATION_RELATIONSHIP_DIVERSITY.md`;
- `docs/specs/M22A_MATERIAL_CHANGES.md`;
- `docs/specs/M22B_PERSISTED_CUSTOMER_LIFECYCLE.md`;
- `docs/specs/M22C_CUSTOMER_MATERIAL_CHANGE_STREAMS.md`;
- `docs/specs/M22D_INVESTIGATION_SEARCH.md`;
- `docs/specs/M22E_OPPORTUNITY_MATERIAL_CHANGES.md`;
- `docs/specs/M22F_MINIMAL_ACCESS_ONBOARDING.md`;
- `docs/specs/M12_SOURCE_INTEGRATION.md`;
- `docs/specs/M13_LIVE_OPERATIONS.md`.

Reuse their proven primitives. Do not rewrite them merely to make this workstream look new.

## Completion output

When `PHASE1-LIVE-OPS-CLOSURE` is complete, return:

1. criterion-by-criterion engineering acceptance evidence;
2. exact gaps implemented, with no unrelated scope;
3. automated verification and fault-injection results;
4. unattended soak dates and operational evidence;
5. source-health/freshness/recovery findings;
6. Material Change volume and selectivity findings without manufactured targets;
7. important misses found and how they were detected;
8. Customer #1 **GO / NO-GO** decision and blockers, if any.

Do not begin any broader post-Phase-1 work from inside this workstream.
