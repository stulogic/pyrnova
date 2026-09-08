"""M6 inferred-join calibration, entity predicates, and corpus acceptance."""

from pyrnova.chains import (
    _INFERRED_ACCEPT_THRESHOLD,
    _INFERRED_DEFER_FLOOR,
    resolve_chain,
    resolve_entity_relationships,
    score_inferred_join,
)
from pyrnova.precursors import ProgramSignal
from pyrnova.replay import load_corpus, run_chain_corpus, run_corpus, summarize_chain_results
from pyrnova.metrics import summarize_results

M4 = "examples/replay/corpus_m4.json"
M5 = "examples/replay/corpus_m5.json"
M6 = "examples/replay/corpus_m6.json"


def _sig(source, ref, stage, program, *, at, agency=None, program_identifier=None, uei=None,
         parent_uei=None, geography=None, amount=None, summary=None, downstream=()):
    return ProgramSignal(
        source_id=source, source_ref=ref, stage=stage, program_key=program,
        summary=summary or ref, available_at=at, agency=agency, geography=geography,
        downstream_refs=tuple(downstream),
        meta={"program_identifier": program_identifier, "entity_uei": uei,
              "parent_uei": parent_uei, "amount_usd": amount,
              "place_of_performance": geography},
    )


# --- weighted inference scoring -------------------------------------------------

def test_shared_program_identifier_plus_agency_accepts_at_threshold():
    left = _sig("appropriations", "a1", "FUNDING", "doe:x", at="2022-01-01T00:00:00+00:00",
                agency="Department of Energy", program_identifier="81.086")
    right = _sig("usaspending", "u1", "AWARD", "doe:y", at="2023-01-01T00:00:00+00:00",
                 agency="Department of Energy", program_identifier="81.086")
    score = score_inferred_join(left, right)
    assert score.anchored and score.disposition == "accept"
    assert score.confidence == _INFERRED_ACCEPT_THRESHOLD  # 0.45 anchor + 0.15 agency == 0.60


def test_entity_uei_match_is_an_anchor():
    left = _sig("grants_gov", "g1", "FUNDING", "navy:a", at="2023-01-01T00:00:00+00:00",
                agency="Department of the Navy", uei="ABC123DEF4567")
    right = _sig("usaspending", "u1", "AWARD", "navy:b", at="2024-01-01T00:00:00+00:00",
                 agency="Department of the Navy", uei="ABC123DEF4567")
    score = score_inferred_join(left, right)
    assert "entity_uei:ABC123DEF4567" in score.anchors
    assert score.disposition == "accept"


def test_topic_and_agency_without_anchor_cannot_reach_threshold():
    # Even maximal non-anchor evidence (agency + identical topic) is capped below the threshold.
    left = _sig("s1", "r1", "MARKET_ENGAGEMENT", "doi:a", at="2024-01-01T00:00:00+00:00",
                agency="Department of the Interior", summary="wildfire detection sensor network")
    right = _sig("s2", "r2", "PROCUREMENT", "doi:b", at="2024-05-01T00:00:00+00:00",
                 agency="Department of the Interior", summary="wildfire detection sensor network")
    score = score_inferred_join(left, right)
    assert not score.anchored
    assert score.confidence < _INFERRED_ACCEPT_THRESHOLD
    assert score.disposition == "reject"


def test_agency_conflict_invalidates_shared_identifier():
    left = _sig("appropriations", "a1", "FUNDING", "doe:x", at="2023-02-01T00:00:00+00:00",
                agency="Department of Energy", program_identifier="12.800")
    right = _sig("sam_opportunities", "s1", "PROCUREMENT", "dod:y", at="2023-06-01T00:00:00+00:00",
                 agency="Department of Defense", program_identifier="12.800")
    score = score_inferred_join(left, right)
    assert score.anchored  # a shared identifier exists...
    assert ("agency_conflict", 0.40) in score.penalties
    assert score.disposition == "reject" and score.reject_reason == "inference_contradiction"


def test_temporal_impossibility_rejects_even_with_identifier():
    # Earlier-stage record postdates the later-stage record it supposedly precedes.
    left = _sig("appropriations", "a1", "AUTHORIZATION", "navy:auth", at="2024-01-05T00:00:00+00:00",
                agency="Department of the Navy", program_identifier="PE0604567N")
    right = _sig("sam_opportunities", "s1", "PROCUREMENT", "navy:proc", at="2022-03-01T00:00:00+00:00",
                 agency="Department of the Navy", program_identifier="PE0604567N")
    score = score_inferred_join(left, right)
    assert ("temporal_impossibility", 0.40) in score.penalties
    assert score.disposition == "reject"


def test_fragment_anchor_lands_in_defer_band():
    left = _sig("acquisition_forecast", "GSA-2024-CLOUD-889001", "MARKET_ENGAGEMENT", "gsa:a",
                at="2024-03-01T00:00:00+00:00", agency="General Services Administration",
                summary="cloud infrastructure modernization")
    right = _sig("sam_opportunities", "SOL-889001-GSA-CLOUD", "PROCUREMENT", "gsa:b",
                 at="2024-08-01T00:00:00+00:00", agency="General Services Administration",
                 summary="cloud infrastructure modernization")
    score = score_inferred_join(left, right)
    assert any(a.startswith("fragment:") for a in score.anchors)
    assert _INFERRED_DEFER_FLOOR <= score.confidence < _INFERRED_ACCEPT_THRESHOLD
    assert score.disposition == "defer"


