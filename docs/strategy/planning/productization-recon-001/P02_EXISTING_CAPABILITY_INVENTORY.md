# PYRNOVA-PRODUCTIZATION-RECON-001 — P02 existing capability inventory

**Status:** COMPLETE — factual repository inventory only

**Governing baseline:** [`P01_CANON_AUTHORITY_BASELINE.md`](P01_CANON_AUTHORITY_BASELINE.md)

**Repository baseline:** `origin/main` at `12c756f5749ff67e536fa7b597410c0073626a33`

**Scope:** what the repository already contains; no final ownership decision beyond current canon

**Does not authorize:** implementation, refactor, product launch, naming, pricing, packaging or a P03–P15 workstream

## 1. Reading rules

Status labels:

- `IMPLEMENTED` — a current code path and relevant tests exist at the baseline.
- `PARTIAL` — implemented behavior exists, but the named capability or required operating boundary is
  incomplete.
- `SPEC-ONLY` — a current specification exists without a corresponding current runtime path.
- `ROADMAP-ONLY` — recorded future capability, not current implementation authority.
- `HISTORICAL` — retained lineage or dated evidence, not current product authority.
- `SUPERSEDED` — an older interpretation explicitly displaced by current authority.
- `UNKNOWN` — the repository does not establish the fact.

Ownership labels:

- `CANONICAL` means current authority explicitly assigns the layer/product mapping.
- `CANDIDATE` or `OBSERVED` is a P02 classification for later reconciliation, not a final decision.
- `SHARED / UNRESOLVED` means reuse is visible but final architectural ownership is not assigned here.

“Customer-facing” below means a current repository surface exists. It does not mean deployed,
production-ready, customer-accepted, standalone-ready or commercially available. File paths are exact
repository evidence; cited tests establish deterministic/offline behavior only unless explicitly stated.

## 2. Capability inventory

### A. Shared Core foundations and operations

