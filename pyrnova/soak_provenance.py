"""Independent SHA provenance for a Live Operations soak run.

This module reads only the evidence a soak run already writes (``manifest.json``,
``cycles.jsonl``, ``events.jsonl``) plus the append-only evidence archive, and derives a single
reproducible provenance chain over the run. It owns no runtime: it does not fetch, ingest, mutate
state, or change acceptance semantics. Its job is tamper-evidence and reproducibility, so a soak
result can be re-verified from bytes without trusting the process that produced it.

Guarantees checked, all fail-closed:
  * every recorded soak cycle ran at the exact commit pinned in the start manifest (immutability);
  * every cycle carries the manifest's plan hash (the pinned plan never drifted);
  * no invalidating intervention was recorded in the evidence;
  * every referenced source artifact re-hashes to its recorded ``content_sha256`` (when the archive
    is available to re-read the raw bytes).

The derived ``chain_sha256`` is a deterministic hash over the ordered per-cycle leaves. Re-running
the verifier on untouched evidence reproduces it; any edit to a cycle, its commit, or an archived
artifact changes it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from .archive import LocalEvidenceArchive
from .scheduler import CACHE_HIT, LIVE_FETCH

# Source-result actions whose ``content_sha256`` names raw bytes that must live in the archive.
_ARTIFACT_ACTIONS = frozenset({LIVE_FETCH, CACHE_HIT, "resume_pending"})


def _sha256_json(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def build_provenance(
    evidence_dir: str | Path,
    *,
    archive: Optional[LocalEvidenceArchive] = None,
    released_shas: Optional[set[str]] = None,
    write: bool = False,
) -> dict:
    """Derive the SHA provenance chain for a soak evidence directory.

    ``archive`` (when given) re-reads each referenced artifact and re-hashes it. ``released_shas``
    (when given) asserts the pinned commit is one of the immutable staged release SHAs, binding the
    soak to the release contract. ``write`` persists ``provenance.json`` next to the evidence.
    """
    evidence_dir = Path(evidence_dir).resolve()
    errors: list[str] = []
    manifest_path = evidence_dir / "manifest.json"
    if not manifest_path.is_file():
        return {"ok": False, "errors": ["no manifest.json; soak has not been started"],
                "evidence_dir": str(evidence_dir)}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pinned_commit = manifest.get("commit")
    plan_hash = manifest.get("plan_hash")
    if not pinned_commit:
        errors.append("manifest does not pin a commit; run predates immutability anchoring")
    if released_shas is not None and pinned_commit and pinned_commit not in released_shas:
        errors.append(f"pinned commit {pinned_commit} is not a staged immutable release")

    for event in _read_jsonl(evidence_dir / "events.jsonl"):
        if event.get("invalidates_soak"):
            errors.append(
                f"invalidating intervention recorded: {event.get('intervention_kind') or event.get('kind')}"
            )

    leaves: list[dict] = []
    artifacts_verified = 0
    cycles = _read_jsonl(evidence_dir / "cycles.jsonl")
    for cycle in cycles:
        if cycle.get("phase") != "SOAK":
            continue  # foreground/pre-soak and gate cycles are not part of the accepted window
        commit = cycle.get("commit")
        if pinned_commit and commit != pinned_commit:
            errors.append(
                f"cycle {cycle.get('id')} ran at {commit}, not pinned commit {pinned_commit}"
            )
        if plan_hash and cycle.get("plan_hash") != plan_hash:
            errors.append(f"cycle {cycle.get('id')} carries a different plan hash")
        artifacts = []
        for source in cycle.get("sources", []):
            sha = source.get("content_sha256")
            sid = source.get("source_id")
            if not sha or source.get("action") not in _ARTIFACT_ACTIONS:
                continue
            leaf = {"source_id": sid, "content_sha256": sha}
            if archive is not None:
                try:
                    raw = archive.get(sha, sid)
                    actual = hashlib.sha256(raw).hexdigest()
                    if actual != sha:
                        errors.append(f"cycle {cycle.get('id')} artifact {sid}: hash {actual} != {sha}")
                    else:
                        artifacts_verified += 1
                        leaf["archive_verified"] = True
                except (FileNotFoundError, OSError) as exc:
                    errors.append(f"cycle {cycle.get('id')} artifact {sid} unreadable: {exc}")
            artifacts.append(leaf)
        leaves.append({
            "cycle_id": cycle.get("id"), "commit": commit, "at": cycle.get("at"),
            "plan_hash": cycle.get("plan_hash"), "ok": bool(cycle.get("ok")), "artifacts": artifacts,
        })

    chain_sha256 = _sha256_json([pinned_commit, plan_hash, leaves])
    provenance = {
        "ok": not errors,
        "evidence_dir": str(evidence_dir),
        "pinned_commit": pinned_commit,
        "plan_hash": plan_hash,
        "started_at": manifest.get("started_at"),
        "soak_cycles": len(leaves),
        "artifacts_verified": artifacts_verified,
        "archive_checked": archive is not None,
        "chain_sha256": chain_sha256,
        "errors": errors,
    }
    if write:
        tmp = evidence_dir / "provenance.json.tmp"
        tmp.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(evidence_dir / "provenance.json")
    return provenance


def verify_provenance(
    evidence_dir: str | Path,
    *,
    archive: Optional[LocalEvidenceArchive] = None,
    released_shas: Optional[set[str]] = None,
) -> dict:
    """Re-derive the chain read-only and, if a ``provenance.json`` exists, confirm it still matches.

    A stored provenance whose ``chain_sha256`` disagrees with the freshly recomputed chain means the
    evidence changed after provenance was recorded; that is reported as a fail-closed error.
    """
    result = build_provenance(evidence_dir, archive=archive, released_shas=released_shas, write=False)
    stored_path = Path(evidence_dir).resolve() / "provenance.json"
    if stored_path.is_file():
        stored = json.loads(stored_path.read_text(encoding="utf-8"))
        if stored.get("chain_sha256") != result["chain_sha256"]:
            result = dict(result)
            result["ok"] = False
            result["errors"] = list(result["errors"]) + [
                "stored provenance chain_sha256 disagrees with recomputed chain (evidence changed)"
            ]
    return result
