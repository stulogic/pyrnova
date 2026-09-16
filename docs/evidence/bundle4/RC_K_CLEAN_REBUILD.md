# RC-K — clean-environment reproducibility (exact candidate)

**Result: clean rebuild reproduces the exact candidate with no dependency/config defect, on BOTH the
declared floor (CPython 3.9.6) and a current 3.11+ target (CPython 3.14.7). No executable code changed.**
`requires-python = ">=3.9"`. The 3.11+ residual noted at first reconciliation is now closed.

## Existing evidence assessed first

- `tests/test_b4_dependency_contract.py` is a **static** contract guard (requires-python floor matches
  verified, locks fully pinned `==`, dev lock extends runtime lock, no undeclared third-party runtime
  dep). It does **not** perform an actual clean rebuild — so it alone does not satisfy RC-K's
  CLEAN-REBUILD requirement. A bounded clean reproduction was therefore performed.

## Bounded clean reproduction (performed)

Isolated venv (`python3 -m venv`, **not** the developer `.venv`), install strictly from repository
manifests, at code-complete SHA `50e1b7a`:

| RC-K sub-requirement | Result |
|---|---|
| Clean environment | Fresh isolated venv, developer `.venv` untouched |
| Canonical dependency install succeeds | `pip install -r requirements-dev.lock.txt` → success |
| Dependencies resolve from accepted manifests/locks | Installed set == pinned locks exactly (`requests==2.32.5` + closure; `pytest==8.4.2` + closure) |
| No hidden local packages required | `pip install .` builds/installs `pyrnova`; `import pyrnova` (+ cli/ops/release/soak_provenance/customer_delivery/alerts/state) resolves from **site-packages** with `PYTHONPATH` unset, from a non-source dir |
| Release configuration identifiable | `requires-python`, pinned locks, `pyproject.toml` extras (`s3`/`postgres`/`dev`), `docs/operations/RELEASE_INSTALL.md`, config env contract |
| Candidate imports / builds / starts | `pyrnova` console entry point resolves + `--help`; full regression **866 passed / 0 failed / 2 skipped** in the clean venv on CPython 3.9.6 |

**No dependency or configuration defect found.** Because RC-K exposed no code defect, no executable
candidate code was changed.

## 3.11+ target verification (now closed)

The recommended **CPython 3.11+** target is verified. The identical isolated clean rebuild was repeated on
**CPython 3.14.7** (`/opt/homebrew/bin/python3.14`): fresh venv, install strictly from
`requirements-dev.lock.txt` (pinned locks resolved), `pip install .`, `import pyrnova` (+ key modules)
from **site-packages** with `PYTHONPATH` unset from a non-source dir, `pyrnova` CLI entry resolves, and
full regression **866 passed / 0 failed / 2 skipped**. **No dependency or configuration defect on 3.14.**

RC-K is therefore clean-rebuild verified on both the declared floor (3.9.6) and a current 3.11+ target
(3.14.7), with no residual and no executable code change.
