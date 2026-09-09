"""Canonical MVP objects (dataclasses).

Only the objects the authority permits now: Entity, Evidence, Claim, Event, Catalyst, Opportunity
(with STRIKE as a lifecycle state), Customer, CapabilityProfile, Outcome — plus Prediction and Review
(the accumulation / benchmark backbone). FLOW / SHIFT / RISK are intentionally absent (deferred).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any, Optional


def _uid() -> str:
    return uuid.uuid4().hex


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


@dataclass
class Evidence:
    source_id: str
    content_sha256: str
    archive_uri: str
    retention_tier: str
    media_type: str = "application/json"
    source_ref: Optional[str] = None
    source_url: Optional[str] = None
    published_at: Optional[str] = None
    first_seen_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class Entity:
    kind: str  # 'recipient' | 'agency' | 'office' | 'program'
    name: str
    canonical_name: str
    uei: Optional[str] = None
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class Event:
    """Source-independent occurrence connected to its archived evidence."""

    kind: str  # 'award' | 'notice_posted' | 'regulatory_precursor' | 'program_signal'
    source_id: str
    source_ref: str
    summary: str
    occurred_at: Optional[str] = None
    stage: Optional[str] = None
    program_key: Optional[str] = None
    evidence_ids: list[str] = field(default_factory=list)
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class Relationship:
    """Evidence-backed edge between canonical records.

    Temporal fields (M5) let replay answer "when could we first have known this relationship?".
    They are optional so the M2/M4 event-enrichment use of this type is unchanged.
    """

    subject_id: str
    predicate: str
    object_id: str
    evidence_ids: list[str] = field(default_factory=list)
    join_method: Optional[str] = None   # deterministic_program_key | deterministic_native_id | inferred_strong_attribute
    confidence: float = 0.0
    rationale: str = ""
    first_observed_at: Optional[str] = None  # earliest time both endpoints were knowable
    available_at: Optional[str] = None       # alias of first_observed_at for point-in-time filters
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class OpportunityTransition:
    """One evidence-caused disposition change in an opportunity/chain lifecycle (M5).

    Derived from the existing scoring policy replayed point-in-time; it records observability, not a
    new scoring model.
    """

    subject_id: str          # opportunity id, chain id, or program_key
    prior_disposition: Optional[str]  # None | SIGNAL | WATCH | STRIKE | REJECT
    new_disposition: str
    cause_stage: Optional[str] = None
    cause_source_id: Optional[str] = None
    cause_source_ref: Optional[str] = None
    cause_evidence_ids: list[str] = field(default_factory=list)
    occurred_at: Optional[str] = None
    scoring_version: str = "scoring_v1"
    basis: str = ""
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class Participant:
    """An economically distinct actor in a capital catalyst / consequence (M7).

    Roles are not interchangeable: who controls the money, who owns the program, who buys, who
    receives the prime award, and who benefits downstream are different economic positions.
    """

    role: str  # FUNDING_AUTHORITY|PROGRAM_OWNER|BUYER|PRIME_RECIPIENT|BENEFICIARY|SUPPLIER|SUBCONTRACTOR|AFFECTED_ENTITY|REGULATED_ENTITY
    entity_ref: Optional[str] = None      # canonical node id (entity:uei:..., agency key) where known
    name: Optional[str] = None
    evidence_ids: list = field(default_factory=list)
    basis: str = ""


@dataclass
class CapitalCatalyst:
    """An evidence-backed change likely to alter economic behavior, expenditure, or capital allocation.

    One catalyst per resolved program chain (deterministic identity from ``program_key``); it references
    canonical graph objects (signals, relationships) rather than duplicating them.
    """

    program_key: str
    catalyst_type: str  # BUDGET_APPROPRIATION|PROGRAM_ESTABLISHMENT|PROCUREMENT_LIFECYCLE|REGULATORY_MANDATE|CAPACITY_BUILDOUT|SUPPLY_DISRUPTION
    summary: str
    controlling_institution: Optional[str] = None      # program owner / funding authority
    triggering_evidence_ids: list = field(default_factory=list)   # source-native signal/evidence ids
    supporting_relationship_ids: list = field(default_factory=list)
    participants: list = field(default_factory=list)   # list[Participant]
    geography: Optional[str] = None
    effective_date: Optional[str] = None
    activation_window: Optional[dict] = None           # {"start":..., "end":...}
    stages_present: list = field(default_factory=list)
    confidence: float = 0.0                            # catalyst confidence — distinct from opportunity score
    first_observed_at: Optional[str] = None
    available_at: Optional[str] = None
    status: str = "active"                             # active | contradicted | superseded
    contradictions: list = field(default_factory=list)
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class ConsequenceFalsifier:
    """Structured negative commercial evidence (M7). A fatal falsifier kills the consequence."""

    code: str
    detail: str = ""
    fatal: bool = False


@dataclass
class CommercialConsequence:
    """A specific, evidence-backed economic behavior a catalyst is likely to cause (M7).

    Distinct from Opportunity/STRIKE: a consequence explains "this catalyst likely causes economic
    behavior X, via mechanism M, for participant role R, requiring capability C, over timeframe T,
    supported by this evidence, subject to these assumptions and falsifiers." A STRIKE is only surfaced
    after consequence analysis and existing screening.
    """

    catalyst_id: str
    program_key: str
    mechanism: str          # one of the mechanism families
    directness: str         # DIRECT | DOWNSTREAM | SECOND_ORDER
    mechanism_confidence: float = 0.0
    mechanism_rationale: str = ""
    participants: list = field(default_factory=list)      # list[Participant] relevant to this consequence
    capability_classes: list = field(default_factory=list)  # list[dict] from capabilities.CapabilityClass
    likely_spend_category: Optional[str] = None
    timing: Optional[dict] = None                          # {"expected_at":..., "window":..., "basis":...}
    geography: Optional[str] = None
    value: dict = field(default_factory=dict)              # value.ValueEstimate as dict
    evidence_ids: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    falsifiers: list = field(default_factory=list)         # list[ConsequenceFalsifier as dict]
    confidence: float = 0.0                                # consequence confidence — distinct from score
    screened_disposition: str = "WATCH"                    # STRIKE | WATCH | REJECT (recommendation only)
    screening_basis: str = ""
    first_supportable_at: Optional[str] = None
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class Exposure:
    """WHO / WHAT is exposed to WHAT (M15 exposure graph).

    An explicit, evidence-backed edge from an affected *subject* (usually a company) to an *exposure
    target* (a sanctioned counterparty, a program, a contract, a regulation, a geography, ...). The
    edge records HOW the join was made (``join_method``) and how strongly it is believed
    (``link_class``/``confidence``), so a weak fuzzy-name resemblance is never silently promoted to an
    authoritative exposure. Temporal fields answer "when could we first have known this exposure?".
    """

    subject_ref: str            # affected entity node id (co_..., entity:uei:..., agency key)
    subject_name: str
    relation_type: str          # one of threat.EXPOSURE_RELATIONS
    target_ref: str             # exposed-to node id (ofac:sdn:..., program_key, agency key, ...)
    target_name: str
    join_method: str            # deterministic_identifier | deterministic_native_id | inferred_strong_attribute | name_only_weak
    link_class: str             # CONFIRMED | INFERRED | CANDIDATE | REJECTED
    confidence: float = 0.0     # numeric join confidence (join strength, NOT threat severity)
    rationale: str = ""
    evidence_ids: list = field(default_factory=list)
    available_at: Optional[str] = None       # earliest time the exposure was knowable
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    status: str = "active"      # active | ended | rejected
    reject_reason: Optional[str] = None
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class Threat:
    """A first-class Pyrnova threat: an evidence-backed adverse economic change to a subject (M15).

    A peer of :class:`CommercialConsequence`, not a negated opportunity or a generic alarm. It names
    the affected subject, the exposure(s) that make it vulnerable, the mechanism by which harm occurs,
    and separates two orthogonal judgments that must never be collapsed into one magic number:

    * ``severity`` — how bad the economic consequence could be *if true* (ordinal).
    * ``confidence`` — how strongly the retained evidence supports the thesis (ordinal).

    ``UNKNOWN`` is a valid, honest value for severity, confidence, and horizon. Identity is
    deterministic where inputs allow (see :func:`threat.threat_id`).
    """

    subject_ref: str
    subject_name: str
    mechanism: str                                    # one of threat.THREAT_MECHANISMS
    exposure_ids: list = field(default_factory=list)
    catalyst_id: Optional[str] = None                 # shared CapitalCatalyst (duality anchor) where present
    affected_value_category: Optional[str] = None     # REVENUE | CONTRACT_POSITION | MARKET_ACCESS | COST_BASE | ELIGIBILITY | CONTINUITY
    economic_effect: str = ""                         # qualitative description of the adverse effect
    severity: str = "UNKNOWN"                         # LOW | MODERATE | HIGH | CRITICAL | UNKNOWN
    severity_basis: str = ""
    confidence: str = "UNKNOWN"                       # LOW | MEDIUM | HIGH | UNKNOWN (evidence strength)
    confidence_basis: str = ""
    horizon: str = "UNKNOWN"                          # IMMEDIATE | NEAR_TERM | MEDIUM_TERM | LONG_TERM | UNKNOWN
    status: str = "ACTIVE"                            # WATCH | ACTIVE | MITIGATED | MATERIALIZED | AVOIDED | FALSE_ALARM | EXPIRED | UNKNOWN
    evidence_ids: list = field(default_factory=list)
    falsifiers: list = field(default_factory=list)    # list[ConsequenceFalsifier as dict] — what would falsify the warning
    mitigations: list = field(default_factory=list)   # evidence-backed candidate responses only
    dual_opportunity_ref: Optional[str] = None        # consequence/opportunity id sharing the catalyst (other side of duality)
    first_observed_at: Optional[str] = None
    available_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    review_state: str = "unreviewed"                  # unreviewed | accepted | rejected | deferred
    engine_version: str = "threat_v1"
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class ThreatRejection:
    """A recorded decision NOT to emit a threat (M15 zero-threat discipline).

    Rejections are first-class output, peers of :class:`Threat`. They keep the threat engine honest:
    most external events must NOT become a threat for a given subject, and the reason is auditable.
    """

    subject_ref: str
    subject_name: str
    reason_code: str            # one of threat.REJECTION_REASONS
    mechanism: Optional[str] = None
    detail: str = ""
    evidence_ids: list = field(default_factory=list)
    exposure_ids: list = field(default_factory=list)
    available_at: Optional[str] = None
    engine_version: str = "threat_v1"
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class EvidenceAssessment:
    """Opportunity-specific evidence weight, separate from provenance and polarity."""

    evidence_id: str
    strength: int  # 1 weak topic, 2 context, 3 named relation, 4 contracting, 5 causal/program
    strength_class: str
    polarity: str  # supporting | contradictory
    basis: str


@dataclass
class Catalyst:
    kind: str  # 'recompete_expiry' | 'sources_sought' | 'rfi' | 'presolicitation' | 'special_notice' | 'solicitation'
    detected_by: str
    summary: str = ""
    horizon_days: Optional[int] = None
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class Opportunity:
    title: str
    catalyst: Catalyst
    state: str = "candidate"  # candidate | reviewing | strike | rejected
    customer_id: Optional[str] = None
    agency: Optional[str] = None
    incumbent: Optional[str] = None
    naics: Optional[str] = None
    psc: Optional[str] = None
    value_usd: Optional[float] = None
    expected_action_at: Optional[str] = None
    relevance_score: float = 0.0          # capability match (kept separate)
    attractiveness: float = 0.0           # opportunity attractiveness (kept separate)
    confidence: float = 0.0               # our confidence in the intelligence (kept separate)
    falsification: str = ""               # mandatory: reasons NOT to pursue
    recommended_action: str = ""
    relevance_reasons: list = field(default_factory=list)
    evidence: list = field(default_factory=list)   # list[Evidence]
    evidence_roles: dict = field(default_factory=dict)  # evidence id -> primary|context|supporting|contra
    evidence_assessments: list = field(default_factory=list)  # list[EvidenceAssessment]
    events: list = field(default_factory=list)     # list[Event]
    relationships: list = field(default_factory=list)  # list[Relationship]
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)

    @property
    def is_strike(self) -> bool:
        return self.state == "strike"


@dataclass
class Prediction:
    opportunity_id: str
    statement: str
    precursor_class: str
    predicted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolve_by: Optional[str] = None
    lead_time_days: Optional[int] = None
    id: str = field(default_factory=_uid)
    meta: dict = field(default_factory=dict)


@dataclass
class Review:
    opportunity_id: str
    decision: str  # legacy/system: 'recommend' | 'watch' | 'reject'; human: accept/watch/reject
    reason: str = ""
    confidence: Optional[float] = None
    reviewer: Optional[str] = "auto-recommend/v1"
    human_decision: Optional[str] = None  # ACCEPT | WATCH | REJECT
    system_disposition: str = "WATCH"  # STRIKE | WATCH | REJECT
    score_at_review: Optional[float] = None
    reviewed_at: Optional[str] = None
    customer_feedback: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    id: str = field(default_factory=_uid)


def to_record(obj: Any) -> dict:
    """Serialize a dataclass (nested) to a json-safe dict for the append-only state log."""
    return _to_jsonable(asdict(obj))
