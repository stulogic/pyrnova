# Phase 1 — Release Lineage / Integration Evidence

Branch: `phase1-integration-001` (release candidate)
Base: authoritative `main` = `3737afd` (origin/main `e7cb2c9` + accepted SOCIAL-GROWTH-001 docs)
Date: 2026-09-15

## Merge-base

All accepted branches share merge-base `e7cb2c9` (= origin/main = pinned Live Ops soak commit).

## Integrated accepted work

1. **Accepted stack, in one merge** (`--no-ff` of `operator-alerts-001` @ `bedf069`), preserving valid stacked ancestry:
   - source-rights-001 `3732d86` (ancestor of →)
   - backup-restore-001 `8275d91` (ancestor of →)
   - operator-alerts-001 `bedf069`
   Verified: `source-rights` ⊂ `backup-restore` ⊂ `operator-alerts` via `git merge-base --is-ancestor`.
2. **website-go-001 `5a748b9`** — independent accepted change (`--no-ff`); confirmed NOT a descendant of the stack.

Both merges were conflict-free (ort strategy); no reconciliation edits required.

## Capability presence confirmed on assembled tree

- Source-rights: `pyrnova/sources/rights.py`
- Backup/restore: `pyrnova/backup.py`
- Operator alerts: `pyrnova/alerts.py`, `pyrnova/watchdog.py`, `pyrnova/heartbeat.py`
- Accepted website: `website-go/`

## Regression (one proportionate run, `.venv` pytest)

- Integration branch: **12 failed**, remainder passed.
- `operator-alerts-001` tip (control): **12 failed**, remainder passed.
- Failing sets are **identical** (`diff` empty) → integration introduced **0 new failures**.
- The 12 failures are pre-existing source-rights-enforcement expectations in tests predating rights
  (`test_sbir`, `test_appropriations`, `test_m14_cross_source`, `test_m4_integration`,
  `test_source_expansion`). Not weakened, not fixed here — carried forward as-is for later adjudication.

## Boundaries respected

- Live Ops soak untouched (read-only; pinned `e7cb2c9` evidence not accessed for write).
- `tooling/workstream-control` NOT merged into product.
- `docs-001` NOT merged.
- Canonical working tree left as found (still on `tooling/workstream-control`); integration done entirely
  in an isolated worktree. Integration branch NOT merged to `main`.

## Resume point

`phase1-integration-001` is the release candidate for Phases 2–8.
