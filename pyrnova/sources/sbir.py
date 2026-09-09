"""SBIR/STTR Awards connector (OBSERVE), matching the SBIR.gov public API.

Uses the keyless ``/awards`` endpoint, which returns a top-level JSON array of
award objects (not wrapped in a ``results`` envelope). As with the other source
adapters, this connector only returns immutable pull metadata alongside
untouched source records; canonical normalization into chain-ready records is
kept in a separate pure function so transport and normalization stay decoupled.

SBIR/STTR awards are the earliest observable capability/commercialization
precursor Pyrnova ingests: they carry a firm's UEI/DUNS, so a later
USAspending prime award to the same UEI can form a deterministic entity chain
(R&D precursor -> procurement lead time) without inferring anything from
topical similarity alone.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from . import http
from .registry import get_spec


def build_params(
    *,
    agency: Optional[str] = None,
    firm: Optional[str] = None,
    year: Optional[int] = None,
    keyword: Optional[str] = None,
    start: int = 0,
    rows: int = 100,
    fmt: str = "json",
) -> dict:
    """Build SBIR.gov awards query parameters without adding empty filters."""
    if not 1 <= rows <= 1000:
        raise ValueError("rows must be between 1 and 1000")
    if start < 0:
        raise ValueError("start must be at least 0")
    params: dict[str, object] = {"start": start, "rows": rows, "format": fmt}
    if agency:
        params["agency"] = agency
    if firm:
        params["firm"] = firm
    if year:
        params["year"] = year
    if keyword:
        params["keyword"] = keyword
    return params


@dataclass(frozen=True)
class SbirAwardsPage:
    """One observed page, retaining source response and request provenance."""

    raw_response: bytes
    awards: list[dict]
    request_params: dict
    fetched_at: str
    source_url: str


class SbirClient:
    def __init__(self):
        self.spec = get_spec("sbir")
        self.search_url = f"{self.spec.base_url}/awards"

    def search_awards(
        self,
        *,
        agency: Optional[str] = None,
        firm: Optional[str] = None,
        year: Optional[int] = None,
        keyword: Optional[str] = None,
        max_pages: int = 1,
        rows: int = 100,
    ) -> list[SbirAwardsPage]:
        """Fetch award-result pages, preserving each exact response for archival."""
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        pages: list[SbirAwardsPage] = []
        for page_index in range(max_pages):
            start = page_index * rows
            params = build_params(
                agency=agency,
                firm=firm,
                year=year,
                keyword=keyword,
                start=start,
                rows=rows,
            )
            status, raw, parsed = http.get_json(self.search_url, params)
            if status != 200 or parsed is None:
                raise RuntimeError(f"SBIR awards search failed: HTTP {status}")
            awards = parsed if isinstance(parsed, list) else []
            pages.append(
                SbirAwardsPage(
                    raw_response=raw,
                    awards=awards,
                    request_params=params,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    source_url=self.search_url,
                )
            )
            if len(awards) < rows:
                break
        return pages


def _normalize_date(value: object) -> Optional[str]:
    """Normalize an SBIR proposal_award_date to an ISO ``YYYY-MM-DD`` string, or None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 4 and text.isdigit():
        return f"{text}-01-01"
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_amount(value: object) -> Optional[float]:
    """Parse an SBIR award_amount string ("$123,456.00") into a float, or None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    cleaned = text.replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _matches_company(firm: object, company_name: str) -> bool:
    firm_text = str(firm or "").strip().lower()
    target = company_name.strip().lower()
    if not firm_text or not target:
        return False
    return target in firm_text or firm_text in target


def parse_sbir_awards(raw: bytes, *, company_name: Optional[str] = None) -> list[dict]:
    """Normalize raw SBIR awards JSON bytes into chain-ready record dicts.

    Pure function: no I/O, no mutation of the input. Feeds
    ``pyrnova.chains.signals_from_records``. Records without a usable
    ``source_ref`` are skipped, since they cannot join deterministically.
    """
    payload = json.loads(raw) if raw else []
    awards = payload if isinstance(payload, list) else []

    records: list[dict] = []
    for award in awards:
        if not isinstance(award, dict):
            continue
        firm = award.get("firm")
        if company_name and not _matches_company(firm, company_name):
            continue

        tracking_number = str(award.get("agency_tracking_number") or "").strip()
        contract = str(award.get("contract") or "").strip()
        source_ref = tracking_number or contract
        if not source_ref:
            continue

        topic_code = award.get("topic_code")
        if tracking_number:
            program_key = f"sbir:{tracking_number}"
        else:
            award_year = award.get("award_year")
            program_key = f"sbir:{firm}:{award_year}:{topic_code}"

        award_title = award.get("award_title")
        phase = award.get("phase")
        program = award.get("program")
        summary = award_title or f"{program} {phase} {topic_code}"

        record = {
            "source_id": "sbir",
            "source_ref": source_ref,
            "stage": "PROGRAM",
            "program_key": program_key,
            "summary": summary,
            "available_at": _normalize_date(award.get("proposal_award_date")),
            "agency": award.get("agency"),
            "recipient": firm,
            "recipient_uei": award.get("uei") or None,
            "amount_usd": _parse_amount(award.get("award_amount")),
            "record_kind": "sbir_award",
            "confidence": "KNOWN",
            "program_identifier": award.get("topic_code") or award.get("solicitation_number") or None,
        }
        records.append(record)
    return records
