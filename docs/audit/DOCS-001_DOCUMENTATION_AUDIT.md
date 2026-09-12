# DOCS-001 documentation audit

Status: descriptive audit, not authority  
Audited: 2026-09-12  
Baseline: local `main` at `ce7ee5c`, isolated branch `docs-001-documentation-foundation`

## Safety and scope

The canonical checkout was not changed. At audit time its local `main` was one commit ahead of and two
commits behind `origin/main`; the common parent was `ff8f475`. The local-only tip adds the owner-approved
product/commercial authority. The remote-only tips change documentation/brand assets. Production code is
identical across those two tips. A separate `phase1.5-replay-evidence` worktree exists and was inspected
read-only. This audit does not merge, rebase, reset, stash, reconcile, or alter either existing worktree.

The documentation branch therefore starts from local `main`: it preserves the owner-approved authority
and changes documentation only. Its divergence from `origin/main` is an explicit integration constraint,
not something DOCS-001 resolves.

## Audit method

Reviewed repository navigation and authority, all tracked Markdown, `db/schema.sql`, package modules,
source registry/adapters, archive and state implementations, replay corpora, Material Change/customer
paths, access and HTTP routes, CLI, frontend assets, tests, configuration, and branch/worktree state.
Claims in the foundation documents are tied to code or an existing authority/specification. Unverified
production behavior is labelled as such.

## Existing-document disposition

| Area | Disposition | Finding |
|---|---|---|
| `AGENTS.md`, `00-INDEX.md`, `01-PROJECT-AUTHORITY.md` | KEEP | Clear authority hierarchy and anti-drift rules. `00-INDEX.md` needed links to role-based docs. |
| `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` | KEEP | Owner-approved tier-1 authority on local `main`; must not be summarized into a replacement authority. |
| Other `docs/strategy/` files | KEEP | Current companions/roadmap with explicit authority levels. Research/roadmap must remain non-executing. |
| `02-EXECUTION.md` | UPDATE by authority owner | Top records M22-F closed, but “Immediate sequence” still stops after M22-D. DOCS-001 does not reconcile authority-adjacent state. |
| `03-CURRENT-STATE.md` | UPDATE carefully | Strong evidence ledger but very long, repeats historical intermediate states, and has dated counts. Retain; future state reconciliation should compact without erasing history. |
| `04-DECISIONS.md` | KEEP | Compact durable decision ledger. New ADRs cross-reference rather than duplicate it. |
| `05-BACKLOG.md` | UPDATE by authority owner | P0 still describes M2/M10 as open although execution/current-state documents record them closed. Do not silently use backlog as current work. |
| `06-HISTORY.md` | KEEP | Appropriate historical record, though milestone chronology could be normalized later. |
| Root `README.md` | UPDATE | Previously centered Capture Radar and did not route to the product/commercial authority or cross-cutting docs. |
| `docs/architecture/` | KEEP + MERGE navigation | Strong doctrine; the old architecture README was only a compact module list. Cross-cutting system docs now complement it. |
| `docs/specs/` | KEEP | High-value milestone and subsystem contracts; many are the best detailed evidence for implemented decisions. They are fragmented and sometimes carry superseded “next” text. |
| `docs/replay/` | KEEP as evidence | Strong dated acceptance/replay record. Never current authority or permanent test-status proof. |
| `docs/handovers/` | KEEP as historical | Dated M2/M3 handover is superseded by current state and should remain clearly historical. |
| `docs/archive/` | KEEP as archived | Superseded authority correctly retained. |
| `docs/research/` | KEEP as research | Useful decision provenance; non-authoritative. |
| `docs/outbound/`, `docs/targets/` | KEEP, restrict access | Customer/target working material; not system documentation and not appropriate for broad diligence disclosure by default. |
| `.env.example`, `docs/specs/LIVE_RUN.md` | UPDATE | Corrected the nonexistent SQLite implication and marked LIVE_RUN as the narrow manual direct-live path, not the unattended-operations runbook. |
| `docs/specs/SOURCE_INGESTION.md` | UPDATE | Extended the implementation boundary through M12/M13 and distinguished the bounded scheduler/live driver from a general daemon and the original direct-live CLI. |
| `docs/specs/SOURCE_MANIFEST.md` | UPDATE | Preserved dated connectivity evidence, removed its contradictory availability sentence, and made registry rights/status metadata the operational control rather than asserting blanket public-domain permission. |

## Implementation coverage and gaps

