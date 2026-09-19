# Pyrnova platform and product architecture

_Status: LOCKED owner-approved cross-phase architecture · effective 2026-09-19 · recorded by D-067 ·
commercial packaging authority closed by D-068_

> **Authority level and scope.** This document records the owner-approved company, platform-layer and
> product boundaries. It is a companion to `PRODUCT_COMMERCIAL_AUTHORITY.md` at the cross-phase
> product-authority tier. `PHASE_1_PRODUCT_AUTHORITY.md` continues to control current Phase 1 packaging
> and implementation scope, and `02-EXECUTION.md` alone authorizes implementation. This decision does
> not itself create a code-reorganization or product-build workstream.

## 1. Canonical architecture

Pyrnova is **one company and one intelligence platform**.

The platform has two shared capability layers and four customer-facing products:

```text
                         PYRNOVA

        SCOUT          STRIKE          VECTOR          ATLAS
     live sensing     judgement      consequence      structural
       + signals     + relevance      + scenarios     intelligence
            \            |               |            /
             \-----------+---------------+-----------/
                         PYRAI
              shared model-agnostic intelligence
                    and orchestration layer
                           |
                          CORE
             shared data and infrastructure substrate
```

The diagram shows shared dependencies, not a mandatory execution sequence. In particular, the products
must not be encoded as `Scout -> Strike -> Vector -> Atlas` pipeline stages.

## 2. Shared platform layers

### Core — shared data and infrastructure substrate

Core owns shared foundational capabilities and canonical intelligence/data infrastructure used across
products. No customer-facing product owns Core. Product boundaries must not create competing versions
of canonical identity, evidence, provenance, temporal truth, source rights, customer boundaries,
historical state or other shared truth.

The current evidence archive, source controls, canonical identities, append-only state, temporal/replay
semantics, global-versus-customer boundaries and shared delivery infrastructure are compatible Core
foundations. This is a semantic mapping, not a claim that the repository already has a separately
deployed or fully modular `Core` service.

### PyrAI — shared intelligence and orchestration layer

PyrAI is model-agnostic shared platform capability, not a customer-facing product. Scout, Strike,
Vector and Atlas may use it.

PyrAI is subordinate to Pyrnova's evidence and truth doctrine:

- model output is not authoritative fact merely because a model generated it;
- source evidence, deterministic computation, human judgement and model-assisted reasoning remain
  attributable and distinguishable;
- provenance, temporal truth, source rights, customer isolation and audit/replay obligations survive
  model or provider changes;
- a model-assisted path may not silently replace an authoritative deterministic state transition.

The current bounded AI seam is compatible with this direction. This decision does not claim that the
full PyrAI layer is already implemented.

## 3. Customer-facing products

### Scout — live sensing and signal discovery

Scout continuously observes broad, high-velocity external information and turns it into useful live
signals through tagging, classification, context, clustering, natural-language filtering/querying and
an adaptable real-time feed. Its primary object is the **signal itself**, rather than deep
customer-specific judgement. Scout is intended to be commercially coherent as a standalone product.

Scout may publish governed intelligence into Core for use by Strike, Vector or Atlas. It does not own
Core, and Strike is not required to receive all intelligence through Scout.

### Strike — autonomous intelligence and judgement

Strike continuously interprets relevant intelligence against a specific customer's situation. It
identifies and qualifies customer-specific opportunities, threats and material developments, applying
evidence, context, relevance and significance judgement to determine what deserves attention or action.
Strike is intended to be commercially coherent as a standalone product.

Existing customer-specific Material Changes, opportunity/threat reasoning, consequence and relevance,
investigation, review, customer lifecycle and outcome functionality map primarily to Strike. They remain
valid and are not discarded or rebuilt merely because the product boundary is now explicit.

### Vector — consequence and scenario modelling

Vector answers **“What happens if?”** for a specific event, intelligence item, decision, scenario,
organization or changing condition. It models plausible consequences, dependencies, second-order
effects, exposures, scenarios and decision implications. Vector is intended to become a coherent
standalone product, not just a visualization or minor screen inside Strike.

Existing consequence, exposure and propagation work may be compatible foundations. The repository does
not thereby claim a complete Vector product or authorize its implementation.

### Atlas — structural intelligence and living operating picture

Atlas maintains durable structural context: entities, relationships, programs, organizations,
dependencies, supply relationships, exposures and other persistent intelligence. It is a continuously
maintained operating picture, not merely a static graph viewer. Atlas is intended to be commercially
coherent as a standalone product.

Existing entity, program, relationship, exposure and investigation state may be compatible foundations.
The repository does not thereby claim a complete Atlas product or authorize its implementation.

## 4. Product relationships

The products are complementary and may exchange intelligence through governed Core/PyrAI interfaces.
Valid relationships include:

- Scout signals informing Strike customer judgement;
- Strike intelligence being passed to Vector for consequence modelling;
- Atlas structural context strengthening Strike judgement;
- Scout events updating Atlas;
- Vector relying on Atlas relationships;
- Strike operating on valid Core inputs that did not originate in Scout.

