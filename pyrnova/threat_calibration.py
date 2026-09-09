"""M16 — threat calibration / evaluation semantics.

A minimal, durable framework for asking "were our threat warnings correct and useful?" WITHOUT
devolving into absence-as-falsehood. Three ORTHOGONAL quality axes are kept separate:

* DETECTION quality — was the threat real? (TRUE_THREAT / FALSE_ALERT / UNRESOLVED / INSUFFICIENT_EVIDENCE)
* EXPOSURE quality — was the linkage right? (CONFIRMED / INFERRED_CORRECT / INFERRED_INCORRECT /
  CANDIDATE_REJECTED / UNRESOLVED)
* OUTCOME quality — what actually happened? (the ``threat.THREAT_OUTCOME_LABELS`` vocabulary)

Hard rules (mirroring pyrnova.outcomes / M15):
- An UNRESOLVED threat is NEVER counted as a false alert.
- Success is never inferred merely because a feared outcome is absent; AVOIDED/MITIGATED require an
  explicit, dated, sourced observation (validated at ingestion in :mod:`pyrnova.threat`).
- The original prediction (severity/confidence at prediction time) is preserved by the caller; this
  module only reads it.
- Every rate is reported WITH its denominator; tiny samples carry an explicit warning.
"""

from __future__ import annotations

from datetime import date
from statistics import median
from typing import Optional

DETECTION_QUALITY = ("TRUE_THREAT", "FALSE_ALERT", "UNRESOLVED", "INSUFFICIENT_EVIDENCE")
EXPOSURE_QUALITY = ("CONFIRMED", "INFERRED_CORRECT", "INFERRED_INCORRECT", "CANDIDATE_REJECTED",
                    "UNRESOLVED")

# Outcome labels that confirm the threat thesis was real (whether or not it was ultimately avoided).
_REAL_THREAT_OUTCOMES = frozenset({"MATERIALIZED", "MITIGATED", "AVOIDED", "DELAYED", "EXPOSURE_ENDED"})


def classify_detection(outcome_label: Optional[str], confidence: Optional[str]) -> str:
    """Classify one threat's detection quality from its RESOLVED outcome + prediction-time confidence.

    A real threat that was mitigated/avoided/delayed is still a TRUE_THREAT (the warning was correct);
    only an explicit ``FALSE_ALARM`` observation is a FALSE_ALERT. With no resolved outcome, a low/unknown
    confidence threat is INSUFFICIENT_EVIDENCE, otherwise UNRESOLVED — never a false alert.
    """
    if outcome_label in _REAL_THREAT_OUTCOMES:
        return "TRUE_THREAT"
    if outcome_label == "FALSE_ALARM":
        return "FALSE_ALERT"
    # UNKNOWN / None
    if confidence in (None, "UNKNOWN", "LOW"):
        return "INSUFFICIENT_EVIDENCE"
    return "UNRESOLVED"


def classify_exposure(link_class: str, graded_correct: Optional[bool]) -> str:
    """Classify one exposure's quality. ``graded_correct`` is a reviewer/outcome judgement (or None).

    CONFIRMED (deterministic) exposures are self-evidencing. INFERRED exposures are correct/incorrect
    only where an explicit grading exists; ungraded stays UNRESOLVED. CANDIDATE/REJECTED weak links are
    CANDIDATE_REJECTED.
    """
    if link_class == "CONFIRMED":
        return "CONFIRMED"
    if link_class in ("CANDIDATE", "REJECTED"):
        return "CANDIDATE_REJECTED"
    if link_class == "INFERRED":
        if graded_correct is True:
            return "INFERRED_CORRECT"
        if graded_correct is False:
            return "INFERRED_INCORRECT"
        return "UNRESOLVED"
    return "UNRESOLVED"


def _days_between(a: Optional[str], b: Optional[str]) -> Optional[int]:
    """Whole days from ISO date ``a`` (threat first knowable) to ``b`` (outcome observed). None if either
    is missing/unparseable or the span is negative."""
    def _d(v):
        try:
            return date.fromisoformat(str(v)[:10])
        except (TypeError, ValueError):
            return None
    da, db = _d(a), _d(b)
    if da is None or db is None:
        return None
    delta = (db - da).days
    return delta if delta >= 0 else None


