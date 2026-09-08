"""NORMALIZE — turn raw source records into normalized dicts with explicit, source-faithful fields.

We never invent fields; missing keys degrade to None. Dates are parsed leniently to `date`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from .sources.usaspending import award_url
from .sources.sam import notice_class_from_type
from .sources.federal_register import document_url


def parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    # Handle ISO, with optional time / timezone, and MM/dd/yyyy.
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s[: len(fmt) + 6], fmt).date()
        except ValueError:
            continue
    # Last resort: take leading YYYY-MM-DD
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def normalize_award(row: dict) -> dict:
    """USAspending spending_by_award result row -> normalized award."""
    gen_id = row.get("generated_internal_id") or row.get("internal_id")
    return {
        "award_id": row.get("Award ID"),
        "recipient_name": row.get("Recipient Name"),
        "amount": _to_float(row.get("Award Amount")),
        "start_date": parse_date(row.get("Start Date")),
        "end_date": parse_date(row.get("End Date")),
        "agency": row.get("Awarding Agency"),
        "sub_agency": row.get("Awarding Sub Agency"),
        "contract_type": row.get("Contract Award Type"),
        "naics": _code(row.get("naics") or row.get("NAICS") or row.get("NAICS Code")),
        "psc": _code(row.get("psc") or row.get("PSC") or row.get("PSC Code")),
        "description": row.get("Description") or row.get("description"),
        "generated_internal_id": gen_id,
        "url": award_url(gen_id),
        "_raw_ref": row.get("Award ID"),
    }


def normalize_precursor(row: dict) -> dict:
    """Federal Register result -> generic precursor record; missing remains missing."""
    agencies = row.get("agencies") or []
    agency_names = [a.get("name") or a.get("raw_name") for a in agencies if isinstance(a, dict)]
    doc_no = row.get("document_number")
    return {
        "precursor_id": doc_no,
        "title": row.get("title"),
        "document_type": row.get("type"),
        "agency_names": [name for name in agency_names if name],
        "publication_date": parse_date(row.get("publication_date")),
        "effective_on": parse_date(row.get("effective_on")),
        "comments_close_on": parse_date(row.get("comments_close_on")),
        "abstract": row.get("abstract"),
        "search_excerpt": row.get("excerpts"),
        "action": row.get("action"),
        "docket_ids": list(row.get("docket_ids") or []),
        "url": row.get("html_url") or document_url(doc_no),
        "official_pdf_url": row.get("pdf_url"),
        "_raw_ref": doc_no,
    }


def normalize_notice(row: dict) -> dict:
    """SAM opportunity record -> normalized notice."""
    raw_type = row.get("type") or row.get("baseType") or ""
    return {
        "notice_id": row.get("noticeId"),
        "title": row.get("title"),
        "notice_type_raw": raw_type,
        "notice_class": notice_class_from_type(raw_type),
        "solicitation_number": row.get("solicitationNumber"),
        "agency": row.get("fullParentPathName") or row.get("organizationName"),
        "naics": _stringify(row.get("naicsCode")),
        "psc": _stringify(row.get("classificationCode")),
        "set_aside": row.get("typeOfSetAsideDescription"),
        "posted_date": parse_date(row.get("postedDate")),
        "response_deadline": parse_date(row.get("responseDeadLine")),
        "active": _to_bool(row.get("active")),
        "archive_date": parse_date(row.get("archiveDate")),
        "url": row.get("uiLink"),
        "_raw_ref": row.get("noticeId"),
    }


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    return str(value).strip().lower() in {"true", "yes", "1"}


def _stringify(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value).strip()


def _code(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        value = value.get("code")
    return _stringify(value)