| Capability | Evidence | Status and current surface | Likely ownership | Dependencies, constraints and change character |
|---|---|---|---|---|
| Source registry and adapter estate | `pyrnova/sources/registry.py`; `pyrnova/sources/*.py`; `docs/specs/SOURCE_MANIFEST.md`; adapter tests | `IMPLEMENTED`, mixed maturity. Nine registered source families; some live/archive-proven, some fixture-only, and SBIR blocked. Operator/developer surface, not a standalone customer feed. | **Core — CANONICAL** foundation; source sensing may feed Scout. | Status/reliability claims are dated. `active`, `operational`, `live_proven` and rights approval are distinct. Ownership classification is semantic; splitting adapters into a service would be refactor/deployment work. |
| Source-rights policy and enforcement | `pyrnova/sources/rights.py`; policy data in `pyrnova/sources/registry.py`; `tests/test_source_rights.py`; `docs/strategy/SOURCE_RIGHTS_AUTHORITY.md` | `IMPLEMENTED`; gates request scope, storage representation, derived use, customer display and model input. Customer reads return restricted diagnostics rather than silently disclosing blocked material. | **Core — CANONICAL** | Unknown/unprofiled/degraded/expired rights fail closed. Three current suite failures preserve an unresolved agency-artifact/appropriations rights posture; this is not permission to weaken the gate. Moving it is semantic only; duplicating product gates would be a defect. |
| Retrieval controls and source state | `pyrnova/sources/control.py`; `pyrnova/sources/source_state.py`; `tests/test_source_control.py`; `tests/test_source_state.py` | `IMPLEMENTED`; OFFLINE/LIVE_SAFE/ACCEPTANCE modes, sanitized fingerprints, budgets, retry metadata, breaker, checkpoints and atomic per-source state. Operator-facing. | **Core — CANONICAL** | Must remain one governed control path. The older direct `capture-radar --live` route is not equivalent to governed scheduling. Service separation would require refactor; ownership mapping does not. |
| Scheduling and narrow live driver | `pyrnova/scheduler.py`; `pyrnova/live_ops.py`; `pyrnova/live_ops_acceptance.py`; `tests/test_m12_scheduler.py`; `tests/test_m13_live_ops.py`; `tests/test_live_ops_acceptance.py` | `PARTIAL` operational capability. Scheduler/runner/harness, cadence, ledgers and pinned-plan checks exist; final revised unattended acceptance has not been shown at this baseline. | **Core — CANONICAL**; sensed outputs may support Scout. | No general queue/worker fabric. Live activation, provider calls and soak acceptance remain separately gated. Productization is semantic; production operation/deployment is substantive implementation. |
| Raw evidence archive and provenance | `pyrnova/archive.py`; `pyrnova/models.py` (`Evidence`); `tests/test_archive.py`; `docs/system/DATA_AND_PROVENANCE.md` | `IMPLEMENTED`; exact or rights-approved representation stored by SHA-256 in local or optional S3-compatible archive with observation metadata. Customer APIs expose references, not generic raw download. | **Core — CANONICAL** | Global archive lacks a distinct customer-private evidence policy. Preserve content identity, source-native references, retrieval time and rights version. Provider migration is refactor/infrastructure work. |
| Canonical entities and conservative resolution | `pyrnova/models.py` (`Entity`); `pyrnova/normalize.py`; `pyrnova/resolve.py`; grounding modules; `pyrnova/investigation.py`; resolution/grounding/M22-D tests | `PARTIAL`; deterministic native identifiers, names/aliases and explicit `EXACT`/`PROBABLE`/`AMBIGUOUS`/`UNRESOLVED` behavior exist. Used in search and investigation. | **Core — CANONICAL** shared identity; Atlas consumes it. | Runtime uses several stable schemes (`Entity.id`, `co_*`, program/native tokens); base Entity lacks first-class validity. Consolidating contracts may require refactor. Product-specific resolvers would fork truth. |
| Shared domain objects and global intelligence | `pyrnova/models.py`; `pyrnova/state.py`; engine modules; `db/schema.sql`; `docs/system/DOMAIN_MODEL.md` | `IMPLEMENTED` in Python/JSONL for evidence, events, relationships, opportunities, consequences, threats, predictions and reviews; relational schema is broader than runtime. No direct customer surface. | **Core — CANONICAL** for canonical truth; product projections remain product-specific. | `Claim` is schema-only/partial. Runtime/schema vocabulary is not always one-to-one. Ownership mapping is semantic; activating a database or splitting services requires migration/refactor. |
| Append-only state and persistence | `pyrnova/state.py`; `pyrnova/sources/source_state.py`; customer/intelligence modules; `db/schema.sql`; state and milestone tests | `PARTIAL`; append-only JSONL is current runtime truth, with atomic per-source control files. PostgreSQL is intended direction only; no runtime repository adapter, migration runner or RLS. | **Core — CANONICAL** | Reads load full streams; no multi-process locking or cross-stream transaction. Changing provider requires verified migration preserving identity, provenance, time, tenancy and replay. |
| Temporal truth, AS-OF and replay | `pyrnova/replay.py`; `pyrnova/transitions.py`; `pyrnova/outcomes.py`; `pyrnova/customer_material_changes.py`; `pyrnova/investigation.py`; replay/temporal tests and corpora | `IMPLEMENTED` across principal Phase 1 paths: availability cutoffs, validity, version history, prediction/outcome separation and future-data exclusion. | **Core — CANONICAL** | Some timestamps remain naive; arbitrary new paths are not proven. Industrial Phase 1.5 replay is evaluation-only. Product-specific replay copies would be semantic divergence. |
| Customer profiles, watchlists and private overlays | `pyrnova/customers.py`; `tests/test_m22b_customers.py`; `docs/adr/0002-global-intelligence-customer-private-state.md` | `IMPLEMENTED`; versioned customer profiles, effective watch scope and append-only review actions. Supports customer Material Changes and investigation overlays. | **Core — CANONICAL** customer boundary; current use is Strike-led. | Customer-private state must never promote itself into global intelligence. Reuse is semantic; product-specific tenant stores would require careful reconciliation and likely refactor. |
| Authentication, tenant isolation and onboarding | `pyrnova/access.py`; `pyrnova/onboarding.py`; `pyrnova/ops_server.py`; M22-F access/onboarding/server tests | `IMPLEMENTED` for a controlled pilot: bearer credentials, credential-derived tenant, route checks, local operator separation and seed-free onboarding. Customer-facing access gate exists. | **Core — CANONICAL** shared access/tenancy foundation | Application-layer only; no MFA/SSO/SCIM/enterprise RBAC, DB RLS, hardened edge/TLS or production security review. Standalone entitlements are absent. Extending this is implementation, not reclassification. |
| Backup and isolated restore | `pyrnova/backup.py`; `tests/test_backup_restore.py`; `docs/operations/BACKUP_RESTORE_EVIDENCE.md` | `IMPLEMENTED` and locally verified for manifest/hash validation, isolated restore, semantic preservation and post-restore rights reconciliation. No customer surface. | **Core — CANDIDATE**, strongly aligned with canonical infrastructure substrate | Off-host production destination/schedule and production recovery evidence remain absent. Ownership classification is semantic; deployment is operational work. |
| Alerts, heartbeat and dead-man watcher | `pyrnova/alerts.py`; `pyrnova/heartbeat.py`; `pyrnova/watchdog.py`; `tests/test_operator_alerts.py`; `docs/operations/OPERATOR_ALERTS_EVIDENCE.md` | `PARTIAL`; durable lifecycle, dedupe, severity, transport seam and independent freshness checks are implemented. Real email delivery and deployed watcher/service wiring are unverified. | **Core — CANDIDATE** shared operations | Must not be copied per product. Real transport/deployment requires authorization and operational verification. |
| Read APIs and projections | `pyrnova/ops.py`; `pyrnova/ops_server.py`; `pyrnova/material_changes.py`; `pyrnova/investigation.py`; route/service tests | `IMPLEMENTED` internal HTTP routes and derived read models for Material Changes, search, company, program, review, versions, source health and operator actions. | **SHARED / UNRESOLVED**: Core supplies canonical inputs; current product projections map primarily to Strike. | No versioned external API contract. Projections are not canonical stores. Surface separation may require refactor; duplicating projection truth is prohibited. |
| Runtime and deployment substrate | `pyrnova/cli.py`; `pyrnova/ops_server.py`; `ops/com.pyrnova.live-ops.plist.template`; `docs/system/SYSTEM_ARCHITECTURE.md` | `PARTIAL`; one Python package, CLI, static browser assets, local threaded server and a supervision template. Not a multi-service production platform. | **Core — CANDIDATE** shared infrastructure | No production queue/worker fabric, HA, centralized observability, verified public edge/TLS or completed final soak. Any topology split is future implementation. |

