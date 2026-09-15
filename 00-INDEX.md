# Pyrnova authority index

This file is the canonical navigation map for humans and agents.

For role-based descriptive documentation, start at `docs/README.md`. It separates system, developer,
operations, ADR, diligence, and historical material without changing the authority order below.

**Agents:** read `AGENTS.md` first — it carries the anti-drift rules, conflict-resolution procedure, and
the start-of-work / end-of-work checks.

## Mandatory reading order

For implementation work, read only what the task requires, in this order:

1. `00-INDEX.md`
2. `01-PROJECT-AUTHORITY.md`
3. `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` (overarching cross-phase product and commercial authority)
4. `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` (sole product and implementation authority within Phase 1 scope)
5. `03-CURRENT-STATE.md`
6. `02-EXECUTION.md`
7. the relevant document under `docs/specs/`

Then consult `04-DECISIONS.md` when a prior choice affects the task and `05-BACKLOG.md` only for
future-scope questions. `06-HISTORY.md` and `docs/handovers/` are continuity records, not current
instructions.

## Authority order

When documents conflict, use this precedence:

1. **Owner decisions / Phase One Constitution** — highest authority. The locked Constitution is incorporated
   in `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`; current owner decisions control any genuine conflict.
2. **Cross-phase product / commercial authority** — `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` governs
   Pyrnova's overarching product and commercial direction across phases.
3. **Phase 1 product / implementation authority** — `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` is sole
   authority within Phase 1 scope. `01-PROJECT-AUTHORITY.md` and the compatible strategy companions summarize
   or specialize current doctrine; none may erase or redefine cross-phase authority outside Phase 1.
4. **Execution / state / milestone / evidence** — `02-EXECUTION.md`, `03-CURRENT-STATE.md`,
   `04-DECISIONS.md`, and relevant `docs/specs/` implement or record the higher authorities.
5. **Architectural authority** — relevant `docs/architecture/` and `db/` authority.
6. **Roadmap** — `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`, then `05-BACKLOG.md`.
7. **Research** — `docs/research/`. Research informs authority and never authorizes implementation by itself.
8. **Historical / superseded** — `06-HISTORY.md`, `docs/handovers/`, and `docs/archive/`.

Research can inform authority but does not independently authorize implementation. Roadmap entries do
not belong to the current milestone unless `02-EXECUTION.md` explicitly authorizes them. Historical
documents never override current authority. If a conflict is genuinely unresolved, record it (in
`04-DECISIONS.md` or the current work order) rather than silently choosing the broader scope.

`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` is the **only canonical product and implementation authority
within Phase 1 scope**. It coexists with, and may not erase, redefine, or supersede, the cross-phase
`docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` outside that scope.

`docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md` is **strategic roadmap authority**: the durable record
of longer-horizon capabilities milestone planning must consult and must not silently drop. It is not
implementation authority — it does not authorize work or override any entry above, and sits above
`05-BACKLOG.md` only in time horizon.

Do not treat `docs/research/`, `docs/archive/`, or `docs/handovers/` as implementation authority unless
a canonical authority or specification explicitly incorporates them.

## Repository map

- `pyrnova/` — application package: adapters, pipeline, evidence, scoring, review, replay, metrics,
  state, and CLI. The current flat layout is intentional while the package remains small.
- `tests/` — deterministic unit, integration, acceptance, and replay coverage. Test purpose is conveyed
  by filenames; split directories only when scale creates navigation cost.
- `tests/fixtures/` — synthetic/offline source-shaped fixtures.
- `examples/profiles/` — example customer capability profiles.
- `examples/replay/` — canonical historical challenge corpus.
- `examples/observations/` — sanitized example observations, never live credentials.
- `examples/real_evidence/` — archived public/authorized evidence used by deterministic replay and grounding.
- `db/` — canonical production schema.
- `AGENTS.md` — agent operating rules: canonical tree, authority hierarchy, anti-drift, start/end checks.
- `docs/specs/` — active product, run, review, and source-ingestion specifications.
- `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` — overarching, owner-approved cross-phase product and
  commercial authority.
