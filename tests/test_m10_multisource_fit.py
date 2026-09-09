"""M10 multi-source real-company fit calibration and corpus acceptance (offline).

These cases attach a constructed opportunity probe to REAL, multi-source-grounded company
profiles (USAspending prime + SEC EDGAR + USAspending recipient/sub-awards), built strictly
point-in-time via ``multisource.build_multisource_profile``. They are evaluated ONLY by the fit
engine; ``scoring_v1`` is unchanged and its stability is proven separately over the frozen M9
corpus. No live calls: every fixture is already archived under ``examples/real_evidence/``.
"""

import json
from pathlib import Path

from pyrnova.metrics import summarize_results
from pyrnova.replay import (
    load_corpus,
    run_corpus,
    run_fit_corpus,
    summarize_fit_results,
    summarize_multisource_results,
)

M9 = "examples/replay/corpus_m9.json"
M10_PATH = Path("examples/replay/corpus_m10.json")


def _m10_cases():
    payload = json.loads(M10_PATH.read_text(encoding="utf-8"))
    return payload


def _m10_fit_cases():
    return _m10_cases()["cases"]


def _results():
    return run_fit_corpus(_m10_fit_cases())


# ---------------------------------------------------------------- corpus wiring

def test_m10_extends_frozen_m9_and_declares_multisource_provenance():
    payload = _m10_cases()
    assert payload["extends"] == "corpus_m9.json"
    assert all(c["profile_source"] == "multisource_real" for c in payload["cases"])
    # Every M10 profile is grounded from multiple archived real source families.
    for case in payload["cases"]:
        for company in case["companies"]:
            sources = company["grounded"]["sources"]
            assert len({s["kind"] for s in sources}) >= 2


def test_m10_real_multisource_fits_all_pass_with_no_leakage():
    results = _results()
    assert all(r["expected_fit_ok"] for r in results)
    ms = summarize_fit_results(results, source="multisource_real")
    assert ms["fit_cases"] == 8 and ms["graded_fits"] == 8
    assert ms["temporal_leakage_violations"] == 0  # hard gate: no future evidence leaked
    assert ms["fit_precision"] == 1.0
    assert ms["no_fit_precision"] == 1.0
    assert ms["false_match_rate"] == 0.0
    assert ms["posture_precision_overall"] == 1.0
    assert ms["blocker_accuracy"] == 1.0
    assert ms["capability_match_coverage"] == 0.875
    assert ms["buyer_history_coverage"] == 1.0
    assert ms["unknown_rate"] == 0.125
    assert ms["small_sample_warning"]  # directional, never hidden


def test_m10_postures_cover_prime_support_team_defend_and_nofit():
    ms = summarize_fit_results(_results(), source="multisource_real")
    dist = ms["posture_distribution"]
    assert dist == {"PRIME": 1, "SUPPORT": 1, "TEAM": 1, "DEFEND": 1, "NO_FIT": 4}
    assert all(v == 1.0 for v in ms["posture_precision"].values())


def test_m10_multisource_diversity_eligibility_and_subcontract_coverage():
    mm = summarize_multisource_results(_results())
    assert mm["profiles_evaluated"] == 8
    assert mm["multi_source_profiles"] == 8
    assert mm["profile_source_diversity_avg"] == 2.5
    assert mm["max_source_families"] == 3
    assert mm["distinct_source_families"] == [
        "sec_edgar", "usaspending_prime", "usaspending_recipient", "usaspending_subawards"
    ]
    assert mm["eligibility_coverage"] == 0.5
    assert mm["subcontract_coverage"] == 0.625
    assert mm["profiles_with_authoritative_partner"] == 5
    assert mm["temporal_leakage_violations"] == 0


# ---------------------------------------------------------------- decisive cases

def _case(results, cid):
    return next(r for r in results if r["case_id"] == cid)


def test_real_team_requires_authoritative_partner_edge():
    fit = _case(_results(), "m10-torch-team-hwil-te")["fits"][0]
    assert fit["posture"] == "TEAM" and fit["fit"] is True


def test_false_tempting_team_resolves_to_support_not_team():
    # SAIC has complementary capability but no authoritative teaming edge -> SUPPORT, never TEAM.
    fit = _case(_results(), "m10-saic-support-false-team")["fits"][0]
    assert fit["posture"] == "SUPPORT" and fit["posture"] != "TEAM"


def test_real_eligibility_blocks_a_capable_firm():
    fit = _case(_results(), "m10-torch-nofit-setaside")["fits"][0]
    assert fit["posture"] == "NO_FIT" and fit["fit"] is False
    assert any(b["code"] == "insufficient_certification" for b in fit["blockers"])


def test_point_in_time_gate_excludes_future_capability_and_subawards():
    r = _case(_results(), "m10-torch-leakage-2017")
    assert not r["leakage_violations"]
    assert r["fits"][0]["posture"] == "NO_FIT"


# ---------------------------------------------------------------- scoring frozen

def test_scoring_v1_frozen_and_m9_base_unchanged():
    # scoring_v1 is unchanged in M10; its behaviour is proven over the frozen M9 corpus.
    m9 = summarize_results(run_corpus(load_corpus(M9)))
    assert m9["case_count"] == 55
    assert m9["false_negative_rate"] == 0.0
    assert m9["confusion_matrix"]["false_strike"] == 1  # no new false positive
