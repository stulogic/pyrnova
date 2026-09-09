"""M16 — real event-stream selectivity harness.

The primary M16 question: *when a large batch of real events arrives, how few produce a credible threat
for a monitored company?* This harness runs the (unchanged) exposure + threat engine over a monitored
company set and reports the funnel:

    raw events -> exposure candidates -> accepted exposures -> threats emitted -> zero-threat rejections

A GOOD result is a large drop through that funnel: most events must NOT produce a threat for most
companies. The harness never lowers evidentiary standards to reduce noise — it measures the standards
that already exist. It makes no live calls; feed it archived bytes.
"""

from __future__ import annotations

from typing import Optional

from .threat import (
    assess_threats,
    declared_exposures,
    incumbency_exposures,
    sanctions_exposures,
    to_record,
)


def _build_exposures(subject: dict, designations: list[dict], as_of: Optional[str]):
    ref, name = subject["ref"], subject["name"]
    exposures, weak = [], []
    if subject.get("counterparty_records") and designations:
        exps, w = sanctions_exposures(ref, name, subject["counterparty_records"], designations,
                                      as_of=as_of)
        exposures += exps
        weak += w
    if subject.get("award_records"):
        exposures += incumbency_exposures(ref, name, subject.get("uei"), subject["award_records"],
                                          as_of=as_of)
    if subject.get("exposure_records"):
        exposures += declared_exposures(ref, name, subject["exposure_records"], as_of=as_of)
    return exposures, weak


def run_selectivity(
    monitored: list[dict],
    *,
    designations: Optional[list[dict]] = None,
    raw_event_count: Optional[int] = None,
    catalyst_records: Optional[list[dict]] = None,
    as_of: Optional[str] = None,
    stream_name: str = "event_stream",
) -> dict:
    """Run the selectivity funnel for one event stream against a monitored company set.

    ``raw_event_count`` is the size of the real event batch (e.g. number of OFAC designations). Each
    monitored subject may carry its own ``catalyst_records`` (adverse changes derived from the stream);
    ``catalyst_records`` here applies to every subject (a stream-wide event). Returns the funnel + the
    emitted threats/rejections for inspection.
    """
    designations = designations or []
    raw_events = raw_event_count if raw_event_count is not None else len(designations)

    confirmed = inferred = weak_total = 0
    all_threats, all_rejections = [], []
    per_company = []
    for subject in monitored:
        exposures, weak = _build_exposures(subject, designations, as_of)
        c = sum(1 for e in exposures if e.link_class == "CONFIRMED")
        i = sum(1 for e in exposures if e.link_class == "INFERRED")
        confirmed += c
        inferred += i
        weak_total += len(weak)
        cats = list(subject.get("catalyst_records", [])) + list(catalyst_records or [])
        threats, rejections = assess_threats(subject["ref"], subject["name"], exposures, cats,
                                             weak_candidates=weak, as_of=as_of)
        all_threats += threats
        all_rejections += rejections
        per_company.append({
            "ref": subject["ref"], "name": subject["name"],
            "confirmed_exposures": c, "inferred_exposures": i, "weak_candidates": len(weak),
            "threats": len(threats), "rejections": len(rejections),
        })

    exposure_candidates = confirmed + inferred + weak_total
    accepted = confirmed + inferred

    def rate(n, d):
        return round(n / d, 6) if d else None

    return {
        "stream": stream_name,
        "monitored_companies": len(monitored),
        "funnel": {
            "raw_events": raw_events,
            "exposure_candidates": exposure_candidates,
            "accepted_exposures": accepted,
            "rejected_weak_exposures": weak_total,
            "threats_emitted": len(all_threats),
            "zero_threat_rejections": len(all_rejections),
        },
        "threat_emission_rate": rate(len(all_threats), raw_events),
        "exposure_acceptance_rate": rate(accepted, exposure_candidates),
        "weak_rejection_rate": rate(weak_total, exposure_candidates),
        "deterministic_exposures": confirmed,
        "inferred_exposures": inferred,
        "per_company": per_company,
        "threats": [to_record(t) for t in all_threats],
        "rejections": [to_record(r) for r in all_rejections],
        "note": ("a good stream shows a large drop from raw_events to threats_emitted; most events must "
                 "produce no threat for most monitored companies"),
    }
