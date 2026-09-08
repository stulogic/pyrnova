"""SAM.gov Contract Opportunities connector (OBSERVE).

Endpoint: GET https://api.sam.gov/opportunities/v2/search  (requires SAM_API_KEY).
Params: api_key, postedFrom, postedTo (MM/dd/yyyy), limit, offset, optional ptype (notice type),
ncode (NAICS), ccode (PSC), etc.

Notice-type (`ptype`) codes per the SAM "Get Opportunities" public API docs. These are configurable and
MUST be re-verified against current SAM docs before production — we do not silently invent contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from . import http
from .registry import get_spec

# ptype code -> canonical Pyrnova notice class (catalyst kind).
NOTICE_TYPE_CODES = {
    "r": "sources_sought",
    "p": "presolicitation",
    "o": "solicitation",
    "k": "combined_synopsis_solicitation",
    "s": "special_notice",
    "a": "award_notice",
    "i": "intent_to_bundle",
    "u": "justification",
    "g": "sale_of_surplus",
}

# Notice classes that constitute the pre-solicitation commercial wedge.
PRESOLICITATION_CLASSES = {
    "sources_sought",
    "rfi",  # RFIs are commonly posted as Special Notice / Sources Sought; classified in the engine
    "presolicitation",
    "special_notice",
}


@dataclass(frozen=True)
class SamObservation:
    """One SAM result page and the non-secret provenance for its retrieval."""

    raw_response: bytes
    rows: list[dict]
    request_params: dict
    fetched_at: str
    request_url: str


def build_params(
    *,
    posted_from: str,
    posted_to: str,
    ptype: Optional[str] = None,
    naics: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Build a public SAM query parameter set without credentials.

    The returned mapping is safe to retain as observation provenance.  The client
    adds its API key only to the ephemeral HTTP request.
    """
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    if offset < 0:
        raise ValueError("offset must be at least 0")
    params: dict[str, object] = {
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "limit": limit,
        "offset": offset,
    }
    if ptype:
        params["ptype"] = ptype
    if naics:
        params["ncode"] = naics
    return params


def notice_class_from_type(raw_type: str) -> str:
    """Map a SAM notice 'type'/'baseType' string or ptype code to a canonical class."""
    if not raw_type:
        return "unknown"
    t = raw_type.strip().lower()
    if t in NOTICE_TYPE_CODES:
        return NOTICE_TYPE_CODES[t]
    if "sources sought" in t:
        return "sources_sought"
    if "presolicitation" in t or "pre-solicitation" in t:
        return "presolicitation"
    if "combined" in t:
        return "combined_synopsis_solicitation"
    if "special notice" in t:
        return "special_notice"
    if "award" in t:
        return "award_notice"
    if "solicitation" in t:
        return "solicitation"
    return t.replace(" ", "_")


class SamClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise RuntimeError("SAM_API_KEY is required for the SAM connector (see .env.example).")
        self.api_key = api_key
        self.spec = get_spec("sam_opportunities")
        self.search_url = f"{self.spec.base_url}/search"

    def search(
        self,
        *,
        posted_from: str,   # MM/dd/yyyy
        posted_to: str,     # MM/dd/yyyy
        ptype: Optional[str] = None,
        naics: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[bytes, list[dict]]:
        params = build_params(
            posted_from=posted_from,
            posted_to=posted_to,
            ptype=ptype,
            naics=naics,
            limit=limit,
            offset=offset,
        )
        status, raw, parsed = http.get_json(
            self.search_url, {"api_key": self.api_key, **params}
        )
        if status != 200 or parsed is None:
            raise RuntimeError(f"SAM search failed: HTTP {status}")
        return raw, (parsed.get("opportunitiesData", []) or [])

    def search_observations(
        self,
        *,
        posted_from: str,
        posted_to: str,
        ptype: Optional[str] = None,
        naics: Optional[str] = None,
        max_pages: int = 1,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SamObservation]:
        """Fetch SAM pages while retaining exact response bytes and safe provenance.

        ``request_params`` intentionally never contains ``api_key``.  The key is
        supplied only to the outgoing request and is therefore not available to
        callers that archive or log returned observations.
        """
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        # Validate the initial cursor before issuing any request.
        build_params(
            posted_from=posted_from,
            posted_to=posted_to,
            ptype=ptype,
            naics=naics,
            limit=limit,
            offset=offset,
        )
        observations: list[SamObservation] = []
        for page_index in range(max_pages):
            page_offset = offset + page_index * limit
            params = build_params(
                posted_from=posted_from,
                posted_to=posted_to,
                ptype=ptype,
                naics=naics,
                limit=limit,
                offset=page_offset,
            )
            status, raw, parsed = http.get_json(
                self.search_url, {"api_key": self.api_key, **params}
            )
            if status != 200 or parsed is None:
                raise RuntimeError(f"SAM search failed: HTTP {status}")
            rows = parsed.get("opportunitiesData", []) or []
            observations.append(
                SamObservation(
                    raw_response=raw,
                    rows=rows,
                    request_params=params,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    request_url=self.search_url,
                )
            )
            total_records = parsed.get("totalRecords")
            if len(rows) < limit or (
                isinstance(total_records, int) and page_offset + len(rows) >= total_records
            ):
                break
        return observations