| Topic | Existing evidence before DOCS-001 | Audit result |
|---|---|---|
| Architecture | Module map, engineering doctrine, milestone specs | Missing a single end-to-end system architecture and state-ownership view. |
| Domain semantics | Dataclasses, schema comments, milestone specs | Rich but dispersed; missing one canonical descriptive glossary with identity/time/tenancy rules. |
| Provenance | Archive code, source doctrine/manifest, replay specs | Strong pieces; missing source-to-presentation lineage and retention/revision synthesis. |
| Replay/time | Replay code and milestone evidence | Strong implementation; missing a reader-oriented temporal model and explicit Phase 1/1.5 separation. |
| Scoring | `replay.py`, `match.py`, review/fit/threat specs | Multiple score/confidence concepts needed one boundary document. |
| Security/tenancy | M22-F spec, access code/tests | Detailed milestone doc; missing a current control matrix and application-layer/RLS truth. |
| Source adapter development | Per-adapter code and source specs | Missing an end-to-end engineer workflow and production activation checklist. |
| Engineering workflow | README, AGENTS, doctrine | Missing setup/change/migration/debug/release guide. |
| Testing | 75 test files and replay docs | Strong coverage; missing hierarchy, environment skips, and merge/release evidence rules. |
| Operations | M12/M13 specs, Operator Console doc | Missing one runbook distinguishing local, live-safe, acceptance, and planned production operation. |
| Repository navigation | `00-INDEX.md`, architecture map | Authority navigation strong; implementation-to-test map incomplete. |
| Technical debt | Scattered limitations sections | Missing one prioritized, evidenced register. |
| ADRs | `04-DECISIONS.md` | Durable product/engineering decisions exist, but no focused architecture rationale format/index. |
| Diligence | Authority, history, tests, schema | Missing a reviewer evidence index and AI-assisted-development trust posture. |

## Documentation architecture established

```text
docs/
├── README.md                         role-based landing page
├── ENGINEERING_HANDOVER.md           senior-engineer onboarding path
├── REPOSITORY_MAP.md                 implementation discovery map
├── KNOWN_LIMITATIONS_AND_TECH_DEBT.md evidenced risk register
├── TECHNICAL_DILIGENCE.md            diligence evidence index and boundaries
├── system/                           descriptive current-system truth
├── development/                      safe engineering/change guidance
├── operations/                       operating and recovery guidance
├── adr/                              evidenced architecture decisions
├── architecture/                     binding doctrine/architecture authority
├── specs/                            detailed subsystem/milestone contracts
├── replay/                           dated acceptance/replay evidence
├── strategy/                         governing strategy and roadmap
├── research/                         non-authoritative analysis
├── handovers/ and archive/           historical/superseded evidence
└── outbound/ and targets/            restricted working material
```

## Supersession and archival decisions

No file was deleted, moved, or archived. The new root README supersedes the former README’s role as the
Capture-Radar-centric entry point. `docs/README.md` becomes the descriptive documentation landing page.
`docs/system/SYSTEM_ARCHITECTURE.md` supersedes the old architecture README only as the detailed system
description; `docs/architecture/README.md` remains the authority/doctrine index.

## Handover test

After this foundation, a senior engineer can locate architecture, run local tests, find code owners by
module, understand global/customer boundaries, trace a source through archival and projections, add a
source against a checklist, and identify production gaps. The test is conditionally passed because a
real clean-machine setup, production deployment, PostgreSQL integration, restore drill, and engineer
walkthrough were not performed in DOCS-001.

## Validation evidence

At `docs-001-documentation-foundation` before commit on 2026-09-12:

- all relative Markdown links from the root README, index, and `docs/**/*.md` resolved inside the
  repository;
- `git diff --check` reported no whitespace errors;
- the changed-path review contained Markdown plus explanatory `.env.example` comments only, with no
  product, schema, test, corpus, asset, or runtime-state change;
- the unchanged test suite completed with **612 passed and 3 skipped in 2.02 seconds** using the
  canonical checkout's existing virtual environment with the isolated worktree on `PYTHONPATH`;
- skips were explicit environment/evidence boundaries: two require the gitignored real OFAC archive and
  one requires a loopback socket bind that this execution environment denied.

This is automated repository evidence, not browser, live-provider, deployed-runtime, clean-machine, or
owner acceptance.

## Remaining documentation debt

- **P0:** authority owner reconciles divergent documentation tips and stale `02-EXECUTION.md`/
  `05-BACKLOG.md` status before merging DOCS-001.
- **P0:** validate/fix `db/schema.sql` as an executable migration artifact before claiming PostgreSQL
  readiness; the current file contains a duplicate `reason` column in `join_review`.
- **P1:** create tested migrations and a runtime PostgreSQL repository adapter, then update storage and
  recovery documentation.
- **P1:** perform a clean-machine onboarding exercise and a controlled restore drill; record dated proof.
- **P1:** add CI/static/security/dependency checks only after choosing a proportionate toolchain.
- **P2:** compact `03-CURRENT-STATE.md` and milestone specs by preserving detailed history under
  `docs/replay/`/`06-HISTORY.md` and keeping a short present-tense state page.
- **P2:** generate a route/API reference if the HTTP surface stabilizes; avoid an unstable API dump now.

## Production impact

None. DOCS-001 changes Markdown and explanatory comments in `.env.example` only. It does not modify
product code, schema, tests, corpora, runtime state, source state, credentials, or existing worktrees.
