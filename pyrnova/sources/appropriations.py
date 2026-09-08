"""Federal appropriations / program-funding precursor ingestion.

There is no single machine-uniform "budget lifecycle" API: a program's funding history is
scattered across the President's Budget request, enacted authorization/appropriation acts, and
agency-published appropriated-account artifacts.  This adapter therefore consumes an explicitly
configured official structured artifact (JSON preferred; the artifact is a JSON array of row
objects), retains its artifact identity, and maps only common factual columns without inventing
missing values.

Rows are normalized to one of three distinct, non-collapsible precursor stages based on an
explicit row field (``budget_stage``/``status``):

- ``INTENT``        -- a President's Budget request / budget justification line (pre-enactment).
- ``AUTHORIZATION``  -- an enacted authorization or appropriation act line (public law authority).
- ``FUNDING``        -- an appropriated account with budget authority available to obligate.

Rows with an unrecognized or blank stage are SKIPPED, never guessed.  These records are
AUTHORIZATION/FUNDING/INTENT precursors and never independent STRIKE or candidate generators.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from ..archive import EvidenceArchive
from ..models import Evidence
from .control import SourceControl, SourceMode, request_fingerprint
from .http import get_bytes
from .registry import get_spec


SOURCE_ID = "appropriations"

_STAGE_MAP = {
    "request": "INTENT",
    "budget request": "INTENT",
    "president's budget": "INTENT",
    "presidents budget": "INTENT",
    "intent": "INTENT",
    "authorization": "AUTHORIZATION",
    "authorized": "AUTHORIZATION",
    "enacted": "AUTHORIZATION",
    "appropriated": "FUNDING",
    "available": "FUNDING",
    "funding": "FUNDING",
}

# Preference order: Treasury Account Symbol > Federal Account > Assistance Listing/CFDA >
# Program Element > Budget Line Item.
_IDENTIFIER_FIELDS = (
    ("treasury_account_symbol", ("treasury account symbol", "tas", "treasury_account_symbol")),
    ("federal_account", ("federal account", "federal_account")),
    ("cfda", ("cfda", "cfda number", "assistance listing", "assistance listing number")),
    ("program_element", ("program element", "pe number", "program_element")),
    ("budget_line_item", ("budget line item", "bli", "line item", "budget_line_item")),
)

_AMOUNT_SUFFIX = {"k": 1_000.0, "m": 1_000_000.0, "b": 1_000_000_000.0}


def _clean(value) -> str | None:
    text = str(value or "").strip()
    return text or None


def _first(row: dict, *names: str) -> str | None:
    lowered = {str(key).strip().casefold(): value for key, value in row.items()}
    for name in names:
        value = _clean(lowered.get(name.casefold()))
        if value:
            return value
    return None


def public_artifact_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError("appropriations artifact must use an explicit HTTPS URL")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_amount(raw: str | None) -> float | None:
    """Parse "$1,200,000" or "1.2M" style amounts into a float; never raises."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").strip()
    match = re.fullmatch(r"[+-]?\d+(?:\.\d+)?([kKmMbB])?", text)
    if not match:
        return None
    suffix = match.group(1)
    numeric = text[: len(text) - 1] if suffix else text
    try:
        value = float(numeric)
    except ValueError:
        return None
    if suffix:
        value *= _AMOUNT_SUFFIX[suffix.lower()]
    return value


def _program_identifier(row: dict) -> tuple[str | None, dict[str, str | None]]:
    raw_ids: dict[str, str | None] = {}
    chosen: str | None = None
    for field_name, aliases in _IDENTIFIER_FIELDS:
        value = _first(row, *aliases)
        raw_ids[field_name] = value
        if chosen is None and value:
            chosen = value
    return chosen, raw_ids


