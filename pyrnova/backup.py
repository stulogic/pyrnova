"""Operational backup + isolated restore for Pyrnova Phase 1 durable state.

Goal (Phase 1 operational blocker): prove Pyrnova can produce a *trustworthy* backup, move it away
from the source runtime, restore it into a clean isolated target, and recover the operationally
important state **without violating current source-rights authority or corrupting temporal semantics**.

Design principles honoured here:

* **Durable vs derived is explicit.** Only canonical, non-regenerable durable state is captured
  (:data:`DURABLE_STATE_STREAMS` + the content-addressed evidence archive + the schema identity).
  Derived, deterministically-regenerable artifacts (:data:`DERIVED_REGENERABLE_STREAMS`, rendered
  ``out/`` briefs, caches) are *recorded as excluded* in the manifest and never copied — the correct
  recovery behaviour is to regenerate them from restored canonical state (see
  :func:`regenerate_derived_summary`).
* **Integrity is independently verifiable.** Every captured file carries a size + SHA-256 in a
  deterministic manifest; the manifest itself carries a ``manifest_sha256`` over the sorted entries and
  an explicit ``status``. A partial/failed capture is written as ``status="failed"`` and verification
  fails closed.
* **Restore fails closed.** Restore verifies integrity first, refuses an unsafe (non-isolated) target,
  refuses an incompatible format/version, and — critically — **reconciles restored state against current
  source-rights enforcement before any customer display**. A backup is not an exception to source-rights
  authority: history may be *retained*, but it is never *resurrected* into permitted display when current
  policy forbids it (see :func:`reconcile_display`).
* **Secrets stay safe.** The ``credentials`` stream persists only salted one-way hashes (see
  :mod:`pyrnova.access`); no plaintext secret exists to leak. The process ``.env`` is never part of a
  backup. Credential *metadata* (identity/lifecycle) is durable and is captured so authenticated access
  survives a restore.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

BACKUP_FORMAT = "pyrnova-backup"
BACKUP_FORMAT_VERSION = 1

# --- durable vs derived classification --------------------------------------------------------
# Canonical durable StateStore streams: identity, tenant/customer records, watch configuration,
# credential metadata (hashes only), append-only material-change/version history, human review
# actions, operational fan-out checkpoints, first-seen opportunity state (the moat's timestamps).
DURABLE_STATE_STREAMS = (
    "customers",
    "credentials",
    "customer_watchlist",
    "customer_material_changes",
    "customer_review_actions",
    "reviews",
    "join_reviews",
    "join_review_queue",
    "operator_actions",
    "opportunities",
    "predictions",
    "fanout_runs",           # operational checkpoints / idempotency ledger
    "scoreboard",
)

# Deterministically regenerable from restored canonical state — intentionally EXCLUDED from backup.
# Recovery behaviour is regeneration, not restore (proven by :func:`regenerate_derived_summary` and
# the replay machinery over the restored evidence archive).
DERIVED_REGENERABLE_STREAMS = (
    "replay_results",        # re-derivable by replaying evidence/opportunities
    "replay_reports",        # re-derivable summaries of replay_results
    "chain_replay_results",  # re-derivable chain replay
)

STATE_SUBDIR = "state"
ARCHIVE_SUBDIR = "archive"
SCHEMA_FILE = "schema.sql"
MANIFEST_FILE = "MANIFEST.json"

# Paths a restore must never target (live runtime / soak / evidence). Matched by resolved-path
# containment so a restore can never land on the source runtime or the pinned soak.
_FORBIDDEN_TARGET_MARKERS = ("var/state", "var/phase1_soak", "var/archive")


class BackupError(RuntimeError):
    """Base class for backup/restore failures (all fail closed)."""


class BackupIntegrityError(BackupError):
    """Manifest and contents disagree, a checksum failed, or an artifact is missing."""


class BackupFormatError(BackupError):
    """Unsupported / incompatible backup format or version."""


class UnsafeRestoreTarget(BackupError):
    """Restore destination is missing, non-empty, or points at protected runtime/soak state."""


class SourceRightsReconciliationError(BackupError):
    """Source-rights reconciliation could not be completed safely (fail closed)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class FileEntry:
    path: str          # POSIX relative path inside the backup
    size: int
    sha256: str

    def as_dict(self) -> dict:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


