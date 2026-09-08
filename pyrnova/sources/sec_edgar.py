"""Focused SEC EDGAR observations for commercial-intelligence review.

This adapter only retrieves official ``submissions`` and ``companyfacts`` JSON.
It does not infer opportunity intent, summarize filings, or create candidates.  It
defaults to OFFLINE so a caller must deliberately opt into a fresh EDGAR call.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Callable, Optional

from ..archive import EvidenceArchive
from ..models import Evidence
from . import http
from .control import CircuitBreaker, SourceControl, request_fingerprint
from .registry import get_spec


_CIK_RE = re.compile(r"^\d{1,10}$")
_CONTACT_RE = re.compile(r"[^\s]+@[^\s]+\.[^\s]+")
_MATERIAL_8K_ITEMS = {
    "1.01": "material_definitive_agreement",
    "1.02": "termination_of_material_agreement",
    "2.01": "acquisition_or_disposition",
    "2.02": "financial_results",
    "2.03": "material_financial_obligation",
    "2.04": "financial_obligation_trigger",
    "2.05": "exit_or_disposal_costs",
    "2.06": "material_impairment",
    "5.02": "leadership_change",
}
_FOCUSED_FORMS = {"8-K", "8-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A"}


class EdgarRateLimitError(RuntimeError):
    """EDGAR throttled the request, or this client is still observing its cooldown."""


@dataclass(frozen=True)
class EdgarObservation:
    """An archive-ready EDGAR response with no credential-bearing request data."""

    raw_response: bytes
    endpoint: str
    cik: str
    request_params: dict
    fetched_at: str
    request_url: str
    records: list[dict]
    request_fingerprint: str


def normalize_cik(cik: str | int) -> str:
    """Return EDGAR's zero-padded source-native CIK; reject ambiguous values."""
    value = str(cik).strip()
    if not _CIK_RE.fullmatch(value):
        raise ValueError("CIK must contain 1 to 10 decimal digits")
    return value.zfill(10)


def submissions_url(cik: str | int) -> str:
    return f"https://data.sec.gov/submissions/CIK{normalize_cik(cik)}.json"


def companyfacts_url(cik: str | int) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{normalize_cik(cik)}.json"


def filing_url(cik: str | int, accession_number: Optional[str], primary_document: Optional[str]) -> Optional[str]:
    """Official EDGAR archive URL, only when its source-native components exist."""
    if not accession_number or not primary_document:
        return None
    accession = str(accession_number).replace("-", "")
    if not accession.isdigit():
        return None
    return f"https://www.sec.gov/Archives/edgar/data/{int(normalize_cik(cik))}/{accession}/{primary_document}"


def filing_identity(cik: str | int, accession_number: Optional[str]) -> Optional[str]:
    if not accession_number:
        return None
    return f"sec-edgar:{normalize_cik(cik)}:{accession_number}"


def _recent_filings(payload: dict) -> list[dict]:
    recent = (payload.get("filings") or {}).get("recent") or {}
    if not isinstance(recent, dict):
        return []
    accessions = recent.get("accessionNumber") or []
    if not isinstance(accessions, list):
        return []
    rows: list[dict] = []
    for index, accession in enumerate(accessions):
        if not accession:
            continue
        row = {key: values[index] for key, values in recent.items() if isinstance(values, list) and index < len(values)}
        rows.append(row)
    return rows


def filings_since(payload: dict, since_accession: Optional[str] = None) -> list[dict]:
    """Return the newest submission rows until a previously archived accession.

    EDGAR orders ``filings.recent`` newest first.  The checkpoint is source-native
    and never skips a row when it is absent (for example after an archive reset).
    """
    rows = _recent_filings(payload)
    if not since_accession:
        return rows
    result: list[dict] = []
    for row in rows:
        if row.get("accessionNumber") == since_accession:
            break
        result.append(row)
    return result