def parse_appropriations(content: bytes, *, agency: str, artifact_url: str,
                          observed_at: str | None = None) -> list[dict]:
    """Parse appropriations/program-funding rows without inventing missing values."""
    safe_url = public_artifact_url(artifact_url)
    if not content or not content.strip():
        return []
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("appropriations artifact is not valid JSON") from exc
    if isinstance(payload, dict):
        payload = payload.get("rows", payload.get("records"))
    if not isinstance(payload, list):
        raise ValueError("appropriations artifact must be a JSON array of rows (or {'rows': [...]})")

    records = []
    for row_number, row in enumerate(payload, start=1):
        if not isinstance(row, dict):
            continue
        title = _first(row, "title", "program title", "account title", "line item title")
        if not title:
            continue
        stage_raw = _first(row, "budget_stage", "status", "stage")
        stage = _STAGE_MAP.get(stage_raw.casefold()) if stage_raw else None
        if not stage:
            continue

        native_id = _first(row, "line_id", "id", "budget_line_id", "native_id")
        source_ref = native_id or f"{safe_url}#row={row_number}"

        program_identifier, raw_ids = _program_identifier(row)
        key_basis = program_identifier or source_ref
        program_key = f"{agency.casefold()}:{key_basis.casefold()}"

        downstream = row.get("downstream_refs")
        if isinstance(downstream, (list, tuple)):
            downstream_refs = tuple(_clean(item) for item in downstream if _clean(item))
        else:
            single = _clean(downstream)
            downstream_refs = (single,) if single else ()

        record = {
            "source_id": SOURCE_ID,
            "source_ref": source_ref,
            "program_key": program_key,
            "stage": stage,
            "program_identifier": program_identifier,
            "agency": agency,
            "title": title,
            "amount_usd": parse_amount(_first(row, "amount", "amount_usd", "budget authority", "value")),
            "signal_role": "precursor",
            "candidate_eligible": False,
            "artifact_url": safe_url,
            "artifact_row": row_number,
            "available_at": observed_at,
            "downstream_refs": downstream_refs,
            "_raw_ref": source_ref,
            **raw_ids,
        }
        records.append(record)
    return records


@dataclass(frozen=True)
class AppropriationsObservation:
    raw_response: bytes
    request_url: str
    fetched_at: str
    agency: str
    mode: str
    request_fingerprint: str

    @property
    def source_id(self) -> str:
        return SOURCE_ID

    def provenance(self) -> dict:
        return {
            "source_id": SOURCE_ID,
            "source_ref": self.request_url,
            "request_url": public_artifact_url(self.request_url),
            "request_params": {},
            "fetched_at": self.fetched_at,
            "raw_response": self.raw_response,
            "mode": self.mode,
            "request_fingerprint": self.request_fingerprint,
        }


class AppropriationsClient:
    """Fetch one explicitly selected official artifact; cadence/budget is owned by adapter controls."""

    def __init__(self, *, mode: SourceMode | str = SourceMode.OFFLINE,
                 request_budget: int = 1, control: SourceControl | None = None):
        self.control = control or SourceControl(mode, max_calls=request_budget)

    def fetch(self, url: str, *, agency: str, timeout: int = 30) -> AppropriationsObservation:
        safe_url = public_artifact_url(url)
        fingerprint = request_fingerprint("GET", safe_url)
        self.control.prepare(request_fingerprint=fingerprint)
        status, content = get_bytes(safe_url, timeout=timeout)
        if status != 200:
            self.control.record_failure("retryable" if status in {429, 500, 502, 503, 504} else "terminal")
            raise RuntimeError(f"appropriations fetch failed: HTTP {status}")
        self.control.record_success(changed=True)
        return AppropriationsObservation(
            raw_response=content,
            request_url=safe_url,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            agency=agency,
            mode=self.control.mode.value,
            request_fingerprint=fingerprint,
        )

    @property
    def metrics(self) -> dict:
        return self.control.snapshot()


def archive_observation(archive: EvidenceArchive, observation: AppropriationsObservation) -> Evidence:
    """Archive exact appropriations artifact bytes with source-safe retrieval metadata."""
    spec = get_spec(SOURCE_ID)
    return archive.put(
        observation.raw_response,
        source_id=SOURCE_ID,
        retention_tier=spec.retention_tier,
        source_ref=observation.request_fingerprint,
        source_url=observation.request_url,
        meta={
            "agency": observation.agency,
            "fetched_at": observation.fetched_at,
            "mode": observation.mode,
            "request_fingerprint": observation.request_fingerprint,
        },
    )
