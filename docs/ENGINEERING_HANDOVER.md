# Engineering handover

Status: onboarding path; not a production readiness claim  
Last reviewed: 2026-09-12

## What you are taking over

Pyrnova is a compact Python evidence/intelligence application for Phase 1 federal-contractor Material
Changes. The implemented development path uses local content-addressed evidence and append-only JSONL;
customer-specific feeds are derived/materialized from global opportunities/threats plus private customer
configuration. Deterministic search, replay, outcome learning, and minimal bearer-based tenant access are
implemented. Production PostgreSQL, edge/TLS, backup/restore, centralized monitoring, and unattended
deployment are not verified.

## First 90 minutes

1. Read [`../AGENTS.md`](../AGENTS.md) and [`../00-INDEX.md`](../00-INDEX.md).
2. Read the three current product/Phase 1 authority documents and current execution/state.
3. Read [`system/SYSTEM_ARCHITECTURE.md`](system/SYSTEM_ARCHITECTURE.md),
   [`system/DOMAIN_MODEL.md`](system/DOMAIN_MODEL.md), and [`REPOSITORY_MAP.md`](REPOSITORY_MAP.md).
4. Create/activate a Python 3.10+ environment and install `.[dev]`.
5. Run `python -m pytest` and record commit/environment/results.
6. Run one offline fixture Capture Radar command using temporary state/archive/output directories.
7. Start the local product, inspect Material Changes and `/console`, and identify whether data is demo or
   persisted runtime state.
8. Trace one Material Change back through its source intelligence/evidence references and one customer
   review action forward without changing data.

## Before your first change

State the current milestone, customer, product goal, non-goals, acceptance criteria, authoritative files,
and whether work is CURRENT or ROADMAP. Confirm branch/upstream/worktree state and do not disturb another
contributor’s unfinished checkout.

Then identify:

- canonical state owner;
- identity and time semantics;
- global versus customer-private boundary;
- named policy/engine version;
- failure and unknown behavior;
- focused and full verification needed;
- documentation update trigger.

## Suggested first bounded change exercise

Choose a documentation/test-only investigation, not a new feature: take one existing source fixture,
locate its registry entry, request parser, archive metadata, normalized id/time fields, test, replay or
Material Change path, and document any discrepancy. Do not make a live call. This exercises repository
navigation without changing scoring, source activation, or customer behavior.

## Things not to change casually

- authority hierarchy or current execution scope;
- `scoring_v1`, thresholds, severity/materiality bands, or frozen corpus results;
- stable source/entity/opportunity/threat/Material Change ids;
- evidence archive/hash/provenance semantics;
- future-data exclusion, relationship validity, prediction immutability, or absence→UNKNOWN behavior;
- global/customer-private state separation and tenant authorization;
- source mode/budget/cadence/breaker/checkpoint ordering;
- customer review lifecycle or rebuild/version idempotency;
- production schema without migration/apply/compatibility evidence;
- Phase 1.5 research as though it were current product behavior.

## Common tasks

| Task | Read first | Code/tests |
|---|---|---|
| Add/fix source adapter | source doctrine/manifest + source guide | `sources/`, matching source test, M12/M13 controls |
| Change domain object | domain model + relevant spec/ADR | owning module/models/schema, focused invariant tests |
| Change scoring/relevance | scoring doc + execution authority | replay/match/material_changes plus full corpus |
| Change time/replay | temporal doc + ADR-0003 | replay/outcomes/customers/relationships plus leakage tests |
| Change customer path | ADR-0002/security doc | customers/material changes/access/ops + cross-tenant tests |
| Change HTTP/UI | security + relevant M22 spec | ops_server/ops_web + route tests and browser verification |
| Change persistence | infrastructure doctrine + limitations | StateStore/archive/schema; migration/shadow/restore tests |
| Operate live source | operations runbook + authority | scheduler/live_ops/source state; dated acceptance evidence |

## Current known traps

- Inspect canonical `main` against `origin/main`; do not assume a remembered branch state remains current.
- `02-EXECUTION.md` and `05-BACKLOG.md` contain stale internal status text. Use the full authority order and
  stop on a genuine unresolved conflict.
- `capture-radar --live` is the original direct manual path, not the governed M12/M13 scheduler path.
- `PYRNOVA_DATABASE_URL` is configuration only; no runtime PostgreSQL repository uses it.
- `db/schema.sql` is not tested as a migration. REPO-RECONCILE-001 found no duplicate `reason` column,
  but clean PostgreSQL apply/upgrade validation remains unperformed.
- The default server may fall back to tracked demo intelligence/customers on empty local state.
- Source registry connectivity/reliability text is dated; do not present it as current without a new run.
- Test skips can hide real archive/socket/browser/deployment coverage.
- `StateStore` reads whole JSONL streams and is not a multi-process transaction layer.

## Completion and handoff

Before handing over a work block:

1. confirm scope stayed authorized and no deferred feature became a dependency;
2. inspect changed paths and secrets/runtime artifacts;
3. run focused and proportionate full verification;
4. state fixture/archive/live/browser/deployed/owner evidence separately;
5. update relevant system/spec/ADR/runbook/limitations docs;
6. record exact branch, commit, upstream/push, and unresolved integration state;
7. leave rollback/recovery instructions for material state changes.

## Handover readiness assessment

The repository now supplies a coherent orientation, architecture, domain semantics, source workflow,
testing model, operations runbook, risk register, and diligence index. A senior engineer should be able to
make a bounded local change without founder oral history.

Readiness remains conditional until an unfamiliar engineer completes the path on a clean machine and the
production persistence/deployment/restore/security gaps are resolved or explicitly accepted for the
intended customer posture.
