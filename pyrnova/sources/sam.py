"""SAM.gov Contract Opportunities connector (OBSERVE).

Endpoint: GET https://api.sam.gov/opportunities/v2/search  (requires SAM_API_KEY).
Params: api_key, postedFrom, postedTo (MM/dd/yyyy), limit, offset, optional ptype (notice type),
ncode (NAICS), ccode (PSC), etc.

Notice-type (`ptype`) codes per the SAM "Get Opportunities" public API docs. These are configurable and
MUST be re-verified against current SAM docs before production — we do not silently invent contracts.
"""

from __future__ import annotations

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
        params = {
            "api_key": self.api_key,
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": limit,
            "offset": offset,
        }
        if ptype:
            params["ptype"] = ptype
        if naics:
            params["ncode"] = naics
        status, raw, parsed = http.get_json(self.search_url, params)
        if status != 200 or parsed is None:
            raise RuntimeError(f"SAM search failed: HTTP {status}")
        return raw, (parsed.get("opportunitiesData", []) or [])