### B. PyrAI foundations

| Capability | Evidence | Status and current surface | Likely ownership | Dependencies, constraints and change character |
|---|---|---|---|---|
| Model-agnostic reasoner seam | `pyrnova/ai.py`; use from `pyrnova/pipeline.py`; pipeline tests | `PARTIAL`; `Reasoner.enrich()` protocol and `NullReasoner` default exist. Deterministic operation requires no model; optional output is non-authoritative metadata/recommendation. No customer AI surface. | **PyrAI — CANONICAL direction** | No provider implementation, shared context service, tool runtime or orchestration plane is established. A full PyrAI layer requires implementation; the current mapping is semantic. |
| Model-input rights gate | `pyrnova/sources/rights.py` (`authorize_model_input`, `guarded_model_call`); `tests/test_source_rights.py` | `IMPLEMENTED` guard for structured normalized/derived, attributed, rights-permitted inputs; no connected model provider. | **Core policy consumed by PyrAI — CANDIDATE boundary** | Rights enforcement must remain canonical and provider-independent. The gate is not evidence of model orchestration. |
| First-class AI claim lifecycle and attribution | `db/schema.sql` (`claim`); `pyrnova/ai.py`; `docs/system/DOMAIN_MODEL.md`; TD-017 | `PARTIAL / SCHEMA-ONLY`; optional `opp.meta['ai']` exists, but no first-class Python Claim repository/validation lifecycle. | **PyrAI — CANDIDATE**, with Core provenance dependency | Implementing persistent attribution would require a governed domain/storage addition, not a naming change. |
| Natural-language query assistance | `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md` area 17; `docs/specs/M22D_INVESTIGATION_SEARCH.md` non-goals | `ROADMAP-ONLY`; current search is deterministic structured retrieval. No RAG, broad document search or NL query planner is implemented. | **PyrAI — CANDIDATE**, potentially supporting all products | Must resolve entities/fields/filters through governed structured query and preserve tenant/time/rights. Requires implementation. |
| Model registry, policy promotion and orchestration | `docs/system/SCORING_AND_DECISION_LOGIC.md`; `docs/strategy/PLATFORM_PRODUCT_ARCHITECTURE.md` | `UNKNOWN / NOT IMPLEMENTED`; repository explicitly reports no model registry or automated policy promotion. | **PyrAI — CANONICAL architectural layer**, detailed ownership unresolved | No product may invent its own authoritative model path. This is future design/implementation, not a repository refactor already waiting to happen. |

### C. Scout and Strike foundations

