"""Decision Lead Time — canonical, derived temporal model (PRELAUNCH-CONVERGENCE-001 · B1.3).

Decision Lead Time is *derived* from temporal anchors that already exist in the intelligence
artifacts; it adds no new persisted schema. The canonical anchors:

    T0  source evidence became publicly available   (record ``available_at`` / ``first_observed_at``)
    T1  Pyrnova acquired / received it               (evidence ``retrieved_at``)
    T2  relevant identity/program/customer resolved  (relationship ``first_observed_at`` / knowability floor)
    T3  consequential assessment completed           (assessment time; deterministic-on-read defaults to T2)
    T4  customer-ready intelligence available         (customer material change ``delivered_at`` / ``first_relevant_at``)
    B   benchmark point at which the ordinary operating environment would reach materially
        equivalent consequential understanding        (NEVER fabricated; ``NOT_ESTABLISHED`` when unknown)

Derived latencies (days, non-negative; a negative span is surfaced as an anomaly, not hidden):

    acquisition_latency          = T1 - T0
    analysis_latency             = T3 - T1
    customer_readiness_latency   = T4 - T3
    external_decision_lead_time  = B  - T4   (how much earlier than the ordinary environment; needs B)

Every span is ``UNKNOWN`` when an endpoint is missing and ``NOT_ESTABLISHED`` for the external lead time
when B is not objectively available. Unknown never silently becomes zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

UNKNOWN = "UNKNOWN"
NOT_ESTABLISHED = "NOT_ESTABLISHED"


def _parse(value: Optional[str]) -> Optional[datetime]:
    if value in (None, "", UNKNOWN, NOT_ESTABLISHED):
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _span_days(start: Optional[str], end: Optional[str], *, missing: str = UNKNOWN):
    a, b = _parse(start), _parse(end)
    if a is None or b is None:
        return missing
    return round((b - a).total_seconds() / 86400.0, 2)


@dataclass(frozen=True)
class TemporalAnchors:
    """Point-in-time anchors, ISO-8601 strings; all optional. None ⇒ UNKNOWN downstream."""

    t0_source_available_at: Optional[str] = None
    t1_acquired_at: Optional[str] = None
    t2_resolved_at: Optional[str] = None
    t3_assessed_at: Optional[str] = None
    t4_customer_ready_at: Optional[str] = None
    benchmark_b: Optional[str] = None


def derive_decision_lead_time(anchors: TemporalAnchors) -> dict:
    """Return the canonical Decision Lead Time record derived from ``anchors``.

    ``assessment_deterministic`` (default True): when T3 is absent, the consequential assessment is
    deterministic-on-read, so it is treated as complete at T2 (or T1) — recorded explicitly via
    ``t3_source`` so the derivation is auditable rather than silently imputed.
    """
    t0, t1 = anchors.t0_source_available_at, anchors.t1_acquired_at
    t2 = anchors.t2_resolved_at
    t3, t3_source = anchors.t3_assessed_at, "explicit"
    if t3 is None:
        # Deterministic-on-read assessment: complete as soon as the inputs are resolvable.
        t3 = t2 or t1
        t3_source = "derived_from_T2" if t2 else ("derived_from_T1" if t1 else None)
        if t3 is None:
            t3_source = "unknown"
    t4 = anchors.t4_customer_ready_at
    b = anchors.benchmark_b

    acquisition = _span_days(t0, t1)
    analysis = _span_days(t1, t3)
    readiness = _span_days(t3, t4)
    internal = _span_days(t0, t4)  # total internal pipeline latency, T0 -> customer-ready
    external = _span_days(t4, b, missing=NOT_ESTABLISHED)

    anomalies = [
        name for name, val in (
            ("acquisition_latency", acquisition),
            ("analysis_latency", analysis),
            ("customer_readiness_latency", readiness),
        )
        if isinstance(val, (int, float)) and val < 0
    ]

    return {
        "anchors": {
            "T0_source_available_at": t0 or UNKNOWN,
            "T1_acquired_at": t1 or UNKNOWN,
            "T2_resolved_at": t2 or UNKNOWN,
            "T3_assessed_at": t3 or UNKNOWN,
            "T3_source": t3_source,
            "T4_customer_ready_at": t4 or UNKNOWN,
            "B_benchmark": b or NOT_ESTABLISHED,
        },
        "acquisition_latency_days": acquisition,
        "analysis_latency_days": analysis,
        "customer_readiness_latency_days": readiness,
        "internal_pipeline_latency_days": internal,
        "external_decision_lead_time_days": external,
        "external_lead_time_established": external != NOT_ESTABLISHED,
        "anomalies": anomalies,
    }


def from_customer_material_change(
    cmc: dict,
    *,
    acquired_at: Optional[str] = None,
    assessed_at: Optional[str] = None,
    benchmark_b: Optional[str] = None,
) -> dict:
    """Derive Decision Lead Time from an existing customer-material-change record.

    Reuses the record's first-seen semantics without adding persistence:
    ``intelligence_observed_at`` anchors T0/T2 (global knowability), ``delivered_at`` (falling back to
    ``first_relevant_at``) anchors T4. ``acquired_at`` (evidence ``retrieved_at``) and ``assessed_at``
    are supplied by the caller when available; ``benchmark_b`` is passed only when objectively known.
    """
    observed = cmc.get("intelligence_observed_at") or cmc.get("observed_at")
    delivered = cmc.get("delivered_at") or cmc.get("first_relevant_at")
    anchors = TemporalAnchors(
        t0_source_available_at=observed,
        t1_acquired_at=acquired_at,
        t2_resolved_at=observed,
        t3_assessed_at=assessed_at,
        t4_customer_ready_at=delivered,
        benchmark_b=benchmark_b,
    )
    return derive_decision_lead_time(anchors)
