"""COMPANY — durable, evidence-linked company capability profile (M8).

Distinct from `match.CapabilityProfile` (a customer's declared relevance profile). This module
builds a point-in-time, source-linked profile of a company's SPECIFIC capabilities, derived only
from `capabilities.extract_capabilities`, plus structured attributes (NAICS/PSC, certifications,
clearances, geography, facilities, scale, contract history, partners, exclusions).

Every capability carried here is source-linked (source_id/source_ref) and time-bounded
(available_at); nothing is asserted about "now" that wasn't knowable "as of" a given date.

Self-contained: imports only from `pyrnova.capabilities`. No imports from fit/replay/catalysts.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict

from pyrnova.capabilities import extract_capabilities, CapabilityClass

_COMPANY_SUFFIXES = {
    "inc", "incorporated", "llc", "corp", "corporation", "co", "company", "ltd", "limited",
}


def _canonicalize_name(name: str) -> str:
    """Lowercase, strip punctuation and common company suffixes, collapse whitespace."""
    text = (name or "").lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    tokens = [t for t in text.split() if t]
    while tokens and tokens[-1] in _COMPANY_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def company_id(name: str) -> str:
    """Deterministic company id: 'co_' + sha256(canonicalized name)[:20]."""
    canonical = _canonicalize_name(name)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return "co_" + digest[:20]


@dataclass(frozen=True)
class CapabilityEvidence:
    """A single specific capability, sourced and time-bounded."""

    label: str
    display: str
    confidence: float
    specificity: str
    source_id: str
    source_ref: str
    raw_phrase: str
    available_at: str | None
    basis: str


@dataclass
class CompanyProfile:
    company_id: str
    name: str
    aliases: list = field(default_factory=list)
    capabilities: list = field(default_factory=list)          # list[CapabilityEvidence]
    naics: list = field(default_factory=list)
    psc: list = field(default_factory=list)
    certifications: list = field(default_factory=list)
    clearances: list = field(default_factory=list)
    geography: list = field(default_factory=list)
    facilities: list = field(default_factory=list)
    scale: dict = field(default_factory=dict)
    contract_history: list = field(default_factory=list)
    partners: list = field(default_factory=list)
    exclusions: list = field(default_factory=list)
    first_observed_at: str | None = None
    available_at: str | None = None
    provenance: list = field(default_factory=list)
    id: str = ""
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = self.company_id


def _raw_phrase(cap: CapabilityClass) -> str:
    """Derive the raw phrase/code that produced a CapabilityClass, from source_fields or basis."""
    fields = cap.source_fields or {}
    if fields:
        values = [str(v) for v in fields.values() if v]
        if values:
            return " ".join(values)
    return cap.basis or ""


def normalize_company_capabilities(records: list, *, as_of: str | None = None) -> list:
    """Extract deduplicated, point-in-time CapabilityEvidence from source-native records.

    Each record may carry: source_id, source_ref, available_at, plus whatever
    `capabilities.extract_capabilities` reads (naics, psc, title, summary/description,
    capability_terms).

    Point-in-time: a record whose available_at is missing or later than `as_of` is skipped
    entirely when `as_of` is given (future capability evidence must not leak backward).

    Dedup: by label, keeping the highest-confidence CapabilityEvidence; provenance (source_ref)
    is merged deterministically via sorted uniqueness at the CompanyProfile level.

    Ordering: sorted by (-confidence, label).
    """
    records = records or []
    best: dict[str, CapabilityEvidence] = {}

    for record in records:
        record = record or {}
        available_at = record.get("available_at")
        if as_of is not None:
            if not available_at or available_at > as_of:
                continue

        source_id = str(record.get("source_id") or "")
        source_ref = str(record.get("source_ref") or "")

        caps = extract_capabilities(record, evidence_id=source_ref or None)
        for cap in caps:
            ev = CapabilityEvidence(
                label=cap.label,
                display=cap.display,
                confidence=cap.confidence,
                specificity="specific",
                source_id=source_id,
                source_ref=source_ref,
                raw_phrase=_raw_phrase(cap),
                available_at=available_at,
                basis=cap.basis,
            )
            existing = best.get(cap.label)
            if existing is None or ev.confidence > existing.confidence:
                best[cap.label] = ev

    result = list(best.values())
    result.sort(key=lambda e: (-e.confidence, e.label))
    return result


def _filter_contract_history(contract_history, as_of: str | None) -> list:
    entries = list(contract_history or [])
    if as_of is None:
        return entries
    filtered = []
    for entry in entries:
        available_at = (entry or {}).get("available_at")
        if available_at and available_at <= as_of:
            filtered.append(entry)
    return filtered


def build_profile(
    name: str,
    records=(),
    *,
    aliases=(),
    naics=(),
    psc=(),
    certifications=(),
    clearances=(),
    geography=(),
    facilities=(),
    scale=None,
    contract_history=(),
    partners=(),
    exclusions=(),
    as_of: str | None = None,
) -> CompanyProfile:
    """Build a point-in-time CompanyProfile from structured attributes and evidence records."""
    caps = normalize_company_capabilities(list(records), as_of=as_of)
    filtered_history = _filter_contract_history(contract_history, as_of)

    available_ats = [c.available_at for c in caps if c.available_at]
    available_ats += [h.get("available_at") for h in filtered_history if h.get("available_at")]
    first_observed_at = min(available_ats) if available_ats else None

    resolved_available_at = as_of if as_of is not None else first_observed_at

    provenance = sorted({c.source_ref for c in caps if c.source_ref})

    cid = company_id(name)

    return CompanyProfile(
        company_id=cid,
        name=name,
        aliases=list(aliases),
        capabilities=caps,
        naics=list(naics),
        psc=list(psc),
        certifications=list(certifications),
        clearances=list(clearances),
        geography=[str(g).casefold() for g in geography],
        facilities=list(facilities),
        scale=dict(scale or {}),
        contract_history=filtered_history,
        partners=list(partners),
        exclusions=list(exclusions),
        first_observed_at=first_observed_at,
        available_at=resolved_available_at,
        provenance=provenance,
        id=cid,
    )


def profile_from_dict(d: dict, *, as_of: str | None = None) -> CompanyProfile:
    """Build a CompanyProfile from a corpus/company dict mirroring build_profile's params.

    Tolerates missing keys. Capability evidence records are read from `capability_records`.
    """
    d = d or {}
    return build_profile(
        d.get("name") or "",
        d.get("capability_records") or (),
        aliases=d.get("aliases") or (),
        naics=d.get("naics") or (),
        psc=d.get("psc") or (),
        certifications=d.get("certifications") or (),
        clearances=d.get("clearances") or (),
        geography=d.get("geography") or (),
        facilities=d.get("facilities") or (),
        scale=d.get("scale"),
        contract_history=d.get("contract_history") or (),
        partners=d.get("partners") or (),
        exclusions=d.get("exclusions") or (),
        as_of=as_of,
    )


def to_record(profile: CompanyProfile) -> dict:
    """Serialize a CompanyProfile (with nested CapabilityEvidence) to a json-safe dict."""
    return asdict(profile)