@dataclass
class Manifest:
    format: str
    format_version: int
    created_at: str
    source_commit: str
    source_root: str
    files: list[FileEntry]
    durable_streams: list[str]
    derived_excluded: list[str]
    status: str = "complete"
    manifest_sha256: str = ""

    def compute_manifest_sha256(self) -> str:
        """Deterministic checksum over the sorted file inventory (path+size+sha256)."""
        blob = json.dumps(
            [e.as_dict() for e in sorted(self.files, key=lambda e: e.path)],
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def to_json(self) -> dict:
        return {
            "format": self.format,
            "format_version": self.format_version,
            "created_at": self.created_at,
            "source_commit": self.source_commit,
            "source_root": self.source_root,
            "status": self.status,
            "durable_streams": list(self.durable_streams),
            "derived_excluded": list(self.derived_excluded),
            "files": [e.as_dict() for e in sorted(self.files, key=lambda e: e.path)],
            "manifest_sha256": self.manifest_sha256,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Manifest":
        return cls(
            format=data.get("format", ""),
            format_version=int(data.get("format_version", -1)),
            created_at=data.get("created_at", ""),
            source_commit=data.get("source_commit", ""),
            source_root=data.get("source_root", ""),
            files=[FileEntry(e["path"], int(e["size"]), e["sha256"]) for e in data.get("files", [])],
            durable_streams=list(data.get("durable_streams", [])),
            derived_excluded=list(data.get("derived_excluded", [])),
            status=data.get("status", ""),
            manifest_sha256=data.get("manifest_sha256", ""),
        )


# ---------------------------------------------------------------------- create

def _iter_durable_sources(source_root: Path) -> Iterable[tuple[str, Path]]:
    """Yield ``(backup_relpath, absolute_source_path)`` for every durable artifact to capture."""
    state_dir = source_root / "var" / "state"
    for stream in DURABLE_STATE_STREAMS:
        p = state_dir / f"{stream}.jsonl"
        if p.exists():
            yield f"{STATE_SUBDIR}/{stream}.jsonl", p
    archive_dir = source_root / "var" / "archive"
    if archive_dir.exists():
        for p in sorted(archive_dir.rglob("*")):
            if p.is_file():
                rel = p.relative_to(archive_dir).as_posix()
                yield f"{ARCHIVE_SUBDIR}/{rel}", p
    schema = source_root / "db" / "schema.sql"
    if schema.exists():
        yield SCHEMA_FILE, schema


def create_backup(source_root: Path, dest_dir: Path, *, source_commit: str = "",
                  now: Optional[str] = None) -> Manifest:
    """Create a backup of Pyrnova durable state at ``source_root`` into a fresh ``dest_dir``.

    Reads the source read-only. Fails loudly (``status='failed'`` + raise) if any required artifact
    cannot be copied; a partial backup is never reported as success.
    """
    source_root = Path(source_root).resolve()
    dest_dir = Path(dest_dir)
    if dest_dir.exists() and any(dest_dir.iterdir()):
        raise BackupError(f"backup destination must be empty: {dest_dir}")
    dest_dir.mkdir(parents=True, exist_ok=True)

    entries: list[FileEntry] = []
    manifest = Manifest(
        format=BACKUP_FORMAT, format_version=BACKUP_FORMAT_VERSION,
        created_at=now or _now(), source_commit=source_commit, source_root=str(source_root),
        files=entries, durable_streams=list(DURABLE_STATE_STREAMS),
        derived_excluded=list(DERIVED_REGENERABLE_STREAMS), status="in_progress",
    )
    try:
        for rel, src in _iter_durable_sources(source_root):
            out = dest_dir / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
            size = out.stat().st_size
            digest = sha256_file(out)
            # Guard against a torn read: the copied bytes are what we checksum, so the manifest is
            # always self-consistent with the artifact actually stored.
            if size != src.stat().st_size and sha256_file(src) != digest:
                # Source changed under us mid-copy; re-copy once for a coherent point-in-time capture.
                shutil.copy2(src, out)
                size = out.stat().st_size
                digest = sha256_file(out)
            entries.append(FileEntry(rel, size, digest))
    except Exception as exc:  # capture failed -> write a failed manifest, then re-raise
        manifest.status = "failed"
        manifest.manifest_sha256 = manifest.compute_manifest_sha256()
        _write_manifest(dest_dir, manifest)
        raise BackupError(f"backup capture failed: {exc}") from exc

    if not entries:
        manifest.status = "failed"
        manifest.manifest_sha256 = manifest.compute_manifest_sha256()
        _write_manifest(dest_dir, manifest)
        raise BackupError("no durable artifacts found to back up")

    manifest.status = "complete"
    manifest.manifest_sha256 = manifest.compute_manifest_sha256()
    _write_manifest(dest_dir, manifest)
    return manifest


def _write_manifest(dest_dir: Path, manifest: Manifest) -> None:
    (dest_dir / MANIFEST_FILE).write_text(
        json.dumps(manifest.to_json(), indent=2, sort_keys=False) + "\n", encoding="utf-8")


def load_manifest(backup_dir: Path) -> Manifest:
    p = Path(backup_dir) / MANIFEST_FILE
    if not p.exists():
        raise BackupIntegrityError(f"manifest missing: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BackupIntegrityError(f"manifest is not valid JSON: {exc}") from exc
    return Manifest.from_json(data)


# ---------------------------------------------------------------------- verify

@dataclass
class VerifyResult:
    ok: bool
    checked: int
    problems: list[str] = field(default_factory=list)


def verify_backup(backup_dir: Path) -> VerifyResult:
    """Independently verify a backup's integrity from its manifest. Fails closed on any mismatch."""
    backup_dir = Path(backup_dir)
    manifest = load_manifest(backup_dir)
    problems: list[str] = []

    if manifest.format != BACKUP_FORMAT:
        raise BackupFormatError(f"unknown backup format: {manifest.format!r}")
    if manifest.format_version != BACKUP_FORMAT_VERSION:
        raise BackupFormatError(
            f"incompatible backup format version {manifest.format_version} "
            f"(this tool supports {BACKUP_FORMAT_VERSION})")
    if manifest.status != "complete":
        problems.append(f"backup status is {manifest.status!r}, not 'complete'")

    recomputed = manifest.compute_manifest_sha256()
    if recomputed != manifest.manifest_sha256:
        problems.append("manifest_sha256 does not match the file inventory (manifest tampered/corrupt)")

    checked = 0
    for entry in manifest.files:
        fp = backup_dir / entry.path
        if not fp.exists():
            problems.append(f"missing artifact: {entry.path}")
            continue
        actual_size = fp.stat().st_size
        if actual_size != entry.size:
            problems.append(f"size mismatch for {entry.path}: {actual_size} != {entry.size}")
        actual_sha = sha256_file(fp)
        if actual_sha != entry.sha256:
            problems.append(f"checksum mismatch for {entry.path}")
        checked += 1

    result = VerifyResult(ok=not problems, checked=checked, problems=problems)
    return result


# ---------------------------------------------------------------------- restore

def _assert_safe_target(target_root: Path) -> None:
    target = Path(target_root).resolve()
    posix = target.as_posix()
    for marker in _FORBIDDEN_TARGET_MARKERS:
        if posix.endswith("/" + marker) or ("/" + marker + "/") in (posix + "/"):
            raise UnsafeRestoreTarget(
                f"refusing to restore into protected runtime/soak path: {target} (matches {marker!r})")
    if target.exists() and any(target.iterdir()):
        raise UnsafeRestoreTarget(f"restore target must be empty/clean: {target}")


@dataclass
class RestoreResult:
    target_root: str
    manifest: Manifest
    restored_files: int
    verify: VerifyResult


def restore_backup(backup_dir: Path, target_root: Path, *, verify: bool = True) -> RestoreResult:
    """Restore a backup into a clean, isolated ``target_root``.

    Order (all fail closed): verify integrity -> assert target is safe/isolated -> materialise files.
    The restored layout mirrors ``var/state`` + ``var/archive`` + ``db/schema.sql`` under ``target_root``
    so a fresh runtime can consume it. Callers MUST run :func:`reconcile_display` before any customer
    display (restore alone does not authorise display — see module docstring / check G).
    """
    backup_dir = Path(backup_dir)
    target_root = Path(target_root)

    verify_result = verify_backup(backup_dir) if verify else VerifyResult(True, 0)
    if verify and not verify_result.ok:
        raise BackupIntegrityError(
            "backup failed integrity verification; refusing to restore:\n  - "
            + "\n  - ".join(verify_result.problems))

    manifest = load_manifest(backup_dir)
    _assert_safe_target(target_root)
    target_root.mkdir(parents=True, exist_ok=True)

    restored = 0
    for entry in manifest.files:
        src = backup_dir / entry.path
        if entry.path == SCHEMA_FILE:
            dest = target_root / "db" / SCHEMA_FILE
        elif entry.path.startswith(STATE_SUBDIR + "/"):
            dest = target_root / "var" / "state" / entry.path[len(STATE_SUBDIR) + 1:]
        elif entry.path.startswith(ARCHIVE_SUBDIR + "/"):
            dest = target_root / "var" / "archive" / entry.path[len(ARCHIVE_SUBDIR) + 1:]
        else:
            dest = target_root / entry.path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        restored += 1

    return RestoreResult(str(Path(target_root).resolve()), manifest, restored, verify_result)


# ---------------------------------------------------------------------- source-rights reconciliation

@dataclass
class DisplayDecision:
    record_id: str
    customer_id: str
    source_ids: list[str]
    allowed: bool
    reason_code: str
    reason: str


@dataclass
class ReconcileReport:
    total: int
    allowed: int
    blocked: int
    decisions: list[DisplayDecision]

    def blocked_source_ids(self) -> set[str]:
        out: set[str] = set()
        for d in self.decisions:
            if not d.allowed:
                out.update(d.source_ids)
        return out


def _display_projection(record: dict, source_ids: list[str]) -> dict:
    """A prose-free customer-display projection carrying only identity/provenance + source ids.

    This isolates the *resurrection* question — does current source-rights policy still permit this
    record's sources to be displayed — from projection-shape concerns. Kept deliberately minimal so the
    decision reduces to source-policy current-permission, which is exactly what a restore must reconcile.
    """
    proj = {
        "record_id": record.get("record_id") or record.get("id") or "",
        "customer_id": record.get("customer_id", ""),
        "source_ids": sorted(source_ids),
        "valid_from": record.get("valid_from"),
        "available_at": record.get("intelligence_observed_at") or record.get("available_at"),
    }
    if isinstance(record.get("source_refs"), dict):
        # Retain reference-only provenance (evidence ids, hashes) — no prose, no raw content.
        proj["source_refs"] = {k: v for k, v in record["source_refs"].items()
                               if k in {"evidence_ids", "source_ref", "archive_hash", "program", "subject_ref"}}
    return proj


def reconcile_display(target_root: Path, *, stream: str = "customer_material_changes") -> ReconcileReport:
    """Reconcile restored customer-facing records against CURRENT source-rights enforcement.

    For every restored record we collect its attributable source ids and ask the authoritative gate
    (:func:`pyrnova.sources.rights.gate_customer_display`) whether current policy still permits display.
    Records whose sources are now restricted are reported BLOCKED: the durable record remains in restored
    state (history is preserved), but it is NOT resurrected into permitted display. Fails closed
    (:class:`SourceRightsReconciliationError`) if the gate itself cannot render a decision.
    """
    from pyrnova.sources import rights  # authoritative, registry-owned enforcement

    state_file = Path(target_root) / "var" / "state" / f"{stream}.jsonl"
    decisions: list[DisplayDecision] = []
    if state_file.exists():
        for line in state_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            source_ids = sorted(rights._collect_source_ids(record))
            proj = _display_projection(record, source_ids)
            try:
                gated = rights.gate_customer_display(proj)
            except Exception as exc:  # gate must render a decision; anything else fails closed
                raise SourceRightsReconciliationError(
                    f"source-rights gate could not decide record {proj['record_id']!r}: {exc}") from exc
            sr = gated.get("source_rights", {})
            allowed = sr.get("display") == "ALLOWED"
            decisions.append(DisplayDecision(
                record_id=proj["record_id"], customer_id=proj["customer_id"],
                source_ids=list(sr.get("source_ids") or source_ids),
                allowed=allowed, reason_code=sr.get("reason_code", ""), reason=sr.get("reason", "")))

    allowed = sum(1 for d in decisions if d.allowed)
    return ReconcileReport(total=len(decisions), allowed=allowed,
                           blocked=len(decisions) - allowed, decisions=decisions)


# ---------------------------------------------------------------------- safe derived regeneration

def regenerate_derived_summary(target_root: Path) -> dict:
    """Deterministically regenerate a derived summary from restored canonical state.

    Demonstrates that derived state intentionally excluded from backup is recoverable *from* the
    restored canonical durable state — the correct recovery behaviour for regenerable artifacts (check F).
    The result is a pure function of restored durable content, so it is byte-reproducible.
    """
    state_dir = Path(target_root) / "var" / "state"
    summary: dict = {"streams": {}, "customers": {}}
    for stream in DURABLE_STATE_STREAMS:
        p = state_dir / f"{stream}.jsonl"
        if not p.exists():
            continue
        records = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        summary["streams"][stream] = len(records)
        for r in records:
            cid = r.get("customer_id")
            if cid:
                summary["customers"].setdefault(cid, {}).setdefault(stream, 0)
                summary["customers"][cid][stream] += 1
    # Content-addressed archive index: proves the derived dedup index regenerates from canonical bytes.
    archive_dir = Path(target_root) / "var" / "archive"
    content_index: dict[str, int] = {}
    if archive_dir.exists():
        for p in sorted(archive_dir.rglob("*")):
            if p.is_file() and not p.name.endswith(".observations.jsonl"):
                content_index[sha256_file(p)] = p.stat().st_size
    summary["archive_objects"] = len(content_index)
    summary["archive_index_sha256"] = hashlib.sha256(
        json.dumps(sorted(content_index.items()), separators=(",", ":")).encode()).hexdigest()
    return summary
