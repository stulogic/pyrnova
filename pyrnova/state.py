"""Append-only local state (predictions, reviews, observations, scoreboard).

This is the Day-1 proprietary accumulation in the local dev path. In production the same records go to
Postgres (db/schema.sql); the interface is intentionally tiny so the Postgres adapter drops in later.
Append-only + timestamped = the point-in-time history the moat depends on.

B4.4 production hardening (single-node, append-only — intentionally NOT distributed):
    * concurrent writers are serialized by a per-file exclusive advisory lock (``fcntl.flock``), and each
      append is O_APPEND + flush + fsync (configurable) so it is atomic and durable and a reader never
      observes a torn line;
    * readers take a shared advisory lock, detect a partial/torn trailing write (a final line with no
      terminating newline — a never-completed append) and drop ONLY that tail (fail-closed recovery), while
      a malformed COMPLETE record raises :class:`StateCorruptionError` rather than being silently skipped
      (no silent truncation, no history rewriting);
    * :meth:`snapshot` gives a backup a consistent, torn-tail-free copy taken under a shared lock, so
      backups coordinate safely with active writes.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterator

try:  # POSIX advisory locks — the single-node production host is Linux/macOS.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback (locking degrades to a no-op)
    fcntl = None


class StateCorruptionError(RuntimeError):
    """A durable state stream contains a malformed COMPLETE record.

    This is genuine corruption (a fully terminated line that is not valid JSON), distinct from a
    recoverable torn/partial trailing write. Raised so the defect is visible and fails closed rather than
    silently dropping committed history.
    """


def _fsync_enabled() -> bool:
    """Durability policy: fsync every append by default (production-safe). Set ``PYRNOVA_STATE_FSYNC=0``
    to disable (e.g. throwaway test volume where durability across a crash does not matter)."""
    return os.environ.get("PYRNOVA_STATE_FSYNC", "1").strip().lower() not in ("0", "false", "no", "off")


class _FileLock:
    """Advisory lock over an open file handle (no-op where ``fcntl`` is unavailable)."""

    def __init__(self, fh, *, exclusive: bool):
        self._fh = fh
        self._exclusive = exclusive

    def __enter__(self):
        if fcntl is not None:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX if self._exclusive else fcntl.LOCK_SH)
        return self._fh

    def __exit__(self, *exc):
        if fcntl is not None:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        return False


class StateStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, stream: str) -> Path:
        return self.root / f"{stream}.jsonl"

    def append(self, stream: str, record: dict) -> None:
        record = {"_ts": datetime.utcnow().isoformat(), **record}
        line = json.dumps(record, ensure_ascii=False) + "\n"
        # O_APPEND positions every write at EOF; the exclusive advisory lock serializes concurrent writers
        # (in-process and cross-process on the same host) and keeps flush+fsync atomic, so a reader never
        # sees a torn line and two writers never interleave a partial record.
        with self._path(stream).open("a", encoding="utf-8") as fh:
            with _FileLock(fh, exclusive=True):
                fh.write(line)
                fh.flush()
                if _fsync_enabled():
                    os.fsync(fh.fileno())

    def _read_committed(self, p: Path) -> tuple[list[str], bool]:
        """Return (terminated lines, torn_tail?) read under a shared lock. A non-empty segment after the
        final newline is a never-completed append (torn/partial write)."""
        with p.open("r", encoding="utf-8") as fh:
            with _FileLock(fh, exclusive=False):
                content = fh.read()
        if not content:
            return [], False
        parts = content.split("\n")
        tail = parts.pop()  # text after the last "\n" ("" for a cleanly terminated file)
        return parts, bool(tail.strip())

    def read(self, stream: str) -> Iterator[dict]:
        p = self._path(stream)
        if not p.exists():
            return iter(())
        lines, _torn_tail = self._read_committed(p)
        records: list[dict] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                # A fully terminated but unparseable record is real corruption — fail closed, never a
                # silent skip (that would rewrite history). A torn TRAILING write is handled above.
                raise StateCorruptionError(f"malformed record in {p.name}: {exc}") from None
        return iter(records)

    def count(self, stream: str) -> int:
        return sum(1 for _ in self.read(stream))

    def latest(self, stream: str, record_id: str) -> dict | None:
        found = None
        for record in self.read(stream):
            if record.get("id") == record_id:
                found = record
        return found

    def snapshot(self, stream: str, dest: Path) -> int:
        """Copy a stream's COMMITTED records to ``dest`` under a shared lock (safe during active writes).

        A torn/partial trailing write is excluded; the destination is written atomically via a temp file
        + ``os.replace``. Returns the number of committed lines copied. Used by the backup path so backups
        coordinate safely with concurrent appends (B4.8)."""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        p = self._path(stream)
        if not p.exists():
            dest.write_text("", encoding="utf-8")
            return 0
        lines, _torn_tail = self._read_committed(p)
        # Preserve exact committed content (every terminated line) minus any torn trailing write.
        payload = "".join(f"{line}\n" for line in lines)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            if _fsync_enabled():
                os.fsync(fh.fileno())
        os.replace(tmp, dest)
        return sum(1 for line in lines if line.strip())
