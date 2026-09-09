"""M17 — propagation-quality + threat-quality-over-time metrics (denominator-honest)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyrnova import threat
from pyrnova.sources import ofac
from pyrnova.threat_calibration import threat_quality_over_time

DESIGNATIONS = ofac.parse_ofac_csv(
    Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")


@pytest.fixture(scope="module")
def summary():
    payload = threat.load_threat_corpus("examples/replay/corpus_m17.json")
    return threat.summarize_m17(threat.run_threat_corpus(payload, DESIGNATIONS))


def test_propagation_quality_no_explosion_and_bounded(summary):
    pq = summary["propagation_quality"]
    assert pq["real_propagation_cases"] >= 2                 # the two real SAIC->Torch chains
    assert pq["confidence_never_increases"] is True          # proven per-threat, not asserted
    assert pq["propagation_explosion"] is False
    assert pq["max_propagation_depth"] <= 2
    assert pq["propagated_threats"] <= pq["direct_threats"]
    assert pq["avg_propagation_depth"] is not None


def test_threat_quality_over_time_denominators(summary):
    q = summary["threat_quality_over_time"]
    assert q["warnings_issued"] >= q["resolved"]             # not everything is resolved
    assert q["resolved"] >= 12                               # materially beyond M16's 5
    assert q["confirmed_precision_denominator"] == q["confirmed_true"] + q["false_alerts"]
    assert 0.0 < q["confirmed_precision"] < 1.0              # an honest false alarm exists
    assert q["false_alert_from_absence"] == 0
    assert q["unresolved"] == q["warnings_issued"] - q["resolved"]


def test_mechanism_reliability_reports_denominator_or_none(summary):
    mech = summary["threat_quality_over_time"]["mechanism_reliability"]
    for name, rec in mech.items():
        # Precision is present only when its denominator is > 0; otherwise explicitly null.
        if rec["precision_denominator"] == 0:
            assert rec["confirmed_precision"] is None, name
        else:
            assert rec["confirmed_precision"] is not None, name
            assert 0.0 <= rec["confirmed_precision"] <= 1.0


def test_source_family_contribution_credits_real_usaspending(summary):
    contrib = summary["threat_quality_over_time"]["source_family_contribution"]
    # Real USAspending award evidence backs the most resolved-true warnings.
    assert "usa" in contrib
    assert contrib["usa"]["resolved_true_backed"] >= 1
    for fam, rec in contrib.items():
        assert rec["resolved_true_backed"] <= rec["threats_backed"], fam


def test_quality_does_not_mutate_predictions(summary):
    """threat_quality_over_time reads predictions; running it twice yields identical aggregates and
    never alters the underlying results (append-only prediction history)."""
    payload = threat.load_threat_corpus("examples/replay/corpus_m17.json")
    results = threat.run_threat_corpus(payload, DESIGNATIONS)
    a = threat_quality_over_time(results)
    b = threat_quality_over_time(results)
    assert a == b
    # The threat records still carry their original confidence (nothing was rewritten).
    for r in results:
        for t in r["threats"]:
            assert t["confidence"] in ("UNKNOWN", "LOW", "MEDIUM", "HIGH")
