# PYRNOVA-PRODUCTIZATION-RECON-001 — P01 canon and authority baseline

**Status:** COMPLETE — planning baseline only

**Baseline:** `origin/main` at `12c756f5749ff67e536fa7b597410c0073626a33`

**Effective for:** P02 and any later separately authorized P03–P15 work

**Does not authorize:** implementation, runtime modification, product launch, packaging, pricing,
entitlements, naming transition, milestone reopening or production activation

## 1. Purpose and use

This document freezes the current repository authority that later productization reconciliation must
obey. It links to, and does not reinterpret or replace, canonical authority. If this baseline conflicts
with a higher-authority source, the source controls and the conflict must be recorded rather than
silently resolved toward broader scope.

This is not a new product strategy. It is a bounded reading of repository authority at the baseline
commit above.

## 2. Authority precedence

P02–P15 must resolve conflicts in this order:

1. **Current owner decisions / Phase One Constitution.** The locked Constitution is incorporated in
   [`PHASE_1_PRODUCT_AUTHORITY.md`](../../PHASE_1_PRODUCT_AUTHORITY.md).
2. **Cross-phase product and commercial authority.** Use
   [`PRODUCT_COMMERCIAL_AUTHORITY.md`](../../PRODUCT_COMMERCIAL_AUTHORITY.md) and its locked companion
   [`PLATFORM_PRODUCT_ARCHITECTURE.md`](../../PLATFORM_PRODUCT_ARCHITECTURE.md), including D-067 and
   D-068.
3. **Phase 1 product and implementation authority.** Within Phase 1,
   [`PHASE_1_PRODUCT_AUTHORITY.md`](../../PHASE_1_PRODUCT_AUTHORITY.md) is sole product and
   implementation authority. It may specialize, but not erase or redefine, cross-phase authority.
4. **Execution, state, milestone and evidence.** Use [`../../../../02-EXECUTION.md`](../../../../02-EXECUTION.md),
   [`../../../../03-CURRENT-STATE.md`](../../../../03-CURRENT-STATE.md),
   [`../../../../04-DECISIONS.md`](../../../../04-DECISIONS.md) and the applicable specification.
   Only `02-EXECUTION.md` authorizes implementation.
5. **Architecture authority.** Use [`../../../architecture/`](../../../architecture/), including the
   engineering and infrastructure doctrines, and `db/`.
6. **Roadmap.** Use [`STRATEGIC_CAPABILITY_ROADMAP.md`](../../STRATEGIC_CAPABILITY_ROADMAP.md), then
   `05-BACKLOG.md`. Roadmap is not implementation authority.
7. **Research.** Research may inform authority and never authorizes implementation by itself.
8. **Historical / superseded material.** History, handovers and archives preserve provenance only.

Repository entry and routing authority remains [`../../../../AGENTS.md`](../../../../AGENTS.md) and
[`../../../../00-INDEX.md`](../../../../00-INDEX.md). A chat, brief, roadmap item, old product name,
test result or implemented behavior cannot outrank this hierarchy.

## 3. Frozen architecture and packaging constraints

The following are binding and must not be re-litigated by later reconciliation:

1. **One company and one platform.** Pyrnova is one company and one intelligence platform.
2. **Core is shared.** Core is the shared canonical data/evidence/provenance/temporal/source-rights/
   identity/replay/infrastructure substrate. The mapping is semantic; it does not claim a separately
   deployed or fully modular Core service.
3. **PyrAI is shared, model-agnostic capability.** PyrAI is the shared intelligence and orchestration
   layer. It is not a fifth customer-facing peer product, and full PyrAI implementation is not claimed.
   Model output does not become authoritative fact by virtue of model generation.
4. **Four distinct customer-facing products.** Scout, Strike, Vector and Atlas are complementary,
   distinct products. They are not mandatory sequential pipeline stages and do not own Core or PyrAI.
5. **Current Phase 1 remains one engagement.** The current commercial package is Pyrnova / Strategic
   Change Pilot, with Material Changes as the dominant customer surface.
6. **Strike-led, not Strike-owned.** Phase 1 maps primarily to Strike because customer-specific
   judgement is its commercial center. Shared truth and cross-product-compatible capability do not
   become Strike-owned by participating in Phase 1.
7. **Five states remain separate.** Architectural product identity, implemented capability, capability
   integrated into Phase 1, standalone readiness, and standalone commercial availability are not
   interchangeable.
8. **No automatic catalog or rename.** The locked architecture does not create four current SKUs and
   does not rename the current offer Strike. Separate availability requires recorded readiness and
   later explicit owner approval under D-068.
9. **Current gates take precedence.** Productization planning must not disrupt Live Ops, prelaunch
   convergence, Customer #1 gating, closed M21/M22 work or the current Strategic Change Pilot path.
