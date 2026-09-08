"""M5 chain-replay integration and corpus-level acceptance."""

from pyrnova.replay import (
    load_corpus,
    run_chain_corpus,
    run_chain_replay,
    run_corpus,
    summarize_chain_results,
)
from pyrnova.metrics import summarize_results

M4 = "examples/replay/corpus_m4.json"
M5 = "examples/replay/corpus_m5.json"


def _case(corpus: str, case_id: str) -> dict:
    return next(c for c in load_corpus(corpus) if c["case_id"] == case_id)


def test_frozen_m4_scoring_baseline_is_unchanged():
    metrics = summarize_results(run_corpus(load_corpus(M4)))
    assert metrics["case_count"] == 23
    assert metrics["strike_precision"] == 0.6667
    assert metrics["watch_conversion"] == 0.8667
    assert metrics["false_positive_rate"] == 0.3333
    assert metrics["false_negative_rate"] == 0.0
    assert metrics["median_lead_time_days"] == 297.5


def test_m5_adds_only_one_explained_true_positive_strike():
    metrics = summarize_results(run_corpus(load_corpus(M5)))
    # Exactly one more STRIKE than the frozen baseline, and it is a true positive.
    assert metrics["confusion_matrix"]["true_strike"] == 3
    assert metrics["confusion_matrix"]["false_strike"] == 1
    assert metrics["false_negative_rate"] == 0.0
    assert metrics["strike_precision"] == 0.75


def test_all_expected_chains_pass_and_no_false_join_created():
    summary = summarize_chain_results(run_chain_corpus(load_corpus(M5)))
    assert summary["expected_chain_cases"] == 4
    assert summary["expected_chain_passing"] == 4
    assert summary["inferred_relationships"] == 0
    assert summary["deterministic_relationships"] == summary["cross_source_relationships"]
    assert summary["rejected_weak_joins"] >= 1


def test_public_sector_lifecycle_reconstructs_full_chain():
    result = run_chain_replay(_case(M5, "chain-navy-c5isr-lifecycle-2023"))
    m = result["chain_metrics"]
    assert m["distinct_sources"] == 3
    assert m["deterministic_relationships"] == 2
    assert m["chain_confidence"]["value"] == 0.95
    assert result["chain_lead_time_days"] == 434
    assert result["transitions"]["trajectory"] == ["WATCH", "STRIKE"]
    assert result["expected_chain_ok"] is True


def test_false_join_case_yields_reject_and_zero_relationships():
    result = run_chain_replay(_case(M5, "chain-false-join-hhs-dhs-cloud-2024"))
    assert result["chain_metrics"]["relationships_total"] == 0
    assert result["chain_metrics"]["rejected_weak_joins"] == 1
    assert result["transitions"]["trajectory"] == ["REJECT"]
    assert result["expected_chain_ok"] is True


def test_chain_replay_is_deterministic():
    case = _case(M5, "chain-navy-c5isr-lifecycle-2023")
    first, second = run_chain_replay(case), run_chain_replay(case)
    assert first["relationships"] == second["relationships"]
    assert first["chain_metrics"] == second["chain_metrics"]