| Capability | Evidence | Status and current surface | Likely ownership | Dependencies, constraints and change character |
|---|---|---|---|---|
| Broad source sensing and signal-shaped records | Source adapters/registry; `pyrnova/chains.py`; `pyrnova/precursors.py`; `pyrnova/adverse_events.py`; M4–M21 tests/specs | `PARTIAL` relative to Scout. Multi-source acquisition, normalized events, precursor stages and adverse-event parsing exist; live coverage is mixed and current operations remain gated. | **Scout — CANDIDATE**; source/evidence/control stay Core | A Scout boundary would consume Core source contracts rather than own them. Productization is more than moving modules; live breadth, feed semantics and operations remain incomplete. |
| Tagging/classification/context | `pyrnova/capabilities.py`; `pyrnova/adverse_events.py`; `pyrnova/chains.py`; `pyrnova/selectivity.py` and tests | `PARTIAL`; deterministic capability classes, event/catalyst types, precursor stages and funnel dispositions exist. No general user-managed tagging system. | **Scout — CANDIDATE** for signal presentation; shared intelligence contracts unresolved | Existing classifiers are domain-specific. Generalizing them risks changing frozen Phase 1 semantics and requires explicit policy/version work. |
| Signal clustering and adaptable real-time feed | `docs/strategy/PLATFORM_PRODUCT_ARCHITECTURE.md`; `docs/system/DATA_AND_PROVENANCE.md`; Phase 1.5 replay gap record | `ROADMAP-ONLY / NOT IMPLEMENTED` as a coherent capability. First-class multi-source event clustering/amendment lineage is explicitly absent; Material Changes is not an alert firehose. | **Scout — CANONICAL product job**, implementation ownership unresolved | Requires event-lineage contract and surface design. Must not collapse separate evidence or duplicate Core event truth. |
| Opportunity detection and relevance | `pyrnova/engines/`; `pyrnova/pipeline.py`; `pyrnova/match.py`; `pyrnova/review.py`; pipeline/engine/match tests | `IMPLEMENTED`; deterministic candidates, source-native identity, evidence attachment, relevance and system disposition. Operator queue and Markdown brief surfaces exist. | **Strike — CANONICAL primary mapping** | `scoring_v1` and corpora are frozen. The `STRIKE` disposition is a lifecycle value, not proof of the Strike product or launch. Product mapping is semantic; extracting a runtime is refactor. |
| Threat and monitoring intelligence | `pyrnova/threat.py`; `pyrnova/material_changes.py`; M15–M21 specs/tests | `IMPLEMENTED`; evidence-backed threats, severity/confidence separation, outcomes and OPPORTUNITY/THREAT/MONITORING projections. Customer-facing in Material Changes. | **Strike — CANONICAL primary mapping**; Scout sensing and Vector exposure may contribute | Domain coverage is bounded; OFAC is not a compliance-screening product. Preserve assessment vs evidence vs customer lifecycle. |
| Customer-specific Material Changes | `pyrnova/material_changes.py`; `pyrnova/customer_material_changes.py`; `pyrnova/ops.py`; `pyrnova/ops_web/material.*`; M22-A/C/E tests/specs | `IMPLEMENTED`; deterministic customer relevance, observed/assessed separation, evidence references, content-versioned per-tenant fan-out and current browser/API surface. | **Strike — CANONICAL primary mapping**; shared truth remains Core | Current Phase 1 dominant surface, not a standalone Strike availability claim. Reimplementation per product would fork truth. |
| Investigation and deterministic search | `pyrnova/investigation.py`; `pyrnova/ops_web/investigation.*`; `tests/test_m22d_investigation.py` | `IMPLEMENTED`; exact identifier/name/alias and scored partial matching with ambiguity/unresolved states, company/program pages and AS-OF. Customer-facing support surface. | **Strike — CANONICAL supporting mapping**; Atlas consumes structural context | Not broad NL/RAG/document search. It is a derived read projection, not a second graph. Surface split may require refactor; ownership change is not decided here. |
| Human review, predictions and outcomes | `pyrnova/review.py`; `pyrnova/review_queue.py`; `pyrnova/outcomes.py`; `pyrnova/transitions.py`; M5/M6/M11 tests | `IMPLEMENTED`; automated vs human decision, uncertain-join queue, frozen prediction and sourced append-only outcome remain distinct. Operator/customer workflow surfaces vary. | **Strike — CANDIDATE** workflow; lineage/storage remain Core | Do not flatten system assessment, human adjudication, customer action and outcome into one mutable state. |
| Decision Lead Time | `pyrnova/decision_lead_time.py`; `tests/test_decision_lead_time.py`; `docs/evidence/bundle1/B1_3_DECISION_LEAD_TIME.md` | `IMPLEMENTED` derived model; T0–T4 latency, anomalies and `NOT_ESTABLISHED` external lead time. No dedicated GUI. | **Strike — CANDIDATE** metric; Core temporal dependency | Pure derived logic; missing anchors remain UNKNOWN. Semantic classification only. |
| Customer Usefulness / Decision Memory | `pyrnova/decision_memory.py`; `tests/test_decision_memory.py`; `docs/evidence/bundle1/B1_4_DECISION_MEMORY.md` | `IMPLEMENTED` data contract; isolated, append-only customer dispositions/outcomes with signal/evidence/assessment references. No GUI. | **Strike — CANDIDATE** learning workflow; Core customer-private lineage | Not CRM/task/account management. Product surface work would be implementation; global/customer separation must remain. |
| Opportunity lifecycle continuity | `pyrnova/chains.py`; `examples/bundle1/lifecycle_probe.py`; `tests/test_opportunity_lifecycle.py`; B1.5 evidence | `PARTIAL`; cross-stage program continuity and AS-OF work, but notice-level `AMENDS`/`SUPERSEDES`/`CANCELS`/`REISSUES` lineage is absent, cancellation is inert, and recompete can conflate with the original. | **Strike — CANDIDATE**; Core event/identity contracts | Correcting this requires a bounded model change, not semantic relabeling. It is carried beyond current Bundle 1. |
| Current customer and operator UI | `pyrnova/ops_web/material.*`; `investigation.*`; `access.*`; `index.html`/`app.js`; `pyrnova/ops_server.py` | `IMPLEMENTED` local static UI: customer Material Changes, investigation/search, access gate, and local-only Operator Console. No browser E2E suite or deployed acceptance shown here. | **Strike — CANDIDATE** current customer surface; operator UI shared/internal | Existing styling predates the latest full brand doctrine and has hard-coded tokens. Visual remapping would be surface implementation, not ownership proof. |
| Markdown briefs and exports | `pyrnova/brief.py`; `pyrnova/scoreboard.py`; pipeline/ops tests | `IMPLEMENTED`; Signal Brief and Capture Radar report/export are operator/customer-delivery lineage. | **Strike — CANDIDATE / LEGACY SURFACE** | Names and copy need later semantic reconciliation; artifacts do not create a separate product. |