10. **Canonical truth cannot fork by product.** Product projections may add product-specific state, but
    they must reference, not duplicate, shared identity, evidence, provenance, temporal truth, source
    rights, customer scope, history and other canonical truth.
11. **Evidence doctrine remains binding.** Preserve evidence lineage, source-native identity, raw-source
    provenance, observed-vs-inferred-vs-assessed distinctions, temporal/as-of truth, historical replay,
    no future-data leakage, source rights, tenant isolation, auditability, review/outcome lineage and
    global-vs-customer-private boundaries. `UNKNOWN` and `UNRESOLVED` remain valid states.
12. **Brand hierarchy is referenced, not recreated.** Pyrnova is the parent/institutional identity.
    Current semantic product color families are Scout green, Strike red/orange, Vector blue and Atlas
    violet/purple; PyrAI uses a subordinate blue/violet treatment and is not a fifth product. Exact
    product marks, most production tokens, font families and product imagery remain approval-gated.
    The current working master-logo concept is governed by D-070, while the exact production asset is
    not yet stored. Use
    [`CORPORATE_POSTURE_AND_BRAND.md`](../../CORPORATE_POSTURE_AND_BRAND.md) and
    [`../../../brand/master/README.md`](../../../brand/master/README.md); do not duplicate visual
    doctrine into product specs.

## 4. Current execution boundary

This program is **PLANNING-ONLY**. At the baseline commit:

- `02-EXECUTION.md` authorizes PHASE1-LIVE-OPS-CLOSURE only and explicitly denies broad product
  expansion;
- [`../../../specs/PRELAUNCH_CONVERGENCE_001.md`](../../../specs/PRELAUNCH_CONVERGENCE_001.md) is the
  mandatory open pre-release work order, with current authorization limited to Gate 0 + Bundle 1;
- no production Customer #1 activation or pre-launch-complete / production-ready declaration is allowed
  while mandatory CLOSE items remain incomplete;
- IronMountain Solutions remains a non-customer, non-commercial operational-soak Lens, not Customer #1;
- closed M21 and M22 capability remains preserved unless a genuine correctness, safety or acceptance
  defect is found under existing authority.

P01 and P02 may describe evidence and semantic mappings. They may not modify runtime code, runtime
state, live operations, source activation, customer state, acceptance evidence or commercial gates.

## 5. What later reconciliation may decide

Only within a separately authorized later workstream, and only beneath the precedence above, later work
may:

- classify existing capabilities against Core, PyrAI, Scout, Strike, Vector and Atlas;
- distinguish canonical ownership from an evidence-backed candidate mapping;
- identify shared contracts, coupling, duplication risk, missing boundaries and refactor implications;
- define coherent product jobs, objects, workflows, exclusions and dependencies without claiming they
  are implemented or available;
- propose readiness criteria, sequencing or packaging options for later owner decision;
- recommend documentation, interface or implementation work for a future explicitly authorized phase.

Candidate classifications are not final merely because they appear in a planning artifact.

## 6. What later reconciliation is forbidden to decide

Without a new higher-authority decision and implementation work order, P02–P15 must not:

- alter the company/platform architecture locked by D-067;
- make Core or PyrAI customer-facing peer products, or make products own shared canonical truth;
- encode Scout → Strike → Vector → Atlas as a mandatory pipeline;
- relabel the current commercial offer as Strike or create a four-SKU Phase 1 catalog;
- claim standalone readiness, production readiness, commercial availability, launch, deployment,
  customer acceptance or owner acceptance without the required evidence and approval;
- create pricing, packaging, entitlements, contracts, launch order or numerical readiness thresholds;
- reopen M21/M22, redesign Phase 1, expand current product scope, or bypass prelaunch/Customer #1 gates;
- authorize implementation, runtime refactoring, source activation, model-provider changes, persistent
  operations, data migration or production infrastructure;
- weaken or duplicate evidence, provenance, identity, source-rights, temporal, replay, tenancy,
  auditability, UNKNOWN/UNRESOLVED or review/outcome semantics;
- turn a roadmap item, specification, test, demo, historical artifact or conceptual compatibility into
  a claim of implemented/current/available capability;
- invent product marks, copy, colors, imagery or logo assets beyond current brand authority.

## 7. Anti-drift rules

1. **Label every claim by state.** Use `IMPLEMENTED`, `PARTIAL`, `SPEC-ONLY`, `ROADMAP-ONLY`,
   `HISTORICAL`, `SUPERSEDED` or `UNKNOWN`; do not blend them.
2. **Label ownership authority.** Use `CANONICAL` only when current authority assigns the boundary.
   Otherwise use `CANDIDATE`, `OBSERVED` or `UNRESOLVED` and cite the evidence.
