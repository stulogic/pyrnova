"""M9 real-company fit calibration and corpus acceptance."""

from pyrnova.replay import (
    load_corpus,
    run_corpus,
    run_fit_corpus,
    summarize_fit_results,
)
from pyrnova.metrics import summarize_results

M8, M9 = "examples/replay/corpus_m8.json", "examples/replay/corpus_m9.json"


def _real_results():
    return run_fit_corpus(load_corpus(M9))


def test_real_profile_fit_all_expected_pass_with_no_leakage():
    results = _real_results()
    real = summarize_fit_results(results, source="real")
    assert real["expected_fit_passing"] == real["expected_fit_cases"] == 7
    assert real["temporal_leakage_violations"] == 0  # hard gate: no future evidence leaked
    assert real["fit_precision"] == 1.0
    assert real["no_fit_precision"] == 1.0
    assert real["false_match_rate"] == 0.0
    assert real["posture_precision_overall"] == 1.0


def test_real_postures_cover_prime_support_defend_and_nofit():
    real = summarize_fit_results(_real_results(), source="real")
    dist = real["posture_distribution"]
    assert dist["PRIME"] >= 1 and dist["SUPPORT"] >= 1 and dist["DEFEND"] >= 1 and dist["NO_FIT"] >= 2
    assert real["unknown_rate"] > 0  # the early-cutoff unknown case is represented


def test_real_and_synthetic_metrics_are_reported_separately():
    results = _real_results()
    real = summarize_fit_results(results, source="real")
    synth = summarize_fit_results(results, source="synthetic")
    # Real profiles come only from the M9 cases; synthetic only from the inherited M8 cases.
    assert real["profile_source"] == "real" and synth["profile_source"] == "synthetic"
    assert real["graded_fits"] == 7 and synth["graded_fits"] == 12
    assert real["small_sample_warning"] and synth["small_sample_warning"]


def test_broad_defense_sector_match_is_rejected_for_a_real_company():
    # Torch is a real defense firm but has no radar-manufacturing capability evidence.
    results = _real_results()
    radar = next(r for r in results if r["case_id"] == "m9-torch-radar-hardware-nofit-2021")
    fit = radar["fits"][0]
    assert fit["posture"] == "NO_FIT" and fit["fit"] is False
    assert any(b["code"] == "no_required_capability" for b in fit["blockers"])


def test_real_defend_is_backed_by_incumbency():
    results = _real_results()
    defend = next(r for r in results if r["case_id"] == "m9-torch-weapons-seta-defend-2023")
    assert defend["fits"][0]["posture"] == "DEFEND"


def test_scoring_v1_stable_and_frozen_corpora_unchanged_under_m9():
    m9 = summarize_results(run_corpus(load_corpus(M9)))
    assert m9["case_count"] == 55
    assert m9["false_negative_rate"] == 0.0
    assert m9["confusion_matrix"]["false_strike"] == 1  # no new false positive
    m8 = summarize_results(run_corpus(load_corpus(M8)))
    assert m8["case_count"] == 48 and m8["strike_precision"] == 0.9231