### D. Vector and Atlas foundations

| Capability | Evidence | Status and current surface | Likely ownership | Dependencies, constraints and change character |
|---|---|---|---|---|
| Capital catalysts and commercial consequence | `pyrnova/catalysts.py`; `pyrnova/value.py`; consequence models; `tests/test_m7_consequences.py`; M7 spec | `IMPLEMENTED` bounded domain logic; evidence-backed mechanisms, participants, timing/value posture, assumptions and falsifiers. Mostly operator/evaluation use. | **Vector — CANDIDATE** foundation; current Phase 1 may use it in Strike judgement | This is not a scenario product. Moving ownership is semantic; creating scenario state/workflows requires implementation. |
| Capability fit and company posture | `pyrnova/company.py`; grounding modules; `pyrnova/multisource.py`; `pyrnova/fit.py`; M8–M10 tests/specs | `IMPLEMENTED`; evidence-linked profile, point-in-time facts, PRIME/SUPPORT/TEAM/DEFEND/NO_FIT and explicit blockers/UNKNOWN. | **Strike — CANDIDATE** current use; Vector/Atlas may consume. Final ownership **UNRESOLVED** | Fit is separate from scoring and consequence. Product-specific copies would drift; extracting shared contracts may require refactor. |
| Exposure and bounded propagation | `pyrnova/relationships.py`; `pyrnova/threat.py`; `pyrnova/propagation.py`; M15–M21 tests/specs | `IMPLEMENTED`; explicit join class/materiality/validity, bounded paths, cycle/duplicate guards, degrading confidence and retained path provenance. Some network view exists in operator service. | **Vector — CANDIDATE** foundation; Atlas supplies structural context; current threat judgement maps to Strike | Not interactive “what happens if?” modelling. Reuse requires stable relationship/exposure contracts; a separate graph would fork truth. |
| Strategic scenario engine | `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md` area 8; platform architecture | `ROADMAP-ONLY`; no scenario object/store/engine or coherent Vector workflow is implemented. | **Vector — CANONICAL product job** | Must be evidence/graph constrained rather than generic model speculation. Requires separately authorized design/implementation. |
| Evidence-backed relationship graph | `pyrnova/models.py` (`Relationship`); `pyrnova/chains.py`; `pyrnova/relationships.py`; `pyrnova/grounding*.py`; relationship/chain tests | `IMPLEMENTED` bounded graph primitives and accepted/deferred/rejected join semantics. No standalone graph database or Atlas runtime. | **Atlas — CANDIDATE** foundation; identity/provenance/time remain Core | Relationship representations span modules and types. Contract reconciliation may require refactor; a second product-owned graph is forbidden. |
| Company/program structural projections | `pyrnova/investigation.py`; `pyrnova/ops.py`; investigation UI/tests | `IMPLEMENTED` computed company/program identities, relationships, government activity, history, gaps and customer overlay. | **Atlas — CANDIDATE** foundation; current supporting use maps to Strike | Projection is read-only and derived, not a durable continuously maintained operating picture. Turning it into one requires implementation. |
| Living operating picture | Platform architecture; roadmap areas for entity dossier/read projections/supply chain | `PARTIAL / ROADMAP-ONLY` relative to Atlas. Durable records and relationships exist, but no standalone, continuously maintained Atlas product boundary/surface/operations are established. | **Atlas — CANONICAL product job** | Requires later factual contract and surface reconciliation. Must preserve Core ownership and avoid “graph viewer = Atlas” drift. |
| Industrial Phase 1.5 replay estate | `examples/replay/industrial_phase1_5/`; `docs/replay/PHASE1_5_INDUSTRIAL_REPLAY_EVIDENCE.md`; `tests/test_phase1_5_replay_evidence.py` | `IMPLEMENTED EVALUATION EVIDENCE`, not production. Expresses facilities, industrial relationships/events and consequence cases; production acquisition/identity/relevance/scoring/outcome paths are locked. | **Vector/Atlas — OBSERVED** candidate evidence only | Cannot be claimed as current product capability. Promotion requires new execution authority and production paths. |

