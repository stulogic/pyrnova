"""Heartbeat / progress evidence for the dead-man liveness path.

The Pyrnova service writes a small, durable heartbeat record each time it makes progress; a *separate*
watcher process (:mod:`pyrnova.watchdog`) reads it and decides whether the service has gone silent. The two
sides share only this bounded on-disk record — the watcher never depends on the service's in-process loop
still running, which is exactly what lets it notice that the service died.

Design points:
- restart-safe: the record is a single JSON file, atomically replaced; a fresh writer continues the
  sequence rather than resetting it;
- fail-closed on read: a missing or corrupt record reads as absence-of-heartbeat (MISSING), never as
  "fresh", so the watcher errs toward raising rather than staying quiet;
- deliberate maintenance is explicit: a maintenance marker in the record suppresses false CRITICALs while
  the service is intentionally down, and is distinguishable from an unexpected silence.

This is the explicit primitive; in production the service's existing per-cycle ``status.json`` write is the
natural place to also call :meth:`HeartbeatWriter.beat`. Nothing here is wired into the running soak.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = "heartbeat_v1"
DEFAULT_COMPONENT = "live_ops"


class Liveness(str, Enum):
    FRESH = "FRESH"            # a recent heartbeat within the accepted silence threshold
    STALE = "STALE"           # a heartbeat exists but is older than the threshold (dead-man expiry)
    MISSING = "MISSING"       # no heartbeat / unreadable record — fail closed, treat as expired
    MAINTENANCE = "MAINTENANCE"  # deliberately disabled; do not raise a false CRITICAL


def _now(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse(ts: Any) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _safe_component(component: str) -> str:
    if not component or not str(component).strip():
        raise ValueError("component is required")
    return "".join(c if (c.isalnum() or c in "._-") else "_" for c in str(component))


class HeartbeatWriter:
    """Writes the service-side heartbeat/progress record (one JSON file per component)."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, component: str) -> Path:
        return self.root / f"{_safe_component(component)}.json"

    def _load(self, component: str) -> dict:
        try:
            doc = json.loads(self._path(component).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return doc if isinstance(doc, dict) else {}

    def _save(self, component: str, doc: dict) -> None:
        doc = dict(doc)
        doc["schema_version"] = SCHEMA_VERSION
        doc["component"] = component
        fd, tmp = tempfile.mkstemp(dir=str(self.root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, sort_keys=True, indent=2)
            os.replace(tmp, self._path(component))
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def beat(self, component: str = DEFAULT_COMPONENT, *, progress: Optional[dict] = None,
             now: Optional[datetime] = None) -> dict:
        """Record one heartbeat. Increments a restart-safe sequence and clears any maintenance marker."""
        stamp = _now(now)
        doc = self._load(component)
        sequence = int(doc.get("sequence") or 0) + 1
        record = {
            "component": component,
            "last_beat_at": _iso(stamp),
            "sequence": sequence,
            "pid": os.getpid(),
            "progress": progress or {},
            "maintenance": {"active": False},
        }
        self._save(component, record)
        return record

    def set_maintenance(self, component: str = DEFAULT_COMPONENT, *, active: bool = True,
                        reason: str = "", now: Optional[datetime] = None) -> dict:
        """Mark a component as deliberately down (or clear it). Prevents false dead-man CRITICALs."""
        stamp = _now(now)
        doc = self._load(component)
        doc.setdefault("component", component)
        doc.setdefault("sequence", int(doc.get("sequence") or 0))
        doc["maintenance"] = {"active": bool(active), "reason": reason, "set_at": _iso(stamp)}
        self._save(component, doc)
        return doc


class HeartbeatReader:
    """Reads a heartbeat record and computes liveness against an accepted silence threshold."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, component: str) -> Path:
        return self.root / f"{_safe_component(component)}.json"

    def read(self, component: str = DEFAULT_COMPONENT) -> Optional[dict]:
        try:
            doc = json.loads(self._path(component).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return doc if isinstance(doc, dict) else None

    def status(self, component: str = DEFAULT_COMPONENT, *, max_silence_seconds: float,
               now: Optional[datetime] = None) -> dict:
        """Return liveness for ``component``: state, age, last beat, and the threshold used.

        Fail-closed: a missing/corrupt record or an unparseable timestamp yields MISSING, so an absent
        service is never mistaken for a fresh one. A record explicitly in maintenance yields MAINTENANCE.
        """
        stamp = _now(now)
        doc = self.read(component)
        if doc is None:
            return {"component": component, "state": Liveness.MISSING.value, "age_seconds": None,
                    "last_beat_at": None, "sequence": None, "max_silence_seconds": max_silence_seconds}
        maintenance = doc.get("maintenance") or {}
        if maintenance.get("active"):
            return {"component": component, "state": Liveness.MAINTENANCE.value, "age_seconds": None,
                    "last_beat_at": doc.get("last_beat_at"), "sequence": doc.get("sequence"),
                    "maintenance_reason": maintenance.get("reason", ""),
                    "max_silence_seconds": max_silence_seconds}
        last = _parse(doc.get("last_beat_at"))
        if last is None:
            return {"component": component, "state": Liveness.MISSING.value, "age_seconds": None,
                    "last_beat_at": doc.get("last_beat_at"), "sequence": doc.get("sequence"),
                    "max_silence_seconds": max_silence_seconds}
        age = max(0.0, (stamp - last).total_seconds())
        state = Liveness.FRESH if age <= float(max_silence_seconds) else Liveness.STALE
        return {"component": component, "state": state.value, "age_seconds": age,
                "last_beat_at": doc.get("last_beat_at"), "sequence": doc.get("sequence"),
                "max_silence_seconds": max_silence_seconds}


__all__ = ["SCHEMA_VERSION", "DEFAULT_COMPONENT", "Liveness", "HeartbeatWriter", "HeartbeatReader"]
