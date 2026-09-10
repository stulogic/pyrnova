# Pyrnova authority index

This file is the canonical navigation map for humans and agents.

**Agents:** read `AGENTS.md` first — it carries the anti-drift rules, conflict-resolution procedure, and
the start-of-work / end-of-work checks.

## Mandatory reading order

For implementation work, read only what the task requires, in this order:

1. `00-INDEX.md`
2. `01-PROJECT-AUTHORITY.md`
3. `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` (overarching product + commercial authority: product,
   ICP, pricing/commercial model, trust gates, validation, expansion discipline) — **read this before
   using research or roadmap material to make any product/commercial decision**
4. `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` (current-product authority: customer, product, non-goals)
5. `03-CURRENT-STATE.md`
6. `02-EXECUTION.md`
7. the relevant document under `docs/specs/`

Then consult `04-DECISIONS.md` when a prior choice affects the task and `05-BACKLOG.md` only for
future-scope questions. `06-HISTORY.md` and `docs/handovers/` are continuity records, not current
instructions.

## Authority order

When documents conflict, use this precedence:

1. **Current product / strategic authority** — `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` (overarching
   product + commercial authority: product, ICP, commercial/pricing model, trust/validation/expansion
   gates; governs on any direct conflict with the companions below), `01-PROJECT-AUTHORITY.md` (mission,
   boundaries, locked doctrine), `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` (current customer, product, non-goals),
   `docs/strategy/COMPETITIVE_DOCTRINE.md` (competitive objective, domination standard, displacement),
   `docs/strategy/COMPETITIVE_INTELLIGENCE_AND_DATA_AUTONOMY.md` (lawful competitive intelligence,
   proper-means, strategic data autonomy — operating discipline binding now, product build deferred),
   and `docs/strategy/CORPORATE_POSTURE_AND_BRAND.md` (external presentation, brand, disclosure posture).
2. **Current milestone work order** — `02-EXECUTION.md` — current milestone and active constraints.
3. **Durable decisions** — `04-DECISIONS.md` — decisions and supersession record.
4. **Current state** — `03-CURRENT-STATE.md` — verified implementation/runtime truth.
5. **Architectural authority** — relevant `docs/specs/` document, `docs/architecture/`, `db/`.
6. **Roadmap** — `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`, then `05-BACKLOG.md` (future work only).
7. **Research** — `docs/research/` — informs authority; never authorizes implementation.
8. **Historical / superseded** — `06-HISTORY.md`, `docs/handovers/`, `docs/archive/` — never override
   current authority.

Research can inform authority but does not independently authorize implementation. Roadmap entries do
not belong to the current milestone unless `02-EXECUTION.md` explicitly authorizes them. Historical
documents never override current authority. If a conflict is genuinely unresolved, record it (in
`04-DECISIONS.md` or the current work order) rather than silently choosing the broader scope.

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
- `db/` — canonical production schema.
- `AGENTS.md` — agent operating rules: canonical tree, authority hierarchy, anti-drift, start/end checks.
- `docs/specs/` — active product, run, review, and source-ingestion specifications.
- `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` — **overarching current product + commercial authority**
  (owner-approved): product identity, ICP, customer job, Material Changes semantics, live-operations and
  source/data doctrine, competitive/displacement strategy, commercial + pricing model, validation and
  trust gates, UX/AI authority, expansion gates, do-not-build/compete. Top of tier 1; the Phase 1 product
  and competitive doctrines are consistent companions and defer to it on any direct conflict. Read before
  using research or roadmap to make a product/commercial decision.
- `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` — canonical current-product authority (Phase 1 customer,
  product surfaces, required loop, explicit non-goals, finishability, moat).
- `docs/strategy/COMPETITIVE_DOCTRINE.md` — binding competitive authority (Phase 1 commercial test,
  domination standard, incumbent map, imitation-surviving advantages, customer displacement).
- `docs/strategy/COMPETITIVE_INTELLIGENCE_AND_DATA_AUTONOMY.md` — lawful competitive-intelligence
  collection, proper-means rule + YELLOW review, clean-room reverse engineering, personnel boundary,
  strategic data autonomy, rights-contamination control, vendor displacement (build deferred).
- `docs/strategy/CORPORATE_POSTURE_AND_BRAND.md` — two-faces posture, customer voice (with D-041),
  external secrecy default (NEED TO KNOW), visual/brand character, competitive reputation.
- `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md` — strategic capability roadmap: durable longer-horizon
  capabilities, non-authoritative over active work but binding on milestone-planning consultation.
- `docs/architecture/` — current system structure and design boundaries. Includes the binding
  **engineering doctrine** (`ENGINEERING_DOCTRINE.md`) and **infrastructure & capital doctrine**
  (`INFRASTRUCTURE_DOCTRINE.md`) — how Pyrnova is built and scaled (D-059); read before substantive
  implementation or infrastructure work.
- `docs/research/` — supporting analysis and retrospective evidence; non-authoritative. Start at
  `docs/research/00-RESEARCH-INDEX.md` (research→decision traceability).
- `docs/replay/` — M3 corpus evidence and reproducible baseline reports.
- `docs/handovers/` — dated continuity records; superseded by current state.
- `docs/archive/` — superseded authorities retained for history.
- `docs/outbound/`, `docs/targets/` — customer/target working material.
- `var/`, `out/`, `.env` — local-only runtime state, outputs, and credentials; all ignored by Git.
