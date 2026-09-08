"""Agency procurement-forecast ingestion.

There is no single federal forecast API or uniform agency schema.  This adapter therefore consumes
an explicitly configured official agency CSV artifact, retains its artifact identity, and maps only
common factual columns.  Rows without a native forecast/solicitation id use the stable artifact row
location as their source-native reference.  Forecasts are MARKET_ENGAGEMENT precursors and never
independent STRIKE generators.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from ..archive import EvidenceArchive
from ..models import Evidence
from .control import SourceControl, SourceMode, request_fingerprint
from .http import get_bytes
from .registry import get_spec


SOURCE_ID = "acquisition_forecast"


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
        raise ValueError("forecast artifact must use an explicit HTTPS URL")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_forecast_csv(content: bytes, *, agency: str, artifact_url: str,
                       observed_at: str | None = None) -> list[dict]:
    """Parse common forecast columns without inventing missing values."""
    safe_url = public_artifact_url(artifact_url)
    text = content.decode("utf-8-sig")
    records = []
    for row_number, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        title = _first(row, "requirement title", "title", "requirement", "procurement description")
        if not title:
            continue
        native_id = _first(row, "forecast id", "requirement id", "solicitation number", "solicitation")
        source_ref = native_id or f"{safe_url}#row={row_number}"
        program_key = _first(row, "program id", "program", "requirement id") or source_ref
        records.append({
            "source_id": SOURCE_ID,
            "source_ref": source_ref,
            "program_key": f"{agency.casefold()}:{program_key.casefold()}",
            "stage": "MARKET_ENGAGEMENT",
            "signal_role": "precursor",
            "candidate_eligible": False,
            "agency": agency,
            "title": title,
            "description": _first(row, "requirements description", "description", "scope"),
            "naics": _first(row, "anticipated naics", "naics", "naics code"),
            "psc": _first(row, "anticipated psc", "psc", "psc code"),
            "estimated_value": _first(row, "anticipated total value", "estimated value", "value range"),
            "anticipated_solicitation": _first(row, "anticipated qtr & year - solicit/rf", "solicitation date", "forecast date"),
            "anticipated_award": _first(row, "anticipated qtr & year - award", "award date"),
            "set_aside": _first(row, "anticipated acquisition strategy", "set aside", "acquisition strategy"),
            "artifact_url": safe_url,
            "artifact_row": row_number,
            "available_at": observed_at,
            "_raw_ref": source_ref,
        })
    return records


@dataclass(frozen=True)
class ForecastObservation:
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


class AcquisitionForecastClient:
    """Fetch one explicitly selected official artifact; cadence/budget is owned by adapter controls."""

    def __init__(self, *, mode: SourceMode | str = SourceMode.OFFLINE,
                 request_budget: int = 1, control: SourceControl | None = None):
        self.control = control or SourceControl(mode, max_calls=request_budget)

    def fetch(self, url: str, *, agency: str, timeout: int = 30) -> ForecastObservation:
        safe_url = public_artifact_url(url)
        fingerprint = request_fingerprint("GET", safe_url)
        self.control.prepare(request_fingerprint=fingerprint)
        status, content = get_bytes(safe_url, timeout=timeout)
        if status != 200:
            self.control.record_failure("retryable" if status in {429, 500, 502, 503, 504} else "terminal")
            raise RuntimeError(f"acquisition forecast fetch failed: HTTP {status}")
        self.control.record_success(changed=True)
        return ForecastObservation(
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


def archive_observation(archive: EvidenceArchive, observation: ForecastObservation) -> Evidence:
    """Archive exact forecast bytes with source-safe retrieval metadata."""
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