Interfaces must preserve stable identity, provenance, temporal meaning, source rights, customer scope,
uncertainty and auditability. A product projection may add product-specific state, but it must reference
rather than fork shared canonical truth.

## 5. Mission and doctrine continuity

The architecture decomposes Pyrnova's capabilities; it does not replace the mission. Pyrnova remains
focused on finding, understanding and acting on economically meaningful external change through
evidence-backed, auditable intelligence.

The following remain binding across every layer and product:

- evidence lineage and raw-source provenance;
- deterministic authoritative state and explicit uncertainty;
- point-in-time and temporal truth, historical replay and no future-data leakage;
- source-rights controls and lawful collection;
- global intelligence separated from customer-private state;
- tenant isolation, review history and outcome lineage;
- accepted security, commercial-gate, validation and engineering doctrine;
- `UNKNOWN` and `UNRESOLVED` rather than fabricated certainty.

## 6. Current Phase 1 mapping and packaging

Current Phase 1 remains a single commercial package branded **Pyrnova**, with Material Changes as the
dominant customer surface and the Strategic Change Pilot as the current offer. It maps primarily to
Strike, supported by shared Core foundations and the bounded PyrAI seam.

The current implementation also contains foundations that may later support Scout, Vector and Atlas,
but that does not make those products current Phase 1 SKUs, implemented standalone products or
independently validated offers. M21, M22 and compatible Phase 1 implementation stay closed/preserved
unless a genuine defect is found under existing authority.

The following are therefore distinct:

1. **Company/platform architecture:** Core + PyrAI + Scout/Strike/Vector/Atlas — LOCKED.
2. **Current Phase 1 commercial packaging:** one Pyrnova / Strategic Change Pilot offer — CURRENT.
3. **Existing implementation:** a shared repository and runtime, predominantly supporting the
   Strike-led Phase 1 workflow — CURRENT as evidenced by repository state.
4. **Future product packaging and rollout:** intentionally flexible, readiness-gated and subject to
   later explicit owner approval under D-068; not a current canon blocker.

## 7. Decision status and supersession

- **LOCKED:** one company and one intelligence platform; shared Core and PyrAI; four distinct
  customer-facing products; no product owns the shared layers.
- **CURRENT:** the existing single Phase 1 commercial offer and compatible Material Changes
  implementation remain in force.
- **SUPERSEDED:** any interpretation of “one product” as a permanent company-wide architecture. It is
  superseded by D-067 and this document; D-062/Decision 16 remain current only for Phase 1 packaging.
- **REJECTED:** a mandatory `Scout -> Strike -> Vector -> Atlas` execution sequence, duplicate product
  truth stores, or treating model output as authoritative merely because a model produced it.
- **EXPERIMENTAL:** no product boundary, packaging plan or implementation split is made experimental by
  this decision. Experiments require separate authorization and explicit status.

## 8. Commercial packaging authority — LOCKED

### Current Phase 1 offer

The current commercial offer remains **Pyrnova / Strategic Change Pilot** as one bounded engagement. It
is not automatically renamed Strike or divided into Scout, Strike, Vector and Atlas SKUs. Architectural
product identity does not establish separate launch, entitlement, pricing, contracting, marketing or
standalone production readiness.

Phase 1 is **Strike-led, not Strike-owned**. Customer-specific judgement is the current center of value,
but shared evidence, identity, provenance, temporal truth, source rights and infrastructure remain owned
by Core or the appropriate shared layer. Capabilities mapping to Scout, Vector or Atlas may participate in
the engagement where useful without becoming Strike-owned implementation or standalone commercial
products.

Repository authority must keep these states distinct:

1. architectural product identity;
2. implemented capability;
3. capability integrated into the Phase 1 engagement;
4. standalone product readiness;
5. standalone commercial availability.

### Standalone commercialization

Scout, Strike, Vector or Atlas may become separately purchasable only after repository authority records
explicit standalone readiness and commercial approval. The determination must address, at minimum:

- a coherent standalone customer problem and product boundary;
- coherent product surfaces, workflows and production-quality customer experience;
- entitlement, access, security and tenant-isolation implications;
- evidence, provenance, temporal-truth and auditability behavior;
- operational support and launch status;
- validation evidence;
- commercial positioning and contractual treatment;
- separately owner-approved pricing or packaging.

Reuse existing Pyrnova validation, security, operational, payment, signature and activation gates where
they govern these concerns. Do not create duplicate governance or infer numerical thresholds or pricing
that the owner has not approved.

### Naming and future flexibility

Strike remains the architectural identity of the autonomous customer-specific judgement product. The
current offer does not adopt that commercial name automatically. A later evidence-supported owner
decision may name or package Strike separately, retain it beneath a broader Pyrnova engagement, or adopt
another coherent arrangement.

Future packaging may use individual products, bundles, a full-platform subscription, customer-specific
combinations, enterprise platform arrangements or another coherent model. Architecture must support
separation without hard-coding one future pricing/bundling model or forcing premature SKU proliferation.

These later launch and packaging choices are intentionally deferred until evidence exists. Their deferral
is governed flexibility, not unresolved architecture or a current owner blocker.
