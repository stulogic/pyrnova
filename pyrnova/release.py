"""B4.6 — immutable release / deploy / rollback contract (single-node).

A simple, Docker-free production release mechanism consistent with the accepted single-node architecture:

    /srv/pyrnova/releases/<sha>     immutable release artifact (exact git SHA)
    /srv/pyrnova/current -> <sha>   atomically-swapped active-release symlink
    /srv/pyrnova/state              DURABLE STATE — lives OUTSIDE releases, never rolled back with code
    (config/secrets live outside the repo/release payload entirely)

Guarantees:
    * a release directory is immutable — staging refuses to overwrite an existing SHA;
    * the exact git SHA and a dependency-lock fingerprint are recorded in a per-release manifest;
    * activation is explicit and atomic (temp symlink + os.replace) — never a silent partial release;
    * activation/rollback fail closed if the target release is missing or fails health verification;
    * rollback repoints code to the previously-activated release ONLY — it never touches durable state
      (code rollback and data recovery are distinct operations; see docs backup/restore for data).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

RELEASE_MANIFEST = "RELEASE.json"
ACTIVATIONS_LOG = "activations.jsonl"
CURRENT_LINK = "current"
RELEASES_DIR = "releases"

# Paths that are runtime/derived state or VCS metadata — never copied into an immutable release artifact.
_EXCLUDE_FROM_RELEASE = {".git", "var", "out", "state", ".venv", "__pycache__", ".DS_Store",
                         "deliveries", "backups"}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_sha(source_dir: Path) -> str:
    """Exact commit SHA of ``source_dir`` (fails closed if not a clean identifiable commit)."""
    out = subprocess.run(["git", "-C", str(source_dir), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def _sha256_file(p: Path) -> Optional[str]:
    if not p.exists():
        return None
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


@dataclass
class ReleaseManifest:
    sha: str
    created_at: str
    python: str
    lock_sha256: Optional[str] = None
    source_root: Optional[str] = None
    notes: str = ""
    extra: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return {"sha": self.sha, "created_at": self.created_at, "python": self.python,
                "lock_sha256": self.lock_sha256, "source_root": self.source_root,
                "notes": self.notes, "extra": self.extra}


def _copy_tree(src: Path, dst: Path) -> None:
    def ignore(_dir, names):
        return [n for n in names if n in _EXCLUDE_FROM_RELEASE]
    shutil.copytree(src, dst, ignore=ignore, symlinks=False)


def stage_release(releases_root: Path, source_dir: Path, *, sha: Optional[str] = None,
                  python_version: Optional[str] = None, notes: str = "",
                  created_at: Optional[str] = None, extra: Optional[dict] = None) -> ReleaseManifest:
    """Materialize an IMMUTABLE release artifact from ``source_dir`` at ``releases_root/releases/<sha>``.

    Refuses to overwrite an existing SHA (immutability). Records the exact SHA + dependency-lock
    fingerprint in the release manifest. Runtime/derived state and VCS metadata are excluded."""
    releases_root = Path(releases_root)
    source_dir = Path(source_dir)
    sha = sha or git_sha(source_dir)
    rel_dir = releases_root / RELEASES_DIR / sha
    if rel_dir.exists():
        raise FileExistsError(f"release {sha} already staged (immutable); refusing to overwrite")
    rel_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp = rel_dir.with_name(rel_dir.name + ".staging")
    if tmp.exists():
        shutil.rmtree(tmp)
    _copy_tree(source_dir, tmp)
    import sys
    manifest = ReleaseManifest(
        sha=sha, created_at=created_at or _utcnow(),
        python=python_version or ".".join(map(str, sys.version_info[:3])),
        lock_sha256=_sha256_file(source_dir / "requirements.lock.txt"),
        source_root=str(source_dir), notes=notes, extra=extra or {})
    (tmp / RELEASE_MANIFEST).write_text(json.dumps(manifest.to_record(), indent=2, sort_keys=True))
    os.replace(tmp, rel_dir)  # atomic publish of the fully-staged artifact (no partial release dir)
    return manifest


def read_manifest(release_dir: Path) -> Optional[dict]:
    p = Path(release_dir) / RELEASE_MANIFEST
    if not p.exists():
        return None
    return json.loads(p.read_text())


def default_health_check(release_dir: Path) -> tuple[bool, str]:
    """Structural health: the release carries a manifest and the importable package + lock."""
    release_dir = Path(release_dir)
    if read_manifest(release_dir) is None:
        return False, "missing RELEASE.json manifest"
    if not (release_dir / "pyrnova" / "__init__.py").exists():
        return False, "missing pyrnova package"
    if not (release_dir / "requirements.lock.txt").exists():
        return False, "missing requirements.lock.txt"
    return True, "ok"


def current_sha(releases_root: Path) -> Optional[str]:
    link = Path(releases_root) / CURRENT_LINK
    if not link.is_symlink() and not link.exists():
        return None
    target = Path(os.readlink(link)) if link.is_symlink() else link.resolve()
    return target.name


def _activate(releases_root: Path, sha: str, *, action: str, health_check: Callable,
              at: Optional[str]) -> dict:
    releases_root = Path(releases_root)
    rel_dir = releases_root / RELEASES_DIR / sha
    if not rel_dir.is_dir():
        raise FileNotFoundError(f"release {sha} is not staged at {rel_dir}")
    if health_check is not None:
        ok, detail = health_check(rel_dir)
        if not ok:
            raise RuntimeError(f"release {sha} failed health verification: {detail}")
    previous = current_sha(releases_root)
    link = releases_root / CURRENT_LINK
    tmp_link = releases_root / (CURRENT_LINK + ".swap")
    if tmp_link.exists() or tmp_link.is_symlink():
        tmp_link.unlink()
    os.symlink(Path(RELEASES_DIR) / sha, tmp_link)  # relative target keeps the tree relocatable
    os.replace(tmp_link, link)  # atomic swap
    record = {"action": action, "sha": sha, "previous": previous, "at": at or _utcnow()}
    _append_activation(releases_root, record)
    return record


def activate(releases_root: Path, sha: str, *, health_check: Callable = default_health_check,
             at: Optional[str] = None) -> dict:
    """Atomically point ``current`` at ``releases/<sha>`` after health verification. Fail closed if the
    release is missing or unhealthy — never a silent partial activation. Appends an audit record."""
    return _activate(releases_root, sha, action="activate", health_check=health_check, at=at)


def _append_activation(releases_root: Path, record: dict) -> None:
    log = Path(releases_root) / ACTIVATIONS_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def activation_history(releases_root: Path) -> list[dict]:
    log = Path(releases_root) / ACTIVATIONS_LOG
    if not log.exists():
        return []
    return [json.loads(l) for l in log.read_text().splitlines() if l.strip()]


def previous_activated_sha(releases_root: Path) -> Optional[str]:
    """The code release that was active immediately before the current one (from the activation log)."""
    hist = activation_history(releases_root)
    cur = current_sha(releases_root)
    for rec in reversed(hist):
        if rec.get("sha") == cur and rec.get("previous"):
            return rec["previous"]
    return None


def rollback(releases_root: Path, *, health_check: Callable = default_health_check,
             at: Optional[str] = None) -> dict:
    """Roll CODE back to the previously-activated release. Fails closed if there is no prior release or it
    is missing/unhealthy. Does NOT touch durable state — data recovery is a separate operation."""
    releases_root = Path(releases_root)
    target = previous_activated_sha(releases_root)
    if not target:
        raise RuntimeError("no previous release to roll back to")
    rel_dir = releases_root / RELEASES_DIR / target
    if not rel_dir.is_dir():
        raise FileNotFoundError(f"previous release {target} is no longer staged at {rel_dir}")
    return _activate(releases_root, target, action="rollback", health_check=health_check, at=at)


def main(argv: Optional[list[str]] = None) -> int:
    """Operator CLI: ``python -m pyrnova.release <stage|activate|rollback|current|history> ...``."""
    import argparse
    parser = argparse.ArgumentParser(prog="pyrnova-release", description="Immutable release/deploy/rollback")
    parser.add_argument("--root", default=os.environ.get("PYRNOVA_RELEASE_ROOT", "/srv/pyrnova"),
                        help="release root (default /srv/pyrnova or $PYRNOVA_RELEASE_ROOT)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_stage = sub.add_parser("stage", help="stage an immutable release from a source checkout")
    p_stage.add_argument("--source", required=True)
    p_stage.add_argument("--sha", default=None)
    p_stage.add_argument("--notes", default="")
    p_act = sub.add_parser("activate", help="atomically activate a staged release")
    p_act.add_argument("sha")
    sub.add_parser("rollback", help="roll code back to the previously-activated release")
    sub.add_parser("current", help="print the currently-active release SHA")
    sub.add_parser("history", help="print the activation history")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.cmd == "stage":
        m = stage_release(root, Path(args.source), sha=args.sha, notes=args.notes)
        print(json.dumps(m.to_record(), indent=2, sort_keys=True))
    elif args.cmd == "activate":
        print(json.dumps(activate(root, args.sha), indent=2, sort_keys=True))
    elif args.cmd == "rollback":
        print(json.dumps(rollback(root), indent=2, sort_keys=True))
    elif args.cmd == "current":
        print(current_sha(root) or "")
    elif args.cmd == "history":
        print(json.dumps(activation_history(root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
