"""M8 capability fit, capture posture, falsification, and corpus acceptance."""

from pyrnova.company import build_profile, company_id
from pyrnova.fit import adjudicate_fit, enqueue_fit_review, evaluate_fit, pending_fit_reviews
from pyrnova.models import CommercialConsequence
from pyrnova.replay import (
    load_corpus,
    run_corpus,
    run_fit_corpus,
    summarize_fit_results,
)
from pyrnova.metrics import summarize_results
from pyrnova.state import StateStore

M7, M8 = "examples/replay/corpus_m7.json", "examples/replay/corpus_m8.json"


def _consequence(caps, *, directness="DIRECT", buyer="Department of the Navy", program_key="navy:x",
                 amount=50000000, spend="334511"):
    c = CommercialConsequence(
        catalyst_id="cat_x", program_key=program_key, mechanism="DIRECT_PROCUREMENT",
        directness=directness,
        capability_classes=[{"label": l} for l in caps],
        participants=[{"role": "BUYER", "name": buyer}],
        likely_spend_category=spend,
        value={"status": "KNOWN", "amount_usd": amount},
        first_supportable_at="2024-06-01T00:00:00+00:00",
    )
    c.id = "cons_x"
    return c


def _cap_record(naics=None, description=None, at="2021-01-01T00:00:00+00:00", ref="CAP"):
    r = {"source_id": "capability_statement", "source_ref": ref, "available_at": at}
    if naics:
        r["naics"] = naics
    if description:
        r["description"] = description
    return r


# --- posture cases -------------------------------------------------------------

def test_prime_when_full_capability_eligible_and_prime_history():
    cons = _consequence(["radar_component_manufacturing"])
    profile = build_profile("Coastal Radar Systems Inc", [_cap_record(naics="334511")],
                            scale={"max_contract_usd": 80000000},
                            contract_history=[{"agency": "Department of the Navy", "naics": "334511",
                                               "role": "prime", "award_ref": "H1", "available_at": "2022-01-01T00:00:00+00:00"}])
    result = evaluate_fit(cons, profile)
    assert result.posture == "PRIME" and result.fit is True
    assert "radar_component_manufacturing" in result.capability_match


def test_support_when_capability_but_no_prime_signal():
    cons = _consequence(["radar_component_manufacturing"])
    profile = build_profile("Antenna Subsystems Co", [_cap_record(naics="334511")],
                            scale={"max_contract_usd": 80000000},
                            contract_history=[{"agency": "Department of the Army", "naics": "334511",
                                               "role": "sub", "award_ref": "H2", "available_at": "2022-01-01T00:00:00+00:00"}])
    result = evaluate_fit(cons, profile)
    assert result.posture == "SUPPORT" and result.fit is True


def test_team_when_partial_capability_and_partners():
    cons = _consequence(["electrical_construction", "semiconductor_process_equipment"])
    profile = build_profile("Copper Line Electric Inc", [_cap_record(naics="238210")],
                            partners=["Fab Equipment Integrators LLC"], scale={"max_contract_usd": 200000000})
    result = evaluate_fit(cons, profile)
    assert result.posture == "TEAM" and result.fit is True


def test_support_when_partial_capability_without_partners():
    cons = _consequence(["electrical_construction", "semiconductor_process_equipment"])
    profile = build_profile("Desert Wiring Co", [_cap_record(naics="238210")], scale={"max_contract_usd": 200000000})
    assert evaluate_fit(cons, profile).posture == "SUPPORT"


def test_defend_when_incumbent():
    cons = _consequence(["radar_component_manufacturing"], program_key="navy:sustain")
    profile = build_profile("Incumbent Radar Inc", [_cap_record(naics="334511")],
                            scale={"max_contract_usd": 80000000},
                            contract_history=[{"agency": "Department of the Navy", "naics": "334511", "role": "prime",
                                               "program_key": "navy:sustain", "award_ref": "H3", "available_at": "2020-01-01T00:00:00+00:00"}])
    assert evaluate_fit(cons, profile).posture == "DEFEND"


def test_no_fit_broad_sector_company_is_rejected():
    cons = _consequence(["radar_component_manufacturing"])
    profile = build_profile("Broad Defense Consulting LLC",
                            [_cap_record(description="technology consulting services and management support")],
                            scale={"max_contract_usd": 20000000})
    result = evaluate_fit(cons, profile)
    assert result.posture == "NO_FIT" and result.fit is False
    assert result.is_unknown  # no capability evidence, not a confident "no"


