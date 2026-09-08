"""M5 opportunity evolution / state-transition history."""

from pyrnova.replay import load_corpus
from pyrnova.transitions import derive_transitions, transition_summary

CORPUS = "examples/replay/corpus_m5.json"


def _case(case_id: str) -> dict:
    return next(c for c in load_corpus(CORPUS) if c["case_id"] == case_id)


def test_lifecycle_promotes_watch_then_strike_with_evidence_causes():
    transitions = derive_transitions(_case("chain-navy-c5isr-lifecycle-2023"))
    summary = transition_summary(transitions)
    assert summary["trajectory"] == ["WATCH", "STRIKE"]
    watch, strike = transitions
    assert watch.prior_disposition is None and watch.new_disposition == "WATCH"
    assert watch.cause_stage == "MARKET_ENGAGEMENT"
    assert strike.prior_disposition == "WATCH" and strike.new_disposition == "STRIKE"
    assert strike.cause_stage == "PROCUREMENT"
    assert strike.cause_source_id == "sam_opportunities"
    assert summary["reached_strike"] is True


def test_transitions_are_point_in_time_and_carry_scoring_version():
    transitions = derive_transitions(_case("chain-navy-c5isr-lifecycle-2023"))
    # Every transition is attributed to a cutoff at or before the case horizon.
    assert all(t.occurred_at <= "2025-01-22T23:59:59+00:00" for t in transitions)
    assert all(t.scoring_version == "scoring_v1" for t in transitions)


def test_grant_stays_watch_and_does_not_fake_a_strike():
    transitions = derive_transitions(_case("chain-doe-battery-hub-downstream-2022"))
    summary = transition_summary(transitions)
    assert summary["trajectory"] == ["WATCH"]
    assert summary["reached_strike"] is False
    assert transitions[0].cause_stage == "FUNDING"


def test_transition_derivation_is_deterministic():
    case = _case("chain-navy-c5isr-lifecycle-2023")
    a = [(t.new_disposition, t.occurred_at) for t in derive_transitions(case)]
    b = [(t.new_disposition, t.occurred_at) for t in derive_transitions(case)]
    assert a == b
