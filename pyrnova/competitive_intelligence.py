"""B2.4 — Incumbent + Competitive Intelligence.

For a material opportunity, expose what public evidence supports about the competitive picture:
incumbent contractor, the current/related contract, incumbent tenure, obligated/known value, period of
performance, renewal/follow-on context, evidenced prior competitors, competitor HYPOTHESES, incumbent
advantages and vulnerabilities, and relevant customer competitive strengths/gaps — each with confidence,
contradictory evidence, source provenance and freshness.

Doctrine: a competitor claim is a HYPOTHESIS WITH EVIDENCE AND UNCERTAINTY. A competitor hypothesis is
emitted only when it rests on a real signal (an entity that actually bid/won a related procurement, or an
explicitly evidenced competitor) — never a "likely bidder" list manufactured from name/topic similarity.
When the evidence is weak, the answer is UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Sequence

from .company import CompanyProfile
from .customer_intelligence import PUBLIC_EVIDENCE, PYRNOVA_DERIVED

COMPETITIVE_INTELLIGENCE_VERSION = "competitive_intelligence_v1"


@dataclass(frozen=True)
class CompetitiveFact:
    dimension: str      # incumbent | current_contract | incumbent_tenure | obligated_value |
                        # period_of_performance | renewal_context | prior_competitor |
                        # competitor_hypothesis | incumbent_advantage | incumbent_vulnerability |
                        # customer_strength | customer_gap
    key: str
    value: Any
    provenance_class: str = PUBLIC_EVIDENCE
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0
    available_at: Optional[str] = None
    uncertainty: str = ""
    contradicts: tuple[str, ...] = ()   # ids/notes of contradictory evidence held visible
    basis: str = ""

    def to_record(self) -> dict:
        return {
            "dimension": self.dimension, "key": self.key, "value": self.value,
            "provenance_class": self.provenance_class, "evidence_ids": list(self.evidence_ids),
            "confidence": self.confidence, "available_at": self.available_at,
            "uncertainty": self.uncertainty, "contradicts": list(self.contradicts), "basis": self.basis,
        }


@dataclass
class CompetitiveIntelligence:
    incumbent_name: Optional[str]
    opportunity_ref: Optional[str] = None
    as_of: Optional[str] = None
    facts: list[CompetitiveFact] = field(default_factory=list)
    is_unknown: bool = False
    version: str = COMPETITIVE_INTELLIGENCE_VERSION

    def by_dimension(self, dimension: str) -> list[CompetitiveFact]:
        return [f for f in self.facts if f.dimension == dimension]

    def competitor_hypotheses(self) -> list[CompetitiveFact]:
        return self.by_dimension("competitor_hypothesis")

    def to_record(self) -> dict:
        return {
            "competitive_intelligence_version": self.version, "incumbent_name": self.incumbent_name,
            "opportunity_ref": self.opportunity_ref, "as_of": self.as_of, "is_unknown": self.is_unknown,
            "facts": [f.to_record() for f in self.facts],
        }


def _days(a: Optional[str], b: Optional[str]) -> Optional[int]:
    def parse(v):
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00").split("T")[0])
        except (TypeError, ValueError):
            return None
    da, db = parse(a), parse(b)
    return (db - da).days if da and db else None


def build_competitive_intelligence(
    *,
    incumbent: Optional[dict] = None,
    current_contract: Optional[dict] = None,
    related_awards: Sequence[dict] = (),
    prior_competitors: Sequence[dict] = (),
    customer_profile: Optional[CompanyProfile] = None,
    as_of: Optional[str] = None,
) -> CompetitiveIntelligence:
    """Assemble incumbent + competitive intelligence as evidence-backed hypotheses with uncertainty."""
    facts: list[CompetitiveFact] = []
    incumbent_name = (incumbent or {}).get("name")
    inc_key = str(incumbent_name).casefold() if incumbent_name else None

    # --- Incumbent + current contract (observed) ------------------------------------------------
    if incumbent_name:
        ev = tuple(r for r in ((incumbent or {}).get("evidence_ref"),) if r)
        facts.append(CompetitiveFact("incumbent", inc_key, incumbent_name, PUBLIC_EVIDENCE, ev,
                                     confidence=0.85 if ev else 0.5,
                                     uncertainty="" if ev else "incumbent asserted without a cited award record",
                                     basis="incumbent contractor for the current/related contract"))
        facts.append(CompetitiveFact("incumbent_advantage", "incumbency", "holds the current contract",
                                     PYRNOVA_DERIVED, ev, confidence=0.7,
                                     basis="incumbency confers transition cost and customer familiarity"))

    if current_contract:
        cc = current_contract
        ref = cc.get("award_id") or cc.get("source_ref")
        ev = tuple(r for r in (ref,) if r)
        facts.append(CompetitiveFact("current_contract", str(ref or "contract"),
                                     {k: cc.get(k) for k in ("award_id", "agency", "value_usd", "obligated_usd") if cc.get(k) is not None},
                                     PUBLIC_EVIDENCE, ev, confidence=0.85, available_at=cc.get("available_at"),
                                     basis="current/related contract of record"))
        if cc.get("obligated_usd") is not None or cc.get("value_usd") is not None:
            facts.append(CompetitiveFact("obligated_value", "usd",
                                         {"obligated_usd": cc.get("obligated_usd"), "value_usd": cc.get("value_usd")},
                                         PUBLIC_EVIDENCE, ev, confidence=0.8, available_at=cc.get("available_at"),
                                         basis="obligated/known contract value"))
        if cc.get("period_start") or cc.get("period_end"):
            facts.append(CompetitiveFact("period_of_performance", "pop",
                                         {"start": cc.get("period_start"), "end": cc.get("period_end")},
                                         PUBLIC_EVIDENCE, ev, confidence=0.8, basis="period of performance of record"))
            tenure = _days(cc.get("period_start"), as_of or cc.get("available_at"))
            if tenure is not None and tenure >= 0:
                facts.append(CompetitiveFact("incumbent_tenure", "days", tenure, PYRNOVA_DERIVED, ev,
                                             confidence=0.7, basis="tenure derived from period start to as-of"))
            # A near-term expiry is a real, evidenced incumbent vulnerability (recompete window opening).
            to_end = _days(as_of or cc.get("available_at"), cc.get("period_end"))
            if to_end is not None and 0 <= to_end <= 365:
                facts.append(CompetitiveFact("incumbent_vulnerability", "expiring_contract",
                                             {"days_to_end": to_end}, PYRNOVA_DERIVED, ev, confidence=0.6,
                                             basis="current contract expires within a year; recompete window opening"))
        if cc.get("renewal") is not None or cc.get("follow_on") is not None:
            facts.append(CompetitiveFact("renewal_context", "renewal",
                                         {"renewal": cc.get("renewal"), "follow_on": cc.get("follow_on")},
                                         PUBLIC_EVIDENCE, ev, confidence=0.7, basis="renewal/follow-on context of record"))
        for note in cc.get("contradictions", ()) or ():
            facts.append(CompetitiveFact("incumbent_vulnerability", "contradiction", note, PUBLIC_EVIDENCE, ev,
                                         confidence=0.6, contradicts=(str(note),),
                                         basis="contradictory evidence against the incumbent's position"))

    # --- Prior competitors (observed) + evidence-backed competitor hypotheses -------------------
    seen_competitors: set[str] = set()
    for award in related_awards:
        recipient = str(award.get("recipient") or "").strip()
        if not recipient or (inc_key and recipient.casefold() == inc_key):
            continue
        ref = award.get("source_ref") or award.get("award_id")
        ev = tuple(r for r in (ref,) if r)
        facts.append(CompetitiveFact("prior_competitor", recipient.casefold(), recipient, PUBLIC_EVIDENCE, ev,
                                     confidence=0.8, available_at=award.get("available_at"),
                                     basis="won/bid a prior related procurement"))
        if recipient.casefold() not in seen_competitors:
            seen_competitors.add(recipient.casefold())
            facts.append(CompetitiveFact("competitor_hypothesis", recipient.casefold(), recipient, PYRNOVA_DERIVED, ev,
                                         confidence=0.55, uncertainty="hypothesis: prior participation does not guarantee a re-bid",
                                         basis="plausible re-bidder — participated in a related procurement"))

    for comp in prior_competitors:
        name = str(comp.get("name") or "").strip()
        if not name or name.casefold() in seen_competitors:
            continue
        seen_competitors.add(name.casefold())
        ev = tuple(r for r in (comp.get("evidence_ref"),) if r)
        facts.append(CompetitiveFact("competitor_hypothesis", name.casefold(), name, PYRNOVA_DERIVED, ev,
                                     confidence=0.6 if ev else 0.4,
                                     uncertainty="hypothesis with cited evidence" if ev else "asserted competitor without cited evidence",
                                     basis=comp.get("basis") or "evidenced competitor"))

    # --- Customer competitive strengths/gaps (light, from the customer's own evidence) ----------
    if customer_profile is not None:
        if customer_profile.capabilities:
            facts.append(CompetitiveFact("customer_strength", "evidenced_capabilities",
                                         [c.label for c in customer_profile.capabilities], PYRNOVA_DERIVED,
                                         confidence=0.6, basis="customer capabilities backed by public evidence"))
        for excl in customer_profile.exclusions:
            facts.append(CompetitiveFact("customer_gap", str(excl).casefold(), excl, PUBLIC_EVIDENCE,
                                         confidence=0.5, basis="customer-declared exclusion narrows competitive reach"))

    is_unknown = not incumbent_name and not related_awards and not any(
        f.dimension == "competitor_hypothesis" for f in facts)
    return CompetitiveIntelligence(incumbent_name=incumbent_name, as_of=as_of, facts=facts, is_unknown=is_unknown)