### E. Brand and surface infrastructure

| Capability | Evidence | Status and current surface | Likely ownership | Dependencies, constraints and change character |
|---|---|---|---|---|
| Parent/product visual doctrine | `docs/strategy/CORPORATE_POSTURE_AND_BRAND.md`; D-069/D-070; `docs/brand/master/README.md` | `CANONICAL` documentation. Parent hierarchy, cyan platform accent and product semantic families are fixed; exact product marks, most tokens/fonts/imagery remain open. Exact production master-logo asset is absent. | Shared brand system; not product-owned | Reference, do not duplicate. Creating marks/tokens/assets requires owner approval and design implementation. |
| Existing static styling system | `pyrnova/ops_web/*.css`; current HTML/JS | `IMPLEMENTED` local UI styling, but it predates full D-069 doctrine and uses several independent hard-coded palettes/type choices. | **SHARED / UNRESOLVED** surface infrastructure | Later design-system extraction would be a refactor. Existing colors are not evidence that product-specific brand systems are complete. |

## 3. Current capability heatmap

This is a foundation map, not a commercial score, priority, readiness claim or implementation order.

Legend: `●` substantial implemented foundation; `◐` bounded/partial foundation; `○` spec/roadmap only;
`—` no material repository evidence found. Cells are P02 observations unless the product mapping is
explicitly canonical in P01.

| Foundation area | Core | PyrAI | Scout | Strike | Vector | Atlas |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Evidence, provenance, rights, time | ● | ◐ | ◐ | ● | ◐ | ◐ |
| Source acquisition and operating controls | ● | — | ◐ | ◐ | — | — |
| Signal/event classification | ◐ | — | ◐ | ◐ | ◐ | ◐ |
| Customer-specific judgement/relevance | ◐ | ◐ | — | ● | ◐ | ◐ |
| Opportunity/threat/monitoring workflow | ◐ | ◐ | ◐ | ● | ◐ | ◐ |
| Consequence/exposure/propagation | ◐ | ◐ | — | ◐ | ● | ● |
| Entity/relationship/structural context | ● | — | ◐ | ◐ | ◐ | ● |
| Scenario modelling | ◐ | ○ | — | — | ○ | ◐ |
| Search/query | ◐ | ○ | ○ | ● | — | ◐ |
| Customer-facing product surface | ◐ | — | — | ● | — | ◐ |
| Review/outcome/decision memory | ● | ◐ | — | ● | ◐ | ◐ |
| Standalone readiness evidence | — | not a peer product | — | — | — | — |

The last row is deliberately empty: repository evidence does not establish any separately available
Scout, Strike, Vector or Atlas product. Current Phase 1 remains one Pyrnova / Strategic Change Pilot.

## 4. Foundations versus gaps

