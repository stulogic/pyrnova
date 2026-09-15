"""B4.5 — dependency / runtime contract guard.

Keeps the deterministic install contract honest so a release candidate stays reproducibly installable:
the declared runtime floor matches what is verified, the lock files are fully pinned, and no undeclared
third-party runtime dependency slips into the ``pyrnova`` package.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECLARED_THIRD_PARTY = {"requests", "boto3", "psycopg"}  # requests (runtime) + s3/postgres extras


def _lock_lines(name: str) -> list[str]:
    return [l.strip() for l in (ROOT / name).read_text().splitlines()
            if l.strip() and not l.strip().startswith("#")]


def test_requires_python_matches_verified_floor():
    text = (ROOT / "pyproject.toml").read_text()
    assert 'requires-python = ">=3.9"' in text


def test_runtime_lock_is_fully_pinned_and_includes_requests():
    lines = _lock_lines("requirements.lock.txt")
    assert any(l.startswith("requests==") for l in lines)
    # Every runtime lock entry is an exact pin (no ranges) for reproducibility.
    for l in lines:
        assert "==" in l and ">=" not in l and "<" not in l, f"unpinned runtime lock entry: {l}"


def test_dev_lock_extends_runtime_and_pins_pytest():
    lines = _lock_lines("requirements-dev.lock.txt")
    assert "-r requirements.lock.txt" in lines
    assert any(l.startswith("pytest==") for l in lines)


def _is_third_party(mod: str) -> bool:
    """A top-level module is third-party if it is not importable as stdlib (spec missing => not installed,
    e.g. an optional extra) or it resolves under site-packages/dist-packages."""
    try:
        spec = importlib.util.find_spec(mod)
    except (ImportError, ValueError, ModuleNotFoundError):
        return True
    if spec is None:
        return True
    origin = (spec.origin or "")
    return "site-packages" in origin or "dist-packages" in origin


def test_no_undeclared_third_party_runtime_import_in_pyrnova():
    third_party: set[str] = set()
    for py in (ROOT / "pyrnova").rglob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    third_party.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                third_party.add(node.module.split(".")[0])
    undeclared = {m for m in third_party
                  if m not in ("pyrnova", "__future__") and _is_third_party(m)
                  and m not in DECLARED_THIRD_PARTY}
    assert undeclared == set(), f"undeclared third-party runtime imports: {sorted(undeclared)}"
