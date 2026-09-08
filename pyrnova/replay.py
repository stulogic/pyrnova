"""Deterministic, versioned point-in-time replay evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from .state import StateStore

GROUND_TRUTH_LABELS = {"TRUE_POSITIVE", "TRUE_NEGATIVE", "PARTIAL", "AMBIGUOUS"}
MECHANISM_FAMILIES = {"procurement", "grants_industrial_policy", "regulation_compliance", "capex_expansion", "disruption_distress", "technology_migration"}
FAILURE_REASONS = {"broad_topical_match", "weak_buyer_specificity", "no_budget_evidence", "no_procurement_mechanism", "expired_stale", "duplicate", "enrichment_only", "incumbent_lock_in", "no_actionable_commercial_path", "low_capability_relevance", "policy_without_funding", "funding_without_executable_demand", "speculative_causality", "future_evidence_leakage", "contradictory_evidence", "insufficient_source_authority"}


@dataclass(frozen=True)
class ScoringPolicy:
    version: str
    evidence_policy_version: str
    threshold_version: str
    mechanism_rule_version: str
    strike_threshold: float = 0.30
    watch_threshold: float = 0.15


SCORING_POLICIES = {
    "scoring_v1": ScoringPolicy("scoring_v1", "evidence_v1", "thresholds_v1", "mechanisms_v1"),
    # Evaluation-only challenger; it changes no production behavior.
    "scoring_v1_stricter_candidate": ScoringPolicy("scoring_v1_stricter_candidate", "evidence_v1", "thresholds_strike_040_candidate", "mechanisms_v1", strike_threshold=0.40),
    "scoring_v2_candidate": ScoringPolicy("scoring_v2_candidate", "evidence_v1", "thresholds_strike_080_candidate", "mechanisms_v1", strike_threshold=0.80),
}
ACTIVE_SCORING_VERSION = "scoring_v1"


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {value}")
    return parsed


def _stable_id(payload: dict, length: int = 20) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:length]


def validate_case(case: dict, *, require_quality: bool = False) -> None:
    required = {"case_id", "mechanism_family", "replay_as_of", "records", "candidate", "expected_affected_entities", "expected_buyer_program_owner", "expected_commercial_mechanism", "actual_outcome", "expected_disposition", "ground_truth", "reviewer"}
    missing = sorted(required - set(case))
    if missing:
        raise ValueError(f"{case.get('case_id', '<unknown>')}: missing {', '.join(missing)}")
    if case["mechanism_family"] not in MECHANISM_FAMILIES:
        raise ValueError(f"{case['case_id']}: unknown mechanism family")
    _dt(case["replay_as_of"])
    if case["expected_disposition"] not in {"STRIKE", "WATCH", "REJECT"}:
        raise ValueError(f"{case['case_id']}: invalid expected disposition")
    truth = case["ground_truth"]
    if truth.get("label") not in GROUND_TRUTH_LABELS or truth.get("confidence") not in {"HIGH", "MEDIUM", "LOW"}:
        raise ValueError(f"{case['case_id']}: invalid ground truth")
    if not str(case["reviewer"]).strip():
        raise ValueError(f"{case['case_id']}: reviewer is required")
    if require_quality and not case["records"]:
        raise ValueError(f"{case['case_id']}: at least one evidence record is required")
    refs = set()
    for record in case["records"]:
        for key in ("source_id", "source_ref", "record_kind"):
            if not record.get(key):
                raise ValueError(f"{case['case_id']}: evidence missing {key}")
        if require_quality and (not record.get("available_at") or not record.get("source_role")):
            raise ValueError(f"{case['case_id']}: canonical evidence requires available_at and source_role")
        if require_quality and (record.get("source_role") not in {"primary", "secondary"} or not record.get("url")):
            raise ValueError(f"{case['case_id']}: canonical evidence requires source role and URL")
        if record.get("available_at"):
            _dt(record["available_at"])
        if record["source_ref"] in refs:
            raise ValueError(f"{case['case_id']}: duplicate source_ref {record['source_ref']}")
        refs.add(record["source_ref"])
        if not 1 <= int(record.get("strength", 0)) <= 5:
            raise ValueError(f"{case['case_id']}: evidence strength must be 1..5")
    for reason in case.get("failure_reasons", []):
        if reason not in FAILURE_REASONS:
            raise ValueError(f"{case['case_id']}: unknown failure reason {reason}")
    if require_quality:
        cutoff = _dt(case["replay_as_of"])
        if not any(_dt(r["available_at"]) <= cutoff for r in case["records"]):
            raise ValueError(f"{case['case_id']}: no known-at-cutoff evidence")
        if not any(_dt(r["available_at"]) > cutoff for r in case["records"]):
            raise ValueError(f"{case['case_id']}: no explicit excluded future evidence")
        adjudication = case.get("human_adjudication") or {}
        if adjudication.get("human_decision") not in {"ACCEPT", "WATCH", "REJECT"} or not adjudication.get("reviewer") or not adjudication.get("reason"):
            raise ValueError(f"{case['case_id']}: complete human adjudication is required")
        outcome = case["actual_outcome"]
        if "occurred" not in outcome or not outcome.get("kind") or not outcome.get("source_ref"):
            raise ValueError(f"{case['case_id']}: documented later outcome is required")
        if outcome.get("occurred") and not outcome.get("occurred_at"):
            raise ValueError(f"{case['case_id']}: occurred outcome requires actual timing")
        if case["ground_truth"]["label"] in {"PARTIAL", "AMBIGUOUS"} and not case.get("ambiguity_notes"):
            raise ValueError(f"{case['case_id']}: uncertain labels require ambiguity notes")


def visible_records(records: list[dict], replay_as_of: str) -> list[dict]:
    """Exclude records without proven availability and all records from the future."""
    cutoff = _dt(replay_as_of)
    visible = [r for r in records if r.get("available_at") and _dt(r["available_at"]) <= cutoff]
    return sorted(visible, key=lambda r: (r["available_at"], r["source_id"], r["source_ref"]))


def _actual_positive(case: dict) -> bool | None:
    label = case["ground_truth"]["label"]
    return True if label == "TRUE_POSITIVE" else False if label == "TRUE_NEGATIVE" else None


def run_replay(case: dict, *, store: Optional[StateStore] = None, scoring_version: str = ACTIVE_SCORING_VERSION) -> dict:
    validate_case(case)
    try:
        policy = SCORING_POLICIES[scoring_version]
    except KeyError as exc:
        raise ValueError(f"unknown scoring version: {scoring_version}") from exc
    replay_as_of = case["replay_as_of"]
    visible = visible_records(case["records"], replay_as_of)
    applicable = [r for r in visible if r.get("applies_to_candidate")]
    candidate = case["candidate"]
    relevance = float(candidate.get("relevance", 0))
    strongest = max((int(r.get("strength", 0)) for r in applicable), default=0)
    score = round(relevance * (strongest / 5.0), 3)
    direct_opportunity = any(r.get("record_kind") == "solicitation" for r in applicable)
    if direct_opportunity and score >= policy.strike_threshold:
        disposition = "STRIKE"
    elif score >= policy.watch_threshold:
        disposition = "WATCH"
    else:
        disposition = "REJECT"
    outcome = case.get("actual_outcome") or {}
    actual_positive = _actual_positive(case)
    predicted_buyer, actual_buyer = candidate.get("predicted_buyer"), outcome.get("buyer")
    directionally_correct = None if actual_positive is None else bool(actual_positive and predicted_buyer and actual_buyer and predicted_buyer.casefold() == actual_buyer.casefold())
    lead_time_days = ((_dt(outcome["occurred_at"]).date() - _dt(replay_as_of).date()).days if outcome.get("occurred") and outcome.get("occurred_at") else None)
    estimated, actual_value = candidate.get("predicted_value_usd"), outcome.get("actual_value_usd")
    value_error = estimated - actual_value if isinstance(estimated, (int, float)) and isinstance(actual_value, (int, float)) else None
    excluded = [r for r in case["records"] if r not in visible]
    basis = {"case_id": case["case_id"], "replay_as_of": replay_as_of, "visible_refs": [r["source_ref"] for r in visible], "candidate": candidate, "scoring_version": policy.version}
    result = {
        "id": _stable_id(basis), "case_id": case["case_id"], "mechanism_family": case["mechanism_family"], "replay_as_of": replay_as_of,
        "scoring_version": policy.version, "evidence_policy_version": policy.evidence_policy_version, "threshold_version": policy.threshold_version, "mechanism_rule_version": policy.mechanism_rule_version,
        "visible_evidence": [{"source_id": r["source_id"], "source_ref": r["source_ref"], "available_at": r["available_at"], "strength": r["strength"], "source_role": r.get("source_role", "unknown"), "record_kind": r["record_kind"], "contradicts": bool(r.get("contradicts")), "url": r.get("url")} for r in visible],
        "excluded_future_records": [{"source_id": r["source_id"], "source_ref": r["source_ref"], "available_at": r.get("available_at")} for r in sorted(excluded, key=lambda r: (r.get("available_at") or "", r["source_ref"]))],
        "future_evidence_excluded": len(excluded), "hypothesis": candidate["hypothesis"], "score": score, "system_disposition": disposition, "expected_disposition": case["expected_disposition"], "disposition_matches_expected": disposition == case["expected_disposition"],
        "predicted_buyer": predicted_buyer, "predicted_timing": candidate.get("predicted_timing"), "predicted_value_usd": estimated, "actual_outcome": outcome, "ground_truth": case["ground_truth"], "reviewer": case["reviewer"], "ambiguity_notes": case.get("ambiguity_notes", ""),
        "human_adjudication": case.get("human_adjudication"),
        "lead_time_days": lead_time_days, "directionally_correct": directionally_correct, "false_positive": disposition == "STRIKE" and actual_positive is False, "false_negative": disposition == "REJECT" and actual_positive is True, "watch_conversion": disposition == "WATCH" and actual_positive is True, "watch_rejection": disposition == "WATCH" and actual_positive is False,
        "watch_duration_days": case.get("watch_duration_days"), "watch_transition": case.get("watch_transition"), "watch_transition_evidence": case.get("watch_transition_evidence", []), "failure_reasons": sorted(case.get("failure_reasons", [])),
        "corroboration_count": max(0, len(applicable) - 1), "contradiction_count": sum(bool(r.get("contradicts")) for r in visible), "value_error_usd": value_error, "value_error_percentage": round(value_error / actual_value * 100, 2) if value_error is not None and actual_value else None,
    }
    if store:
        store.append("replay_results", result)
    return result


def run_chain_replay(case: dict, *, scoring_version: str = ACTIVE_SCORING_VERSION,
                     store: Optional[StateStore] = None) -> dict:
    """Reconstruct the cross-source capital chain for a case and validate any ``expected_chain``.

    Chain reconstruction is retrospective: it links every source-native signal in the case, but each
    relationship carries its own ``first_observed_at`` so the earliest knowable time of every link is
    explicit. Disposition transitions are derived strictly point-in-time from the existing scoring
    policy and never see evidence beyond a given cutoff.
    """
    from .chains import resolve_chain, signals_from_records
    from .transitions import derive_transitions, transition_summary

    validate_case(case)
    signals = signals_from_records(case["records"])
    resolution = resolve_chain(signals)
    transitions = derive_transitions(case, scoring_version=scoring_version, subject_id=case["case_id"])
    metrics = resolution.metrics()

    # Uncertain inferred joins are queued for human review, not linked (M6).
    if store is not None and resolution.deferred:
        from .review_queue import enqueue_deferred

        for deferred_join in resolution.deferred:
            enqueue_deferred(store, deferred_join.to_queue_record())

    outcome = case.get("actual_outcome") or {}
    first_signal_at = min((s.available_at for s in resolution.signals if s.available_at), default=None)
    chain_lead_time_days = None
    if first_signal_at and outcome.get("occurred") and outcome.get("occurred_at"):
        chain_lead_time_days = (_dt(outcome["occurred_at"]).date() - _dt(first_signal_at).date()).days

    checks = _check_expected_chain(case.get("expected_chain"), resolution, transitions)
    result = {
        "case_id": case["case_id"],
        "mechanism_family": case["mechanism_family"],
        "scoring_version": scoring_version,
        "chain_metrics": metrics,
        "relationships": [
            {"subject": r.subject_id, "predicate": r.predicate, "object": r.object_id,
             "join_method": r.join_method, "confidence": r.confidence,
             "first_observed_at": r.first_observed_at, "rationale": r.rationale}
            for r in resolution.relationships
        ],
        "rejected_joins": [{"reason": j.reason, "detail": j.detail} for j in resolution.rejected],
        "deferred_joins": [
            {"relationship_id": d.relationship_id, "predicate": d.predicate,
             "confidence": d.confidence, "rationale": d.rationale,
             "first_observed_at": d.first_observed_at} for d in resolution.deferred
        ],
        "entity_relationships": [
            {"subject": r.subject_id, "predicate": r.predicate, "object": r.object_id,
             "join_method": r.join_method, "confidence": r.confidence,
             "first_observed_at": r.first_observed_at, "rationale": r.rationale}
            for r in resolution.entity_relationships
        ],
        "ground_truth": case.get("ground_truth"),
        "transitions": transition_summary(transitions),
        "chain_lead_time_days": chain_lead_time_days,
        "expected_chain_checks": checks,
        "expected_chain_ok": all(c["ok"] for c in checks) if checks else None,
    }
    if store:
        store.append("chain_replay_results", result)
    return result


def run_consequence_replay(case: dict, *, scoring_version: str = ACTIVE_SCORING_VERSION,
                           store: Optional[StateStore] = None) -> dict:
    """Derive capital catalysts and commercial consequences for a case and validate any
    ``expected_consequences``. Retrospective chain reconstruction with per-consequence
    ``first_supportable_at``; never creates a candidate or changes ``scoring_v1``."""
    from .catalysts import build_catalysts_and_consequences
    from .chains import resolve_chain, signals_from_records

    validate_case(case)
    resolution = resolve_chain(signals_from_records(case["records"]))
    catalysts, consequences = build_catalysts_and_consequences(case["records"], resolution)

    staged_keys = {r["program_key"] for r in case["records"] if r.get("program_key") and r.get("stage")}
    scoring = run_replay(case, scoring_version=scoring_version)
    checks = _check_expected_consequences(case.get("expected_consequences"), catalysts, consequences)
    result = {
        "case_id": case["case_id"],
        "mechanism_family": case["mechanism_family"],
        "scoring_version": scoring_version,
        "ground_truth": case.get("ground_truth"),
        "scoring_disposition": scoring["system_disposition"],
        "catalysts": [to_record_safe(c) for c in catalysts],
        "consequences": [to_record_safe(c) for c in consequences],
        "catalyst_count": len(catalysts),
        "consequence_count": len(consequences),
        "program_keys": sorted(staged_keys),
        "duplicate_catalysts_collapsed": max(0, len(staged_keys) - len(catalysts)) if catalysts else 0,
        "expected_consequence_checks": checks,
        "expected_consequence_ok": all(c["ok"] for c in checks) if checks else None,
        "outcome_occurred_at": (case.get("actual_outcome") or {}).get("occurred_at"),
    }
    if store is not None:
        from .catalysts import persist
        persist(store, catalysts, consequences)
        store.append("consequence_replay_results", {k: v for k, v in result.items()
                                                    if k not in ("catalysts", "consequences")})
    return result


def to_record_safe(obj) -> dict:
    from .models import to_record
    return to_record(obj)


def _check_expected_consequences(expected: dict | None, catalysts, consequences) -> list[dict]:
    if not expected:
        return []
    checks: list[dict] = []

    def check(name, ok, got, want):
        checks.append({"check": name, "ok": bool(ok), "got": got, "want": want})

    mechanisms = sorted({c.mechanism for c in consequences})
    directness = sorted({c.directness for c in consequences})
    roles = sorted({p["role"] for c in consequences for p in c.participants})
    dispositions = sorted({c.screened_disposition for c in consequences})
    if "catalyst_count" in expected:
        check("catalyst_count", len(catalysts) == expected["catalyst_count"], len(catalysts), expected["catalyst_count"])
    if "catalyst_type" in expected:
        got = sorted({c.catalyst_type for c in catalysts})
        check("catalyst_type", expected["catalyst_type"] in got, got, expected["catalyst_type"])
    if "min_consequences" in expected:
        check("min_consequences", len(consequences) >= expected["min_consequences"], len(consequences), expected["min_consequences"])
    if "max_consequences" in expected:
        check("max_consequences", len(consequences) <= expected["max_consequences"], len(consequences), expected["max_consequences"])
    if "mechanisms" in expected:
        check("mechanisms", set(expected["mechanisms"]) <= set(mechanisms), mechanisms, sorted(expected["mechanisms"]))
    if "directness" in expected:
        check("directness", set(expected["directness"]) <= set(directness), directness, sorted(expected["directness"]))
    if "roles" in expected:
        check("roles", set(expected["roles"]) <= set(roles), roles, sorted(expected["roles"]))
    if "require_capability" in expected and expected["require_capability"]:
        got = all(c.capability_classes for c in consequences if c.screened_disposition == "STRIKE")
        check("require_capability", got and bool(consequences), got, True)
    if "value_status" in expected:
        got = sorted({c.value.get("status") for c in consequences})
        check("value_status", set(expected["value_status"]) <= set(got), got, sorted(expected["value_status"]))
    if "screened_dispositions" in expected:
        check("screened_dispositions", set(expected["screened_dispositions"]) <= set(dispositions),
              dispositions, sorted(expected["screened_dispositions"]))
    if "expect_rejected" in expected:
        got = any(c.screened_disposition == "REJECT" for c in consequences)
        check("expect_rejected", got == expected["expect_rejected"], got, expected["expect_rejected"])
    return checks


def run_consequence_corpus(cases: Iterable[dict], *, scoring_version: str = ACTIVE_SCORING_VERSION,
                           store: Optional[StateStore] = None) -> list[dict]:
    selected = [c for c in cases if any(r.get("program_key") and r.get("stage") for r in c["records"])]
    return [run_consequence_replay(c, scoring_version=scoring_version, store=store) for c in selected]


def summarize_consequence_results(results: list[dict]) -> dict:
    """Commercial-consequence observability across the corpus (no scoring impact)."""
    from statistics import median

    catalysts = [c for r in results for c in r["catalysts"]]
    consequences = [c for r in results for c in r["consequences"]]
    label_by_case = {r["case_id"]: (r.get("ground_truth") or {}).get("label") for r in results}
    # Precision is graded only where a case declares consequence-level ground truth. A case whose label
    # is about join-correctness (e.g. an M6 false-join case) is not a verdict on whether an individual
    # record carries commercial merit, so it must not be scored as a false consequence.
    graded_cases = {r["case_id"] for r in results if r.get("expected_consequence_ok") is not None}
    case_of = {}
    for r in results:
        for c in r["consequences"]:
            case_of[id(c)] = r["case_id"]

    def has_role(c, roles):
        return any(p["role"] in roles for p in c.get("participants", []))

    directness_dist = {d: sum(c["directness"] == d for c in consequences)
                       for d in ("DIRECT", "DOWNSTREAM", "SECOND_ORDER")}
    mechanism_dist = {}
    for c in consequences:
        mechanism_dist[c["mechanism"]] = mechanism_dist.get(c["mechanism"], 0) + 1

    accepted = [c for c in consequences if c["screened_disposition"] in ("STRIKE", "WATCH")]
    rejected = [c for c in consequences if c["screened_disposition"] == "REJECT"]
    graded_accepted = [c for c in accepted if case_of[id(c)] in graded_cases]
    true_acc = sum(1 for c in graded_accepted if label_by_case.get(case_of[id(c)]) == "TRUE_POSITIVE")
    false_acc = sum(1 for c in graded_accepted if label_by_case.get(case_of[id(c)]) == "TRUE_NEGATIVE")
    decided = true_acc + false_acc

    value_status = {}
    for c in consequences:
        s = (c.get("value") or {}).get("status", "UNKNOWN")
        value_status[s] = value_status.get(s, 0) + 1

    rejected_reasons = {}
    for c in rejected:
        for f in c.get("falsifiers", []):
            if f.get("fatal"):
                rejected_reasons[f["code"]] = rejected_reasons.get(f["code"], 0) + 1

    # Catalyst lead time: first_observed_at -> case outcome.
    leads = []
    for r in results:
        occurred = r.get("outcome_occurred_at")
        for c in r["catalysts"]:
            if occurred and c.get("first_observed_at"):
                leads.append((_dt(occurred).date() - _dt(c["first_observed_at"]).date()).days)

    mechanism_precision = {}
    for mech in sorted(mechanism_dist):
        rows = [c for c in graded_accepted if c["mechanism"] == mech]
        t = sum(1 for c in rows if label_by_case.get(case_of[id(c)]) == "TRUE_POSITIVE")
        f = sum(1 for c in rows if label_by_case.get(case_of[id(c)]) == "TRUE_NEGATIVE")
        mechanism_precision[mech] = round(t / (t + f), 4) if (t + f) else None

    return {
        "consequence_engine_version": "commercial_consequence_v1",
        "catalysts_created": len(catalysts),
        "catalysts_contradicted": sum(c["status"] == "contradicted" for c in catalysts),
        "duplicate_catalysts_collapsed": sum(r["duplicate_catalysts_collapsed"] for r in results),
        "average_catalyst_lead_time_days": round(sum(leads) / len(leads), 1) if leads else None,
        "median_catalyst_lead_time_days": median(leads) if leads else None,
        "consequences_created": len(consequences),
        "zero_consequence_catalysts": sum(r["consequence_count"] == 0 and r["catalyst_count"] > 0 for r in results),
        "multi_consequence_cases": sum(r["consequence_count"] > 1 for r in results),
        "directness_distribution": directness_dist,
        "mechanism_distribution": dict(sorted(mechanism_dist.items())),
        "mechanism_families_exercised": sorted(mechanism_dist),
        "buyer_resolution_rate": round(sum(has_role(c, {"BUYER", "PRIME_RECIPIENT"}) for c in consequences) / len(consequences), 4) if consequences else None,
        "capability_resolution_rate": round(sum(bool(c["capability_classes"]) for c in consequences) / len(consequences), 4) if consequences else None,
        "value_status_distribution": dict(sorted(value_status.items())),
        "rejected_consequences": len(rejected),
        "rejected_consequence_reasons": dict(sorted(rejected_reasons.items())),
        "consequence_precision": round(true_acc / decided, 4) if decided else None,
        "false_consequence_rate": round(false_acc / decided, 4) if decided else None,
        "mechanism_precision": mechanism_precision,
        "expected_consequence_cases": sum(r.get("expected_consequence_ok") is not None for r in results),
        "expected_consequence_passing": sum(bool(r.get("expected_consequence_ok")) for r in results),
        "small_sample_warning": ("consequence precision rests on very few decided consequences; treat as directional"
                                 if decided < 12 else None),
    }


def _check_expected_chain(expected: dict | None, resolution, transitions) -> list[dict]:
    if not expected:
        return []
    metrics = resolution.metrics()
    summary = {t.new_disposition: t for t in transitions}
    checks: list[dict] = []

    def check(name, ok, got, want):
        checks.append({"check": name, "ok": bool(ok), "got": got, "want": want})

    if "min_relationships" in expected:
        want = expected["min_relationships"]
        check("min_relationships", metrics["relationships_total"] >= want, metrics["relationships_total"], want)
    if "min_deterministic" in expected:
        want = expected["min_deterministic"]
        check("min_deterministic", metrics["deterministic_relationships"] >= want, metrics["deterministic_relationships"], want)
    if "min_inferred" in expected:
        want = expected["min_inferred"]
        check("min_inferred", metrics["inferred_relationships"] >= want, metrics["inferred_relationships"], want)
    if "max_inferred" in expected:
        want = expected["max_inferred"]
        check("max_inferred", metrics["inferred_relationships"] <= want, metrics["inferred_relationships"], want)
    if "min_deferred" in expected:
        want = expected["min_deferred"]
        check("min_deferred", metrics["deferred_joins"] >= want, metrics["deferred_joins"], want)
    if "entity_predicates" in expected:
        got = metrics["entity_predicates"]
        want = sorted(expected["entity_predicates"])
        check("entity_predicates", set(want) <= set(got), got, want)
    if "min_rejected" in expected:
        want = expected["min_rejected"]
        check("min_rejected", metrics["rejected_weak_joins"] >= want, metrics["rejected_weak_joins"], want)
    if "max_relationships" in expected:
        want = expected["max_relationships"]
        check("max_relationships", metrics["relationships_total"] <= want, metrics["relationships_total"], want)
    if "predicates" in expected:
        got = sorted({r.predicate for r in resolution.relationships})
        want = sorted(expected["predicates"])
        check("predicates", set(want) <= set(got), got, want)
    if "final_disposition" in expected:
        got = transitions[-1].new_disposition if transitions else None
        check("final_disposition", got == expected["final_disposition"], got, expected["final_disposition"])
    if "promotion_causes" in expected:
        for want in expected["promotion_causes"]:
            transition = summary.get(want["to"])
            got = transition.cause_stage if transition else None
            check(f"promotion_to_{want['to']}", got == want["stage"], got, want["stage"])
    if "contradicted" in expected:
        got = resolution.confidence.get("contradicted", False)
        check("contradicted", got == expected["contradicted"], got, expected["contradicted"])
    return checks


def load_corpus(path: Path, _seen: set[Path] | None = None) -> list[dict]:
    path = Path(path).resolve()
    seen = set(_seen or ())
    if path in seen:
        raise ValueError(f"cyclic corpus extension: {path}")
    seen.add(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(cases, list):
        raise ValueError("corpus must be a list or an object containing cases")
    if isinstance(payload, dict) and payload.get("extends"):
        base_path = (path.parent / str(payload["extends"])).resolve()
        cases = load_corpus(base_path, seen) + cases
    seen = set()
    for case in cases:
        validate_case(case, require_quality=True)
        if case["case_id"] in seen:
            raise ValueError(f"duplicate case_id: {case['case_id']}")
        seen.add(case["case_id"])
    return sorted(cases, key=lambda c: c["case_id"])


def run_corpus(cases: Iterable[dict], *, scoring_version: str = ACTIVE_SCORING_VERSION, mechanism: str | None = None, store: Optional[StateStore] = None) -> list[dict]:
    selected = [c for c in cases if mechanism is None or c["mechanism_family"] == mechanism]
    return [run_replay(c, store=store, scoring_version=scoring_version) for c in selected]


def report_id(results: list[dict], report_kind: str = "corpus") -> str:
    return _stable_id({"kind": report_kind, "result_ids": sorted(r["id"] for r in results)}, length=24)


def run_chain_corpus(cases: Iterable[dict], *, scoring_version: str = ACTIVE_SCORING_VERSION,
                     store: Optional[StateStore] = None) -> list[dict]:
    """Resolve chains only for cases that declare cross-source program identity in their records."""
    selected = [c for c in cases if any(r.get("program_key") and r.get("stage") for r in c["records"])]
    return [run_chain_replay(c, scoring_version=scoring_version, store=store) for c in selected]


def evaluate_inferred_threshold(cases: Iterable[dict],
                                candidate_thresholds: tuple[float, ...] = (0.45, 0.50, 0.55, 0.60, 0.65, 0.70)) -> dict:
    """Sweep the inferred-join acceptance threshold over every anchored candidate in the corpus.

    Each anchored candidate is paired with its case's ground-truth label (which reports whether the
    intended cross-source linkage is real), so precision and false-join rate can be reported at each
    candidate threshold. This is calibration evidence only; it does not change the frozen threshold.
    """
    from .chains import signals_from_records

    scored: list[tuple[float, bool | None]] = []  # (confidence, is_true_join)
    for case in cases:
        if not any(r.get("program_key") and r.get("stage") for r in case["records"]):
            continue
        resolution = _resolve_case_chain(case)
        label = (case.get("ground_truth") or {}).get("label")
        is_true = True if label == "TRUE_POSITIVE" else False if label == "TRUE_NEGATIVE" else None
        for score in resolution.inference_scores:
            scored.append((score.confidence, is_true))

    sweep = []
    for threshold in candidate_thresholds:
        accepted = [truth for conf, truth in scored if conf >= threshold]
        decided = [t for t in accepted if t is not None]
        true_accepts = sum(1 for t in decided if t)
        false_accepts = sum(1 for t in decided if t is False)
        sweep.append({
            "threshold": threshold,
            "accepted": len(accepted),
            "true_joins": true_accepts,
            "false_joins": false_accepts,
            "precision": round(true_accepts / len(decided), 4) if decided else None,
            "deferred_below": sum(1 for conf, _ in scored if conf < threshold),
        })
    return {
        "active_threshold": 0.60,
        "anchored_candidates": len(scored),
        "sweep": sweep,
        "recommendation": (
            "keep threshold at 0.60: too few reviewed anchored inferred candidates to justify a change"
            if len(scored) < 10 else "sufficient sample — review sweep before any change"
        ),
    }


def _resolve_case_chain(case: dict):
    from .chains import resolve_chain, signals_from_records

    return resolve_chain(signals_from_records(case["records"]))


def summarize_chain_results(results: list[dict]) -> dict:
    """Aggregate cross-source chain observability across the corpus (no scoring impact)."""
    def total(key: str) -> int:
        return sum(r["chain_metrics"][key] for r in results)

    leads = [r["chain_lead_time_days"] for r in results if r.get("chain_lead_time_days") is not None]
    checked = [r for r in results if r.get("expected_chain_ok") is not None]
    promotions = [c for r in results for c in r["transitions"]["promotion_causes"]]

    # Inferred-join calibration. A case's ground-truth label reports whether its intended cross-source
    # join is real, so we score inferred accepts/rejects against it. A "false join" is an accepted
    # inferred relationship in a case whose ground truth is a true negative.
    def label(r: dict) -> str | None:
        return (r.get("ground_truth") or {}).get("label")

    accepted_inferred = [r for r in results if r["chain_metrics"]["inferred_relationships"] > 0]
    true_accepts = [r for r in accepted_inferred if label(r) == "TRUE_POSITIVE"]
    false_accepts = [r for r in accepted_inferred if label(r) == "TRUE_NEGATIVE"]
    inferred_precision = round(len(true_accepts) / len(accepted_inferred), 4) if accepted_inferred else None
    false_join_rate = round(len(false_accepts) / len(accepted_inferred), 4) if accepted_inferred else None
    entity_predicates = sorted({p for r in results for p in r["chain_metrics"].get("entity_predicates", [])})
    return {
        "chain_cases": len(results),
        "cross_source_relationships": total("relationships_total"),
        "deterministic_relationships": total("deterministic_relationships"),
        "inferred_relationships": total("inferred_relationships"),
        "deferred_joins": total("deferred_joins"),
        "corroborations": total("corroborations"),
        "contradictions": total("contradictions"),
        "rejected_weak_joins": total("rejected_weak_joins"),
        "duplicates_collapsed": total("duplicates_collapsed"),
        "entity_relationships": total("entity_relationships"),
        "entity_predicates_exercised": entity_predicates,
        "inferred_accepted_cases": len(accepted_inferred),
        "inferred_true_join_cases": len(true_accepts),
        "inferred_false_join_cases": len(false_accepts),
        "inferred_precision": inferred_precision,
        "inferred_false_join_rate": false_join_rate,
        "deferred_join_cases": sum(r["chain_metrics"]["deferred_joins"] > 0 for r in results),
        "promotion_events": len(promotions),
        "promotion_causes_by_stage": {
            stage: sum(p["stage"] == stage for p in promotions)
            for stage in sorted({p["stage"] for p in promotions if p["stage"]})
        },
        "median_chain_lead_time_days": sorted(leads)[len(leads) // 2] if leads else None,
        "expected_chain_cases": len(checked),
        "expected_chain_passing": sum(bool(r["expected_chain_ok"]) for r in checked),
        "small_sample_warning": (
            "inferred-join precision is measured on very few accepted inferred joins; treat as "
            "directional, not a stable rate"
            if accepted_inferred and len(accepted_inferred) < 10 else None
        ),
    }
