"""Per-source M4 contribution accounting, separate from scoring policy."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class SourceContribution:
    raw_records: int = 0
    normalized_events: int = 0
    duplicates_removed: int = 0
    candidates_created: int = 0
    candidates_enriched: int = 0
    watch_promotions: int = 0
    strike_promotions: int = 0
    rejects: int = 0
    lead_time_days_gained: list[int] = field(default_factory=list)
    evidence_levels: Counter = field(default_factory=Counter)

    def snapshot(self) -> dict:
        gains = sorted(self.lead_time_days_gained)
        midpoint = len(gains) // 2
        median_gain = None
        if gains:
            median_gain = gains[midpoint] if len(gains) % 2 else (gains[midpoint - 1] + gains[midpoint]) / 2
        return {
            "raw_records": self.raw_records,
            "normalized_events": self.normalized_events,
            "duplicates_removed": self.duplicates_removed,
            "candidates_created": self.candidates_created,
            "candidates_enriched": self.candidates_enriched,
            "watch_promotions": self.watch_promotions,
            "strike_promotions": self.strike_promotions,
            "rejects": self.rejects,
            "evidence_level_contribution": dict(sorted(self.evidence_levels.items())),
            "median_lead_time_gain_days": median_gain,
        }


class SourceContributionLedger:
    def __init__(self) -> None:
        self._sources: dict[str, SourceContribution] = {}

    def source(self, source_id: str) -> SourceContribution:
        return self._sources.setdefault(source_id, SourceContribution())

    def snapshots(self) -> dict[str, dict]:
        return {source_id: values.snapshot() for source_id, values in sorted(self._sources.items())}


def measure_replay_source_contribution(cases: list[dict], *, scoring_version: str = "scoring_v1") -> dict:
    """Measure each source by deterministic leave-one-source-out replay.

    This is an attribution diagnostic, not a scoring change.  It reports only differences the current
    replay policy can prove; missing precision/lead-time comparisons remain ``None``.
    """
    from copy import deepcopy
    from datetime import datetime

    from .metrics import summarize_results
    from .replay import run_replay, visible_records

    baseline = [run_replay(case, scoring_version=scoring_version) for case in cases]
    baseline_metrics = summarize_results(baseline)
    source_ids = sorted({record["source_id"] for case in cases for record in case["records"]})
    report = {}
    rank = {"REJECT": 0, "WATCH": 1, "STRIKE": 2}
    for source_id in source_ids:
        source_records = [record for case in cases for record in case["records"] if record["source_id"] == source_id]
        unique_refs = {(case["case_id"], record["source_ref"]) for case in cases for record in case["records"] if record["source_id"] == source_id}
        ablated_cases = []
        visible_count = enriched = candidate_created = rejects = noise_records = 0
        evidence_levels = Counter()
        lead_gains = []
        for case in cases:
            visible = visible_records(case["records"], case["replay_as_of"])
            source_visible = [record for record in visible if record["source_id"] == source_id]
            other_visible = [record for record in visible if record["source_id"] != source_id]
            visible_count += len(source_visible)
            evidence_levels.update(int(record["strength"]) for record in source_visible)
            noise_records += sum(not record.get("applies_to_candidate") for record in source_visible)
            if source_visible and other_visible:
                enriched += 1
            source_direct = any(record.get("record_kind") == "solicitation" and record.get("applies_to_candidate") for record in source_visible)
            other_direct = any(record.get("record_kind") == "solicitation" and record.get("applies_to_candidate") for record in other_visible)
            candidate_created += bool(source_direct and not other_direct)
            if source_visible and case.get("expected_disposition") == "REJECT":
                rejects += 1
            if source_visible and other_visible:
                source_first = min(datetime.fromisoformat(r["available_at"].replace("Z", "+00:00")) for r in source_visible)
                other_first = min(datetime.fromisoformat(r["available_at"].replace("Z", "+00:00")) for r in other_visible)
                if source_first < other_first:
                    lead_gains.append((other_first.date() - source_first.date()).days)
            ablated = deepcopy(case)
            ablated["records"] = [r for r in ablated["records"] if r["source_id"] != source_id]
            ablated_cases.append(ablated)
        ablated_results = [run_replay(case, scoring_version=scoring_version) for case in ablated_cases]
        ablated_metrics = summarize_results(ablated_results)
        watch_promotions = strike_promotions = 0
        for included, excluded in zip(baseline, ablated_results):
            if rank[included["system_disposition"]] > rank[excluded["system_disposition"]]:
                watch_promotions += included["system_disposition"] == "WATCH"
                strike_promotions += included["system_disposition"] == "STRIKE"
        precision = baseline_metrics["strike_precision"]
        without_precision = ablated_metrics["strike_precision"]
        report[source_id] = {
            "raw_records": len(source_records),
            "normalized_events": visible_count,
            "duplicates_removed": len(source_records) - len(unique_refs),
            "candidates_created": candidate_created,
            "candidates_enriched": enriched,
            "watch_promotions": watch_promotions,
            "strike_promotions": strike_promotions,
            "rejects": rejects,
            "evidence_level_contribution": dict(sorted(evidence_levels.items())),
            "median_lead_time_gain_days": sorted(lead_gains)[len(lead_gains) // 2] if lead_gains else None,
            "strike_precision_with_source": precision,
            "strike_precision_without_source": without_precision,
            "precision_delta": round(precision - without_precision, 4) if precision is not None and without_precision is not None else None,
            "noise_records": noise_records,
        }
    return report
