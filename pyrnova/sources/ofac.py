"""OFAC sanctions (SDN + Consolidated) bulk-download source connector (OBSERVE).

OFAC publishes the Specially Designated Nationals (SDN) list and the
Consolidated Sanctions list as headerless, comma-separated, double-quote
quoted fixed-field CSV files (12 columns; a missing field is the literal
string ``"-0-"``). This is a bulk-download adapter (very low call
amplification), unlike the JSON REST connectors elsewhere in this package,
but it keeps the same provenance discipline: raw bytes are preserved
untouched, a content hash is computed, and normalization is a pure function
kept separate from transport.

Doctrine: sanctions data is intelligence evidence ONLY. Name-only matching
(:func:`name_candidates`) is explicitly weak and non-authoritative — it must
never be treated as a confirmed sanctions hit or used as an authoritative
compliance screening result.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from . import http
from .registry import get_spec

# Canonical OFAC bulk download file names (relative to the registry base_url).
SDN = "sdn.csv"
CONSOLIDATED = "consolidated/cons_prim.csv"

_MISSING = "-0-"

_GENERIC_TOKENS = {
    "inc",
    "llc",
    "ltd",
    "corp",
    "co",
    "company",
    "the",
    "and",
    "group",
    "holdings",
}


def download_url(list_name: str) -> str:
    """Build the bulk-download URL for ``list_name`` ('sdn' or 'consolidated')."""
    spec = get_spec("sanctions_ofac")
    if list_name == "sdn":
        filename = SDN
    elif list_name == "consolidated":
        filename = CONSOLIDATED
    else:
        raise ValueError(f"unknown OFAC list_name {list_name!r}; expected 'sdn' or 'consolidated'")
    return f"{spec.base_url}/{filename}"


def _clean(value: Optional[str]) -> Optional[str]:
    """Strip whitespace and convert the OFAC missing-field sentinel to None."""
    if value is None:
        return None
    value = value.strip()
    if not value or value == _MISSING:
        return None
    return value


def parse_ofac_csv(raw: bytes, *, list_name: str = "sdn") -> list[dict]:
    """Parse a headerless 12-column OFAC SDN/Consolidated CSV into designation dicts.

    Pure normalization function: no I/O. Blank lines are skipped. Rows whose
    first field is not an integer ``ent_num`` are skipped (defensive against
    stray blank/malformed trailing lines).
    """
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text), skipinitialspace=True)
    record_kind = "sdn_designation" if list_name == "sdn" else "consolidated_designation"

    designations: list[dict] = []
    for row in reader:
        if not row or all((cell is None or cell.strip() == "") for cell in row):
            continue
        # Pad defensively in case a row has fewer than 12 fields.
        row = row + [""] * (12 - len(row))
        ent_num_raw = row[0].strip()
        try:
            ent_num = int(ent_num_raw)
        except ValueError:
            continue

        sdn_name = _clean(row[1])
        if sdn_name is None:
            continue

        designations.append(
            {
                "source_id": "sanctions_ofac",
                "source_ref": f"ofac:{list_name}:{ent_num}",
                "ent_num": ent_num,
                "sdn_name": sdn_name,
                "sdn_type": _clean(row[2]),
                "program": _clean(row[3]),
                "title": _clean(row[4]),
                "remarks": _clean(row[11]),
                "list_name": list_name,
                "record_kind": record_kind,
            }
        )
    return designations


@dataclass(frozen=True)
class OfacListSnapshot:
    """One observed OFAC list download, retaining raw bytes and provenance."""

    raw_response: bytes
    designations: list[dict]
    list_name: str
    fetched_at: str
    source_url: str
    content_sha256: str


class OfacClient:
    def __init__(self):
        self.spec = get_spec("sanctions_ofac")

    def fetch_list(
        self,
        list_name: str = "sdn",
        *,
        offline_bytes: Optional[bytes] = None,
    ) -> OfacListSnapshot:
        """Fetch (or accept injected offline bytes for) an OFAC bulk CSV list.

        ``offline_bytes`` lets tests and archive-replay callers supply the raw
        CSV without a network call; when omitted, ``http.get_bytes`` performs
        a live GET against the registry-declared base_url.
        """
        url = download_url(list_name)
        if offline_bytes is not None:
            raw = offline_bytes
        else:
            status, raw = http.get_bytes(url, source_id=self.spec.id)
            if status != 200:
                raise RuntimeError(f"OFAC {list_name} download failed: HTTP {status}")

        designations = parse_ofac_csv(raw, list_name=list_name)
        return OfacListSnapshot(
            raw_response=raw,
            designations=designations,
            list_name=list_name,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source_url=url,
            content_sha256=hashlib.sha256(raw).hexdigest(),
        )


def _normalize_tokens(name: str) -> set[str]:
    """Lowercase, strip punctuation, drop short/generic tokens."""
    lowered = re.sub(r"[^a-z0-9\s]", " ", name.lower())
    tokens = {tok for tok in lowered.split() if len(tok) >= 3}
    return tokens - _GENERIC_TOKENS


def name_candidates(designations: list[dict], company_name: str) -> list[dict]:
    """Return WEAK, name-only OFAC candidates sharing a significant token with ``company_name``.

    This is explicitly NOT an authoritative sanctions match. OFAC screening
    for compliance decisions requires authoritative identity resolution
    (e.g. matching identifiers, addresses, dates of birth) that this helper
    does not perform. It exists only to surface designations for human
    review; every returned dict carries ``match_basis="name_only_weak"`` and
    ``authoritative=False`` so downstream code cannot silently treat it as a
    confirmed hit. Matching requires at least one shared significant token
    (length >= 3, generic corporate words like "inc"/"llc"/"the" excluded);
    generic words alone never produce a match.
    """
    query_tokens = _normalize_tokens(company_name)
    if not query_tokens:
        return []

    candidates: list[dict] = []
    for designation in designations:
        name_tokens = _normalize_tokens(designation.get("sdn_name", ""))
        if query_tokens & name_tokens:
            candidate = dict(designation)
            candidate["match_basis"] = "name_only_weak"
            candidate["authoritative"] = False
            candidates.append(candidate)
    return candidates