def calibrate_threats(results: list[dict]) -> dict:
    """Aggregate detection/outcome calibration over threat-case results (from ``run_threat_case``).

    Only cases carrying a resolved outcome contribute to precision; the denominator is reported beside
    every rate. Lead time is the median span from a threat's ``available_at`` (first knowable) to its
    outcome's ``observed_at``, where both exist.
    """
    graded = []          # (detection_quality, outcome_label, threat)
    lead_times = []
    for r in results:
        outcome = r.get("outcome") or {}
        label = outcome.get("label")
        if not r.get("threats"):
            continue
        threat = r["threats"][0]
        detection = classify_detection(label, threat.get("confidence"))
        if outcome.get("resolved"):
            graded.append((detection, label, threat))
            observed_at = (outcome.get("basis") or {}).get("observed_at")
            lt = _days_between(threat.get("available_at"), observed_at)
            if lt is not None:
                lead_times.append(lt)

    resolved_n = len(graded)
    true_threats = sum(1 for d, _, _ in graded if d == "TRUE_THREAT")
    false_alerts = sum(1 for d, _, _ in graded if d == "FALSE_ALERT")
    materialized = sum(1 for _, lbl, _ in graded if lbl == "MATERIALIZED")
    mitig_avoided = sum(1 for _, lbl, _ in graded if lbl in ("MITIGATED", "AVOIDED"))
    all_threats = [t for r in results for t in r["threats"]]
    unresolved = sum(1 for r in results if r["threats"]
                     and not (r.get("outcome") or {}).get("resolved"))

    def rate(n, d):
        return round(n / d, 4) if d else None

    precision_denominator = true_threats + false_alerts
    return {
        "threats_total": len(all_threats),
        "resolved_outcomes": resolved_n,
        "detection_distribution": {q: sum(1 for d, _, _ in graded if d == q) for q in DETECTION_QUALITY
                                   if any(d == q for d, _, _ in graded)},
        "confirmed_threat_precision": rate(true_threats, precision_denominator),
        "confirmed_threat_precision_denominator": precision_denominator,
        "unresolved_threats": unresolved,
        "unresolved_rate": rate(unresolved, len(all_threats)),
        "materialization_rate": rate(materialized, resolved_n),
        "materialization_denominator": resolved_n,
        "mitigation_or_avoidance_rate": rate(mitig_avoided, resolved_n),
        "median_lead_time_days": median(lead_times) if lead_times else None,
        "lead_time_sample": len(lead_times),
        "false_alert_from_absence": 0,  # invariant: absence never becomes a false alert
        "small_sample_warning": (
            "threat calibration rests on very few resolved outcomes; precision is directional, not a "
            "stable rate" if resolved_n < 20 else None),
    }


def _evidence_family(evidence_id: str) -> str:
    """Coarse source-family bucket from an evidence id (the token before the first ':')."""
    token = str(evidence_id).split(":", 1)[0].strip().lower()
    return token or "unknown"


def threat_quality_over_time(results: list[dict]) -> dict:
    """M17 — durable threat-quality aggregates derived from append-only predictions + later outcomes.

    Answers, over time and WITHOUT mutating any original prediction: how many warnings were issued,
    resolved, materialized, mitigated/avoided, delayed, false-alerted, or remain unresolved; the median
    lead time; per-mechanism reliability (precision reported only WITH its denominator); and which source
    families contribute *useful* (resolved-true) warning signal. Absence is never a false alert.
    """
    per_mech: dict[str, dict[str, int]] = {}
    family_useful: dict[str, int] = {}
    family_total: dict[str, int] = {}
    lead_times = []
    issued = resolved = materialized = mitig_avoided = delayed = false_alerts = true_threats = 0

    for r in results:
        if not r.get("threats"):
            continue
        threat = r["threats"][0]
        issued += 1
        mech = threat.get("mechanism", "UNKNOWN")
        outcome = r.get("outcome") or {}
        label = outcome.get("label")
        detection = classify_detection(label, threat.get("confidence"))
        families = {_evidence_family(e) for e in (threat.get("evidence_ids") or [])} or {"unknown"}
        for fam in families:
            family_total[fam] = family_total.get(fam, 0) + 1

        mrec = per_mech.setdefault(mech, {"issued": 0, "resolved": 0, "true": 0, "false": 0})
        mrec["issued"] += 1
        if not outcome.get("resolved"):
            continue
        resolved += 1
        mrec["resolved"] += 1
        if detection == "TRUE_THREAT":
            true_threats += 1
            mrec["true"] += 1
            for fam in families:
                family_useful[fam] = family_useful.get(fam, 0) + 1
        elif detection == "FALSE_ALERT":
            false_alerts += 1
            mrec["false"] += 1
        if label == "MATERIALIZED":
            materialized += 1
        elif label in ("MITIGATED", "AVOIDED"):
            mitig_avoided += 1
        elif label == "DELAYED":
            delayed += 1
        observed_at = (outcome.get("basis") or {}).get("observed_at")
        lt = _days_between(threat.get("available_at"), observed_at)
        if lt is not None:
            lead_times.append(lt)

    def rate(n, d):
        return round(n / d, 4) if d else None

    mechanism_reliability = {
        mech: {
            "issued": v["issued"], "resolved": v["resolved"],
            "confirmed_precision": rate(v["true"], v["true"] + v["false"]),
            "precision_denominator": v["true"] + v["false"],
        }
        for mech, v in sorted(per_mech.items())
    }
    source_contribution = {
        fam: {"threats_backed": family_total[fam],
              "resolved_true_backed": family_useful.get(fam, 0)}
        for fam in sorted(family_total)
    }
    return {
        "warnings_issued": issued,
        "resolved": resolved,
        "unresolved": issued - resolved,
        "materialized": materialized,
        "mitigated_or_avoided": mitig_avoided,
        "delayed": delayed,
        "false_alerts": false_alerts,
        "confirmed_true": true_threats,
        "resolution_rate": rate(resolved, issued),
        "confirmed_precision": rate(true_threats, true_threats + false_alerts),
        "confirmed_precision_denominator": true_threats + false_alerts,
        "median_lead_time_days": median(lead_times) if lead_times else None,
        "lead_time_sample": len(lead_times),
        "mechanism_reliability": mechanism_reliability,
        "source_family_contribution": source_contribution,
        "false_alert_from_absence": 0,
        "small_sample_warning": (
            "threat-quality rates rest on few resolved outcomes; treat per-mechanism precision as "
            "directional" if resolved < 20 else None),
    }
