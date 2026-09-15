# Pyrnova — release install / dependency & runtime contract (B4.5)

The deterministic, reproducible install contract for the release candidate.

## Supported runtime

- **Verified runtime floor: CPython 3.9** (`requires-python = ">=3.9"` in `pyproject.toml`).
  The release-candidate fresh-install verification runs the full regression **green on CPython 3.9.6**,
  and the code uses no `>=3.10`-only runtime syntax.
- **Recommended production target: CPython 3.11+.** A fresh-install verification on 3.11+ is an
  environment dependency (no `>=3.10` interpreter is available in the current build environment); nothing
  in the code blocks it, but it is not yet independently verified here.

## Dependencies

Runtime is intentionally tiny — the kernel runs fully local. The only required runtime third-party package
is `requests` (source-fetch layer). Optional extras are declared in `pyproject.toml` and are **not**
required to run or test the kernel:

| Extra      | Package             | Used by                                   |
|------------|---------------------|-------------------------------------------|
| `s3`       | `boto3>=1.34`       | `pyrnova/archive.py` off-host object store |
| `postgres` | `psycopg[binary]`   | future Postgres adapter (Phase 1 is JSONL) |
| `dev`      | `pytest>=8.0`       | test suite                                 |

### Locked (deterministic) install

- `requirements.lock.txt` — fully pinned runtime closure (`requests` + `certifi` + `charset-normalizer`
  + `idna` + `urllib3`).
- `requirements-dev.lock.txt` — the runtime lock plus the pinned test toolchain.

Locks pin exact versions for release-candidate reproducibility. `requirements.txt` remains the simplest
human install (`requests>=2.31`); the locks are the authority for a reproducible build.

## Fresh install (from repository authority)

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.lock.txt   # runtime + test toolchain, pinned
pip install .                              # installs the pyrnova package + `pyrnova` CLI entry point
```

Running `python -m pyrnova.cli` from the repo root does **not** require installing the package.

## Deterministic test invocation

```sh
python -m pytest            # honours [tool.pytest.ini_options] (testpaths=tests, -q)
```

`PYRNOVA_STATE_FSYNC=0` may be set to skip per-append fsync for throwaway test volume (durability across a
crash does not matter there); production leaves it on (default).

## Fresh-install verification (recorded)

An isolated venv created with `python3 -m venv` (no access to the developer `.venv`), installing **only**
from `requirements-dev.lock.txt` + `pip install .`:

- `pyrnova` console entry point resolves; `import pyrnova` works from the installed site-packages with no
  `PYTHONPATH`.
- Full regression: **836 passed / 0 failed / 2 skipped** on CPython 3.9.6.

No dependency on developer-machine global packages; `boto3`/`psycopg` are absent from the runtime install
and their code paths are import-guarded/optional.
