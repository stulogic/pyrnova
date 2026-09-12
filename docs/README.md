# Pyrnova documentation

This is the role-based landing page for Pyrnova documentation. It does not alter the authority hierarchy
in [`../00-INDEX.md`](../00-INDEX.md).

## Understand Pyrnova

Read in this order:

1. [`../README.md`](../README.md) — product, boundaries, quick start, and architecture summary.
2. [`system/SYSTEM_ARCHITECTURE.md`](system/SYSTEM_ARCHITECTURE.md) — implemented planes and data flow.
3. [`system/DOMAIN_MODEL.md`](system/DOMAIN_MODEL.md) — identities, state, time, evidence, and invariants.
4. [`system/DATA_AND_PROVENANCE.md`](system/DATA_AND_PROVENANCE.md) — source-to-evidence lineage.
5. [`system/REPLAY_AND_TEMPORAL_TRUTH.md`](system/REPLAY_AND_TEMPORAL_TRUTH.md) — historical reconstruction.
6. [`system/SCORING_AND_DECISION_LOGIC.md`](system/SCORING_AND_DECISION_LOGIC.md) — current policies and
   human decision boundaries.
7. [`system/SECURITY_AND_TENANCY.md`](system/SECURITY_AND_TENANCY.md) — actual access controls and limits.

## Change Pyrnova

1. Read [`../AGENTS.md`](../AGENTS.md) and perform its start-of-work check.
2. Resolve scope using [`../00-INDEX.md`](../00-INDEX.md); only [`../02-EXECUTION.md`](../02-EXECUTION.md)
   authorizes current implementation.
3. Follow [`development/ENGINEERING_GUIDE.md`](development/ENGINEERING_GUIDE.md).
4. For a source, follow [`development/SOURCE_ADAPTER_GUIDE.md`](development/SOURCE_ADAPTER_GUIDE.md).
5. Verify against [`development/TESTING_AND_ACCEPTANCE.md`](development/TESTING_AND_ACCEPTANCE.md).
6. Record a materially important architectural decision under [`adr/`](adr/README.md), but only when
   authority and code evidence support it.

## Operate Pyrnova

- [`operations/OPERATIONS_RUNBOOK.md`](operations/OPERATIONS_RUNBOOK.md) — local operation, live-safe source
  control, failure response, restart/recovery, and explicit production gaps.
- [`OPERATOR_CONSOLE.md`](OPERATOR_CONSOLE.md) — local Operator Console and customer-access commands.
- [`specs/LIVE_RUN.md`](specs/LIVE_RUN.md) — narrow founder live-run walkthrough; use only when fresh
  retrieval is authorized.
- [`specs/SOURCE_INGESTION.md`](specs/SOURCE_INGESTION.md) and
  [`specs/SOURCE_MANIFEST.md`](specs/SOURCE_MANIFEST.md) — binding source-operation contracts.

## Review Pyrnova technically

- [`TECHNICAL_DILIGENCE.md`](TECHNICAL_DILIGENCE.md) — evidence index and explicit unverified areas.
- [`KNOWN_LIMITATIONS_AND_TECH_DEBT.md`](KNOWN_LIMITATIONS_AND_TECH_DEBT.md) — prioritized evidenced register.
- [`REPOSITORY_MAP.md`](REPOSITORY_MAP.md) — code, dependencies, tests, and documentation by area.
- [`ENGINEERING_HANDOVER.md`](ENGINEERING_HANDOVER.md) — new-engineer readiness and first bounded change.
- [`audit/DOCS-001_DOCUMENTATION_AUDIT.md`](audit/DOCS-001_DOCUMENTATION_AUDIT.md) — the 2026-09-12
  documentation audit and gap disposition.

## Governing authority

The exact precedence is in [`../00-INDEX.md`](../00-INDEX.md). In summary:

1. owner decisions and the Phase One Constitution;
2. cross-phase product and commercial authority;
3. Phase 1 product and implementation authority within Phase 1 scope;
4. execution, state, milestone, and evidence records;
5. architectural authority;
6. roadmap;
7. research;
8. historical and superseded records.

System, developer, operations, ADR, handover, audit, and diligence documents are descriptive. They must
point to authority and code, not silently create new product scope.

## Historical and acceptance evidence

- `specs/` states milestone and subsystem contracts.
- `replay/` records dated replay/acceptance evidence.
- `handovers/` is dated continuity evidence and may be stale.
- `archive/` retains superseded authority.
- `research/` informs decisions but never authorizes implementation.
- `outbound/` and `targets/` are customer/target working material, not system authority.

## Ownership and freshness

“Owner” below is a role, not a named person. Updates are event-driven.

| Document area | Purpose | Owner role | Update trigger | Controlling source | Last reviewed |
|---|---|---|---|---|---|
| Root README and this page | Entry and routing | Engineering lead | Product surface or doc topology changes | Authority index + repository | 2026-09-12 |
| `system/SYSTEM_ARCHITECTURE.md` | Implemented design | Engineering lead | Data flow, state owner, or boundary changes | Code + architecture authority | 2026-09-12 |
| `system/DOMAIN_MODEL.md` | Canonical semantics | Domain/engineering lead | Model, identity, lifecycle, or time semantics change | Models + schema + specs | 2026-09-12 |
| `system/DATA_AND_PROVENANCE.md` | Evidence lineage | Data engineering lead | Source/archive/provenance contract changes | Registry + archive + source specs | 2026-09-12 |
| `system/REPLAY_AND_TEMPORAL_TRUTH.md` | Historical truth | Intelligence engineering lead | Replay/outcome/cutoff behavior changes | Replay code + corpora + specs | 2026-09-12 |
| `system/SCORING_AND_DECISION_LOGIC.md` | Decision policies | Intelligence/product owner | Policy/version/review semantics change | Code + approved authority | 2026-09-12 |
| `system/SECURITY_AND_TENANCY.md` | Security boundary | Security/engineering lead | Identity, route, store, deployment, or tenant changes | Access code + tests | 2026-09-12 |
| `development/` | Safe engineering workflow | Engineering lead | Tooling, layout, or acceptance process changes | Repository + CI/runtime evidence | 2026-09-12 |
| `operations/` | Operation and recovery | Operations owner | Runtime, source, persistence, monitoring, or incident path changes | Operational code + verified run evidence | 2026-09-12 |
| `adr/` | Durable architectural rationale | Engineering lead | Material decision is approved/implemented | Existing authority + code | 2026-09-12 |
| `TECHNICAL_DILIGENCE.md` | Reviewer evidence index | Engineering lead | Release, material risk, dependency, or control changes | Repository evidence | 2026-09-12 |
| `KNOWN_LIMITATIONS_AND_TECH_DEBT.md` | Risk register | Engineering/product owners | Risk discovered, mitigated, accepted, or reprioritized | Tests/incidents/code/authority | 2026-09-12 |

Historical test counts, connectivity checks, and live runs remain dated evidence. They are never silently
promoted to current operational or production acceptance.