| Layer/product | Existing foundations | Material factual gaps at this baseline |
|---|---|---|
| **Core** | Registry/adapters, rights gates, archive/provenance, deterministic identity, append-only state, temporal/replay, customer boundaries, pilot auth/onboarding, backup, alerts, read APIs. | Runtime PostgreSQL/RLS/migrations absent; JSONL scale/concurrency limits; identity schemes not fully unified; timestamp consistency gap; production edge/HA/central observability/final soak absent; several source rights/live statuses unresolved or dated. |
| **PyrAI** | Model-agnostic reasoner protocol, NullReasoner, non-authoritative output rule and model-input rights gate. | No provider/orchestration plane, shared context/tool layer, first-class runtime Claim lifecycle, model registry, policy promotion, NL query planner or customer AI surface. |
| **Scout** | Multi-source adapters, controlled acquisition, archived events/signals, precursor stages, domain classifiers and selectivity instrumentation. | No coherent standalone signal object/feed, event clustering/version lineage, adaptable real-time feed, broad tagging/context UX, NL filtering/querying, standalone surface or live-operational acceptance. |
| **Strike** | The most complete current path: opportunity/threat judgement, customer relevance, Material Changes, investigation/search, review, lifecycle, access/onboarding, outcomes, decision memory and UI. | Current offer is not separately named/launched Strike; standalone readiness/entitlements/operations are absent; opportunity notice lineage/cancellation/recompete gaps remain; UI browser/deployment acceptance and enterprise trust remain open. |
| **Vector** | Consequence, fit, exposure, propagation, paths, falsifiers and industrial replay examples. | No scenario object/engine, counterfactual/versioned scenario state, interactive “what happens if?” workflow, standalone customer surface or readiness evidence. |
| **Atlas** | Entities, programs, evidence-backed relationships, exposures, history, deterministic search and company/program projections. | No continuously maintained standalone operating picture, resolved unified identity/relationship contract, structural update workflow, standalone surface or readiness evidence. Existing investigation view is not itself Atlas. |

## 5. Duplication and coupling watchlist

| Watch item | Current evidence | Productization risk |
|---|---|---|
| Canonical identity has several representations | `models.Entity`, `company.company_id`, `co_*` references, program keys and source-native ids | Product-specific resolvers or convenience ids could split one entity into incompatible truths. Reconcile contracts before topology. |
| Global intelligence vs customer-private state | ADR-0002; `customers.py`; customer fan-out/decision memory | Copying threats/opportunities/evidence into a product-owned tenant store could turn a projection into a second truth system. |
| Material Changes and investigation share derived inputs | `material_changes.py`; `investigation.py`; `ops.py`; ADR-0001 | Separate product read models could disagree on relevance, AS-OF, evidence or identity unless they share canonical contracts. |
| JSONL runtime vs PostgreSQL schema | `state.py`; `db/schema.sql`; TD-001/002/003 | Treating schema-only objects or RLS as implemented would overclaim; parallel repositories could drift without shadow comparison/migration evidence. |
| Relationship/exposure concepts span modules | `models.Relationship`; `chains.py`; `relationships.py`; `threat.py`; `propagation.py` | Vector and Atlas could each invent overlapping graph contracts. Preserve validity, join class, evidence and uncertainty in one canonical pattern. |
| Scoring/fit/consequence are distinct | `replay.py`; `match.py`; `fit.py`; `catalysts.py`; scoring doc | Product-specific “scores” could collapse relevance, attractiveness, confidence, materiality, fit and human judgment. |
| Governed scheduler vs direct live path | `scheduler.py`/`live_ops.py` vs `cli.py` and `docs/specs/LIVE_RUN.md` | A Scout service built from the legacy direct path could bypass budgets, rights, checkpoints or freshness semantics. |
| AI metadata vs schema Claim | `ai.py`; `opp.meta['ai']`; `db/schema.sql` | A product/provider-specific AI store could make model output authoritative or lose attribution. |
| Event vs opportunity lifecycle | `chains.py`; B1.5 evidence | Without notice-level lineage, product projections may disagree about amendment, cancellation, reissue and recompete identity. |
| Event clustering is absent | provenance doc; Phase 1.5 evidence | Scout/Atlas/Vector could independently cluster the same source records and create incompatible event identity/history. |
| Access and entitlement are currently one pilot boundary | `access.py`; `ops_server.py`; M22-F | Per-product client-side gates would weaken credential-derived tenancy; standalone entitlements need a shared server-side model. |
| UI tokens are duplicated/hard-coded | `ops_web/styles.css`, `material.css`, `investigation.css`, `access.css` | Product color work could fragment accessibility and parent hierarchy unless a later approved shared system is extracted. |
| Operational alerts and source health are not product-specific | `alerts.py`; `watchdog.py`; scheduler/health reports | Separate alerting stacks would fragment failure truth and incident history. |

## 6. Legacy and stale naming

