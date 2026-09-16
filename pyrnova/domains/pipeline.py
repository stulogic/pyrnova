"""National pipeline adapter — runs a national domain's chain THROUGH the shared kernel.

This is where "SHARE MECHANISM, KEEP NATIONAL TRUTH NATIONAL" becomes executable. The adapter is
domain-parameterized (works for any :class:`NationalDomain`) and demonstrated with Australia. National
truth — lifecycle stage, route meaning, access, Industrial Position, Important Miss — is owned by the
domain; the temporal/decision machinery (strict AS-OF, the Decision-Lead-Time engine, the Integrated
Decision object) is the shared kernel's and is NOT re-implemented per country.

Chain:  NATIONAL SOURCE -> NATIONAL EVIDENCE -> NATIONAL EVENT -> NATIONAL MATERIAL CHANGE
        -> NATIONAL ACQUISITION STATE -> ACCESS / INDUSTRIAL POSITION -> CUSTOMER-SPECIFIC OPPORTUNITY
        -> SHARED DECISION OBJECT (+ shared DLT) -> customer product / brief.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..decision_lead_time import TemporalAnchors, derive_decision_lead_time
from ..decision_object import assemble_decision, IntegratedDecision
from .base import NationalDomain, SourceActivation


class ASOFViolation(RuntimeError):
    """Raised when evidence dated after the AS-OF instant would leak into a point-in-time view."""


@dataclass(frozen=True)
class NationalEvidence:
    """A national source fact with provenance + AS-OF availability. Original-language authority is a
    national concern; ``language`` records the original, and any translation would be PYRNOVA DERIVED."""

    evidence_id: str
    source_id: str
    available_at: str            # ISO-8601 — when this evidence became lawfully available (T0/T1)
    lifecycle_stage: str         # national lifecycle stage this evidence observes
    route: str                   # national acquisition route code
    language: str = "en"         # ORIGINAL language of this evidence (both EN and FR are ORIGINAL for CA)
    # Optional PYRNOVA-DERIVED translation of this evidence. When present it is DERIVED content, NEVER the
    # evidentiary authority — the ``language`` original above stays authoritative. Shape (national concern):
    # {"language": "en"|"fr", "text_ref": ..., "provenance": "machine"|"human", "derived": True}.
    translation: Optional[dict] = None
    # Optional cross-language ENTITY key: the same programme identity across EN/FR variants. Differing
    # EN/FR strings are NOT different programmes; a shared entity_key links them without normalizing away
    # the original-language provenance.
    entity_key: Optional[str] = None
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class NationalMaterialChange:
    """A materially significant national event. Material Change != Opportunity (a shared kernel truth),
    so this may or may not become a customer opportunity depending on national access/fit."""

    material_change_id: str
    domain_code: str
    lifecycle_stage: str
    route: str
    important_miss_kind: Optional[str]     # which national Important-Miss category this addresses, if any
    evidence_ids: tuple[str, ...]
    observed_at: str
    # UK-style consequential-change state (created/expanded/narrowed/access-changed/prime-changed/window-
    # changed/closed/post-award-risk/capability-insertion). None for domains that model change only via
    # important_miss; drives the shared opportunity disposition when present.
    consequential_change_kind: Optional[str] = None
    # SSCR / QDC (Single Source Contract Regulations / Qualifying Defence Contract) status — a SEPARATE
    # EVIDENCED field. NEVER derived from route/single-source/incumbency/sovereignty: UNKNOWN unless
    # contract-specific evidence supports it. Values: UNKNOWN | QDC_CONFIRMED | NOT_QDC.
    sscr_qdc: str = "UNKNOWN"
    # National MECHANISM family (e.g. CA competitive/open, directed/OEM, FMS/GtG, strategic-source,
    # digital/ICT). None for domains that do not classify mechanism; different mechanisms carry different
    # timing/access/industrial meaning and must not be flattened.
    mechanism: Optional[str] = None
    # National TIMING class — how the timing evidence is qualified with NO numeric DLT threshold
    # (EXACT/BOUNDED/CONTAMINATED/N_A/UNKNOWN). Refuses to fabricate exactness. Default UNKNOWN.
    timing_class: str = "UNKNOWN"
    # ITB / Value-Proposition EVIDENCED state — a SEPARATE evidenced field, NEVER inferred from value,
    # ownership, presence, or access. Default UNKNOWN.
    itb_vp: str = "UNKNOWN"


@dataclass(frozen=True)
class NationalAccessPosition:
    """National access + Industrial Position for a customer against a material change.

    ``verdict`` is read by the shared decision object's uncertainty view. Access != customer decision:
    a strong access position is not itself a pursuit decision (a shared kernel distinction)."""

    verdict: str                 # an access_class from the national domain
    industrial_position: str     # an industrial_position_class from the national domain
    facts: tuple = ()            # evidence-referencing facts (shared decision object reads .facts)


@dataclass(frozen=True)
class NationalOpportunity:
    material_change: NationalMaterialChange
    access: NationalAccessPosition
    customer_id: str


def _assert_asof(available_at: str, as_of: Optional[str]) -> None:
    if as_of and available_at and available_at > as_of:
        raise ASOFViolation(f"evidence available_at={available_at!r} is after as_of={as_of!r} "
                            "(strict AS-OF: no future-data leakage)")


def derive_material_change(domain: NationalDomain, evidence: NationalEvidence, *,
                           as_of: Optional[str], important_miss_kind: Optional[str] = None,
                           mc_id: Optional[str] = None, consequential_change_kind: Optional[str] = None,
                           sscr_qdc: str = "UNKNOWN", mechanism: Optional[str] = None,
                           timing_class: str = "UNKNOWN", itb_vp: str = "UNKNOWN") -> NationalMaterialChange:
    """National classification of a source fact into a Material Change. Fails closed on unknown national
    truth (route/stage) and on AS-OF violation — the source is evidence, never the ontology."""
    _assert_asof(evidence.available_at, as_of)
    if not domain.is_ingestible(evidence.source_id):
        # UNKNOWN => DENY. A non-ACTIVE source (fixture/declared/prohibited) cannot back a *live* change;
        # replay/fixtures set the domain source to FIXTURE_ONLY and use derive_material_change_fixture.
        raise PermissionError(f"[{domain.code}] source {evidence.source_id!r} is not ACTIVE for live "
                              "ingestion (UNKNOWN => DENY)")
    return _material_change(domain, evidence, important_miss_kind, mc_id,
                            consequential_change_kind, sscr_qdc, mechanism, timing_class, itb_vp)


def derive_material_change_fixture(domain: NationalDomain, evidence: NationalEvidence, *,
                                   as_of: Optional[str], important_miss_kind: Optional[str] = None,
                                   mc_id: Optional[str] = None,
                                   consequential_change_kind: Optional[str] = None,
                                   sscr_qdc: str = "UNKNOWN", mechanism: Optional[str] = None,
                                   timing_class: str = "UNKNOWN", itb_vp: str = "UNKNOWN") -> NationalMaterialChange:
    """Replay/fixture path: lawful for a FIXTURE_ONLY source. Never permitted for a PROHIBITED source."""
    _assert_asof(evidence.available_at, as_of)
    src = domain.source(evidence.source_id)
    if src is None or src.activation is SourceActivation.PROHIBITED:
        domain.assert_ingestible(evidence.source_id)  # raises ProhibitedSourceIngestion / denies
    return _material_change(domain, evidence, important_miss_kind, mc_id,
                            consequential_change_kind, sscr_qdc, mechanism, timing_class, itb_vp)


_SSCR_QDC_VALUES = ("UNKNOWN", "QDC_CONFIRMED", "NOT_QDC")


def _material_change(domain, evidence, important_miss_kind, mc_id,
                     consequential_change_kind=None, sscr_qdc="UNKNOWN",
                     mechanism=None, timing_class="UNKNOWN", itb_vp="UNKNOWN") -> NationalMaterialChange:
    if not domain.known_route(evidence.route):
        raise ValueError(f"[{domain.code}] unknown national route {evidence.route!r}")
    if evidence.lifecycle_stage not in domain.lifecycle:
        raise ValueError(f"[{domain.code}] unknown national lifecycle stage {evidence.lifecycle_stage!r}")
    if important_miss_kind is not None and important_miss_kind not in domain.important_miss:
        raise ValueError(f"[{domain.code}] unknown Important-Miss kind {important_miss_kind!r}")
    if consequential_change_kind is not None and not domain.known_consequential_state(consequential_change_kind):
        raise ValueError(f"[{domain.code}] unknown consequential-change state {consequential_change_kind!r}")
    if sscr_qdc not in _SSCR_QDC_VALUES:
        # SSCR/QDC is a separate EVIDENCED field; only the reviewed values are permitted (never derived).
        raise ValueError(f"[{domain.code}] invalid SSCR/QDC status {sscr_qdc!r} (expected one of "
                         f"{_SSCR_QDC_VALUES})")
    # National MECHANISM: when set it must be a declared national mechanism family (never a free string).
    if mechanism is not None and not domain.known_mechanism(mechanism):
        raise ValueError(f"[{domain.code}] unknown acquisition mechanism {mechanism!r}")
    # National TIMING class: "UNKNOWN" is always permissible; any other value must be a declared class.
    # This is the guardrail that refuses to promote BOUNDED/CONTAMINATED timing to fabricated exactness.
    if timing_class != "UNKNOWN" and not domain.known_timing_class(timing_class):
        raise ValueError(f"[{domain.code}] unknown timing class {timing_class!r}")
    # ITB/VP is a SEPARATE evidenced field; "UNKNOWN" is always permissible, any other must be declared —
    # it is NEVER derived from route, value, ownership, presence, or access.
    if itb_vp != "UNKNOWN" and not domain.known_itb_vp(itb_vp):
        raise ValueError(f"[{domain.code}] unknown ITB/VP state {itb_vp!r} (evidenced, never derived)")
    return NationalMaterialChange(
        material_change_id=mc_id or f"{domain.code.lower()}-mc-{evidence.evidence_id}",
        domain_code=domain.code, lifecycle_stage=evidence.lifecycle_stage, route=evidence.route,
        important_miss_kind=important_miss_kind, evidence_ids=(evidence.evidence_id,),
        observed_at=evidence.available_at, consequential_change_kind=consequential_change_kind,
        sscr_qdc=sscr_qdc, mechanism=mechanism, timing_class=timing_class, itb_vp=itb_vp)


def assess_access(domain: NationalDomain, *, access_class: str, industrial_position: str,
                  facts: tuple = ()) -> NationalAccessPosition:
    if access_class not in domain.access_classes:
        raise ValueError(f"[{domain.code}] unknown access class {access_class!r}")
    if industrial_position not in domain.industrial_position_classes:
        raise ValueError(f"[{domain.code}] unknown Industrial Position {industrial_position!r}")
    return NationalAccessPosition(verdict=access_class, industrial_position=industrial_position, facts=facts)


def to_decision(domain: NationalDomain, opportunity: NationalOpportunity, *,
                anchors: TemporalAnchors, as_of: Optional[str] = None) -> IntegratedDecision:
    """Project a national opportunity through the SHARED decision object + SHARED DLT engine.

    National meaning travels as data on the shared object (route, lifecycle stage, access, Industrial
    Position); the composition and Decision-Lead-Time derivation are the kernel's, not re-implemented."""
    mc = opportunity.material_change
    dlt = derive_decision_lead_time(anchors)  # shared, country-neutral engine
    national_material_change = {
        "material_change_id": mc.material_change_id, "domain": mc.domain_code,
        "lifecycle_stage": mc.lifecycle_stage, "route": mc.route,
        "route_meaning": domain.routes.get(mc.route), "important_miss_kind": mc.important_miss_kind,
        "consequential_change_kind": mc.consequential_change_kind, "sscr_qdc": mc.sscr_qdc,
        "mechanism": mc.mechanism, "timing_class": mc.timing_class, "itb_vp": mc.itb_vp,
        "evidence_ids": list(mc.evidence_ids), "observed_at": mc.observed_at,
        "industrial_position": opportunity.access.industrial_position,
    }
    return assemble_decision(
        opportunity_ref=f"{domain.code}:{mc.material_change_id}:{opportunity.customer_id}",
        program_key=mc.material_change_id,
        material_changes=[national_material_change],
        vehicle_access=opportunity.access,      # shared object reads .verdict / .facts
        decision_lead_time=dlt,
        as_of=as_of,
    )
