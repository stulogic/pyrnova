"""USAspending.gov connector (OBSERVE).

Endpoint: POST /api/v2/search/spending_by_award/  (public, no API key).
We request contract awards (award_type_codes A/B/C/D) and the "End Date" field
(period_of_performance_current_end_date), then the recompete engine filters by expiry window.

Field contracts are per the USAspending API docs. Result rows echo the requested `fields` plus
`internal_id` / `generated_internal_id` (used for the citation URL).
See: https://api.usaspending.gov/docs/endpoints -> spending_by_award.
"""

from __future__ import annotations

from typing import Optional

from . import http
from .registry import get_spec

CONTRACT_TYPE_CODES = ["A", "B", "C", "D"]

REQUEST_FIELDS = [
    "Award ID",
    "Recipient Name",
    "Start Date",
    "End Date",
    "Award Amount",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Contract Award Type",
    "recipient_id",
    "generated_internal_id",
]


def award_url(generated_internal_id: Optional[str]) -> Optional[str]:
    if not generated_internal_id:
        return None
    return f"https://www.usaspending.gov/award/{generated_internal_id}"


def build_payload(
    *,
    naics_codes: Optional[list[str]] = None,
    agency_name: Optional[str] = None,
    recipient_search: Optional[list[str]] = None,
    action_date_start: str,
    action_date_end: str,
    page: int = 1,
    limit: int = 100,
) -> dict:
    filters: dict = {
        "award_type_codes": CONTRACT_TYPE_CODES,
        "time_period": [{"start_date": action_date_start, "end_date": action_date_end}],
    }
    if naics_codes:
        filters["naics_codes"] = list(naics_codes)
    if recipient_search:
        # High-precision, reliable filter: fuzzy-matches the recipient name. Anchors a run on the
        # target company's own award history (incumbency + their upcoming recompetes).
        filters["recipient_search_text"] = list(recipient_search)
    if agency_name:
        # NOTE: agency-name filtering is brittle (toptier vs subtier naming). Prefer recipient/NAICS.
        filters["agencies"] = [
            {"type": "awarding", "tier": "toptier", "name": agency_name}
        ]
    return {
        "filters": filters,
        "fields": REQUEST_FIELDS,
        "page": page,
        "limit": limit,
        "sort": "Award Amount",
        "order": "desc",
    }


class USAspendingClient:
    def __init__(self):
        self.spec = get_spec("usaspending")
        self.search_url = f"{self.spec.base_url}/search/spending_by_award/"

    def search_awards(
        self,
        *,
        naics_codes: Optional[list[str]] = None,
        agency_name: Optional[str] = None,
        recipient_search: Optional[list[str]] = None,
        action_date_start: str,
        action_date_end: str,
        max_pages: int = 2,
        limit: int = 100,
    ) -> list[tuple[bytes, list[dict]]]:
        """Return a list of (raw_bytes, results) per page so raw evidence can be archived per pull."""
        pages: list[tuple[bytes, list[dict]]] = []
        for page in range(1, max_pages + 1):
            payload = build_payload(
                naics_codes=naics_codes,
                agency_name=agency_name,
                recipient_search=recipient_search,
                action_date_start=action_date_start,
                action_date_end=action_date_end,
                page=page,
                limit=limit,
            )
            status, raw, parsed = http.post_json(self.search_url, payload)
            if status != 200 or not parsed:
                raise RuntimeError(f"USAspending search failed: HTTP {status}")
            results = parsed.get("results", []) or []
            pages.append((raw, results))
            if not (parsed.get("page_metadata", {}) or {}).get("hasNext"):
                break
        return pages
