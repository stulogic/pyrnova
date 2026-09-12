"""M13 — controlled live operations over the M12 durable scheduler.

This is the thin, offline-safe *driver* that M13 uses to prove Pyrnova can run continuously against real
sources while making only the external calls it actually needs. It adds three things and nothing more:

- ``http_fetcher`` — the real ``fetcher(request) -> bytes`` the scheduler calls when (and only when) a
  source is opted into a live mode. It performs the HTTP, archives nothing itself (the scheduler owns
  archival + provenance), and tags a 429 with ``failure_category="throttle"`` so throttle metrics are
  honest. It sends only what the request dict carries — no credentials are injected here.
- ``LiveRunner`` — a recording wrapper around ``scheduler.poll`` that runs one narrow live scenario and
  captures the per-request efficiency ledger M13 requires (attempted / sent / cache-hit / avoided /
  records returned / new vs unchanged). ``run_job`` and the scheduler's semantics are unchanged.
- ``operating_cost_report`` — rolls per-source durable metrics into the answer to "what does a day of
  Pyrnova source operation cost in calls?" For free APIs it records calls, never invented dollars.

No adapter is modified. No live call happens unless a caller both opts a source into a live mode AND the
runner is given a real fetcher (``http_fetcher`` is the default, but a run stays offline whenever the
effective mode is OFFLINE).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.parse import urlsplit, urlunsplit

from . import scheduler as sched
from .sources import http
from .sources.registry import get_spec

# A fetcher takes the scheduler's request dict and returns raw response bytes (what gets archived).
Fetcher = Callable[[dict], bytes]
# A record counter turns raw response bytes into a count of source records (for new-records/call metrics).
RecordCounter = Callable[[bytes], int]


class LiveFetchError(RuntimeError):
    """A live retrieval returned a non-success status. Tagged so the scheduler records the right fault."""

    def __init__(self, message: str, *, status: Optional[int] = None,
                 failure_category: str = "service", retry_after_seconds: Optional[float] = None):
        super().__init__(message)
        self.status = status
        self.failure_category = failure_category
        self.retry_after_seconds = retry_after_seconds


def _retry_after_seconds(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def http_fetcher(request: dict) -> bytes:
    """Real ``fetcher(request) -> bytes`` for GET/POST JSON sources (USAspending, SEC EDGAR, …).

    Sends exactly what ``request`` carries. A 429 is tagged ``throttle`` so backoff/quota metrics are
    accurate; any other non-2xx is a ``service`` fault. On success the raw bytes are returned verbatim
    for exact-byte archival — no decoding, no mutation, no credential is added here."""
    method = str(request.get("method", "GET")).upper()
    url = request.get("url")
    if not url:
        raise LiveFetchError("request has no url", failure_category="terminal")
    from requests.exceptions import RequestException

    parsed_url = urlsplit(str(url))
    safe_url = urlunsplit((parsed_url.scheme, parsed_url.netloc.rsplit("@", 1)[-1], parsed_url.path, "", ""))
    headers = request.get("headers") or {}
    try:
        if method == "POST":
            status, raw, _, response_headers = http.post_json_response(
                url, request.get("payload") or {}, headers=headers
            )
        else:
            status, raw, response_headers = http.get_bytes_response(
                url, request.get("params"), headers=headers
            )
    except RequestException as exc:
        # Requests exception text may include the prepared URL with query-string credentials. Keep the
        # transport type and source endpoint, never the provider's credential-bearing exception string.
        raise LiveFetchError(f"{type(exc).__name__} retrieving {safe_url}",
                             failure_category="service") from None
    if status == 429:
        raise LiveFetchError(f"HTTP 429 throttled by provider for {safe_url}", status=429,
                             failure_category="throttle",
                             retry_after_seconds=_retry_after_seconds(response_headers.get("Retry-After")))
    if not 200 <= status < 300:
        raise LiveFetchError(f"HTTP {status} from {safe_url}", status=status, failure_category="service")
    return raw


# ---------------------------------------------------------------------------- record counters


def usaspending_record_count(content: bytes) -> int:
    """Count award rows in a USAspending spending_by_award response (0 on anything unparseable)."""
    try:
        return len((json.loads(content) or {}).get("results") or [])
    except (ValueError, AttributeError, TypeError):
        return 0


def _null_counter(content: bytes) -> int:
    return 0


# ---------------------------------------------------------------------------- request builders


def usaspending_request(payload: dict) -> dict:
    """Wrap a USAspending search payload as a scheduler request dict (POST spending_by_award)."""
    base = get_spec("usaspending").base_url
    return {"method": "POST", "url": f"{base}/search/spending_by_award/", "payload": payload}


# ---------------------------------------------------------------------------- live runner


@dataclass
class LiveRunEntry:
    """One recorded scheduler request: action + the efficiency ledger for that request."""

    source_id: str
    action: str
    mode: str
    request_fingerprint: Optional[str]
    content_sha256: Optional[str]
    from_archive: bool
    requests_attempted: int
    requests_sent: int          # a real external call was made (LIVE_FETCH)
    cache_hit: int              # served from dedupe/cache index
    call_avoided: int           # cache hit or offline replay — an external call we did NOT make
    records_returned: Optional[int]
    is_new_content: Optional[bool]   # True if this sha was not already indexed for this source
    reason: str
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class LiveRunner:
    """Cadence-aware, recording driver over a :class:`~pyrnova.scheduler.SourceScheduler`.

    It never touches the network on its own; it hands the scheduler a ``fetcher`` and lets the scheduler's
    offline-default resolution decide whether a live call is even permitted. Every request is logged with
    the metrics M13 must report so a run is auditable after the fact."""

    scheduler: Any
    source_id: str
    mode: str = "LIVE_SAFE"
    fetcher: Fetcher = http_fetcher
    record_counter: RecordCounter = _null_counter
    max_calls: Optional[int] = None
    entries: list[LiveRunEntry] = field(default_factory=list)

    def _known_shas(self) -> set:
        doc = self.scheduler.state.load(self.source_id)
        return {v.get("content_sha256") for v in (doc.get("requests") or {}).values()}

    def run(self, request: dict, *, checkpoint: Optional[str] = None, changed: bool = True,
            now: Optional[float] = None) -> LiveRunEntry:
        """Run one request through the cadence-aware scheduler and record the efficiency ledger."""
        known_before = self._known_shas()
        result = self.scheduler.poll(
            self.source_id, request=request, now=now, fetcher=self.fetcher,
            mode=self.mode, max_calls=self.max_calls, checkpoint=checkpoint, changed=changed,
        )
        sent = 1 if result.action == sched.LIVE_FETCH else 0
        cache_hit = 1 if result.action == sched.CACHE_HIT else 0
        avoided = 1 if result.action in (sched.CACHE_HIT, sched.OFFLINE_REPLAY) else 0
        records: Optional[int] = None
        is_new: Optional[bool] = None
        if result.content_sha256 is not None:
            is_new = result.content_sha256 not in known_before
            if result.action in (sched.LIVE_FETCH, sched.OFFLINE_REPLAY) and self.archive_bytes_available(result):
                records = self._count_records(result)
        entry = LiveRunEntry(
            source_id=self.source_id, action=result.action, mode=result.mode,
            request_fingerprint=result.request_fingerprint, content_sha256=result.content_sha256,
            from_archive=result.from_archive,
            requests_attempted=1 if result.action not in (sched.SKIPPED_NOT_DUE, sched.SKIPPED_PAUSED) else 0,
            requests_sent=sent, cache_hit=cache_hit, call_avoided=avoided,
            records_returned=records, is_new_content=is_new, reason=result.reason,
            error=result.error,
        )
        self.entries.append(entry)
        return entry

    def archive_bytes_available(self, result) -> bool:
        return self.scheduler.archive is not None and result.content_sha256 is not None

    def _count_records(self, result) -> Optional[int]:
        try:
            content = self.scheduler.archive.get(result.content_sha256, self.source_id)
        except Exception:  # noqa: BLE001 — record counting is best-effort telemetry, never fatal
            return None
        return self.record_counter(content)

    def summary(self) -> dict:
        """Aggregate the recorded ledger for this run (the WS-A / WS-D efficiency figures)."""
        from collections import Counter

        actions = Counter(e.action for e in self.entries)
        sent = sum(e.requests_sent for e in self.entries)
        avoided = sum(e.call_avoided for e in self.entries)
        cache_hits = sum(e.cache_hit for e in self.entries)
        records = sum(e.records_returned or 0 for e in self.entries)
        new_records = sum((e.records_returned or 0) for e in self.entries if e.is_new_content)
        return {
            "source_id": self.source_id,
            "requests": len(self.entries),
            "requests_sent": sent,
            "calls_avoided": avoided,
            "cache_hits": cache_hits,
            "records_returned": records,
            "new_records": new_records,
            "unchanged_records": records - new_records,
            "actions": dict(actions),
        }


# ---------------------------------------------------------------------------- operating-cost telemetry


def operating_cost_report(scheduler: Any, *, source_ids: Optional[list[str]] = None,
                          window_seconds: Optional[float] = None) -> dict:
    """Roll durable per-source metrics into a call-cost view.

    Answers "what does a day of source operation cost in calls?" from real counters — calls made, calls
    avoided, cache-hit rate. Dollar cost is never invented; only calls (and quota state where a provider
    exposes one) are reported. If ``window_seconds`` is given, a calls/day projection is added, clearly
    labelled as a projection of the observed window, not a measured daily total."""
    rows = scheduler.health(source_ids)
    per_source = []
    total_made = total_avoided = total_cache = 0
    for r in rows:
        made = r.get("calls_made") or 0
        avoided = r.get("calls_avoided") or 0
        cache = r.get("cache_hits") or 0
        total_made += made
        total_avoided += avoided
        total_cache += cache
        denom = made + avoided
        entry = {
            "source_id": r["source_id"],
            "calls_made": made,
            "calls_avoided": avoided,
            "cache_hits": cache,
            "cache_hit_rate": round(cache / denom, 4) if denom else 0.0,
            "avoidance_rate": round(avoided / denom, 4) if denom else 0.0,
            "budget_limit": r.get("budget_limit"),
            "budget_remaining": r.get("budget_remaining"),
            "throttles": r.get("retryable_errors"),
            "circuit_state": r.get("circuit_state"),
            "next_poll_at": r.get("next_poll_at"),
            "last_successful_call": r.get("last_successful_call"),
        }
        if window_seconds:
            entry["projected_calls_per_day"] = round(made * 86400.0 / window_seconds, 2)
        per_source.append(entry)
    denom = total_made + total_avoided
    report = {
        "generated_at": sched._iso_now(),
        "window_seconds": window_seconds,
        "total_calls_made": total_made,
        "total_calls_avoided": total_avoided,
        "total_cache_hits": total_cache,
        "overall_avoidance_rate": round(total_avoided / denom, 4) if denom else 0.0,
        "sources": per_source,
    }
    if window_seconds:
        report["projected_total_calls_per_day"] = round(total_made * 86400.0 / window_seconds, 2)
    return report


__all__ = [
    "Fetcher", "RecordCounter", "LiveFetchError", "http_fetcher",
    "usaspending_record_count", "usaspending_request",
    "LiveRunEntry", "LiveRunner", "operating_cost_report",
]
