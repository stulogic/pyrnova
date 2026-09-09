"""M12 — durable source integration: scheduler / jobs over the existing source primitives.

This layer *composes* three things that already exist independently and wires them into a runnable,
offline-default job runner:

- ``sources.control.SourceControl`` — mode, budget, circuit breaker, retry metadata, metrics.
- ``sources.source_state.SourceStateStore`` — durable cross-restart budget/breaker/checkpoint + a
  request-dedupe/cache index.
- ``sources.registry`` — which sources are active, with rights/retention.
- ``archive.EvidenceArchive`` — exact-byte Tier-B storage (dedupe/cache/archive/resume).

It performs **no HTTP of its own** and imports no adapter. Live fetching happens only when the caller
supplies a ``fetcher`` callable AND the effective mode is not OFFLINE. The default mode is OFFLINE, so a
scheduler run never reaches the network unless a caller explicitly opts a source into a live mode and
hands it a fetcher — the anti-accumulation / offline-first doctrine, enforced structurally.

Operator controls (pause/resume, mode override, breaker reset) are persisted in the source's durable
state document under ``operator`` and survive restarts. ``health()`` renders an operator-visible view of
every source: mode, budget remaining, circuit state, cache hits, calls avoided, checkpoint, last change,
and paused status — the data the Operations Panel surfaces.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .sources.control import (
    CircuitOpen,
    CircuitState,
    ExternalCallBlocked,
    RequestBudgetExceeded,
    SourceControl,
    SourceMode,
    request_fingerprint,
)
from .sources.registry import REGISTRY, active_sources
from .sources.source_state import SourceStateStore

# Job actions (the outcome of one scheduled request).
CACHE_HIT = "cache_hit"           # served from the dedupe/cache index (no budget spent)
OFFLINE_REPLAY = "offline_replay"  # OFFLINE fixture bytes archived + indexed (no network)
LIVE_FETCH = "live_fetch"          # a live call was authorized and made
SKIPPED_PAUSED = "skipped_paused"  # operator paused this source
SKIPPED_OFFLINE = "skipped_offline"  # OFFLINE mode, nothing cached, no fixture bytes
SKIPPED_BUDGET = "skipped_budget"  # durable budget exhausted for this epoch
SKIPPED_NOT_DUE = "skipped_not_due"  # poll cadence not yet elapsed; no request issued
CIRCUIT_OPEN = "circuit_open"      # breaker is open; next poll deferred
ERROR = "error"                    # fetcher raised; failure recorded, backoff advised


@dataclass
class SourceJobResult:
    source_id: str
    action: str
    mode: str
    request_fingerprint: Optional[str] = None
    content_sha256: Optional[str] = None
    from_archive: bool = False
    checkpoint: Optional[str] = None
    reason: str = ""
    retry: Optional[dict] = None
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None or k in ("from_archive",)}


class SourceScheduler:
    """Offline-default job runner that ties durable state, control, and archive together per source."""

    def __init__(
        self,
        state_store: SourceStateStore,
        *,
        archive: Any = None,
        default_mode: SourceMode | str = SourceMode.OFFLINE,
        budget_epoch: Optional[str] = None,
    ):
        self.state = state_store
        self.archive = archive
        self.default_mode = self._as_mode(default_mode)
        self.budget_epoch = budget_epoch

    @staticmethod
    def _as_mode(mode: SourceMode | str) -> SourceMode:
        return mode if isinstance(mode, SourceMode) else SourceMode(str(mode).upper().replace("-", "_"))

    # ------------------------------------------------------------------ operator controls

    def _operator(self, source_id: str) -> dict:
        return self.state.load(source_id).get("operator") or {}

    def _set_operator(self, source_id: str, **changes) -> None:
        doc = self.state.load(source_id)
        operator = dict(doc.get("operator") or {})
        operator.update(changes)
        doc["operator"] = operator
        self.state.save(source_id, doc)

    def pause(self, source_id: str, *, reason: str = "") -> None:
        self._set_operator(source_id, paused=True, paused_reason=reason)

    def resume(self, source_id: str) -> None:
        self._set_operator(source_id, paused=False, paused_reason="")

    def is_paused(self, source_id: str) -> bool:
        return bool(self._operator(source_id).get("paused"))

    def set_mode(self, source_id: str, mode: SourceMode | str) -> None:
        """Persist an operator mode override for a source (e.g. OFFLINE -> LIVE_SAFE)."""
        self._set_operator(source_id, mode_override=self._as_mode(mode).value)

    def clear_mode(self, source_id: str) -> None:
        self._set_operator(source_id, mode_override=None)

    def effective_mode(self, source_id: str, requested: SourceMode | str | None = None) -> SourceMode:
        if requested is not None:
            return self._as_mode(requested)
        override = self._operator(source_id).get("mode_override")
        return self._as_mode(override) if override else self.default_mode

    def reset_breaker(self, source_id: str) -> None:
        doc = self.state.load(source_id)
        doc["breaker"] = {"state": CircuitState.CLOSED.value, "consecutive_failures": 0,
                          "next_permitted_poll": None}
        self.state.save(source_id, doc)

    # ------------------------------------------------------------------ poll cadence (M13)

    def _schedule(self, source_id: str) -> dict:
        return self.state.load(source_id).get("schedule") or {}

    def set_poll_interval(self, source_id: str, seconds: float) -> None:
        """Persist a minimum interval (seconds) between live polls for a source."""
        if seconds < 0:
            raise ValueError("poll interval must be non-negative")
        doc = self.state.load(source_id)
        sched = dict(doc.get("schedule") or {})
        sched["interval_seconds"] = float(seconds)
        doc["schedule"] = sched
        self.state.save(source_id, doc)

    def get_poll_interval(self, source_id: str) -> Optional[float]:
        val = self._schedule(source_id).get("interval_seconds")
        return float(val) if isinstance(val, (int, float)) else None

    def mark_polled(self, source_id: str, *, now: Optional[float] = None) -> float:
        """Record that a live poll was attempted for a source (advances the cadence clock)."""
        stamp = float(now) if now is not None else _epoch_now()
        doc = self.state.load(source_id)
        sched = dict(doc.get("schedule") or {})
        sched["last_polled"] = stamp
        doc["schedule"] = sched
        self.state.save(source_id, doc)
        return stamp

    def _breaker_next_poll(self, source_id: str) -> Optional[float]:
        npp = (self.state.load(source_id).get("breaker") or {}).get("next_permitted_poll")
        return float(npp) if isinstance(npp, (int, float)) else None

    def next_poll_due(self, source_id: str) -> Optional[float]:
        """Epoch seconds when this source may next be polled: the later of cadence and breaker cooldown.

        ``None`` interval means 'no cadence configured' → cadence never defers (breaker may still)."""
        sched = self._schedule(source_id)
        interval = sched.get("interval_seconds")
        last = sched.get("last_polled")
        cadence_due = (float(last) + float(interval)) if (
            isinstance(interval, (int, float)) and isinstance(last, (int, float))) else None
        breaker_due = self._breaker_next_poll(source_id)
        candidates = [c for c in (cadence_due, breaker_due) if c is not None]
        return max(candidates) if candidates else None

    def next_poll_at(self, source_id: str) -> Optional[str]:
        """ISO-8601 rendering of :meth:`next_poll_due` for operator display."""
        due = self.next_poll_due(source_id)
        if due is None:
            return None
        from datetime import datetime, timezone

        return datetime.fromtimestamp(due, tz=timezone.utc).isoformat()

    def due(self, source_id: str, *, now: Optional[float] = None) -> bool:
        """Is this source due for a live poll? Paused/circuit-open/cadence-not-elapsed all defer it."""
        if self.is_paused(source_id):
            return False
        current = float(now) if now is not None else _epoch_now()
        due_at = self.next_poll_due(source_id)
        return True if due_at is None else current >= due_at

    def due_sources(self, source_ids: Optional[list[str]] = None, *, now: Optional[float] = None) -> list[str]:
        ids = source_ids if source_ids is not None else self.known_sources()
        return [sid for sid in ids if self.due(sid, now=now)]

    def poll(
        self,
        source_id: str,
        *,
        request: dict,
        now: Optional[float] = None,
        **run_job_kwargs: Any,
    ) -> SourceJobResult:
        """Cadence-aware wrapper over :meth:`run_job`.

        If the source is not yet due (cadence not elapsed, circuit cooling, or paused) it returns a
        ``SKIPPED_NOT_DUE`` / ``SKIPPED_PAUSED`` result **without** issuing any request. Otherwise it
        runs the job and advances the cadence clock. ``run_job`` itself is unchanged, so nothing that
        does not opt into ``poll`` sees any behaviour change."""
        eff_mode = self.effective_mode(source_id, run_job_kwargs.get("mode"))
        fp = request_fingerprint(
            request.get("method", "GET"), request.get("url", ""),
            params=request.get("params"), headers=request.get("headers"),
            payload=request.get("payload"))
        if self.is_paused(source_id):
            return SourceJobResult(source_id, SKIPPED_PAUSED, eff_mode.value, fp,
                                   reason=self._operator(source_id).get("paused_reason") or "operator paused",
                                   checkpoint=self.state.get_checkpoint(source_id))
        # The cadence gate only governs requests that would actually reach the network. A request already
        # in the dedupe/cache index (served from archive, no budget) is not deferred by cadence — nor is
        # an OFFLINE replay of supplied fixture bytes. Only a genuine live call obeys the poll window.
        would_hit_network = not (
            (self.state.seen_request(source_id, fp) and eff_mode != SourceMode.ACCEPTANCE)
            or eff_mode == SourceMode.OFFLINE
        )
        if would_hit_network and not self.due(source_id, now=now):
            return SourceJobResult(source_id, SKIPPED_NOT_DUE, eff_mode.value, fp,
                                   reason=f"not due until {self.next_poll_at(source_id)}",
                                   checkpoint=self.state.get_checkpoint(source_id))
        result = self.run_job(source_id, request=request, now=now, **run_job_kwargs)
        # Advance the cadence clock on any real attempt (live fetch, offline replay, or error), but not
        # on a pure cache hit — a dedupe hit did not consume a poll window.
        if result.action != CACHE_HIT:
            self.mark_polled(source_id, now=now)
        return result

    # ------------------------------------------------------------------ control hydration

    def control_for(
        self, source_id: str, *, mode: SourceMode | str | None = None, max_calls: Optional[int] = None
    ) -> SourceControl:
        """Build a fresh SourceControl at the effective mode and hydrate durable budget/breaker/metrics."""
        control = SourceControl(self.effective_mode(source_id, mode), max_calls=max_calls)
        return self.state.hydrate_control(source_id, control, budget_epoch=self.budget_epoch)

    def _persist(self, source_id: str, control: SourceControl) -> None:
        self.state.persist_control(source_id, control, budget_epoch=self.budget_epoch)

    # ------------------------------------------------------------------ one scheduled request

    def run_job(
        self,
        source_id: str,
        *,
        request: dict,
        fetcher: Optional[Callable[[dict], bytes]] = None,
        offline_bytes: Optional[bytes] = None,
        mode: SourceMode | str | None = None,
        max_calls: Optional[int] = None,
        checkpoint: Optional[str] = None,
        now: Any = None,
        changed: bool = True,
        retention_tier: str = "B",
    ) -> SourceJobResult:
        """Run one point-in-time source request under durable budget/dedupe/cache/breaker/checkpoint.

        Resolution order (offline-safe):
          1. operator paused           -> SKIPPED_PAUSED
          2. request already indexed   -> CACHE_HIT (served from archive, no budget)
          3. OFFLINE + fixture bytes   -> OFFLINE_REPLAY (archive + index, no network)
          4. OFFLINE + nothing cached  -> SKIPPED_OFFLINE
          5. live mode + fetcher       -> reserve budget / check breaker -> LIVE_FETCH | SKIPPED_BUDGET
                                          | CIRCUIT_OPEN | ERROR
        """
        eff_mode = self.effective_mode(source_id, mode)
        fp = request_fingerprint(
            request.get("method", "GET"), request.get("url", ""),
            params=request.get("params"), headers=request.get("headers"), payload=request.get("payload"),
        )

        if self.is_paused(source_id):
            return SourceJobResult(source_id, SKIPPED_PAUSED, eff_mode.value, fp,
                                   reason=self._operator(source_id).get("paused_reason") or "operator paused",
                                   checkpoint=self.state.get_checkpoint(source_id))

        control = self.control_for(source_id, mode=eff_mode, max_calls=max_calls)

        # 2. dedupe / cache: an equivalent request was already fetched and archived.
        seen = self.state.seen_request(source_id, fp)
        if seen and eff_mode != SourceMode.ACCEPTANCE:
            control.prepare(request_fingerprint=fp, cache_hit=True)  # accounts calls_avoided
            self._persist(source_id, control)
            return SourceJobResult(source_id, CACHE_HIT, eff_mode.value, fp,
                                   content_sha256=seen.get("content_sha256"), from_archive=True,
                                   reason="served from dedupe/cache index",
                                   checkpoint=self.state.get_checkpoint(source_id))

        # 3/4. OFFLINE: replay a fixture (archive + index) or skip. Never touches the network.
        if eff_mode == SourceMode.OFFLINE:
            if offline_bytes is None:
                return SourceJobResult(source_id, SKIPPED_OFFLINE, eff_mode.value, fp,
                                       reason="OFFLINE: no cached response and no fixture bytes",
                                       checkpoint=self.state.get_checkpoint(source_id))
            try:
                sha = self._archive_and_index(source_id, fp, offline_bytes, request, retention_tier)
            except Exception as exc:  # noqa: BLE001 — a storage fault must not crash the runner
                control.record_failure("service", now=now)
                retry = control.retry_metadata(control.breaker.consecutive_failures,
                                               reason=f"archive/index failed: {exc}")
                self._persist(source_id, control)
                return SourceJobResult(source_id, ERROR, eff_mode.value, fp,
                                       reason="archive/index failed on offline replay",
                                       retry=_retry_dict(retry), error=str(exc),
                                       checkpoint=self.state.get_checkpoint(source_id))
            control.record_cache_hit(request_fingerprint=fp)  # offline replay avoids a live call
            control.record_success(now=now, changed=changed)
            if checkpoint is not None:
                self.state.set_checkpoint(source_id, checkpoint)
            self._persist(source_id, control)
            return SourceJobResult(source_id, OFFLINE_REPLAY, eff_mode.value, fp, content_sha256=sha,
                                   from_archive=True, reason="archived offline fixture bytes",
                                   checkpoint=checkpoint or self.state.get_checkpoint(source_id))

        # 5. live mode: authorize (budget + breaker), then fetch.
        if fetcher is None:
            return SourceJobResult(source_id, SKIPPED_OFFLINE, eff_mode.value, fp,
                                   reason=f"{eff_mode.value} requested but no fetcher supplied",
                                   checkpoint=self.state.get_checkpoint(source_id))
        try:
            control.prepare(request_fingerprint=fp, now=now)
        except CircuitOpen as exc:
            self._persist(source_id, control)
            return SourceJobResult(source_id, CIRCUIT_OPEN, eff_mode.value, fp, reason=str(exc),
                                   checkpoint=self.state.get_checkpoint(source_id))
        except RequestBudgetExceeded as exc:
            self._persist(source_id, control)
            return SourceJobResult(source_id, SKIPPED_BUDGET, eff_mode.value, fp, reason=str(exc),
                                   checkpoint=self.state.get_checkpoint(source_id))
        except ExternalCallBlocked as exc:
            self._persist(source_id, control)
            return SourceJobResult(source_id, SKIPPED_OFFLINE, eff_mode.value, fp, reason=str(exc),
                                   checkpoint=self.state.get_checkpoint(source_id))

        try:
            content = fetcher(request)
        except Exception as exc:  # noqa: BLE001 — the scheduler owns backoff, not the fetcher
            # A fetcher may tag its exception with ``failure_category`` (e.g. "throttle" for HTTP 429)
            # so throttle/quota metrics reflect reality; anything untagged is a generic "service" fault.
            category = getattr(exc, "failure_category", "service") or "service"
            control.record_failure(category, now=now)
            retry = control.retry_metadata(control.breaker.consecutive_failures, reason=str(exc))
            self._persist(source_id, control)
            return SourceJobResult(source_id, ERROR, eff_mode.value, fp, reason="fetcher raised",
                                   retry=_retry_dict(retry), error=str(exc),
                                   checkpoint=self.state.get_checkpoint(source_id))

        try:
            sha = self._archive_and_index(source_id, fp, content, request, retention_tier)
        except Exception as exc:  # noqa: BLE001 — the live call already happened; count it, back off, no crash
            # A storage fault AFTER a successful live fetch: the external call was spent, so record it as a
            # failure (engaging backoff/circuit to prevent a retry storm under a persistent archive outage)
            # and persist the control so the spent budget is durable. Downstream state is never half-written.
            control.record_failure("service", now=now)
            retry = control.retry_metadata(control.breaker.consecutive_failures,
                                           reason=f"archive/index failed after live fetch: {exc}")
            self._persist(source_id, control)
            return SourceJobResult(source_id, ERROR, eff_mode.value, fp,
                                   reason="archive/index failed after live fetch",
                                   retry=_retry_dict(retry), error=str(exc),
                                   checkpoint=self.state.get_checkpoint(source_id))
        control.record_success(now=now, changed=changed)
        if checkpoint is not None:
            self.state.set_checkpoint(source_id, checkpoint)
        self._persist(source_id, control)
        return SourceJobResult(source_id, LIVE_FETCH, eff_mode.value, fp, content_sha256=sha,
                               reason="live retrieval archived", checkpoint=checkpoint or
                               self.state.get_checkpoint(source_id))

    # ------------------------------------------------------------------ archive + index

    def _archive_and_index(self, source_id: str, fp: str, content: bytes, request: dict,
                           retention_tier: str) -> str:
        from .archive import sha256_hex

        sha = sha256_hex(content)
        source_url = request.get("url")
        if self.archive is not None:
            self.archive.put(content=content, source_id=source_id, retention_tier=retention_tier,
                             source_url=source_url)
        self.state.record_request(source_id, fp, content_sha256=sha,
                                  fetched_at=_iso_now(), source_url=source_url)
        return sha

    # ------------------------------------------------------------------ health / operator view

    def health(self, source_ids: Optional[list[str]] = None) -> list[dict]:
        """Operator-visible per-source health, merging durable state with a hydrated control snapshot."""
        ids = source_ids if source_ids is not None else self.known_sources()
        rows = []
        for sid in ids:
            doc = self.state.load(sid)
            control = self.control_for(sid)
            snap = control.snapshot()
            operator = doc.get("operator") or {}
            spec = REGISTRY.get(sid)
            # Surface the DURABLE budget ceiling from persisted state. control_for builds a fresh control
            # without the caller's max_calls, so the snapshot's budget_limit would otherwise be null; the
            # persisted budget (within the active epoch) is the authoritative operator view.
            budget = doc.get("budget") or {}
            budget_limit = snap.get("budget_limit")
            budget_remaining = snap.get("budget_remaining")
            # The durable call count is epoch-independent operator truth. A health view that does not know
            # the active budget_epoch (e.g. the Operations Panel) would otherwise see the hydrated control
            # reset calls_made to 0; the persisted budget/metrics hold the real count.
            persisted_made = budget.get("calls_made")
            if not isinstance(persisted_made, int):
                persisted_made = (doc.get("metrics") or {}).get("calls_made")
            calls_made = persisted_made if isinstance(persisted_made, int) else snap.get("calls_made")
            if budget_limit is None and isinstance(budget.get("max_calls"), int):
                budget_limit = budget["max_calls"]
                made = budget.get("calls_made") if isinstance(budget.get("calls_made"), int) else 0
                budget_remaining = max(0, budget_limit - made)
            rows.append({
                "source_id": sid,
                "name": spec.name if spec else sid,
                "active": bool(spec.active) if spec else None,
                "retention_tier": spec.retention_tier if spec else None,
                "mode": self.effective_mode(sid).value,
                "paused": bool(operator.get("paused")),
                "paused_reason": operator.get("paused_reason") or "",
                "budget_limit": budget_limit,
                "budget_remaining": budget_remaining,
                "circuit_state": snap.get("circuit_state"),
                "next_permitted_poll": snap.get("next_permitted_poll"),
                "cache_hits": snap.get("cache_hits"),
                "calls_avoided": snap.get("calls_avoided"),
                "calls_made": calls_made,
                "retryable_errors": snap.get("retryable_errors"),
                "terminal_errors": snap.get("terminal_errors"),
                "last_successful_call": snap.get("last_successful_call"),
                "last_detected_change": snap.get("last_detected_change"),
                "checkpoint": doc.get("checkpoint"),
                "indexed_requests": len(doc.get("requests") or {}),
                "poll_interval_seconds": self.get_poll_interval(sid),
                "next_poll_at": self.next_poll_at(sid),
                "due": self.due(sid),
            })
        return rows

    def known_sources(self) -> list[str]:
        """Active registry sources plus any that already have a durable state file."""
        ids = {s.id for s in active_sources()}
        for path in sorted(Path(self.state.root).glob("*.json")):
            ids.add(path.stem)
        return sorted(ids)

    def health_report(self) -> dict:
        rows = self.health()
        return {
            "generated_at": _iso_now(),
            "default_mode": self.default_mode.value,
            "budget_epoch": self.budget_epoch,
            "source_count": len(rows),
            "paused_count": sum(1 for r in rows if r["paused"]),
            "open_circuits": sum(1 for r in rows if r["circuit_state"] == CircuitState.OPEN.value),
            "total_calls_avoided": sum(r.get("calls_avoided") or 0 for r in rows),
            "total_calls_made": sum(r.get("calls_made") or 0 for r in rows),
            "sources": rows,
        }


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _epoch_now() -> float:
    import time

    return time.time()


def _retry_dict(retry: Any) -> dict:
    if retry is None:
        return {}
    if hasattr(retry, "__dict__"):
        return {k: v for k, v in vars(retry).items() if not k.startswith("_")}
    try:
        return dict(asdict(retry))
    except Exception:  # noqa: BLE001
        return {}


__all__ = [
    "SourceScheduler", "SourceJobResult",
    "CACHE_HIT", "OFFLINE_REPLAY", "LIVE_FETCH", "SKIPPED_PAUSED", "SKIPPED_OFFLINE",
    "SKIPPED_BUDGET", "SKIPPED_NOT_DUE", "CIRCUIT_OPEN", "ERROR",
]
