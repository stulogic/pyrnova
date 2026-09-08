"""Federal Register document connector (OBSERVE).

Uses the public ``/documents.json`` endpoint.  The connector returns immutable
pull metadata alongside untouched source records; canonical normalization is
deliberately kept outside this source adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from . import http
from .registry import get_spec


def build_params(
    *,
    agency_ids: Optional[list[str]] = None,
    document_types: Optional[list[str]] = None,
    term: Optional[str] = None,
    publication_date_start: Optional[str] = None,
    publication_date_end: Optional[str] = None,
    page: int = 1,
    per_page: int = 100,
    order: str = "newest",
) -> dict:
    """Build Federal Register query parameters without adding empty filters."""
    if page < 1:
        raise ValueError("page must be at least 1")
    if not 1 <= per_page <= 1000:
        raise ValueError("per_page must be between 1 and 1000")
    params: dict[str, object] = {"page": page, "per_page": per_page, "order": order}
    if agency_ids:
        params["conditions[agency_ids][]"] = list(agency_ids)
    if document_types:
        params["conditions[type][]"] = list(document_types)
    if term:
        params["conditions[term]"] = term
    if publication_date_start:
        params["conditions[publication_date][gte]"] = publication_date_start
    if publication_date_end:
        params["conditions[publication_date][lte]"] = publication_date_end
    return params


def document_url(document_number: Optional[str]) -> Optional[str]:
    if not document_number:
        return None
    return f"https://www.federalregister.gov/documents/{document_number}"


@dataclass(frozen=True)
class FederalRegisterPage:
    """One observed page, retaining source response and request provenance."""

    raw_response: bytes
    documents: list[dict]
    request_params: dict
    fetched_at: str
    source_url: str


class FederalRegisterClient:
    def __init__(self):
        self.spec = get_spec("federal_register")
        self.search_url = f"{self.spec.base_url}/documents.json"

    def search_documents(
        self,
        *,
        agency_ids: Optional[list[str]] = None,
        document_types: Optional[list[str]] = None,
        term: Optional[str] = None,
        publication_date_start: Optional[str] = None,
        publication_date_end: Optional[str] = None,
        max_pages: int = 1,
        per_page: int = 100,
        order: str = "newest",
    ) -> list[FederalRegisterPage]:
        """Fetch document-result pages, preserving each exact response for archival."""
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        pages: list[FederalRegisterPage] = []
        for page in range(1, max_pages + 1):
            params = build_params(
                agency_ids=agency_ids,
                document_types=document_types,
                term=term,
                publication_date_start=publication_date_start,
                publication_date_end=publication_date_end,
                page=page,
                per_page=per_page,
                order=order,
            )
            status, raw, parsed = http.get_json(self.search_url, params)
            if status != 200 or parsed is None:
                raise RuntimeError(f"Federal Register document search failed: HTTP {status}")
            documents = parsed.get("results", []) or []
            pages.append(
                FederalRegisterPage(
                    raw_response=raw,
                    documents=documents,
                    request_params=params,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    source_url=self.search_url,
                )
            )
            if len(documents) < per_page:
                break
        return pages