def test_confidence_is_deterministic():
    left = _sig("appropriations", "a1", "FUNDING", "doe:x", at="2022-01-01T00:00:00+00:00",
                agency="Department of Energy", program_identifier="81.086")
    right = _sig("usaspending", "u1", "AWARD", "doe:y", at="2023-01-01T00:00:00+00:00",
                 agency="Department of Energy", program_identifier="81.086")
    assert score_inferred_join(left, right) == score_inferred_join(left, right)


def test_resolve_chain_defers_ambiguous_join_and_keeps_rationale():
    signals = [
        _sig("acquisition_forecast", "GSA-2024-CLOUD-889001", "MARKET_ENGAGEMENT", "gsa:a",
             at="2024-03-01T00:00:00+00:00", agency="General Services Administration",
             summary="cloud infrastructure modernization"),
        _sig("sam_opportunities", "SOL-889001-GSA-CLOUD", "PROCUREMENT", "gsa:b",
             at="2024-08-01T00:00:00+00:00", agency="General Services Administration",
             summary="cloud infrastructure modernization"),
    ]
    resolution = resolve_chain(signals)
    assert resolution.relationships == ()
    assert len(resolution.deferred) == 1
    deferred = resolution.deferred[0]
    assert deferred.automated_recommendation == "DEFER"
    assert "fragment" in deferred.rationale
    assert deferred.to_queue_record()["join_method"] == "inferred_strong_attribute"


# --- entity predicates ----------------------------------------------------------

def test_entity_predicates_from_authoritative_fields():
    signals = [
        _sig("usaspending", "u1", "AWARD", "navy:b", at="2024-01-01T00:00:00+00:00",
             agency="Department of the Navy", uei="ABC123DEF4567", parent_uei="PARENT99887766",
             geography="Crane, IN"),
    ]
    rels = resolve_entity_relationships(signals)
    predicates = {r.predicate for r in rels}
    assert predicates == {"AWARDED_TO", "SUBSIDIARY_OF", "LOCATED_AT"}
    assert all(r.join_method == "authoritative_entity_field" and r.confidence == 0.95 for r in rels)
    assert all(r.first_observed_at == "2024-01-01T00:00:00+00:00" for r in rels)


def test_entity_predicates_require_uei():
    signals = [_sig("usaspending", "u1", "AWARD", "navy:b", at="2024-01-01T00:00:00+00:00",
                    agency="Department of the Navy", geography="Crane, IN")]
    assert resolve_entity_relationships(signals) == []


# --- corpus acceptance ----------------------------------------------------------

def test_frozen_baselines_unchanged_under_m6():
    m4 = summarize_results(run_corpus(load_corpus(M4)))
    m5 = summarize_results(run_corpus(load_corpus(M5)))
    assert m4["case_count"] == 23 and m4["strike_precision"] == 0.6667
    assert m5["case_count"] == 27 and m5["strike_precision"] == 0.75


def test_m6_scoring_keeps_fnr_zero_and_no_new_false_positive():
    m6 = summarize_results(run_corpus(load_corpus(M6)))
    assert m6["case_count"] == 35
    assert m6["false_negative_rate"] == 0.0
    # The only false strike is inherited; M6 adds one true-positive STRIKE (the appropriation chain).
    assert m6["confusion_matrix"]["true_strike"] == 4
    assert m6["confusion_matrix"]["false_strike"] == 1
    assert m6["strike_precision"] == 0.8


def test_m6_inferred_calibration_is_measurable_and_clean():
    summary = summarize_chain_results(run_chain_corpus(load_corpus(M6)))
    assert summary["expected_chain_passing"] == summary["expected_chain_cases"]
    assert summary["inferred_accepted_cases"] == 2
    assert summary["inferred_true_join_cases"] == 2
    assert summary["inferred_false_join_cases"] == 0
    assert summary["inferred_precision"] == 1.0
    assert summary["inferred_false_join_rate"] == 0.0
    assert summary["deferred_joins"] == 1
    assert summary["rejected_weak_joins"] >= 4
    assert set(summary["entity_predicates_exercised"]) == {"AWARDED_TO", "SUBSIDIARY_OF", "LOCATED_AT"}
    assert summary["small_sample_warning"]  # never hidden


def test_m6_precursor_chain_extends_lead_time_from_appropriation():
    from pyrnova.replay import run_chain_replay
    case = next(c for c in load_corpus(M6) if c["case_id"] == "m6-precursor-appropriation-chain-airforce-2021")
    result = run_chain_replay(case)
    # Appropriation (2021-03-15) to award (2024-02-01): earlier than any procurement-anchored signal.
    assert result["chain_lead_time_days"] == 1053
    assert result["transitions"]["trajectory"] == ["WATCH", "STRIKE"]
    assert result["expected_chain_ok"] is True
