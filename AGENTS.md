# Pyrnova — agent operating rules (anti-drift)

This file is the mandatory entrypoint for any agent (Claude, Codex, or other) beginning substantive work
in Pyrnova. It exists to catch scope drift **before** tokens and code are spent. It is lightweight by
design — not process theatre.

## Canonical working tree

Pyrnova's only local implementation authority is **`/Users/stu/Documents/Pyrnova` on `main`**
(GitHub `origin/main` is repository authority). A separate clone at `/Users/stu/pyrnova` is **not**
authoritative — it lacks credentials and real evidence and must not be used for milestone work. If your
session started elsewhere, switch first. The untracked `.codex/` directory is intentional; leave it.

## Authority hierarchy (resolve conflicts in this order)

1. **Current product / strategic authority** — `01-PROJECT-AUTHORITY.md` and
   `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`.
2. **Current milestone work order** — `02-EXECUTION.md`.
3. **Durable decisions** — `04-DECISIONS.md`.
4. **Current state** — `03-CURRENT-STATE.md`.
5. **Architectural authority** — `docs/architecture/`, `db/`, relevant `docs/specs/`.
6. **Roadmap** — `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`, then `05-BACKLOG.md`.
7. **Research** — `docs/research/` (informs authority; never authorizes implementation).
8. **Historical / superseded** — `06-HISTORY.md`, `docs/handovers/`, `docs/archive/`.

Rules:
- **Research can inform authority; it does not independently authorize implementation.**
- **Roadmap entries do not belong to the current milestone unless `02-EXECUTION.md` explicitly says so.**
- **Historical documents never override current authority.**

## Reading order (read only what the task needs)

`00-INDEX.md` → `01-PROJECT-AUTHORITY.md` → `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` →
`03-CURRENT-STATE.md` → `02-EXECUTION.md` → the relevant `docs/specs/` document. Consult `04-DECISIONS.md`
when a prior choice affects the task; consult roadmap/research only for future-scope questions.

## Do NOT treat as higher authority than current repository authority

README marketing language; stale plans; historical work orders; future-roadmap items; research
recommendations; comments in old code; previous chat prompts. If any of these conflict with current
authority, **stop the conflicting interpretation** and use the hierarchy above. If a conflict is
genuinely unresolved, **record the conflict** (in `04-DECISIONS.md` or the current work order) rather
than silently choosing the broader scope.

## Start-of-work check (state these before implementing)

1. Current milestone.
2. Current customer.
3. Current product goal.
4. Explicit non-goals.
5. Relevant acceptance criteria.
6. Files/documents treated as authoritative for this task.
7. Whether the proposed work is **CURRENT** or **ROADMAP**. If ROADMAP, stop and get authority.

## End-of-work check (verify before closing a work block)

- Work stayed within current authority.
- No deferred feature became an accidental dependency.
- Relevant decision/state docs were updated.
- Newly discovered future ideas were roadmapped, not silently implemented.
- Current-state documentation still matches the code.
- Tests remain proportional to risk; no acceptance criterion was weakened.

## Finishability rule (binding)

A missing capability may block a phase **only** for correctness, safety, architectural integrity,
existing acceptance criteria, or real Phase 1 customer decision value. Research curiosity, elegance,
theoretical usefulness, competitor parity, "while we are here", an interesting dataset, or an agent
noticing another useful relationship/event/source do **not** qualify. Default: **DOCUMENT → ROADMAP →
DEFER.** See `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` and D-047.
