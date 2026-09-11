# Pyrnova authority index

This file is the canonical navigation map for humans and agents.

**Agents:** read `AGENTS.md` first. It carries the anti-drift rules, conflict-resolution procedure, and the start-of-work / end-of-work checks.

## Mandatory reading order

For implementation work, read only what the task requires, in this order:

1. `00-INDEX.md`
2. `01-PROJECT-AUTHORITY.md`
3. `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` (single canonical Phase 1 product and commercial authority)
4. `03-CURRENT-STATE.md`
5. `02-EXECUTION.md`
6. the relevant document under `docs/specs/`

Then consult `04-DECISIONS.md` when a prior choice affects the task and `05-BACKLOG.md` only for future-scope questions. `06-HISTORY.md` and `docs/handovers/` are continuity records, not current instructions.

## Authority order

When documents conflict, use this precedence:

1. **Current Product / Strategic Authority**: `01-PROJECT-AUTHORITY.md`, `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`, `docs/strategy/COMPETITIVE_DOCTRINE.md`, `docs/strategy/COMPETITIVE_INTELLIGENCE_AND_DATA_AUTONOMY.md`, and `docs/strategy/CORPORATE_POSTURE_AND_BRAND.md`.
2. **Current Milestone / Work Order**: `02-EXECUTION.md`.
3. **Durable Decisions**: `04-DECISIONS.md`.
4. **Current State**: `03-CURRENT-STATE.md`.
5. **Architectural Authority**: relevant `docs/specs/`, `docs/architecture/`, and `db/` authority.
6. **Roadmap**: `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`, then `05-BACKLOG.md`.
7. **Research**: `docs/research/`. Research informs authority and never authorizes implementation by itself.
8. **Historical / Superseded**: `06-HISTORY.md`, `docs/handovers/`, and `docs/archive/`.

Research can inform authority but does not independently authorize implementation. Roadmap entries do not belong to the current workstream unless `02-EXECUTION.md` explicitly authorizes them. Historical documents never override current authority.

If a conflict is genuinely unresolved, record it in the current authority/work order or durable decision record rather than silently choosing the broader scope.

`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` is the **only canonical Phase 1 product/commercial authority**. Any stale reference to `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` resolves to it; no peer product/commercial authority may override it.

`docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md` is strategic roadmap authority: the durable record of longer-horizon capabilities milestone planning must consult and must not silently drop. It is not implementation authority and does not override any entry above.

Do not treat `docs/research/`, `docs/archive/`, or `docs/handovers/` as implementation authority unless a current canonical authority or specification explicitly incorporates them.

## Repository map

- `pyrnova/`: application package, including adapters, pipeline, evidence, scoring, review, replay, metrics, state, and CLI.
- `tests/`: deterministic unit, integration, acceptance, and replay coverage.
- `tests/fixtures/`: synthetic/offline source-shaped fixtures.
- `examples/profiles/`: example capability profiles and engineering fixtures.
- `examples/replay/`: historical challenge and replay corpora.
- `examples/observations/`: sanitized example observations, never live credentials.
- `examples/real_evidence/`: archived public/authorized evidence used by deterministic replay and grounding.
- `db/`: canonical production schema direction.
- `AGENTS.md`: agent operating rules, canonical tree, authority hierarchy, anti-drift, and start/end checks.
- `docs/specs/`: implementation and acceptance specifications. Closed milestone specs remain implementation evidence, not current product scope authority.
- `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`: canonical Phase 1 product/commercial authority, including category, ICP, customer order, commercial offer, intelligence lineage, Phase 1 gates, non-goals, Live Ops doctrine, validation, and deferred scope.
- `docs/strategy/COMPETITIVE_DOCTRINE.md`: binding competitive authority, including the incumbent-displacement test and imitation-surviving advantages.
- `docs/strategy/COMPETITIVE_INTELLIGENCE_AND_DATA_AUTONOMY.md`: lawful competitive-intelligence collection, proper-means rule, clean-room discipline, strategic data autonomy, and rights-contamination control.
- `docs/strategy/CORPORATE_POSTURE_AND_BRAND.md`: external presentation, brand, voice, and disclosure posture.
- `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`: longer-horizon capability roadmap, below current authority and work orders.
- `docs/architecture/`: binding engineering/infrastructure doctrine and architecture references.
- `docs/research/`: supporting analysis and research-to-decision provenance, non-authoritative by itself.
- `docs/replay/`: replay and acceptance evidence.
- `docs/handovers/`: dated continuity records, superseded by current state.
- `docs/archive/`: superseded authorities retained for history.
- `docs/outbound/`, `docs/targets/`: customer/target working material; never higher authority than current product/customer order.
- `var/`, `out/`, `.env`: local-only runtime state, outputs, and credentials; ignored by Git.

## Current execution pointer

`02-EXECUTION.md` authorizes exactly one immediate workstream: **PHASE1-LIVE-OPS-CLOSURE**.

The next decision after that workstream closes is **Customer #1 GO / NO-GO** for IronMountain Solutions. No broad product expansion is authorized before that decision.
