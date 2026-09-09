"""M11 — production opportunity lifecycle + append-only outcome learning (offline).

Authoritative point-in-time outcomes, preserved predictions, never infer loss from absence, strict
future-outcome exclusion, and challengers evaluated but never promoted. scoring_v1 stays production.
"""

import json
from pathlib import Path

import pytest

from pyrnova.outcomes import (
    CAPTURE_NEGATIVE,
    CAPTURE_POSITIVE,
    OUTCOME_LABELS,
    OutcomeObservation,
    build_learning_record,
    evaluate_challenger,
    load_outcome_corpus,
    record_observation,
    resolve_outcome,
    run_outcome_corpus,
    summarize_learning,
)
from pyrnova.replay import ACTIVE_SCORING_VERSION, load_corpus
from pyrnova.state import StateStore

M10 = "examples/replay/corpus_m10.json"
M11_PATH = "examples/replay/corpus_m11.json"


def _payload():
    return load_outcome_corpus(M11_PATH)


def _records():
    return run_outcome_corpus(_payload())


# ---------------------------------------------------------------- corpus wiring

def test_m11_extends_frozen_m10_and_all_cases_pass():
    payload = _payload()
    assert payload["extends"] == "corpus_m10.json"
    records = run_outcome_corpus(payload)
    assert len(records) == 13
    assert all(r["ok"] for r in records)


def test_all_twelve_authoritative_labels_are_exercised():
    dist = summarize_learning(_records())["outcome_distribution"]
    assert set(dist) == set(OUTCOME_LABELS)  # every label appears at least once


def test_learning_metrics_are_exact_and_directional():
    s = summarize_learning(_records())
    assert s["ledger_size"] == 13
    assert s["resolved_count"] == 11 and s["unknown_count"] == 2
    assert s["resolution_rate"] == 0.8462
    assert s["capture_count"] == 4
    assert s["win_rate_among_contested"] == 0.6667
    assert s["confirmed"] == 4 and s["overcalled"] == 2
    assert s["loss_inferred_from_absence"] == 0  # hard invariant
    assert s["future_outcomes_excluded"] == 1
    assert s["small_sample_warning"]


# ---------------------------------------------------------------- invariants

def test_absence_resolves_to_unknown_never_loss():
    r = next(r for r in _records() if r["case_id"] == "m11-absence-is-unknown-not-loss")
    assert r["outcome_label"] == "UNKNOWN"
    assert r["outcome_label"] not in CAPTURE_NEGATIVE
    assert r["resolved_outcome"]["loss_inferred_from_absence"] is False
    assert r["resolved_outcome"]["resolved"] is False


def test_future_outcome_is_strictly_excluded():
    r = next(r for r in _records() if r["case_id"] == "m11-future-outcome-excluded")
    assert r["outcome_label"] == "UNKNOWN"  # the 2025 WON must not leak into a 2024-06 reconstruction
    assert r["resolved_outcome"]["future_excluded_count"] == 1
    assert "W-FUTURE-2025-0001" in r["resolved_outcome"]["future_excluded_refs"]


def test_prediction_is_preserved_verbatim():
    payload = _payload()
    case = next(c for c in payload["outcome_cases"] if c["case_id"] == "m11-won-army-hwil")
    record = build_learning_record(case["prediction"], case["observations"], as_of=case["replay_as_of"])
    assert record["prediction"] == case["prediction"]  # untouched snapshot
    assert record["outcome_label"] == "WON" and record["correctness"] == "CONFIRMED"


def test_unknown_is_not_a_recordable_observation():
    with pytest.raises(ValueError):
        OutcomeObservation("opp-x", "UNKNOWN", "2024-01-01T00:00:00+00:00", "s", "r")


def test_negative_outcomes_cannot_be_inferred_without_a_source():
    # LOST/AWARD_TO_OTHER require an explicit dated source_ref — never inferred from absence.
    with pytest.raises(ValueError):
        OutcomeObservation("opp-x", "LOST", "2024-01-01T00:00:00+00:00", "s", "")
    with pytest.raises(ValueError):
        OutcomeObservation("opp-x", "AWARD_TO_OTHER", "", "s", "r")
    with pytest.raises(ValueError):  # authoritative negative needs strength >= 3
        OutcomeObservation("opp-x", "LOST", "2024-01-01T00:00:00+00:00", "s", "r", evidence_strength=2)


def test_resolution_prefers_authoritative_over_open_state():
    obs = [
        {"opportunity_id": "o", "label": "DELAYED", "observed_at": "2024-01-01T00:00:00+00:00",
         "source_id": "sam", "source_ref": "amd-1", "evidence_strength": 3},
        {"opportunity_id": "o", "label": "WON", "observed_at": "2024-03-01T00:00:00+00:00",
         "source_id": "usaspending", "source_ref": "award-1", "evidence_strength": 5},
    ]
    assert resolve_outcome(obs, as_of="2024-06-01T00:00:00+00:00")["label"] == "WON"
    # As of the earlier cutoff only DELAYED is knowable.
    assert resolve_outcome(obs, as_of="2024-02-01T00:00:00+00:00")["label"] == "DELAYED"


# ---------------------------------------------------------------- append-only store

def test_observations_are_append_only_and_idempotent(tmp_path):
    store = StateStore(tmp_path)
    obs = OutcomeObservation("opp-1", "WON", "2024-01-01T00:00:00+00:00", "usaspending", "award-1",
                             evidence_strength=5)
    id1 = record_observation(store, obs)
    id2 = record_observation(store, obs)  # same observation -> no duplicate row
    assert id1 == id2
    assert store.count("outcome_observations") == 1


# ---------------------------------------------------------------- challenger is eval-only

def test_challenger_is_evaluated_but_never_promoted():
    ev = evaluate_challenger(
        _records(), challenger="scoring_v2_recompete_bias",
        predicted_positive=lambda p: p.get("precursor_class") == "recompete_expiry",
    )
    assert ev["promoted"] is False
    assert ev["production_scoring_version"] == "scoring_v1"
    assert ev["contested_cases"] == 6
    assert ev["precision"] == 0.75 and ev["recall"] == 0.75
    # Production scorer is untouched by any challenger evaluation.
    assert ACTIVE_SCORING_VERSION == "scoring_v1"


# ---------------------------------------------------------------- scoring frozen

def test_scoring_v1_and_frozen_lifecycle_unchanged():
    # The frozen canonical scoring base (M9) still loads unchanged; outcome learning adds nothing to
    # scoring. The M10 fit corpus (constructed opportunity probes) chains onto it via `extends`.
    assert len(load_corpus("examples/replay/corpus_m9.json")) == 55
    assert json.loads(Path(M10).read_text(encoding="utf-8"))["extends"] == "corpus_m9.json"
    assert json.loads(Path(M11_PATH).read_text(encoding="utf-8"))["extends"] == "corpus_m10.json"
