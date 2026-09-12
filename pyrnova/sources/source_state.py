"""Durable, cross-restart source state — budgets, breaker, checkpoints, request dedupe.

`control.SourceControl` is deliberately in-process only: its budget counter, circuit breaker, and
metrics all reset when the process restarts, and it reads no cache. That leaves a doctrine gap
(`SOURCE_INGESTION.md`: persistent cursors/checkpoints, request deduplication, cache reuse in
OFFLINE/LIVE-SAFE, and a budget that actually stops across restarts).

This module closes that gap as an ISOLATED infrastructure layer. It persists one JSON document per
source under a state directory and can hydrate a fresh `SourceControl` from it and persist it back. It
also maintains a request-dedupe / cache index (sanitized ``request_fingerprint`` -> archived
``content_sha256`` + ``fetched_at``) so an equivalent request can be served from the archive instead of
a fresh live call. It performs NO HTTP and imports no adapter; adapters opt in explicitly. Nothing in
``control.py`` or the existing adapters is modified.

Budget epochs: a live-call budget is meaningful only within a window (e.g. a provider's daily quota).
Callers pass a ``budget_epoch`` label; when the stored epoch differs, the persisted call count resets
to zero on hydrate, so a new window starts fresh rather than inheriting an exhausted budget.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = "source_state_v1"


def _safe_source_id(source_id: str) -> str:
    if not source_id or not str(source_id).strip():
        raise ValueError("source_id is required")
    # keep the filename to a conservative charset; never allow path traversal
    cleaned = "".join(c if (c.isalnum() or c in "._-") else "_" for c in str(source_id))
    return cleaned


class SourceStateStore:
    """Persist and reload per-source control state, checkpoints, and a request-dedupe index."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, source_id: str) -> Path:
        return self.root / f"{_safe_source_id(source_id)}.json"

    # ------------------------------------------------------------------ raw document

    def load(self, source_id: str) -> dict:
        """Return the persisted document for ``source_id`` (empty scaffold if absent/corrupt)."""
        path = self._path(source_id)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            doc = {}
        if not isinstance(doc, dict):
            doc = {}
        doc.setdefault("schema_version", SCHEMA_VERSION)
        doc.setdefault("source_id", source_id)
        doc.setdefault("budget", {})
        doc.setdefault("breaker", {})
        doc.setdefault("metrics", {})
        doc.setdefault("checkpoint", None)
        doc.setdefault("requests", {})
        return doc

    def save(self, source_id: str, doc: dict) -> None:
        """Atomically write the document for ``source_id`` (tmp file + os.replace)."""
        path = self._path(source_id)
        doc = dict(doc)
        doc["schema_version"] = SCHEMA_VERSION
        doc["source_id"] = source_id
        fd, tmp = tempfile.mkstemp(dir=str(self.root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, sort_keys=True, indent=2)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # ------------------------------------------------------------------ checkpoint / cursor

    def get_checkpoint(self, source_id: str) -> Optional[str]:
        return self.load(source_id).get("checkpoint")

    def set_checkpoint(self, source_id: str, cursor: Optional[str]) -> None:
        doc = self.load(source_id)
        doc["checkpoint"] = cursor
        self.save(source_id, doc)

    # ------------------------------------------------------------------ operational history

    def record_operation(
        self,
        source_id: str,
        *,
        action: str,
        at: Optional[str] = None,
        error: Optional[str] = None,
        network_attempted: bool = False,
        acquisition_succeeded: bool = False,
    ) -> None:
        """Persist the latest scheduler-cycle truth used by operator health views.

        This is deliberately a compact latest-state record, not a second event store. The soak
        harness owns the append-only per-cycle evidence ledger; source state owns only the values
        required to recover and answer whether a source is current, degraded, or retrying.
        """
        stamp = at or datetime.now(timezone.utc).isoformat()
        doc = self.load(source_id)
        operation = dict(doc.get("operation") or {})
        operation["last_cycle_at"] = stamp
        operation["last_action"] = action
        if network_attempted:
            operation["last_network_attempt_at"] = stamp
        if acquisition_succeeded:
            operation["last_successful_acquisition_at"] = stamp
            operation["consecutive_failed_cycles"] = 0
            operation["last_error"] = None
        elif error:
            operation["consecutive_failed_cycles"] = int(
                operation.get("consecutive_failed_cycles") or 0
            ) + 1
            operation["last_error"] = str(error)
        doc["operation"] = operation
        self.save(source_id, doc)

    # ------------------------------------------------------------------ request dedupe / cache index

    def seen_request(self, source_id: str, fingerprint: str) -> Optional[dict]:
        """Return the archived reference for a previously recorded request, else None."""
        if not fingerprint:
            return None
        return self.load(source_id).get("requests", {}).get(fingerprint)

    def record_request(self, source_id: str, fingerprint: str, *, content_sha256: str,
                       fetched_at: str, source_url: Optional[str] = None) -> None:
        """Index a completed request so an equivalent one can be deduplicated / served from archive."""
        if not fingerprint:
            raise ValueError("fingerprint is required to record a request")
        doc = self.load(source_id)
        doc.setdefault("requests", {})[fingerprint] = {
            "content_sha256": content_sha256,
            "fetched_at": fetched_at,
            "source_url": source_url,
        }
        self.save(source_id, doc)

    # ------------------------------------------------------------------ SourceControl hydration

    def persist_control(self, source_id: str, control: Any, *,
                        budget_epoch: Optional[str] = None) -> None:
        """Write a SourceControl's budget, breaker, and metrics to durable state."""
        doc = self.load(source_id)
        doc["budget"] = {
            "epoch": budget_epoch,
            "max_calls": control.budget.max_calls,
            "calls_made": control.budget.calls_made,
        }
        breaker = control.breaker
        doc["breaker"] = {
            "state": breaker.state.value,
            "consecutive_failures": breaker.consecutive_failures,
            "next_permitted_poll": breaker.next_permitted_poll,
        }
        doc["metrics"] = control.metrics.as_dict(
            next_permitted_poll=breaker.next_permitted_poll,
            circuit_state=breaker.state.value,
        )
        self.save(source_id, doc)

    def hydrate_control(self, source_id: str, control: Any, *,
                        budget_epoch: Optional[str] = None) -> Any:
        """Apply persisted budget/breaker/metrics onto a fresh SourceControl and return it.

        If the stored budget epoch differs from ``budget_epoch``, the call count resets to zero — a new
        budget window must not inherit an exhausted count from a previous one."""
        from .control import CircuitState  # local import keeps this module import-light

        doc = self.load(source_id)
        budget = doc.get("budget") or {}
        if budget.get("epoch") == budget_epoch and isinstance(budget.get("calls_made"), int):
            control.budget.calls_made = max(0, budget["calls_made"])
        else:
            control.budget.calls_made = 0

        breaker = doc.get("breaker") or {}
        if breaker.get("state") in {s.value for s in CircuitState}:
            control.breaker.state = CircuitState(breaker["state"])
        if isinstance(breaker.get("consecutive_failures"), int):
            control.breaker.consecutive_failures = breaker["consecutive_failures"]
        control.breaker.next_permitted_poll = breaker.get("next_permitted_poll")

        metrics = doc.get("metrics") or {}
        for name in ("calls_made", "cache_hits", "calls_avoided", "retryable_errors",
                     "throttles", "terminal_errors", "last_successful_call",
                     "last_detected_change", "quota_state"):
            if name in metrics and metrics[name] is not None:
                setattr(control.metrics, name, metrics[name])
        # Keep the live budget counter and the metrics mirror consistent.
        control.metrics.calls_made = control.budget.calls_made
        return control


__all__ = ["SCHEMA_VERSION", "SourceStateStore"]
