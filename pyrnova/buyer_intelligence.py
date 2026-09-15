"""B2.3 — opportunity-specific Buyer Intelligence.

For ONE material opportunity, derive what is defensible about the buying organization from public
procurement evidence: contracting agency / sub-agency / office / program office, prior related
procurements, buying cadence, typical award scale, small-business/set-aside behaviour, relevant vehicles,
incumbent vendors, and a budget/program relationship where an upstream funding link is supplied. Every
claim carries provenance (PUBLIC_EVIDENCE observed on a record, or PYRNOVA_DERIVED over those records),
evidence ids, freshness and uncertainty.

This is deliberately NOT a ZoomInfo, a government contact directory, or a speculative personal dossier:
people appear only as a procurement POC explicitly named on an official notice, and any pattern (cadence,
scale, set-aside behaviour, likely vehicle) is derived only from actual related procurements. When the
evidence is too thin to support a pattern, the fact is UNKNOWN rather than invented.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from .customer_intelligence import PUBLIC_EVIDENCE, PYRNOVA_DERIVED

BUYER_INTELLIGENCE_VERSION = "buyer_intelligence_v1"


@dataclass(frozen=True)
class BuyerFact:
    dimension: str      # contracting_agency | sub_agency | contracting_office | program_office |
                        # procurement_poc | prior_procurement | buying_cadence | typical_award_scale |
                        # set_aside_behavior | vehicle | incumbent_vendor | budget_relationship
    key: str
    value: Any
    provenance_class: str = PUBLIC_EVIDENCE
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    available_at: Optional[str] = None
    uncertainty: str = ""
    basis: str = ""

    def to_record(self) -> dict:
        return {
            "dimension": self.dimension, "key": self.key, "value": self.value,
            "provenance_class": self.provenance_class, "evidence_ids": list(self.evidence_ids),
            "confidence": self.confidence, "available_at": self.available_at,
            "uncertainty": self.uncertainty, "basis": self.basis,
        }


@dataclass
class BuyerIntelligence:
    agency: Optional[str]
    opportunity_ref: Optional[str] = None
    as_of: Optional[str] = None
    facts: list[BuyerFact] = field(default_factory=list)
    is_unknown: bool = False
    version: str = BUYER_INTELLIGENCE_VERSION

    def by_dimension(self, dimension: str) -> list[BuyerFact]:
        return [f for f in self.facts if f.dimension == dimension]

    def incumbent_vendors(self) -> list[BuyerFact]:
        return self.by_dimension("incumbent_vendor")

    def to_record(self) -> dict:
        return {
            "buyer_intelligence_version": self.version, "agency": self.agency,
            "opportunity_ref": self.opportunity_ref, "as_of": self.as_of,
            "is_unknown": self.is_unknown, "facts": [f.to_record() for f in self.facts],
        }


def _ref(record: dict) -> Optional[str]:
    sid, sref = record.get("source_id"), record.get("source_ref") or record.get("notice_id") or record.get("award_id")
    if sid and sref:
        return f"{sid}:{sref}"
    return sref or None


def _days_between(dates: list[str]) -> list[int]:
    from datetime import datetime
    parsed = []
    for d in dates:
        try:
            parsed.append(datetime.fromisoformat(str(d).replace("Z", "+00:00").split("T")[0]))
        except (TypeError, ValueError):
            continue
    parsed.sort()
    return [(b - a).days for a, b in zip(parsed, parsed[1:])]


def build_buyer_intelligence(
    *,
    agency: Optional[str] = None,
    sub_agency: Optional[str] = None,
    contracting_office: Optional[str] = None,
    program_office: Optional[str] = None,
    opportunity_ref: Optional[str] = None,
    related_records: Sequence[dict] = (),
    pocs: Sequence[dict] = (),
    budget_links: Sequence[dict] = (),
    as_of: Optional[str] = None,
) -> BuyerIntelligence:
    """Derive opportunity-specific buyer intelligence from public procurement evidence.

    ``related_records`` are prior procurement/award records already resolved to this buyer (each may carry
    ``value_usd``, ``set_aside``, ``vehicle``, ``recipient``, ``available_at``). ``pocs`` are official
    procurement contacts named on a notice. ``budget_links`` are upstream funding/program references.
    """
    related = list(related_records)
    facts: list[BuyerFact] = []

    # --- Organizational identity (observed structured fields) -----------------------------------
    for dim, val in (("contracting_agency", agency), ("sub_agency", sub_agency),
                     ("contracting_office", contracting_office), ("program_office", program_office)):
        if val:
            facts.append(BuyerFact(dim, str(val).casefold(), val, PUBLIC_EVIDENCE, confidence=0.9,
                                   available_at=as_of, basis="named on the opportunity's procurement record"))

    # --- Prior related procurements (each an observed record) -----------------------------------
    proc_dates: list[str] = []
    values: list[float] = []
    set_asides: dict[str, int] = {}
    vehicles: dict[str, str] = {}
    vendors: dict[str, list[str]] = {}
    for rec in related:
        ref = _ref(rec)
        ev = tuple(r for r in (ref,) if r)
        facts.append(BuyerFact(
            "prior_procurement", ref or (rec.get("title") or "procurement"),
            {k: rec.get(k) for k in ("title", "value_usd", "set_aside", "vehicle", "recipient", "naics") if rec.get(k) is not None},
            PUBLIC_EVIDENCE, ev, confidence=0.85, available_at=rec.get("available_at"),
            basis="prior procurement observed for this buyer"))
        if rec.get("available_at"):
            proc_dates.append(rec["available_at"])
        if isinstance(rec.get("value_usd"), (int, float)):
            values.append(float(rec["value_usd"]))
        if rec.get("set_aside"):
            set_asides[str(rec["set_aside"])] = set_asides.get(str(rec["set_aside"]), 0) + 1
        if rec.get("vehicle"):
            vehicles.setdefault(str(rec["vehicle"]).casefold(), str(rec["vehicle"]))
        if rec.get("recipient") and ref:
            vendors.setdefault(str(rec["recipient"]), []).append(ref)

    # --- Derived patterns (honest UNKNOWN when the evidence is thin) -----------------------------
    gaps = _days_between(proc_dates)
    if len(gaps) >= 2:
        median_gap = int(statistics.median(gaps))
        facts.append(BuyerFact("buying_cadence", "median_gap_days", median_gap, PYRNOVA_DERIVED,
                               confidence=0.7, basis=f"median gap across {len(gaps)+1} dated procurements"))
    elif related:
        facts.append(BuyerFact("buying_cadence", "median_gap_days", None, PYRNOVA_DERIVED,
                               confidence=0.0, uncertainty="too few dated procurements to establish cadence",
                               basis="UNKNOWN cadence"))

    if values:
        facts.append(BuyerFact("typical_award_scale", "usd_range",
                               {"min": min(values), "median": statistics.median(values), "max": max(values), "n": len(values)},
                               PYRNOVA_DERIVED, confidence=0.7 if len(values) >= 3 else 0.4,
                               uncertainty="" if len(values) >= 3 else "small sample; scale is indicative only",
                               basis=f"derived from {len(values)} observed award value(s)"))

    for label, count in sorted(set_asides.items(), key=lambda kv: (-kv[1], kv[0])):
        facts.append(BuyerFact("set_aside_behavior", str(label).casefold(),
                               {"set_aside": label, "count": count, "of": len(related)}, PYRNOVA_DERIVED,
                               confidence=0.6, basis=f"{count} of {len(related)} related procurements used {label}"))

    for key, display in sorted(vehicles.items()):
        facts.append(BuyerFact("vehicle", key, display, PUBLIC_EVIDENCE, confidence=0.7,
                               basis="contract vehicle named on a related procurement"))

    for vendor, refs in sorted(vendors.items()):
        facts.append(BuyerFact("incumbent_vendor", str(vendor).casefold(), vendor, PUBLIC_EVIDENCE,
                               tuple(refs), confidence=0.75,
                               basis=f"named as recipient on {len(refs)} related award(s)"))

    # --- People: only an official procurement POC explicitly named on a notice ------------------
    for poc in pocs:
        name = str(poc.get("name") or "").strip()
        if not name:
            continue
        facts.append(BuyerFact("procurement_poc", name.casefold(),
                               {"name": name, "role": poc.get("role"), "notice_ref": poc.get("notice_ref")},
                               PUBLIC_EVIDENCE, tuple(r for r in (poc.get("notice_ref"),) if r), confidence=0.8,
                               basis="procurement contact explicitly named on an official notice"))

    # --- Budget/program relationship (explicit upstream funding link) ---------------------------
    for link in budget_links:
        facts.append(BuyerFact("budget_relationship", str(link.get("program_key") or link.get("ref") or "budget"),
                               {k: link.get(k) for k in ("program_key", "ref", "fiscal_year", "amount_usd") if link.get(k) is not None},
                               PYRNOVA_DERIVED, tuple(r for r in (link.get("ref"),) if r), confidence=link.get("confidence", 0.5),
                               basis="explicit upstream funding/program reference"))

    is_unknown = not related and not any(f.dimension in {"contracting_agency"} for f in facts)
    return BuyerIntelligence(agency=agency, opportunity_ref=opportunity_ref, as_of=as_of,
                             facts=facts, is_unknown=is_unknown)
