# Pyrnova authority index

This file is the canonical navigation map for humans and agents.

**Agents:** read `AGENTS.md` first. It carries the anti-drift rules, conflict-resolution procedure, and the start-of-work / end-of-work checks.

## Mandatory reading order

For implementation work, read only what the task requires, in this order:

1. `00-INDEX.md`
2. `01-PROJECT-AUTHORITY.md`
3. `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` (overarching cross-phase product and commercial authority)
4. `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` (sole product and implementation authority within Phase 1 scope)
5. `03-CURRENT-STATE.md`
6. `02-EXECUTION.md`
7. the relevant document under `docs/specs/`

Then consult `04-DECISIONS.md` when a prior choice affects the task and `05-BACKLOG.md` only for future-scope questions. `06-HISTORY.md` and `docs/handovers/` are continuity records, not current instructions.

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

Research can inform authority but does not independently authorize implementation. Roadmap entries do not belong to the current workstream unless `02-EXECUTION.md` explicitly authorizes them. Historical documents never override current authority.

If a conflict is genuinely unresolved, record it in the current authority/work order or durable decision record rather than silently choosing the broader scope.

`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` is the **only canonical product and implementation authority
within Phase 1 scope**. It coexists with, and may not erase, redefine, or supersede, the cross-phase
`docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` outside that scope.

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
- `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md`: overarching, owner-approved cross-phase product and commercial authority.
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
