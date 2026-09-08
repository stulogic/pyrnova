"""MATCH — deterministic capability relevance scoring.

Answers: "is this opportunity materially relevant to this company?" Kept SEPARATE from opportunity
attractiveness and from our confidence in the intelligence. No full Capability Graph (deferred).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import Opportunity
from .resolve import canonicalize_name


@dataclass
class CapabilityProfile:
    name: str
    agencies: list[str] = field(default_factory=list)      # names/keywords
    naics: list[str] = field(default_factory=list)         # codes or prefixes
    psc: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)  # keywords expected in titles
    geography: list[str] = field(default_factory=list)
    size_min_usd: Optional[float] = None
    size_max_usd: Optional[float] = None
    set_asides: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)    # hard "cannot pursue" keywords
    incumbencies: list[str] = field(default_factory=list)
    recipient_names: list[str] = field(default_factory=list)  # USAspending recipient search anchors

    @classmethod
    def from_dict(cls, d: dict) -> "CapabilityProfile":
        return cls(
            name=d.get("name", "Unnamed customer"),
            agencies=list(d.get("agencies", [])),
            naics=[str(x) for x in d.get("naics", [])],
            psc=[str(x) for x in d.get("psc", [])],
            capabilities=list(d.get("capabilities", [])),
            geography=list(d.get("geography", [])),
            size_min_usd=d.get("size_min_usd"),
            size_max_usd=d.get("size_max_usd"),
            set_asides=list(d.get("set_asides", [])),
            exclusions=list(d.get("exclusions", [])),
            incumbencies=list(d.get("incumbencies", [])),
            recipient_names=list(d.get("recipient_names", [])),
        )

    @property
    def search_names(self) -> list[str]:
        return self.recipient_names or [self.name]


# Component weights (sum to 1.0).
_W_AGENCY = 0.30
_W_NAICS = 0.30
_W_CAPABILITY = 0.25
_W_SIZE = 0.15


def _agency_match(opp: Opportunity, profile: CapabilityProfile) -> tuple[float, Optional[str]]:
    if not profile.agencies or not opp.agency:
        return 0.0, None
    opp_agency = canonicalize_name(opp.agency)
    for a in profile.agencies:
        ca = canonicalize_name(a)
        if ca and (ca in opp_agency or opp_agency in ca):
            return 1.0, f"agency match: '{a}'"
    return 0.0, None


def _naics_match(opp: Opportunity, profile: CapabilityProfile) -> tuple[float, Optional[str]]:
    if not profile.naics or not opp.naics:
        return 0.0, None
    for code in profile.naics:
        if opp.naics.startswith(code) or code.startswith(opp.naics):
            return 1.0, f"NAICS match: {opp.naics} ~ {code}"
    return 0.0, None


def _capability_match(opp: Opportunity, profile: CapabilityProfile) -> tuple[float, Optional[str]]:
    if not profile.capabilities:
        return 0.0, None
    hay = f"{opp.title} {opp.meta.get('solicitation_number', '')}".lower()
    hits = [kw for kw in profile.capabilities if kw.lower() in hay]
    if not hits:
        return 0.0, None
    return min(1.0, len(hits) / 2.0), f"capability keywords: {', '.join(hits)}"


def _size_match(opp: Opportunity, profile: CapabilityProfile) -> tuple[float, Optional[str]]:
    v = opp.value_usd
    if v is None or (profile.size_min_usd is None and profile.size_max_usd is None):
        return 0.0, None
    if profile.size_min_usd is not None and v < profile.size_min_usd:
        return 0.0, f"below size floor (${v:,.0f} < ${profile.size_min_usd:,.0f})"
    if profile.size_max_usd is not None and v > profile.size_max_usd:
        return 0.0, f"above size ceiling (${v:,.0f} > ${profile.size_max_usd:,.0f})"
    return 1.0, "within target contract size band"


def score_relevance(opp: Opportunity, profile: CapabilityProfile) -> tuple[float, list[str], bool]:
    """Return (score 0..1, reasons, exclusion_hit)."""
    hay = f"{opp.title} {opp.agency or ''}".lower()
    for ex in profile.exclusions:
        if ex.lower() in hay:
            return 0.0, [f"EXCLUDED by '{ex}'"], True

    reasons: list[str] = []
    score = 0.0
    for weight, fn in (
        (_W_AGENCY, _agency_match),
        (_W_NAICS, _naics_match),
        (_W_CAPABILITY, _capability_match),
        (_W_SIZE, _size_match),
    ):
        comp, reason = fn(opp, profile)
        score += weight * comp
        if reason:
            reasons.append(reason)

    # Incumbency note (does not change score, informs review).
    if opp.incumbent:
        inc = canonicalize_name(opp.incumbent)
        for known in profile.incumbencies:
            if canonicalize_name(known) == inc:
                reasons.append(f"customer is the incumbent ({opp.incumbent})")
    return round(min(1.0, score), 3), reasons, False


def apply_match(opp: Opportunity, profile: CapabilityProfile) -> Opportunity:
    score, reasons, _ = score_relevance(opp, profile)
    opp.relevance_score = score
    opp.relevance_reasons = reasons
    return opp
