# RC-K — clean-environment reproducibility (exact candidate)

**Result: clean rebuild reproduces the exact candidate with no dependency/config defect. No executable
code changed.** Verified runtime floor CPython 3.9 (`requires-python = ">=3.9"`). The recommended 3.11+
target could not be exercised here (no 3.11+ interpreter available/installable) — see the residual.

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

## Residual (environment dependency, not a candidate defect)

The **CPython 3.11+** recommended-target clean reproduction is **not** verified here: no `>=3.10`
interpreter is available in this build environment, and none is installable (`brew`/`pyenv`/`uv` all
absent, no authorized network install). The code carries no `>=3.10`-only syntax and `requires-python`
is `>=3.9`, so nothing blocks 3.11+; it simply needs an operator-provided/authorized 3.11+ interpreter to
be independently exercised. This is the single item preventing a fully unqualified RC-K closure.