| Name/statement | Repository locations | Current interpretation |
|---|---|---|
| **Capture Radar** | `pyproject.toml`, `pyrnova/__init__.py`, `cli.py`, `pipeline.py`, `brief.py`, Operator Console copy, `docs/specs/CAPTURE_RADAR_V1.md` | Valid implementation/history name for the opportunity engine and CLI path; not current company/category/product authority and not automatically Scout or Strike. Package metadata and CLI copy still use it. |
| **Business Opportunity Pipeline** | `pyrnova/__init__.py`; current-state historical note; archived authority | Historical Phase 1 lineage. The `__init__.py` statement that it is the “only” initial phase is stale against current Material Changes authority. |
| **Signal Brief / Capture Radar Report** | `pyrnova/brief.py`; console export | Implemented delivery artifacts with legacy naming; not standalone products. |
| **STRIKE** lifecycle/disposition | `models.py`, `review.py`, replay/scoring docs | A deterministic disposition/state. It must not be confused with the title-cased customer-facing **Strike** product. |
| **Operator Console v0.1** | current `ops_web/index.html` plus historical orphan references in `06-HISTORY.md` | The orphan console is superseded; canonical main has a later internal Operator Console. Do not revive or merge the orphan branch. |
| **One product** | D-062 / Decision 16 language retained in product-commercial authority | Current only for Phase 1 packaging. Permanent company-wide single-product architecture is superseded by D-067. |
| **M14 active spec** | `docs/specs/M14_MULTI_SOURCE_EXPANSION.md` header | Stale status label: current state says M2–M21 are closed. Its implemented contracts remain evidence. |
| **7 days / 5 business days soak** | `02-EXECUTION.md`; dated Live Ops closure evidence | Stale for final release acceptance; D-066/PRELAUNCH-CONVERGENCE-001 revises the final rule to 72 consecutive hours across at least 3 business days on an immutable pinned release. |
| **Operator alerts not on main** | `docs/operations/OPERATOR_ALERTS_EVIDENCE.md` | Dated branch-state statement. `docs/operations/PHASE1_INTEGRATION_EVIDENCE.md` and current source tree establish later integration; real delivery remains unverified. |
| **Historical test counts/status snapshots** | milestone specs, evidence files, `03-CURRENT-STATE.md` | Dated evidence only. They do not supersede a current run or prove runtime/deployment acceptance. |

## 7. Unanswered factual questions for later evidence-led work

These are not invitations to assume answers. Later workstreams must resolve them from authority, code,
tests, runtime evidence or an explicit owner decision.

1. What single canonical identity contract should encompass `Entity.id`, company refs, program keys and
   source-native identifiers without rewriting historical ids?
2. Which relationship/exposure representation is canonical at each boundary, and which module variants
   are projections or candidates for consolidation?
3. Which registered sources are currently reachable, rights-approved, live-enabled and operational at
   the time a future product depends on them? Dated registry/evidence is not a current probe.
4. What is the authoritative event identity/version-lineage contract for duplicate reports,
   amendments, cancellations, reissues and recompetes?
5. Does Scout require a new canonical signal object, or is an existing Event/ProgramSignal structure
   sufficient after evidence-based comparison?
6. What persisted claim/attribution contract is required before any real PyrAI provider path, and which
   model-assisted actions may remain ephemeral?
7. Which deterministic services are shared inputs to Vector scenarios, and what new state would a
   scenario create without changing canonical facts?
8. What makes Atlas continuously maintained rather than a computed investigation view, and which
   structural states are canonical versus projections?
9. Which current HTTP routes are internal implementation details versus candidates for a stable shared
   contract? No versioned external API authority exists.
10. What product-neutral entitlement model is required before standalone products can share one tenant
    safely? Current bearer access does not answer this.
11. Which UI tokens/assets can be reused under D-069/D-070, and which require owner approval? The exact
    production master-logo asset and product marks remain absent/open.
12. What current runtime evidence closes source-coverage, final-soak, browser, alert-delivery, public-edge,
    backup-destination and production-security gaps? Tests and dated branch evidence cannot answer this.

## 8. Verification and current repository conflicts

P02 changed documentation only. A full baseline test run was executed with the canonical virtual
environment and bytecode/cache disabled. It completed with three known failures, matching the documented
Gate 0 Category-C source-rights blockers:

- appropriations archive path has no matching reviewed source policy;
- acquisition-forecast raw archive use has no matching reviewed/allowed representation;
- source-expansion offline flow attempts representations incompatible with current SEC/forecast rights
  policies.

See `docs/operations/GATE0_TEST_ADJUDICATION.md`. The failures were not changed, skipped or reclassified by
this program. Three tests also skipped under the current local environment; no runtime or live-provider
claim is inferred.

Other reconciliation notes:

- current implementation is a single package/runtime, not separate Core/PyrAI/product services;
- final Live Ops/prelaunch acceptance remains open and outranks productization implementation;
- source reliability/status and operational evidence are dated and must be revalidated when relied on;
- exact standalone product readiness, commercial availability and owner acceptance remain unclaimed.

## 9. P02 completion boundary

This inventory is sufficient to drive later ownership/contracts/product-definition work because it
records current capability, evidence, state, surface, candidate mapping, dependencies, gaps and
refactor implications without deciding unresolved ownership. It does not rank products commercially or
authorize an implementation order.