def _form_signals(form: Optional[str], items: object) -> list[str]:
    normalized_form = (form or "").upper()
    if normalized_form in {"10-K", "10-K/A", "10-Q", "10-Q/A"}:
        return ["periodic_disclosure"]
    if normalized_form not in {"8-K", "8-K/A"}:
        return []
    raw_items = str(items or "")
    return [
        signal
        for item, signal in _MATERIAL_8K_ITEMS.items()
        if re.search(rf"(?<![\\d.]){re.escape(item)}(?![\\d.])", raw_items)
    ]


def normalize_filing(row: dict, *, cik: str | int, company_metadata: Optional[dict] = None) -> dict:
    """Normalize a focused EDGAR filing without creating derived commercial facts."""
    source_cik = normalize_cik(cik)
    form = row.get("form")
    accession = row.get("accessionNumber")
    primary_document = row.get("primaryDocument")
    metadata = company_metadata or {}
    return {
        "filing_identity": filing_identity(source_cik, accession),
        "cik": source_cik,
        "accession_number": accession,
        "form": form,
        "focused_form": bool(form and form.upper() in _FOCUSED_FORMS),
        "filing_date": row.get("filingDate"),
        "report_date": row.get("reportDate") or None,
        "primary_document": primary_document,
        "primary_document_description": row.get("primaryDocDescription") or None,
        "items": row.get("items") or None,
        "signals": _form_signals(form, row.get("items")),
        "is_amendment": bool(form and form.upper().endswith("/A")),
        "company_name": metadata.get("name") or metadata.get("entityName") or None,
        "tickers": list(metadata.get("tickers") or []),
        "sic": metadata.get("sic") or None,
        "sic_description": metadata.get("sicDescription") or None,
        "url": filing_url(source_cik, accession, primary_document),
        "_raw_ref": accession,
    }


def companyfacts_metadata(payload: dict) -> dict:
    """Extract source-provided entity metadata only; XBRL facts remain raw evidence."""
    cik = payload.get("cik")
    return {
        "cik": normalize_cik(cik) if cik not in (None, "") else None,
        "entityName": payload.get("entityName") or None,
        "tickers": list(payload.get("tickers") or []),
        "exchanges": list(payload.get("exchanges") or []),
    }


def extract_capex_facts(payload: dict) -> list[dict]:
    """Extract filed US-GAAP cash capex facts without estimating missing periods or values."""
    cik = normalize_cik(payload.get("cik"))
    us_gaap = ((payload.get("facts") or {}).get("us-gaap") or {})
    tags = (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForAdditionsToPropertyPlantAndEquipment",
    )
    selected: dict[str, dict] = {}
    for tag in tags:
        fact = us_gaap.get(tag) or {}
        units = (fact.get("units") or {}).get("USD") or []
        for item in units:
            if not isinstance(item, dict) or item.get("form") not in _FOCUSED_FORMS:
                continue
            if not item.get("accn") or not item.get("filed") or item.get("val") is None:
                continue
            identity = f"sec-edgar:{cik}:capex:{tag}:{item['accn']}:{item.get('end') or ''}"
            selected[identity] = {
                "fact_identity": identity,
                "cik": cik,
                "taxonomy": "us-gaap",
                "tag": tag,
                "label": fact.get("label") or None,
                "value_usd": item["val"],
                "period_start": item.get("start") or None,
                "period_end": item.get("end") or None,
                "filed_at": item["filed"],
                "form": item["form"],
                "accession_number": item["accn"],
                "fiscal_year": item.get("fy"),
                "fiscal_period": item.get("fp") or None,
                "signal": "reported_capex_cash_flow",
                "candidate_eligible": False,
            }
    return [selected[key] for key in sorted(selected)]


