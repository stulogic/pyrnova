"""B2.2 — evidence-backed Customer Intelligence Profile.

Composes one customer/company profile from three PROVENANCE-DISTINCT kinds of fact, never collapsing
them together:

* ``CUSTOMER_SUPPLIED`` — asserted by the customer (capabilities claimed, agency focus, strategic
  priorities/exclusions, preferred deal shapes). Carried as a claim, never silently promoted to evidence.
* ``PUBLIC_EVIDENCE`` — observed in public sources via :class:`pyrnova.company.CompanyProfile`
  (capabilities with evidence, past-performance contracts, contract scale, vehicles, certifications).
* ``PYRNOVA_DERIVED`` — Pyrnova's own inference over the public evidence (agency familiarity from repeat
  contracts, a capability the customer claims but that has no public support).

It reuses the existing capability/company/customer structures and adds only the composition + provenance
layer, so the system can say: *"fits because contracts A and B demonstrate capability X, prior work
establishes agency familiarity Y, while capability C remains unsupported"* — with every clause traceable
to its provenance class, evidence ids, freshness (``available_at``) and confidence. It is NOT a CRM, a
curated corporate database, or textual-similarity matching: claimed and evidenced capabilities are joined
only on exact normalized capability labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from .company import CompanyProfile
from .customers import CustomerProfile

CUSTOMER_SUPPLIED = "CUSTOMER_SUPPLIED"
PUBLIC_EVIDENCE = "PUBLIC_EVIDENCE"
PYRNOVA_DERIVED = "PYRNOVA_DERIVED"
PROVENANCE_CLASSES = (CUSTOMER_SUPPLIED, PUBLIC_EVIDENCE, PYRNOVA_DERIVED)

CUSTOMER_INTELLIGENCE_VERSION = "customer_intelligence_v1"


@dataclass(frozen=True)
class ProfileFact:
    """One provenance-tagged fact about a customer, with freshness and uncertainty."""

    dimension: str                 # capability | past_performance | agency_served | contract_scale |
                                   # incumbency | vehicle_access | certification | strategic_priority |
                                   # strategic_exclusion | preferred_deal_shape | gap
    key: str                       # stable within a dimension (capability label, agency, award ref…)
    value: Any
    provenance_class: str
    source: str = ""               # customer name | source_id:source_ref | "pyrnova"
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    available_at: Optional[str] = None   # freshness / AS-OF of the underlying evidence
    uncertainty: str = ""
    basis: str = ""

    def to_record(self) -> dict:
        return {
            "dimension": self.dimension, "key": self.key, "value": self.value,
            "provenance_class": self.provenance_class, "source": self.source,
            "evidence_ids": list(self.evidence_ids), "confidence": self.confidence,
            "available_at": self.available_at, "uncertainty": self.uncertainty, "basis": self.basis,
        }


@dataclass
class CustomerIntelligenceProfile:
    customer_id: str
    name: str
    as_of: Optional[str] = None
    facts: list[ProfileFact] = field(default_factory=list)
    version: str = CUSTOMER_INTELLIGENCE_VERSION

    # --- provenance / dimension views -----------------------------------------------------------
    def by_provenance(self, provenance_class: str) -> list[ProfileFact]:
        return [f for f in self.facts if f.provenance_class == provenance_class]

    def by_dimension(self, dimension: str) -> list[ProfileFact]:
        return [f for f in self.facts if f.dimension == dimension]

    # --- decision-useful accessors --------------------------------------------------------------
    def supported_capabilities(self) -> list[ProfileFact]:
        """Capabilities backed by public evidence."""
        return [f for f in self.facts if f.dimension == "capability" and f.provenance_class == PUBLIC_EVIDENCE]

    def claimed_capabilities(self) -> list[ProfileFact]:
        return [f for f in self.facts if f.dimension == "capability" and f.provenance_class == CUSTOMER_SUPPLIED]

    def unsupported_claims(self) -> list[ProfileFact]:
        """Customer-claimed capabilities with no public evidence (a derived gap)."""
        return [f for f in self.facts if f.dimension == "gap"]

    def agencies_served(self) -> list[ProfileFact]:
        return self.by_dimension("agency_served")

    def to_record(self) -> dict:
        return {
            "customer_intelligence_version": self.version,
            "customer_id": self.customer_id, "name": self.name, "as_of": self.as_of,
            "facts": [f.to_record() for f in self.facts],
            "provenance_counts": {c: len(self.by_provenance(c)) for c in PROVENANCE_CLASSES},
        }


def _norm_label(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def _evidence_ref(source_id: str | None, source_ref: str | None) -> Optional[str]:
    if source_ref and source_id:
        return f"{source_id}:{source_ref}"
    return source_ref or None


def build_customer_intelligence(
    *,
    customer: Optional[CustomerProfile] = None,
    company: Optional[CompanyProfile] = None,
    strategic_priorities: Sequence[str] = (),
    strategic_exclusions: Sequence[str] = (),
    preferred_deal_shapes: Sequence[str] = (),
    as_of: Optional[str] = None,
) -> CustomerIntelligenceProfile:
    """Compose a provenance-distinct customer intelligence profile from supplied + public + derived facts."""
    if customer is None and company is None:
        raise ValueError("a customer or company profile is required")
    customer_id = (customer.customer_id if customer else (company.company_id if company else "")) or ""
    name = (customer.name if customer else (company.name if company else "")) or ""
    supplier = name or "customer"
    facts: list[ProfileFact] = []

    supported_labels: set[str] = set()

    # --- PUBLIC EVIDENCE (from the observed company profile) ------------------------------------
    if company is not None:
        for cap in company.capabilities:
            label = _norm_label(cap.label)
            supported_labels.add(label)
            facts.append(ProfileFact(
                dimension="capability", key=label, value=cap.display,
                provenance_class=PUBLIC_EVIDENCE, source=_evidence_ref(cap.source_id, cap.source_ref) or supplier,
                evidence_ids=tuple(e for e in (_evidence_ref(cap.source_id, cap.source_ref),) if e),
                confidence=cap.confidence, available_at=cap.available_at, basis=cap.basis,
            ))

        agency_contracts: dict[str, list[dict]] = {}
        for entry in company.contract_history:
            agency = str(entry.get("agency") or "").strip()
            award_ref = str(entry.get("award_ref") or entry.get("award_id") or "").strip()
            ev = tuple(r for r in (award_ref,) if r)
            facts.append(ProfileFact(
                dimension="past_performance",
                key=award_ref or agency or "contract",
                value={k: entry.get(k) for k in ("agency", "value_usd", "naics", "role", "award_ref") if entry.get(k) is not None},
                provenance_class=PUBLIC_EVIDENCE, source=_evidence_ref("usaspending", award_ref) or "usaspending",
                evidence_ids=ev, confidence=0.9, available_at=entry.get("available_at"),
                basis="observed federal award record",
            ))
            if entry.get("vehicle"):
                facts.append(ProfileFact(
                    dimension="vehicle_access", key=_norm_label(entry["vehicle"]), value=entry["vehicle"],
                    provenance_class=PUBLIC_EVIDENCE, source=_evidence_ref("usaspending", award_ref) or "usaspending",
                    evidence_ids=ev, confidence=0.85, available_at=entry.get("available_at"),
                    basis="contract vehicle named on an observed award",
                ))
            if entry.get("incumbent") is True or str(entry.get("role") or "").lower() == "incumbent":
                facts.append(ProfileFact(
                    dimension="incumbency", key=agency or award_ref or "incumbency",
                    value={"agency": agency, "award_ref": award_ref},
                    provenance_class=PUBLIC_EVIDENCE, source=_evidence_ref("usaspending", award_ref) or "usaspending",
                    evidence_ids=ev, confidence=0.85, available_at=entry.get("available_at"),
                    basis="observed current/incumbent contract",
                ))
            if agency:
                agency_contracts.setdefault(agency, []).append(entry)

        # PYRNOVA-DERIVED: agency familiarity from repeat observed contracts.
        for agency, entries in sorted(agency_contracts.items()):
            ev = tuple(str(e.get("award_ref") or e.get("award_id") or "").strip() for e in entries
                       if e.get("award_ref") or e.get("award_id"))
            availables = sorted(e.get("available_at") for e in entries if e.get("available_at"))
            facts.append(ProfileFact(
                dimension="agency_served", key=str(agency).casefold(), value=agency,
                provenance_class=PYRNOVA_DERIVED, source="pyrnova", evidence_ids=ev,
                confidence=min(0.95, 0.6 + 0.1 * len(entries)),
                available_at=availables[-1] if availables else None,
                uncertainty="" if len(entries) > 1 else "single contract; familiarity is tentative",
                basis=f"{len(entries)} observed contract(s) with {agency} establish agency familiarity",
            ))

        # PYRNOVA-DERIVED: contract scale from observed award values.
        values = [e.get("value_usd") for e in company.contract_history if isinstance(e.get("value_usd"), (int, float))]
        if values:
            facts.append(ProfileFact(
                dimension="contract_scale", key="max_observed_award_usd", value=max(values),
                provenance_class=PYRNOVA_DERIVED, source="pyrnova", confidence=0.8,
                basis=f"largest of {len(values)} observed award value(s)",
            ))

        for cert in company.certifications:
            facts.append(ProfileFact(
                dimension="certification", key=_norm_label(cert), value=cert,
                provenance_class=PUBLIC_EVIDENCE, source="company_profile", confidence=0.7,
                available_at=company.available_at, uncertainty="declared in company profile; not independently re-verified here",
                basis="certification/status declared in the observed company profile",
            ))
        for excl in company.exclusions:
            facts.append(ProfileFact(
                dimension="strategic_exclusion", key=_norm_label(excl), value=excl,
                provenance_class=PUBLIC_EVIDENCE, source="company_profile", confidence=0.6,
                basis="exclusion declared in the observed company profile",
            ))

    # --- CUSTOMER SUPPLIED (from the operator-configured customer profile + explicit overlays) ---
    claimed_labels: list[str] = []
    if customer is not None:
        for cap in customer.capabilities:
            label = _norm_label(cap)
            claimed_labels.append(label)
            facts.append(ProfileFact(
                dimension="capability", key=label, value=cap, provenance_class=CUSTOMER_SUPPLIED,
                source=supplier, confidence=0.5, available_at=customer.effective_from,
                uncertainty="asserted by customer; not independently evidenced",
                basis="capability claimed by the customer",
            ))
        for agency in customer.agencies:
            facts.append(ProfileFact(
                dimension="strategic_priority", key=str(agency).casefold(), value=agency,
                provenance_class=CUSTOMER_SUPPLIED, source=supplier, confidence=0.5,
                available_at=customer.effective_from, basis="agency focus supplied by the customer",
            ))
    for priority in strategic_priorities:
        facts.append(ProfileFact(dimension="strategic_priority", key=_norm_label(priority), value=priority,
                                 provenance_class=CUSTOMER_SUPPLIED, source=supplier, confidence=0.5,
                                 basis="strategic priority supplied by the customer"))
    for exclusion in strategic_exclusions:
        facts.append(ProfileFact(dimension="strategic_exclusion", key=_norm_label(exclusion), value=exclusion,
                                 provenance_class=CUSTOMER_SUPPLIED, source=supplier, confidence=0.5,
                                 basis="strategic exclusion supplied by the customer"))
    for shape in preferred_deal_shapes:
        facts.append(ProfileFact(dimension="preferred_deal_shape", key=_norm_label(shape), value=shape,
                                 provenance_class=CUSTOMER_SUPPLIED, source=supplier, confidence=0.5,
                                 basis="preferred deal shape supplied by the customer"))

    # --- PYRNOVA DERIVED: claimed-but-unsupported capabilities (a gap, joined on exact label) -----
    for label in claimed_labels:
        if label not in supported_labels:
            facts.append(ProfileFact(
                dimension="gap", key=label, value=label, provenance_class=PYRNOVA_DERIVED, source="pyrnova",
                confidence=0.6, uncertainty="absence of evidence is not evidence of absence",
                basis="capability claimed by the customer but not found in public evidence",
            ))

    return CustomerIntelligenceProfile(customer_id=customer_id, name=name, as_of=as_of, facts=facts)
