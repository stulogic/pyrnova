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


def load_corpus(path: Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(cases, list):
        raise ValueError("corpus must be a list or an object containing cases")
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
