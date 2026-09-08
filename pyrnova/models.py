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
    decision: str  # 'accept' | 'reject' | 'recommend'
    reason: str = ""
    confidence: Optional[float] = None
    reviewer: str = "auto-recommend/v1"
    customer_feedback: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    id: str = field(default_factory=_uid)


def to_record(obj: Any) -> dict:
    """Serialize a dataclass (nested) to a json-safe dict for the append-only state log."""
    return _to_jsonable(asdict(obj))