def test_hard_blocker_capability_mismatch_forbids_fit():
    cons = _consequence(["radar_component_manufacturing"])
    profile = build_profile("Environmental Co", [_cap_record(naics="562910")],  # environmental remediation
                            scale={"max_contract_usd": 80000000})
    result = evaluate_fit(cons, profile)
    assert result.posture == "NO_FIT"
    assert any(b["code"] == "no_required_capability" and b["fatal"] for b in result.blockers)


def test_certification_and_clearance_blockers_forbid_fit():
    cons = _consequence(["radar_component_manufacturing"])
    profile = build_profile("SecureRadar Corp", [_cap_record(naics="334511")], scale={"max_contract_usd": 80000000})
    result = evaluate_fit(cons, profile, requirements={"clearance": "FCL_SECRET"})
    assert result.posture == "NO_FIT"
    assert any(b["code"] == "security_clearance_mismatch" for b in result.blockers)


def test_zero_capability_requirement_is_unknown_not_prime():
    cons = _consequence([])  # consequence declares no specific capability
    profile = build_profile("Anyone Inc", [_cap_record(naics="334511")], scale={"max_contract_usd": 80000000})
    result = evaluate_fit(cons, profile)
    assert result.posture == "NO_FIT" and result.is_unknown


# --- temporal ------------------------------------------------------------------

def test_future_capability_evidence_is_excluded():
    cons = _consequence(["radar_component_manufacturing"])
    profile = build_profile("Future Corp", [_cap_record(naics="334511", at="2025-06-01T00:00:00+00:00")],
                            as_of="2024-11-01T23:59:59+00:00", scale={"max_contract_usd": 80000000})
    result = evaluate_fit(cons, profile, as_of="2024-11-01T23:59:59+00:00")
    assert result.posture == "NO_FIT" and result.is_unknown  # future evidence cannot establish earlier fit


def test_first_supportable_at_is_the_later_of_consequence_and_capability():
    cons = _consequence(["radar_component_manufacturing"])
    profile = build_profile("Coastal", [_cap_record(naics="334511", at="2021-01-01T00:00:00+00:00")],
                            scale={"max_contract_usd": 80000000},
                            contract_history=[{"agency": "Department of the Navy", "naics": "334511", "role": "prime",
                                               "award_ref": "H", "available_at": "2022-01-01T00:00:00+00:00"}])
    result = evaluate_fit(cons, profile)
    assert result.first_supportable_at == "2024-06-01T00:00:00+00:00"  # consequence gates it


# --- human review --------------------------------------------------------------

def test_fit_review_accept_reject_defer(tmp_path):
    store = StateStore(tmp_path)
    cons = _consequence(["radar_component_manufacturing"])
    profile = build_profile("Coastal", [_cap_record(naics="334511")], scale={"max_contract_usd": 80000000})
    result = evaluate_fit(cons, profile)
    enqueue_fit_review(store, result)
    enqueue_fit_review(store, result)  # idempotent
    assert len(pending_fit_reviews(store)) == 1
    review = adjudicate_fit(store, result.id, decision="ACCEPT_FIT", reviewer="analyst", reason="checked")
    assert review["automated_posture"] == result.posture
    assert review["pre_review_confidence"] == result.fit_confidence
    assert pending_fit_reviews(store) == []


# --- corpus acceptance ---------------------------------------------------------

def test_m8_fit_corpus_all_expected_pass_and_precision_clean():
    summary = summarize_fit_results(run_fit_corpus(load_corpus(M8)))
    assert summary["expected_fit_passing"] == summary["expected_fit_cases"] == 5
    assert summary["fit_precision"] == 1.0
    assert summary["no_fit_precision"] == 1.0
    assert summary["false_match_rate"] == 0.0
    assert summary["posture_precision_overall"] == 1.0
    assert {"PRIME", "SUPPORT", "TEAM", "DEFEND", "NO_FIT"} <= set(
        p for p, n in summary["posture_distribution"].items() if n > 0)
    assert summary["blocker_accuracy"] == 1.0
    assert summary["unknown_rate"] > 0  # unknown-fit cases are represented
    assert summary["small_sample_warning"]


def test_scoring_v1_stable_and_frozen_corpora_unchanged_under_m8():
    m8 = summarize_results(run_corpus(load_corpus(M8)))
    assert m8["case_count"] == 48
    assert m8["false_negative_rate"] == 0.0
    assert m8["confusion_matrix"]["false_strike"] == 1  # no new false positive
    for corpus, cases, prec in ((M7, 43, 0.875),):
        m = summarize_results(run_corpus(load_corpus(corpus)))
        assert m["case_count"] == cases and m["strike_precision"] == prec
