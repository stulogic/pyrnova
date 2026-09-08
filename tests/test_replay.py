"""Point-in-time replay regression coverage."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from pyrnova.metrics import evaluation_snapshot, summarize_results
from pyrnova.archive import LocalEvidenceArchive
from pyrnova.pipeline import run
from pyrnova.replay import load_corpus, report_id, run_corpus, run_replay, visible_records
from pyrnova.state import StateStore


FIXTURE = Path(__file__).parent / "fixtures" / "replay_chips_2022.json"
CORPUS = Path(__file__).parents[1] / "examples" / "replay" / "corpus_v1.json"


def _chips_case() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_replay_excludes_future_and_unavailable_evidence_and_is_deterministic():
    case = _chips_case()
    unavailable = {
        "source_id": "unproven",
        "source_ref": "unproven-availability",
        "record_kind": "policy_funding",
        "strength": 5,
        "applies_to_candidate": True,
    }
    case["records"].append(unavailable)

    visible = visible_records(case["records"], case["replay_as_of"])
    assert [record["source_ref"] for record in visible] == ["PLAW-117publ167"]

    first = run_replay(case)
    second = run_replay(deepcopy(case))
    assert first == second
    assert first["future_evidence_excluded"] == 3
    assert first["system_disposition"] == "WATCH"
    assert first["directionally_correct"] is True
    assert first["lead_time_days"] == 203


def test_replay_persists_result(tmp_path):
    store = StateStore(tmp_path / "state")
    result = run_replay(_chips_case(), store=store)

    assert store.count("replay_results") == 1
    assert store.latest("replay_results", result["id"])["id"] == result["id"]


def test_evaluation_reports_watch_conversion_false_rates_and_unknown_value(tmp_path):
    store = StateStore(tmp_path / "state")
    chips = run_replay(_chips_case(), store=store)

    false_positive = deepcopy(_chips_case())
    false_positive["case_id"] = "false-positive"
    false_positive["candidate"]["relevance"] = 0.9
    false_positive["records"] = [
        {
            "source_id": "test",
            "source_ref": "known-solicitation",
            "record_kind": "solicitation",
            "source_role": "primary",
            "available_at": false_positive["replay_as_of"],
            "strength": 5,
            "applies_to_candidate": True,
        }
    ]
    false_positive["actual_outcome"] = {"occurred": False}
    false_positive["ground_truth"] = {"label": "TRUE_NEGATIVE", "confidence": "HIGH"}
    assert run_replay(false_positive, store=store)["false_positive"] is True

    false_negative = deepcopy(_chips_case())
    false_negative["case_id"] = "false-negative"
    false_negative["candidate"]["relevance"] = 0.1
    false_negative["records"] = []
    assert run_replay(false_negative, store=store)["false_negative"] is True

    snapshot = evaluation_snapshot(store)
    assert chips["watch_conversion"] is True
    assert chips["value_error_usd"] is None
    assert snapshot["watch_conversion"] == 1.0
    assert snapshot["false_positive_rate"] == 1.0
    assert snapshot["false_negative_rate"] == 0.5
    assert snapshot["estimated_vs_actual_value"] == []


def test_pipeline_replay_clock_blocks_future_source_records(
    tmp_path, profile, notice_rows, as_of
):
    past = deepcopy(notice_rows[0])
    past["_pyrnova_timing"] = {"available_at": "2026-09-01T00:00:00+00:00"}
    future = deepcopy(notice_rows[1])
    future["_pyrnova_timing"] = {"available_at": "2026-09-20T00:00:00+00:00"}
    store = StateStore(tmp_path / "state")
    report = run(
        profile=profile,
        notice_rows=[past, future],
        archive=LocalEvidenceArchive(tmp_path / "archive"),
        store=store,
        as_of=as_of,
        replay_as_of="2026-09-08T23:59:59+00:00",
    )
    all_opps = report.strikes + report.watch + report.rejected
    assert {o.meta.get("notice_id") for o in all_opps} == {past["noticeId"]}
    assert report.stats["future_records_excluded"] == 1


def test_canonical_corpus_meets_m3_quality_floor_and_is_deterministic():
    cases = load_corpus(CORPUS)
    assert len(cases) >= 20
    assert len({case["mechanism_family"] for case in cases}) >= 4
    labels = {case["ground_truth"]["label"] for case in cases}
    assert {"TRUE_POSITIVE", "TRUE_NEGATIVE"} <= labels

    first = run_corpus(cases, scoring_version="scoring_v1")
    second = run_corpus(cases, scoring_version="scoring_v1")
    assert first == second
    assert report_id(first) == report_id(second)
    assert all(result["future_evidence_excluded"] >= 1 for result in first)
    assert all(result["scoring_version"] == "scoring_v1" for result in first)


def test_full_corpus_scoring_comparison_and_metrics():
    cases = load_corpus(CORPUS)
    baseline = run_corpus(cases, scoring_version="scoring_v1")
    challenger = run_corpus(cases, scoring_version="scoring_v2_candidate")
    assert len(baseline) == len(challenger) == len(cases)
    assert {r["id"] for r in baseline}.isdisjoint({r["id"] for r in challenger})

    metrics = summarize_results(baseline)
    assert metrics["case_count"] >= 20
    assert metrics["mechanism_family_count"] >= 4
    assert metrics["strike_precision"] is not None
    assert metrics["watch_conversion_rate"] is not None
    assert metrics["median_lead_time_days"] is not None
    assert metrics["evidence_level_contribution"]
    assert metrics["human_adjudications"] == len(cases)
    assert len(metrics["calibration"]) == 6
