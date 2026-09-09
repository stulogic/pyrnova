"""M16 — merged threat corpus (m15+m16) replay + propagation + calibration metrics."""

from __future__ import annotations

from pathlib import Path

from pyrnova import threat
from pyrnova.sources import ofac

CORPUS = Path("examples/replay/corpus_m16.json")
DESIGNATIONS = ofac.parse_ofac_csv(
    Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn"
)


def _results():
    payload = threat.load_threat_corpus(CORPUS)
    return payload, threat.run_threat_corpus(payload, DESIGNATIONS)


def test_merged_corpus_all_pass_and_extends_m15():
    payload, results = _results()
    assert payload["extends"] == "corpus_m15.json"
    # merged = 17 (m15) + 18 (m16)
    assert len(results) == 35
    failed = [(r["case_id"], [c for c in r["checks"] if not c["ok"]]) for r in results if not r["ok"]]
    assert not failed, failed


def test_new_exposure_families_exercised():
    _, results = _results()
    mechanisms = {t["mechanism"] for r in results for t in r["threats"]}
    assert {"SUPPLIER_DEPENDENCY_DISRUPTION", "TECHNOLOGY_SUBSTITUTION",
            "GEOGRAPHY_FACILITY_DISRUPTION"} <= mechanisms


def test_propagation_bounded_and_present():
    _, results = _results()
    m = threat.summarize_m16(results)
    assert m["propagation_cases"] >= 2
    assert m["propagated_threats"] >= 3          # 1 + 2 across the two cases
    assert m["beneficiary_opportunities"] >= 2
    assert m["max_propagation_depth"] == 2       # bounded
    assert m["direct_threats"] > m["propagated_threats"]   # no propagation explosion


def test_calibration_reports_precision_with_denominator():
    _, results = _results()
    cal = threat.summarize_m16(results)["calibration"]
    # 4 resolved TRUE_THREAT outcomes (materialized/avoided/mitigated/delayed), 0 false alerts.
    assert cal["resolved_outcomes"] >= 4
    assert cal["confirmed_threat_precision"] == 1.0
    assert cal["confirmed_threat_precision_denominator"] >= 4
    assert cal["false_alert_from_absence"] == 0
    assert cal["median_lead_time_days"] is not None
    assert cal["unresolved_threats"] >= 2        # unresolved never counted false


def test_expanded_negative_corpus():
    _, results = _results()
    reasons = {rj["reason_code"] for r in results for rj in r["rejections"]}
    assert {"NO_DEPENDENCY", "VAGUE_TREND_NOT_EVIDENCE", "OUTSIDE_EXPOSURE_GEOGRAPHY",
            "WEAK_NAME_MATCH_ONLY", "NO_EXPOSURE", "IMMATERIAL"} <= reasons


def test_frozen_m15_corpus_still_loads_unchanged():
    # Loading m15 directly must be unaffected by the m16 chain-merge.
    payload = threat.load_threat_corpus("examples/replay/corpus_m15.json")
    assert payload["extends"] == "corpus_m11.json"
    assert len(payload["threat_cases"]) == 17
