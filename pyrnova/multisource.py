"""Multi-source company grounding (M10) — SourceFact model, point-in-time merger, orchestrator.

M10 extends M9's single-family (USAspending prime) grounding to multiple authoritative families
(SEC EDGAR, USAspending recipient/award-detail, USAspending sub-awards) WITHOUT changing the fit
engine or scoring. The whole milestone is additive: this module and the parsers turn archived real
bytes into an evidence-backed :class:`~pyrnova.company.CompanyProfile`, filtered strictly point-in-time.

Two hard invariants:

1. **Point-in-time truth.** Every SourceFact carries ``available_at``; the merger drops any fact dated
   after the cutoff, and record-level evidence (capabilities, contract history) is filtered by
   ``company.build_profile(as_of=cutoff)``. Nothing knowable only in the future can leak backward.
2. **No fabrication.** A lower-authority fact never overwrites a higher-authority one; conflicts are
   recorded, not silently resolved. Set-aside eligibility is derived only from real recipient
   categories (a large business simply holds no small-business certification).

Authority (highest first): SAM > USAspending recipient/award-detail > USAspending prime > SEC EDGAR >
official primary source > announcement.

Self-contained: imports only from ``pyrnova.company`` and the ``grounding_*`` parsers (which import
only this module). No imports from fit/replay/scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

REAL_EVIDENCE_DIR = Path("examples/real_evidence")

# Source authority rank (higher wins a scalar conflict).
SOURCE_AUTHORITY = {
    "sam": 60,
    "usaspending_recipient": 50,
    "usaspending": 40,
    "usaspending_prime": 40,
    "usaspending_subawards": 40,
    "sec_edgar": 30,
    "primary": 20,
    "announcement": 10,
}

# Fact types merged as unioned lists vs. single scalar (authority-resolved).
_LIST_FACTS = {"geography", "certification", "alias", "facility", "eligibility"}
_SCALAR_FACTS = {"uei", "sector"}


@dataclass(frozen=True)
class SourceFact:
    """One evidence-backed, temporally-provenanced fact about a company."""

    fact_type: str
    value: object
    source_id: str
    source_ref: str
    available_at: Optional[str]
    evidence_strength: int          # existing 1..5 evidence-strength scale
    confidence: float
    provenance: str = ""


def _authority(source_id: str) -> int:
    return SOURCE_AUTHORITY.get(source_id, 0)


def _knowable(available_at: Optional[str], cutoff: Optional[str]) -> bool:
    if cutoff is None:
        return True
    return bool(available_at) and available_at <= cutoff


def merge_source_facts(facts: list[SourceFact], *, cutoff: Optional[str]) -> dict:
    """Merge SourceFacts into profile-augmentation inputs, filtered strictly point-in-time.

    Returns a dict with keys: geography, certifications, aliases, facilities, eligibility (lists),
    uei, sector (scalars, authority-resolved), source_facts (kept facts as dicts), conflicts.
    """
    kept = [f for f in facts if _knowable(f.available_at, cutoff)]

    geography: list[str] = []
    certifications: list[str] = []
    aliases: list[str] = []
    facilities: list[dict] = []
    eligibility: list[str] = []
    scalars: dict[str, tuple[int, object, str]] = {}   # fact_type -> (authority, value, source_ref)
    conflicts: list[dict] = []

    def _add_unique(bucket: list, value) -> None:
        if value not in bucket:
            bucket.append(value)

    for f in kept:
        if f.fact_type == "geography":
            _add_unique(geography, str(f.value))
        elif f.fact_type == "certification":
            _add_unique(certifications, str(f.value))
        elif f.fact_type == "alias":
            _add_unique(aliases, str(f.value))
        elif f.fact_type == "facility":
            if f.value not in facilities:
                facilities.append(f.value if isinstance(f.value, dict) else {"location": str(f.value)})
        elif f.fact_type == "eligibility":
            for item in (f.value if isinstance(f.value, (list, tuple)) else [f.value]):
                _add_unique(eligibility, str(item))
        elif f.fact_type in _SCALAR_FACTS:
            rank = _authority(f.source_id)
            existing = scalars.get(f.fact_type)
            if existing is None or rank > existing[0]:
                if existing is not None and existing[1] != f.value:
                    conflicts.append({"fact_type": f.fact_type, "kept": f.value,
                                      "dropped": existing[1], "reason": "higher authority"})
                scalars[f.fact_type] = (rank, f.value, f.source_ref)
            elif existing[1] != f.value:
                conflicts.append({"fact_type": f.fact_type, "kept": existing[1],
                                  "dropped": f.value, "reason": "lower authority"})

    return {
        "geography": geography,
        "certifications": certifications,
        "aliases": aliases,
        "facilities": facilities,
        "eligibility": sorted(set(eligibility)),
        "uei": scalars.get("uei", (0, None, ""))[1],
        "sector": scalars.get("sector", (0, None, ""))[1],
        "source_facts": [asdict(f) for f in kept],
        "conflicts": conflicts,
    }


def build_multisource_profile(company_name: str, sources: list[dict], cutoff: Optional[str], *,
                              base_meta: Optional[dict] = None, evidence_dir: Optional[Path] = None):
    """Build a point-in-time CompanyProfile from multiple archived source families.

    ``sources`` is a list of ``{"kind": ..., "fixture": ...}`` entries; a ``usaspending_recipient``
    entry must also carry ``available_at`` (the observation date). Point-in-time filtering is enforced
    here (source facts, partners) and by ``company.build_profile(as_of=cutoff)`` (records, history).
    """
    from .company import build_profile
    from .grounding import parse_usaspending_awards, detect_vehicles
    from .grounding_recipient import parse_recipient
    from .grounding_sec import parse_sec_submissions
    from .grounding_subawards import parse_subawards

    ev_dir = Path(evidence_dir) if evidence_dir else REAL_EVIDENCE_DIR

    facts: list[SourceFact] = []
    prime_parsed: dict = {}
    sub: dict = {}
    for src in sources:
        kind = src["kind"]
        raw = (ev_dir / src["fixture"]).read_bytes()
        if kind == "usaspending_prime":
            prime_parsed = parse_usaspending_awards(
                raw, company_name=company_name, dominant_recipient_only=True)
        elif kind == "sec_submissions":
            facts += parse_sec_submissions(raw, company_name=company_name)
        elif kind == "usaspending_recipient":
            facts += parse_recipient(raw, company_name=company_name, available_at=src["available_at"])
        elif kind == "usaspending_subawards":
            sub = parse_subawards(raw, company_name=company_name)
        else:
            raise ValueError(f"unknown source kind {kind!r}")

    merged = merge_source_facts(facts, cutoff=cutoff)

    cap_records = list(prime_parsed.get("capability_records", []))
    contract_history = list(prime_parsed.get("contract_history", []))
    if sub:
        cap_records += sub["capability_records"]
        contract_history += sub["contract_history"]

    # Authoritative sub-award partners knowable at the cutoff (repeat relationships only).
    partners: list[dict] = []
    for p in sub.get("partners", []) if sub else []:
        if p["authoritative"] and _knowable(p.get("first_observed_at"), cutoff):
            partners.append(p)

    # Point-in-time scale / naics / psc / vehicles / buyers from prime+sub history knowable at cutoff.
    known = [r for r in contract_history if _knowable(r.get("available_at"), cutoff)]
    max_amt = max((r["value_usd"] for r in known if r.get("value_usd")), default=None)
    scale = {"max_contract_usd": max_amt} if max_amt is not None else {}
    naics = sorted({r["naics"] for r in known if r.get("naics")})
    psc = sorted({r["psc"] for r in known if r.get("psc")})
    vehicles = sorted({v for r in known for v in detect_vehicles(r.get("description") or "")})
    buyers = sorted({r["agency"] for r in known if r.get("agency")})

    # Source families that actually contributed knowable evidence (for source-diversity metric).
    contributing: set[str] = set()
    if any(r.get("role") == "prime" for r in known):
        contributing.add("usaspending_prime")
    if any(r.get("role") == "sub" for r in known):
        contributing.add("usaspending_subawards")
    for f in merged["source_facts"]:
        contributing.add(f["source_id"])

    meta = {
        "contract_vehicles": vehicles,
        "buyer_agencies": buyers,
        "grounding_source": "multisource",
        "source_families": sorted(contributing),
        "source_family_count": len(contributing),
        "source_facts": merged["source_facts"],
        "fact_conflicts": merged["conflicts"],
        "eligibility": merged["eligibility"],
        "uei": merged["uei"],
        "sector": merged["sector"],
        "partners_detail": partners,
        "non_authoritative_partners": sorted(
            p["name"] for p in (sub.get("partners", []) if sub else []) if not p["authoritative"]),
    }
    meta.update(base_meta or {})

    profile = build_profile(
        company_name,
        cap_records,
        aliases=list(prime_parsed.get("recipient_names", [])) + merged["aliases"],
        naics=naics,
        psc=psc,
        certifications=merged["certifications"],
        clearances=(),
        geography=merged["geography"],
        facilities=merged["facilities"],
        scale=scale,
        contract_history=contract_history,
        partners=[p["name"] for p in partners],
        exclusions=(),
        as_of=cutoff,
    )
    profile.meta.update(meta)
    return profile