- `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` — sole product and implementation authority within Phase 1
  scope, including category, ICP, customer order, commercial offer, intelligence lineage, gates, non-goals,
  Live Ops doctrine, validation, and deferred scope.
- `docs/strategy/COMPETITIVE_DOCTRINE.md` — binding competitive authority (Phase 1 commercial test,
  domination standard, incumbent map, imitation-surviving advantages, customer displacement).
- `docs/strategy/COMPETITIVE_INTELLIGENCE_AND_DATA_AUTONOMY.md` — lawful competitive-intelligence
  collection, proper-means rule + YELLOW review, clean-room reverse engineering, personnel boundary,
  strategic data autonomy, rights-contamination control, vendor displacement (build deferred).
- `docs/strategy/CORPORATE_POSTURE_AND_BRAND.md` — two-faces posture, customer voice (with D-041),
  external secrecy default (NEED TO KNOW), visual/brand character, competitive reputation.
- `docs/strategy/SOCIAL_GROWTH_AUTHORITY.md` — accepted SOCIAL-GROWTH-001 audience, distribution,
  disclosure, rights, visual and human-approval authority; planning assets are linked from it.
- `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md` — strategic capability roadmap: durable longer-horizon
  capabilities, non-authoritative over active work but binding on milestone-planning consultation.
- `docs/architecture/` — current system structure and design boundaries. Includes the binding
  **engineering doctrine** (`ENGINEERING_DOCTRINE.md`) and **infrastructure & capital doctrine**
  (`INFRASTRUCTURE_DOCTRINE.md`) — how Pyrnova is built and scaled (D-059); read before substantive
  implementation or infrastructure work.
- `docs/strategy/SOURCE_RIGHTS_AUTHORITY.md` — source-rights policy and fail-closed boundary doctrine;
  it does not authorize Live Ops, deployment, or Customer #1 readiness.
- `docs/strategy/SOURCE_RIGHTS_ENFORCEMENT_EVIDENCE.md` — isolated engineering verification for the
  Customer #1 source-rights gate; overall readiness and soak acceptance remain separate.
- `docs/system/` — descriptive cross-cutting system documentation: architecture, domain semantics,
  provenance, replay/temporal truth, scoring, and security/tenancy. These documents explain implemented
  behavior and do not create product authority.
- `docs/development/` — engineer setup, safe change workflows, testing/acceptance, source-adapter
  development, and the code-documentation standard.
- `docs/operations/` — current local/live-safe operating and recovery procedures, with planned production
  operations labelled explicitly.
- `docs/adr/` — architecture decision records derived from existing authority and implemented contracts;
  ADRs do not override the authority hierarchy.
- `docs/TECHNICAL_DILIGENCE.md` — evidence index, limitations, AI-assisted-development posture, and
  repository/corporate data-room boundary.
- `docs/ENGINEERING_HANDOVER.md` — bounded onboarding path for a senior engineer.
- `docs/audit/` — dated documentation audits and gap maps; evidence, not current authority.
- `docs/research/` — supporting analysis and retrospective evidence; non-authoritative. Start at
  `docs/research/00-RESEARCH-INDEX.md` (research→decision traceability).
- `docs/replay/` — M3 corpus evidence and reproducible baseline reports.
- `docs/handovers/` — dated continuity records; superseded by current state.
- `docs/archive/` — superseded authorities retained for history.
- `docs/outbound/`, `docs/targets/` — customer/target working material.
- `var/`, `out/`, `.env` — local-only runtime state, outputs, and credentials; all ignored by Git.

## Current execution pointer

`02-EXECUTION.md` authorizes exactly one immediate workstream: **PHASE1-LIVE-OPS-CLOSURE**.

The next decision after that workstream closes is **Customer #1 GO / NO-GO** for IronMountain Solutions.
No broad product expansion is authorized before that decision.