3. **Repository evidence is mandatory.** Name code, tests, specs or current authority for factual claims.
   Absence of evidence is `UNKNOWN`, not proof of absence.
4. **Separate semantics from topology.** A capability can map semantically to Core or a product without
   being a separate service, package, deployment or SKU.
5. **Separate implementation from acceptance.** Passing tests or implemented code does not prove live
   operation, standalone readiness, commercial availability, customer acceptance or owner approval.
6. **Link rather than copy authority.** Repeat only the minimum needed for a usable baseline; canonical
   doctrine remains in its source document.
7. **Preserve historical belief.** Later evidence may resolve prior uncertainty but must not silently
   rewrite point-in-time state or backfill forecasts.
8. **Preserve shared truth.** A proposed product surface consumes governed Core/PyrAI contracts; it does
   not gain a convenience copy as a new authoritative store.
9. **No implementation by implication.** A classification, gap, interface sketch or readiness proposal
   is planning until `02-EXECUTION.md` or a successor explicitly authorizes work.
10. **Stop on genuine conflict.** Record the competing authorities and request reconciliation; do not
    select the broader or newer-sounding interpretation without precedence evidence.

## 8. Common terminology

| Term | Meaning in this program |
|---|---|
| **Pyrnova** | The single company and intelligence platform; also the current Phase 1 commercial brand under existing authority. |
| **Core** | Shared canonical data and infrastructure substrate across products: evidence, provenance, temporal/source-rights/identity/replay and related foundations. A semantic ownership boundary, not proof of a standalone deployed service. |
| **PyrAI** | Shared, model-agnostic intelligence and orchestration capability subordinate to deterministic evidence/truth rules; not a customer-facing fifth peer product. |
| **Scout** | Customer-facing live sensing and signal-discovery product whose primary object is the signal. Product identity is canonical; implemented standalone status is not implied. |
| **Strike** | Customer-facing customer-specific intelligence and judgement product. Current Phase 1 is Strike-led but remains branded Pyrnova and is not Strike-owned. |
| **Vector** | Customer-facing consequence and scenario-modelling product answering “What happens if?”. Existing propagation/exposure work may be foundational but does not prove a complete product. |
| **Atlas** | Customer-facing structural-intelligence and living-operating-picture product for durable entities, relationships and dependencies; not merely a graph viewer. |
| **Productization** | Controlled reconciliation of capability, ownership, contracts, product boundaries, surfaces and readiness. It is not automatic implementation, packaging or launch. |
| **Implemented capability** | Behavior evidenced in current code/tests at a named baseline. It may be internal, partial, unintegrated or not customer-facing. |
| **Integrated Phase 1 capability** | Implemented behavior participating in the current Pyrnova / Strategic Change Pilot path. This does not transfer architectural ownership or create a standalone product. |
| **Standalone readiness** | Repository-recorded evidence that a product has a coherent problem/boundary/surface, production-quality experience, governed access/security/tenancy/evidence behavior, operational support and validation. It is not equivalent to commercial approval. |
| **Commercial availability** | Separately approved purchasability/launch state with explicit positioning, contractual treatment, pricing/packaging, entitlements and launch status. Architecture or readiness alone cannot establish it. |
| **Canonical ownership** | A boundary explicitly assigned by current authority. |
| **Candidate ownership** | A P02 or later evidence-backed observation awaiting authorized reconciliation. |
| **Shared** | Cross-cutting behavior or contract whose final ownership is not necessarily resolved merely by broad reuse. Use with a candidate/authority label. |

## 9. Recorded authority tension — do not silently propagate

The current repository contains stale operational wording, not a product-architecture conflict:

- `02-EXECUTION.md` and the dated `PHASE1_LIVE_OPS_CLOSURE.md` evidence record retain a 7-calendar-day /
  5-business-day soak statement.
- The newer D-066 mandatory work order, `PRELAUNCH_CONVERGENCE_001.md`, revises final Live Ops acceptance
  to an immutable pinned release/worktree and 72 consecutive unattended hours spanning at least 3
  business days; `03-CURRENT-STATE.md` points to that revised rule.

For release-gate planning at this baseline, the mandatory prelaunch work order and current-state pointer
govern the revised final acceptance rule. This program does not edit the older records or claim the gate
has run or passed. Later workstreams must not use the stale duration to make a readiness claim.

## 10. P01 completion test

P01 is complete because the authority precedence, locked constraints, current execution boundary,
allowed/forbidden decision scope, anti-drift rules and terminology required by the program are explicit
and traceable to current repository authority. P01 creates no product strategy or implementation
authority. P02 must use this document as its governing baseline.
