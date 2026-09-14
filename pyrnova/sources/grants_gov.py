"""Grants.gov Search2 adapter (OBSERVE), defaulting to offline operation.

The adapter archives exact successful response bytes and only returns source
records.  It has no dependency on Capture Radar's pipeline: a Grants.gov record
can be a direct funding opportunity, precursor funding context, or enrichment,
but it cannot manufacture a candidate by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import random
import time
from typing import Any, Callable, Optional

from ..archive import EvidenceArchive
from ..models import Evidence
from . import http
from .control import CircuitBreaker, CircuitOpen, SourceControl, SourceControlError
from .registry import get_spec
from .rights import authorize_request, validate_source_payload

LIVE_MODES = frozenset({"LIVE-SAFE", "ACCEPTANCE"})
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
_SENSITIVE_PARAM_PARTS = ("api_key", "apikey", "token", "secret", "password", "authorization", "cookie")


class GrantsGovError(RuntimeError):
    """A Grants.gov response or operating-mode failure."""


@dataclass(frozen=True)
class GrantsGovPage:
    """A successful Search2 result page with archival-safe request provenance."""

    raw_response: bytes
    opportunities: list[dict]
    request_params: dict
    fetched_at: str
    source_url: str
    mode: str
    attempts: int


def build_payload(
    *,
    keyword: Optional[str] = None,
    agency_code: Optional[str] = None,
    opportunity_statuses: Optional[list[str]] = None,
    rows: int = 25,
    start_record_num: int = 0,
    sort_by: str = "openDate|desc",
) -> dict:
    """Build a Search2 payload without empty filters or any credentials."""
    if not 1 <= rows <= 1000:
        raise ValueError("rows must be between 1 and 1000")
    if start_record_num < 0:
        raise ValueError("start_record_num must be at least 0")
    payload: dict[str, object] = {
        "rows": rows,
        "startRecordNum": start_record_num,
        "sortBy": sort_by,
    }
    if keyword and keyword.strip():
        payload["keyword"] = keyword.strip()
    if agency_code and agency_code.strip():
        payload["agencies"] = agency_code.strip()
    statuses = [status.strip() for status in (opportunity_statuses or []) if status and status.strip()]
    if statuses:
        payload["oppStatuses"] = "|".join(statuses)
    return payload


def sanitize_request_params(value: Any) -> Any:
    """Drop credential-shaped request fields recursively before they can be retained."""
    if isinstance(value, dict):
        return {
            str(key): sanitize_request_params(item)
            for key, item in value.items()
            if not any(part in str(key).lower() for part in _SENSITIVE_PARAM_PARTS)
        }
    if isinstance(value, list):
        return [sanitize_request_params(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_request_params(item) for item in value]
    return value


def grant_opportunity_identity(row: dict) -> Optional[str]:
    """Return a deterministic source-native identity, or None for unidentifiable rows."""
    record_id = row.get("id") or row.get("opportunityId") or row.get("opportunity_id")
    if record_id is not None and str(record_id).strip():
        return f"grants.gov:opportunity:{str(record_id).strip()}"
    number = row.get("number") or row.get("opportunityNumber")
    if number is not None and str(number).strip():
        return f"grants.gov:number:{str(number).strip()}"
    return None


def grant_opportunity_url(record_id: Optional[str]) -> Optional[str]:
    if not record_id:
        return None
    return f"https://www.grants.gov/search-results-detail/{record_id}"


def grant_signal_class(row: dict) -> str:
    """Classify only the source's explicit lifecycle state; unknown remains enrichment."""
    status = str(row.get("oppStatus") or row.get("status") or "").strip().lower()
    if status in {"posted", "open", "available"}:
        return "direct_opportunity"
    if status in {"forecasted", "forecast", "planned", "planning"}:
        return "precursor_funding"
    return "enrichment"


def deduplicate_opportunities(rows: list[dict]) -> list[dict]:
    """Choose one deterministic representative per source identity.

    The raw page is always archived unchanged.  This helper is only for a
    consumer's current result set; it cannot erase archived amendments.
    """
    selected: dict[str, tuple[tuple[int, str], dict]] = {}
    anonymous: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Grants.gov opportunities must be objects")
        identity = grant_opportunity_identity(row)
        if not identity:
            anonymous.append(row)
            continue
        canonical = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
        completeness = sum(value not in (None, "", [], {}) for value in row.values())
        rank = (completeness, canonical)
        current = selected.get(identity)
        if current is None or rank > current[0]:
            selected[identity] = (rank, row)
    return [selected[key][1] for key in sorted(selected)] + sorted(
        anonymous,
        key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":"), default=str),
    )