class EdgarClient:
    """EDGAR client with deliberate LIVE-SAFE opt-in and SEC contact discipline."""

    def __init__(
        self,
        *,
        user_agent: Optional[str] = None,
        mode: str = "offline",
        min_interval_seconds: float = 0.1,
        cooldown_seconds: float = 60.0,
        request_budget: int = 10,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        if mode not in {"offline", "live-safe", "acceptance"}:
            raise ValueError("mode must be offline, live-safe, or acceptance")
        if min_interval_seconds < 0 or cooldown_seconds < 0:
            raise ValueError("EDGAR intervals must be non-negative")
        self.user_agent = user_agent
        self.mode = mode
        self.min_interval_seconds = min_interval_seconds
        self.cooldown_seconds = cooldown_seconds
        self.now = now
        self.next_permitted_poll: Optional[datetime] = None
        self.control = SourceControl(
            mode,
            max_calls=request_budget,
            breaker=CircuitBreaker(failure_threshold=1, cooldown_seconds=cooldown_seconds),
        )
        self.spec = get_spec("sec_edgar")

    @property
    def metrics(self) -> dict:
        snapshot = self.control.snapshot()
        if self.next_permitted_poll:
            snapshot["next_permitted_poll"] = self.next_permitted_poll.isoformat()
        return snapshot

    def _headers(self) -> dict:
        if not self.user_agent or not _CONTACT_RE.search(self.user_agent):
            raise RuntimeError("SEC EDGAR requires a User-Agent identifying the caller and contact email")
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    def _fetch(self, *, endpoint: str, cik: str, request_url: str, since_accession: Optional[str] = None) -> EdgarObservation:
        now = self.now()
        if self.next_permitted_poll and now < self.next_permitted_poll:
            raise EdgarRateLimitError(f"SEC EDGAR next permitted poll is {self.next_permitted_poll.isoformat()}")
        headers = self._headers()
        fingerprint = request_fingerprint("GET", request_url, headers=headers)
        self.control.prepare(request_fingerprint=fingerprint, now=now)
        status, raw, parsed = http.get_json(request_url, {}, headers=headers)
        if status == 429:
            self.next_permitted_poll = now + timedelta(seconds=self.cooldown_seconds)
            self.control.record_failure("throttle", now=now)
            raise EdgarRateLimitError(f"SEC EDGAR throttled request; next permitted poll is {self.next_permitted_poll.isoformat()}")
        if status != 200 or not isinstance(parsed, dict):
            self.control.record_failure("service" if status in {500, 502, 503, 504} else "terminal", now=now)
            raise RuntimeError(f"SEC EDGAR {endpoint} failed: HTTP {status}")
        self.next_permitted_poll = now + timedelta(seconds=self.min_interval_seconds)
        self.control.record_success(now=now, changed=True)
        records = filings_since(parsed, since_accession) if endpoint == "submissions" else []
        return EdgarObservation(
            raw_response=raw,
            endpoint=endpoint,
            cik=cik,
            request_params={"cik": cik, **({"since_accession": since_accession} if since_accession else {})},
            fetched_at=now.isoformat(),
            request_url=request_url,
            records=records,
            request_fingerprint=fingerprint,
        )

    def submissions(self, cik: str | int, *, since_accession: Optional[str] = None) -> EdgarObservation:
        normalized_cik = normalize_cik(cik)
        return self._fetch(endpoint="submissions", cik=normalized_cik, request_url=submissions_url(normalized_cik), since_accession=since_accession)

    def companyfacts(self, cik: str | int) -> EdgarObservation:
        normalized_cik = normalize_cik(cik)
        return self._fetch(endpoint="companyfacts", cik=normalized_cik, request_url=companyfacts_url(normalized_cik))


def archive_observation(archive: EvidenceArchive, observation: EdgarObservation) -> Evidence:
    """Archive one exact source response with secret-free retrieval provenance."""
    return archive.put(
        observation.raw_response,
        source_id="sec_edgar",
        retention_tier=get_spec("sec_edgar").retention_tier,
        source_ref=f"{observation.endpoint}:{observation.cik}",
        source_url=observation.request_url,
        meta={
            "endpoint": observation.endpoint,
            "cik": observation.cik,
            "request_params": observation.request_params,
            "fetched_at": observation.fetched_at,
            "records_returned": len(observation.records),
            "request_headers": {"user_agent": "configured_not_retained"},
            "request_fingerprint": observation.request_fingerprint,
        },
    )
