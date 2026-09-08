"""Deterministic empirical metrics for replay and human adjudication."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median

from .state import StateStore

BANDS = ((0.90, 1.01, "0.90-1.00"), (0.80, 0.90, "0.80-0.89"), (0.70, 0.80, "0.70-0.79"), (0.60, 0.70, "0.60-0.69"), (0.50, 0.60, "0.50-0.59"), (0.0, 0.50, "below-0.50"))


def _rate(numerator: int, denominator: int):
    return round(numerator / denominator, 4) if denominator else None


def _known_positive(record: dict) -> bool | None:
    label = (record.get("ground_truth") or {}).get("label")
    return True if label == "TRUE_POSITIVE" else False if label == "TRUE_NEGATIVE" else None


def summarize_results(results: list[dict], reviews: list[dict] | None = None, duplicate_rate=None) -> dict:
    results = sorted(results, key=lambda r: (r.get("case_id", ""), r.get("scoring_version", "")))
    strikes = [r for r in results if r.get("system_disposition") == "STRIKE"]
    watches = [r for r in results if r.get("system_disposition") == "WATCH"]
    rejects = [r for r in results if r.get("system_disposition") == "REJECT"]
    known = [r for r in results if _known_positive(r) is not None]
    positives = [r for r in known if _known_positive(r)]
    negatives = [r for r in known if not _known_positive(r)]
    false_positives = [r for r in strikes if _known_positive(r) is False]
    false_negatives = [r for r in rejects if _known_positive(r) is True]
    true_strikes = [r for r in strikes if _known_positive(r) is True]

    evidence_levels, source_families, source_roles = Counter(), Counter(), Counter()
    for result in results:
        for evidence in result.get("visible_evidence", []):
            evidence_levels[str(evidence.get("strength"))] += 1
            source_families[evidence.get("source_id", "unknown")] += 1
            source_roles[evidence.get("source_role", "unknown")] += 1

    calibration = []
    for low, high, label in BANDS:
        rows = [r for r in known if low <= float(r.get("score", 0)) < high]
        calibration.append({"band": label, "cases": len(rows), "observed_positive_rate": _rate(sum(_known_positive(r) is True for r in rows), len(rows))})

    lead_by_mechanism = defaultdict(list)
    for result in results:
        if result.get("lead_time_days") is not None:
            lead_by_mechanism[result["mechanism_family"]].append(result["lead_time_days"])
    mechanism_diagnostics = {}
    for mechanism in sorted({r.get("mechanism_family") for r in results}):
        rows = [r for r in results if r.get("mechanism_family") == mechanism]
        mechanism_diagnostics[mechanism] = {
            "cases": len(rows),
            "strike_precision": _rate(sum(r.get("system_disposition") == "STRIKE" and _known_positive(r) is True for r in rows), sum(r.get("system_disposition") == "STRIKE" and _known_positive(r) is not None for r in rows)),
            "watch_conversion": _rate(sum(r.get("system_disposition") == "WATCH" and _known_positive(r) is True for r in rows), sum(r.get("system_disposition") == "WATCH" and _known_positive(r) is not None for r in rows)),
            "median_lead_time_days": median(lead_by_mechanism[mechanism]) if lead_by_mechanism[mechanism] else None,
        }

    reviews = list(reviews or [])
    corpus_reviews = [
        {**r["human_adjudication"], "system_disposition": r.get("system_disposition"), "case_id": r.get("case_id"), "ground_truth": r.get("ground_truth")}
        for r in results if r.get("human_adjudication")
    ]
    reviews.extend(corpus_reviews)
    decisions = Counter(r.get("human_decision") for r in reviews if r.get("human_decision"))
    overrides = sum(
        (r.get("human_decision") == "ACCEPT" and r.get("system_disposition") != "STRIKE")
        or (r.get("human_decision") == "REJECT" and r.get("system_disposition") != "REJECT")
        or (r.get("human_decision") == "WATCH" and r.get("system_disposition") != "WATCH")
        for r in reviews
    )
    model_closer = human_closer = ties = 0
    for review in corpus_reviews:
        positive = True if (review.get("ground_truth") or {}).get("label") == "TRUE_POSITIVE" else False if (review.get("ground_truth") or {}).get("label") == "TRUE_NEGATIVE" else None
        if positive is None:
            continue
        model_correct = (review.get("system_disposition") == "STRIKE") if positive else (review.get("system_disposition") == "REJECT")
        human_disposition = {"ACCEPT": "STRIKE", "WATCH": "WATCH", "REJECT": "REJECT"}.get(review.get("human_decision"))
        human_correct = (human_disposition == "STRIKE") if positive else (human_disposition == "REJECT")
        if model_correct == human_correct:
            ties += 1
        elif model_correct:
            model_closer += 1
        else:
            human_closer += 1
    values = [r for r in results if r.get("value_error_usd") is not None]
    value_by_mechanism = {}
    for mechanism in sorted({r["mechanism_family"] for r in values}):
        rows = [r for r in values if r["mechanism_family"] == mechanism]
        bias = sum(r["value_error_usd"] for r in rows) / len(rows)
        value_by_mechanism[mechanism] = {
            "cases": len(rows),
            "mean_error_usd": round(bias, 2),
            "bias": "overestimate" if bias > 0 else "underestimate" if bias < 0 else "unbiased",
        }
    measured_duplicate_rate = duplicate_rate
    if measured_duplicate_rate is None:
        measured_duplicate_rate = _rate(len(results) - len({(r.get("case_id"), r.get("scoring_version")) for r in results}), len(results))
    return {
        "case_count": len(results),
        "mechanism_family_count": len({r.get("mechanism_family") for r in results}),
        "ground_truth_distribution": dict(sorted(Counter((r.get("ground_truth") or {}).get("label", "UNKNOWN") for r in results).items())),
        "confusion_matrix": {"true_strike": len(true_strikes), "false_strike": len(false_positives), "true_reject": sum(r.get("system_disposition") == "REJECT" and _known_positive(r) is False for r in known), "false_reject": len(false_negatives), "watch_positive": sum(r.get("system_disposition") == "WATCH" and _known_positive(r) is True for r in known), "watch_negative": sum(r.get("system_disposition") == "WATCH" and _known_positive(r) is False for r in known)},
        "strike_precision": _rate(len(true_strikes), len([r for r in strikes if _known_positive(r) is not None])),
        "watch_conversion_rate": _rate(sum(_known_positive(r) is True for r in watches), len([r for r in watches if _known_positive(r) is not None])),
        "watch_conversion": _rate(sum(_known_positive(r) is True for r in watches), len([r for r in watches if _known_positive(r) is not None])),
        "watch_rejection_rate": _rate(sum(_known_positive(r) is False for r in watches), len([r for r in watches if _known_positive(r) is not None])),
        "false_positive_rate": _rate(len(false_positives), len(negatives)),
        "false_negative_rate": _rate(len(false_negatives), len(positives)),
        "human_adjudications": len(reviews),
        "human_acceptance_rate": _rate(decisions["ACCEPT"], len(reviews)),
        "human_override_rate": _rate(overrides, len(reviews)),
        "human_decisions": dict(sorted(decisions.items())),
        "model_vs_human": {"model_closer": model_closer, "human_closer": human_closer, "ties": ties},
        "rejection_reason_distribution": dict(sorted(Counter(reason for r in results for reason in r.get("failure_reasons", [])).items())),
        "duplicate_opportunity_rate": measured_duplicate_rate,
        "evidence_level_contribution": dict(sorted(evidence_levels.items())),
        "source_family_contribution": dict(sorted(source_families.items())),
        "primary_vs_secondary_contribution": dict(sorted(source_roles.items())),
        "mean_corroboration_count": round(sum(r.get("corroboration_count", 0) for r in results) / len(results), 3) if results else None,
        "contradiction_frequency": _rate(sum(r.get("contradiction_count", 0) > 0 for r in results), len(results)),
        "median_lead_time_days": median([r["lead_time_days"] for r in results if r.get("lead_time_days") is not None]) if any(r.get("lead_time_days") is not None for r in results) else None,
        "median_lead_time_by_mechanism": {k: median(v) for k, v in sorted(lead_by_mechanism.items())},
        "lead_time_vs_confidence": [{"case_id": r["case_id"], "lead_time_days": r.get("lead_time_days"), "ground_truth_confidence": (r.get("ground_truth") or {}).get("confidence")} for r in results if r.get("lead_time_days") is not None],
        "lead_time_vs_eventual_value": [{"case_id": r["case_id"], "lead_time_days": r.get("lead_time_days"), "actual_value_usd": (r.get("actual_outcome") or {}).get("actual_value_usd")} for r in results if r.get("lead_time_days") is not None and (r.get("actual_outcome") or {}).get("actual_value_usd") is not None],
        "calibration": calibration,
        "estimated_vs_actual_value": [{"case_id": r["case_id"], "estimated": r.get("predicted_value_usd"), "actual": (r.get("actual_outcome") or {}).get("actual_value_usd"), "error_usd": r.get("value_error_usd"), "error_percentage": r.get("value_error_percentage")} for r in values],
        "value_bias_usd": round(sum(r["value_error_usd"] for r in values) / len(values), 2) if values else None,
        "value_calibration_by_mechanism": value_by_mechanism,
        "watch_analysis": {"converted": sum(bool(r.get("watch_conversion")) for r in watches), "rejected": sum(bool(r.get("watch_rejection")) for r in watches), "median_duration_days": median([r["watch_duration_days"] for r in watches if r.get("watch_duration_days") is not None]) if any(r.get("watch_duration_days") is not None for r in watches) else None, "transition_evidence": dict(sorted(Counter(item for r in watches for item in r.get("watch_transition_evidence", [])).items()))},
        "mechanism_diagnostics": mechanism_diagnostics,
    }


def evaluation_snapshot(store: StateStore, scoring_version: str | None = None) -> dict:
    latest_human = {}
    for review in store.read("reviews"):
        if review.get("human_decision"):
            latest_human[review["opportunity_id"]] = review
    latest_replay = {}
    for result in store.read("replay_results"):
        version = result.get("scoring_version", "legacy")
        if scoring_version is None or version == scoring_version:
            latest_replay[(result.get("case_id"), version)] = result
    scoreboard = list(store.read("scoreboard"))
    dup = sum(float(e.get("value", 0)) for e in scoreboard if e.get("metric") == "duplicate_opportunities")
    candidates = sum(float(e.get("value", 0)) for e in scoreboard if e.get("metric") == "candidate_opportunities") + dup
    return summarize_results(list(latest_replay.values()), list(latest_human.values()), _rate(int(dup), int(candidates)))
