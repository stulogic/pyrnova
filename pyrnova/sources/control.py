"""Small, adapter-neutral controls for governed source retrieval.

This module deliberately does not perform HTTP, read a cache, or persist state.  An
adapter asks :class:`SourceControl` for permission immediately before a request and
reports the result afterwards.  The intended call boundary is::

    decision = control.prepare(request_fingerprint=fingerprint)
    # perform the HTTP call only when decision.action == "live_call"
    control.record_success()  # or control.record_failure("throttle")

For a cache/archive hit, pass ``cache_hit=True`` to ``prepare``.  This keeps OFFLINE
and LIVE-SAFE useful without silently allowing cached data in ACCEPTANCE.  A live
call is counted when ``prepare`` authorizes it; failed calls therefore still consume
the configured budget.  No retry loop or sleep is hidden here: ``retry_metadata``
only returns bounded timing metadata for an adapter to apply.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Mapping, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class SourceMode(str, Enum):
    OFFLINE = "OFFLINE"
    LIVE_SAFE = "LIVE_SAFE"
    ACCEPTANCE = "ACCEPTANCE"


# A broad, conservative key list is intentional: an unknown credential must not
# reach retained request provenance merely because a provider named it unusually.
_SECRET_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?key|secret|token|password|passwd|credential|"
    r"authorization|auth|cookie|session|private[_-]?key|client[_-]?secret)",
    re.IGNORECASE,
)
REDACTED = "[REDACTED]"


def _secret_key(key: Any) -> bool:
    return bool(_SECRET_KEY.search(str(key)))


def redact(value: Any, *, key: Any = None) -> Any:
    """Return a JSON-safe copy with credential-like fields redacted."""
    if key is not None and _secret_key(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {str(k): redact(v, key=k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return {"sha256": hashlib.sha256(value).hexdigest(), "length": len(value)}
    return str(value)


def _safe_url(url: str) -> str:
    """Canonicalize a URL while removing query credentials and fragments."""
    parts = urlsplit(str(url))
    query = []
    for name, value in parse_qsl(parts.query, keep_blank_values=True):
        query.append((name, REDACTED if _secret_key(name) else value))
    query.sort()
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", urlencode(query), "")
    )


def sanitized_request(
    method: str,
    url: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    headers: Optional[Mapping[str, Any]] = None,
    payload: Any = None,
) -> dict[str, Any]:
    """Build retained-safe request provenance without retaining credentials."""
    safe_headers = {
        str(name).lower(): redact(value, key=name)
        for name, value in (headers or {}).items()
    }
    return {
        "method": str(method).upper(),
        "url": _safe_url(url),
        "params": redact(params or {}),
        "headers": dict(sorted(safe_headers.items())),
        "payload": redact(payload),
    }


def request_fingerprint(
    method: str,
    url: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    headers: Optional[Mapping[str, Any]] = None,
    payload: Any = None,
    body: Any = None,
) -> str:
    """Return a deterministic SHA-256 identity for a sanitized request.

    ``body`` is accepted as a convenience alias for ``payload``.  Credential
    values affect neither the retained canonical request nor its fingerprint.
    Mapping order and query-parameter order do not affect the result.
    """
    if payload is not None and body is not None:
        raise ValueError("pass either payload or body, not both")
    safe = sanitized_request(
        method, url, params=params, headers=headers, payload=payload if payload is not None else body
    )
    canonical = json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Common alternate spelling for callers that prefer the verb first.
fingerprint_request = request_fingerprint


class SourceControlError(RuntimeError):
    """Base class for a retrieval denied by source controls."""


class ExternalCallBlocked(SourceControlError):
    pass


class AcceptanceCacheForbidden(SourceControlError):
    pass


class RequestBudgetExceeded(SourceControlError):
    pass


class CircuitOpen(SourceControlError):
    pass


@dataclass
class RequestBudget:
    """Per-source live-call budget. ``None`` means no local numeric limit."""

    max_calls: Optional[int] = None
    calls_made: int = 0

    def __post_init__(self) -> None:
        if self.max_calls is not None and self.max_calls < 0:
            raise ValueError("max_calls must be non-negative or None")

    @property
    def remaining(self) -> Optional[int]:
        if self.max_calls is None:
            return None
        return max(0, self.max_calls - self.calls_made)

    def reserve(self) -> None:
        if self.max_calls is not None and self.calls_made >= self.max_calls:
            raise RequestBudgetExceeded(
                f"source request budget exhausted ({self.max_calls} calls)"
            )
        self.calls_made += 1


@dataclass
class SourceMetrics:
    calls_made: int = 0
    cache_hits: int = 0
    calls_avoided: int = 0
    retryable_errors: int = 0
    throttles: int = 0
    terminal_errors: int = 0
    last_successful_call: Optional[float] = None
    last_detected_change: Optional[float] = None
    quota_state: str = "unknown"

    @property
    def avoided_calls(self) -> int:
        """Compatibility spelling used by existing source metric output."""
        return self.calls_avoided

    def __getitem__(self, name: str) -> Any:
        """Allow lightweight mapping-style inspection in operator code/tests."""
        return getattr(self, name)

    def as_dict(self, *, next_permitted_poll: Optional[float], circuit_state: str) -> dict[str, Any]:
        return {
            "calls_made": self.calls_made,
            "cache_hits": self.cache_hits,
            "calls_avoided": self.calls_avoided,
            "avoided_calls": self.calls_avoided,
            "retryable_errors": self.retryable_errors,
            "throttles": self.throttles,
            "terminal_errors": self.terminal_errors,
            "last_successful_call": self.last_successful_call,
            "last_detected_change": self.last_detected_change,
            "quota_state": self.quota_state,
            "next_permitted_poll": next_permitted_poll,
            "circuit_state": circuit_state,
        }


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def _timestamp(value: Any = None) -> float:
    if value is None:
        return time.time()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()
    return float(value)


class CircuitBreaker:
    """Minimal failure circuit for quota, throttle, and service failures."""

    def __init__(self, *, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = float(cooldown_seconds)
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.next_permitted_poll: Optional[float] = None
        self._probe_in_flight = False

    def allow(self, now: Any = None) -> bool:
        current = _timestamp(now)
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.next_permitted_poll is None or current < self.next_permitted_poll:
                return False
            self.state = CircuitState.HALF_OPEN
        if self.state == CircuitState.HALF_OPEN:
            if self._probe_in_flight:
                return False
            self._probe_in_flight = True
        # One probe is permitted in HALF_OPEN; a failure reopens the circuit.
        return True

    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.next_permitted_poll = None
        self._probe_in_flight = False

    def record_failure(self, category: str, now: Any = None) -> None:
        category = category.lower()
        if category not in {"quota", "throttle", "service", "retryable"}:
            return
        current = _timestamp(now)
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self._probe_in_flight = False
            # The cooldown grows modestly with repeated failures, but remains
            # bounded so the caller can observe a concrete next poll time.
            multiplier = 2 ** max(0, self.consecutive_failures - self.failure_threshold)
            self.next_permitted_poll = current + self.cooldown_seconds * min(multiplier, 16)


@dataclass(frozen=True)
class RetryMetadata:
    attempt: int
    max_attempts: int
    reason: str
    retryable: bool
    delay_seconds: float
    provider_retry_after_seconds: Optional[float]


class RetryPolicy:
    """Bounded exponential backoff metadata; it never sleeps."""

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        jitter_ratio: float = 0.25,
        jitter_fn: Optional[Callable[[float], float]] = None,
    ):
        if max_attempts < 1 or base_delay_seconds < 0 or max_delay_seconds < 0:
            raise ValueError("retry limits and delays must be non-negative")
        if jitter_ratio < 0:
            raise ValueError("jitter_ratio must be non-negative")
        self.max_attempts = max_attempts
        self.base_delay_seconds = float(base_delay_seconds)
        self.max_delay_seconds = float(max_delay_seconds)
        self.jitter_ratio = float(jitter_ratio)
        self.jitter_fn = jitter_fn

    def metadata(
        self,
        attempt: int,
        *,
        reason: str,
        retryable: bool = True,
        retry_after_seconds: Optional[float] = None,
    ) -> RetryMetadata:
        if attempt < 1:
            raise ValueError("attempt must be at least 1")
        provider_retry_after = (
            None if retry_after_seconds is None else max(0.0, float(retry_after_seconds))
        )
        exponential = self.base_delay_seconds * (2 ** (attempt - 1))
        if self.jitter_fn is not None:
            jitter = max(0.0, float(self.jitter_fn(exponential * self.jitter_ratio)))
        else:
            jitter = random.uniform(0.0, exponential * self.jitter_ratio)
        delay = min(exponential + jitter, self.max_delay_seconds)
        # A provider's explicit Retry-After is authoritative, even when it is
        # longer than the local exponential cap.  The local cap still bounds
        # retries when the provider gives no guidance.
        if provider_retry_after is not None:
            delay = max(delay, provider_retry_after)
        return RetryMetadata(
            attempt=attempt,
            max_attempts=self.max_attempts,
            reason=reason,
            retryable=retryable and attempt < self.max_attempts,
            delay_seconds=delay,
            provider_retry_after_seconds=provider_retry_after,
        )


@dataclass(frozen=True)
class RequestDecision:
    action: str
    request_fingerprint: Optional[str] = None
    reason: str = ""


class SourceControl:
    """Mode, budget, accounting, retry metadata, and circuit state for one source."""

    def __init__(
        self,
        mode: SourceMode | str = SourceMode.OFFLINE,
        *,
        budget: RequestBudget | int | None = None,
        request_budget: RequestBudget | int | None = None,
        max_calls: Optional[int] = None,
        breaker: Optional[CircuitBreaker] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        self.mode = mode if isinstance(mode, SourceMode) else SourceMode(str(mode).upper().replace("-", "_"))
        supplied_budgets = [value for value in (budget, request_budget, max_calls) if value is not None]
        if len(supplied_budgets) > 1:
            raise ValueError("pass only one of budget, request_budget, or max_calls")
        budget = request_budget if request_budget is not None else budget
        self.budget = budget if isinstance(budget, RequestBudget) else RequestBudget(
            max_calls=budget if isinstance(budget, int) else max_calls
        )
        self.breaker = breaker or CircuitBreaker()
        self.retry_policy = retry_policy or RetryPolicy()
        self.metrics = SourceMetrics()

    @property
    def calls_made(self) -> int:
        return self.budget.calls_made

    @property
    def cache_hits(self) -> int:
        return self.metrics.cache_hits

    @property
    def calls_avoided(self) -> int:
        return self.metrics.calls_avoided

    @property
    def avoided_calls(self) -> int:
        return self.metrics.calls_avoided

    def prepare(
        self,
        *,
        request_fingerprint: Optional[str] = None,
        cache_hit: bool = False,
        now: Any = None,
    ) -> RequestDecision:
        """Authorize a cache hit or reserve one live call."""
        if cache_hit:
            self.record_cache_hit(request_fingerprint=request_fingerprint)
            return RequestDecision("cache_hit", request_fingerprint, "reused cached/archive response")
        if self.mode == SourceMode.OFFLINE:
            raise ExternalCallBlocked("OFFLINE mode permits fixtures/archive reads, not external calls")
        if not self.breaker.allow(now):
            raise CircuitOpen(
                f"source circuit is open; next permitted poll is {self.breaker.next_permitted_poll}"
            )
        self.budget.reserve()
        self.metrics.calls_made = self.budget.calls_made
        return RequestDecision("live_call", request_fingerprint, f"authorized in {self.mode.value}")

    # Clear aliases for adapters that use authorization vocabulary.
    authorize = prepare
    before_request = prepare

    def record_cache_hit(self, *, request_fingerprint: Optional[str] = None) -> None:
        """Account for a reused response without consuming a live-call budget."""
        if self.mode == SourceMode.ACCEPTANCE:
            raise AcceptanceCacheForbidden("ACCEPTANCE requires a fresh uncached retrieval")
        self.metrics.cache_hits += 1
        self.metrics.calls_avoided += 1

    @property
    def next_permitted_poll(self) -> Optional[float]:
        return self.breaker.next_permitted_poll

    @property
    def circuit_state(self) -> CircuitState:
        return self.breaker.state

    def record_success(self, *, now: Any = None, changed: bool = False) -> None:
        current = _timestamp(now)
        self.metrics.last_successful_call = current
        if changed:
            self.metrics.last_detected_change = current
        self.breaker.record_success()

    def record_failure(self, category: str = "service", *, now: Any = None) -> None:
        category = category.lower()
        if category in {"quota", "throttle"}:
            self.metrics.throttles += 1
            self.metrics.quota_state = category
        if category in {"quota", "throttle", "service", "retryable"}:
            self.metrics.retryable_errors += 1
        else:
            self.metrics.terminal_errors += 1
        self.breaker.record_failure(category, now)

    def retry_metadata(
        self,
        attempt: int,
        *,
        reason: str,
        retryable: bool = True,
        retry_after_seconds: Optional[float] = None,
    ) -> RetryMetadata:
        """Return backoff metadata only; the adapter owns sleeping and retries."""
        return self.retry_policy.metadata(
            attempt,
            reason=reason,
            retryable=retryable,
            retry_after_seconds=retry_after_seconds,
        )

    def snapshot(self) -> dict[str, Any]:
        """Return operator-visible mode, quota, budget, and breaker state."""
        return {
            "mode": self.mode.value,
            "budget_limit": self.budget.max_calls,
            "budget_remaining": self.budget.remaining,
            **self.metrics.as_dict(
                next_permitted_poll=self.breaker.next_permitted_poll,
                circuit_state=self.breaker.state.value,
            ),
        }


__all__ = [
    "AcceptanceCacheForbidden",
    "CircuitOpen",
    "CircuitState",
    "CircuitBreaker",
    "ExternalCallBlocked",
    "REDACTED",
    "RequestBudget",
    "RequestBudgetExceeded",
    "RequestDecision",
    "RetryMetadata",
    "RetryPolicy",
    "SourceControl",
    "SourceControlError",
    "SourceMetrics",
    "SourceMode",
    "fingerprint_request",
    "redact",
    "request_fingerprint",
    "sanitized_request",
]
