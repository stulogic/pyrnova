# Pyrnova authority index

This file is the canonical navigation map for humans and agents.

## Mandatory reading order

For implementation work, read only what the task requires, in this order:

1. `00-INDEX.md`
2. `01-PROJECT-AUTHORITY.md`
3. `03-CURRENT-STATE.md`
4. `02-EXECUTION.md`
5. the relevant document under `docs/specs/`

Then consult `04-DECISIONS.md` when a prior choice affects the task and `05-BACKLOG.md` only for
future-scope questions. `06-HISTORY.md` and `docs/handovers/` are continuity records, not current
instructions.

## Authority order

When documents conflict, use this precedence:

1. `01-PROJECT-AUTHORITY.md` — mission, boundaries, and locked doctrine.
2. `02-EXECUTION.md` — current milestone and active constraints.
3. `03-CURRENT-STATE.md` — verified implementation/runtime truth.
4. `04-DECISIONS.md` — durable decisions and supersession record.
5. Relevant `docs/specs/` document — detailed implementation contract.
6. `05-BACKLOG.md` — prioritized future work only.

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
- `docs/specs/` — active product, run, review, and source-ingestion specifications.
- `docs/strategy/` — strategic capability roadmap: durable longer-horizon capabilities, non-authoritative
  over active work but binding on milestone-planning consultation.
- `docs/architecture/` — current system structure and design boundaries.
- `docs/research/` — supporting analysis and retrospective evidence; non-authoritative.
- `docs/replay/` — M3 corpus evidence and reproducible baseline reports.
- `docs/handovers/` — dated continuity records; superseded by current state.
- `docs/archive/` — superseded authorities retained for history.
- `docs/outbound/`, `docs/targets/` — customer/target working material.
- `var/`, `out/`, `.env` — local-only runtime state, outputs, and credentials; all ignored by Git.