def _request_identity(request_params: dict) -> str:
    canonical = json.dumps(request_params, sort_keys=True, separators=(",", ":"), default=str)
    return "search2:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def archive_page(archive: EvidenceArchive, page: GrantsGovPage) -> Evidence:
    """Archive one successful page with safe, durable retrieval provenance."""
    spec = get_spec("grants_gov")
    return archive.put(
        page.raw_response,
        source_id=spec.id,
        retention_tier=spec.retention_tier,
        source_ref=_request_identity(page.request_params),
        source_url=page.source_url,
        meta={
            "retrieved_at": page.fetched_at,
            "request_params": page.request_params,
            "mode": page.mode,
            "attempts": page.attempts,
        },
    )


class GrantsGovClient:
    """Bounded Search2 client.  OFFLINE is the safe default and makes no calls."""

    def __init__(
        self,
        *,
        mode: str = "OFFLINE",
        request_budget: int = 1,
        max_retries: int = 2,
        backoff_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        jitter: Callable[[float, float], float] = random.uniform,
    ):
        normalized_mode = mode.upper()
        if normalized_mode not in LIVE_MODES | {"OFFLINE"}:
            raise ValueError("mode must be OFFLINE, LIVE-SAFE, or ACCEPTANCE")
        if request_budget < 1:
            raise ValueError("request_budget must be at least 1")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if backoff_seconds <= 0:
            raise ValueError("backoff_seconds must be positive")
        self.mode = normalized_mode
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._sleep = sleep
        self._now = now
        self._jitter = jitter
        self.control = SourceControl(
            normalized_mode,
            max_calls=request_budget,
            breaker=CircuitBreaker(
                failure_threshold=max_retries + 1,
                cooldown_seconds=backoff_seconds,
            ),
        )
        self.spec = get_spec("grants_gov")
        self.search_url = f"{self.spec.base_url}/search2"

    @property
    def metrics(self) -> dict:
        return self.control.snapshot()

    def search_opportunities(
        self,
        *,
        keyword: Optional[str] = None,
        agency_code: Optional[str] = None,
        opportunity_statuses: Optional[list[str]] = None,
        rows: int = 25,
        start_record_num: int = 0,
        sort_by: str = "openDate|desc",
    ) -> GrantsGovPage:
        """Make one explicit permitted live request and retain exact success bytes."""
        payload = build_payload(
            keyword=keyword,
            agency_code=agency_code,
            opportunity_statuses=opportunity_statuses,
            rows=rows,
            start_record_num=start_record_num,
            sort_by=sort_by,
        )
        safe_payload = sanitize_request_params(payload)
        last_status = 0
        for attempt in range(1, self.max_retries + 2):
            try:
                self.control.prepare(now=self._now())
            except CircuitOpen as exc:
                raise GrantsGovError(f"Grants.gov circuit open: {exc}") from exc
            except SourceControlError as exc:
                raise GrantsGovError(f"Grants.gov {exc}") from exc
            authorize_request("grants_gov", "POST", self.search_url)
            status, raw, parsed = http.post_json(self.search_url, payload, source_id="grants_gov")
            last_status = status
            if status == 200:
                validate_source_payload("grants_gov", parsed)
                data = parsed.get("data") if isinstance(parsed, dict) else None
                if not isinstance(data, dict) or not isinstance(data.get("oppHits"), list):
                    raise GrantsGovError("Grants.gov Search2 returned malformed success payload")
                opportunities = data["oppHits"]
                if not all(isinstance(row, dict) for row in opportunities):
                    raise GrantsGovError("Grants.gov Search2 response contains a non-object opportunity")
                self.control.record_success(now=self._now(), changed=True)
                return GrantsGovPage(
                    raw_response=raw,
                    opportunities=opportunities,
                    request_params=safe_payload,
                    fetched_at=self._now().isoformat(),
                    source_url=self.search_url,
                    mode=self.mode,
                    attempts=attempt,
                )
            if status in RETRYABLE_STATUSES:
                self.control.record_failure("throttle" if status == 429 else "service", now=self._now())
            else:
                self.control.record_failure("terminal", now=self._now())
            if status not in RETRYABLE_STATUSES or attempt > self.max_retries:
                break
            delay = self.backoff_seconds * (2 ** (attempt - 1))
            self._sleep(delay * self._jitter(0.75, 1.25))
        raise GrantsGovError(f"Grants.gov Search2 failed: HTTP {last_status}")
