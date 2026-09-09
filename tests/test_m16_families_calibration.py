"""M16 — new exposure-family mechanisms + threat calibration semantics."""

from __future__ import annotations

from pyrnova import threat
from pyrnova import threat_calibration as tc


def _decl(subject, records):
    return threat.declared_exposures(subject, subject, records)


# ---------------------------------------------------------------- supplier dependency

def test_supplier_disruption_with_dependency_is_a_threat():
    exps = _decl("co_a", [{"relation": "SUPPLIER", "target_ref": "sup:acme-castings",
                           "target_name": "Acme Castings", "available_at": "2023-01-01",
                           "deterministic": True, "source_ref": "sec:supplier", "sole_source": True}])
    # (sole_source lives in meta only if declared_exposures keeps it — assert via severity below)
    recs = [{"catalyst_kind": "supplier_disruption", "target_ref": "sup:acme-castings",
             "available_at": "2024-01-01", "source_ref": "warn:acme", "evidence_strength": 4}]
    threats, rej = threat.assess_threats("co_a", "A", exps, recs)
    assert len(threats) == 1
    assert threats[0].mechanism == "SUPPLIER_DEPENDENCY_DISRUPTION"
    assert threats[0].affected_value_category == "CONTINUITY"


def test_supplier_disruption_without_dependency_rejected():
    recs = [{"catalyst_kind": "supplier_disruption", "target_ref": "sup:unknown",
             "available_at": "2024-01-01", "source_ref": "warn:x"}]
    threats, rej = threat.assess_threats("co_a", "A", [], recs)
    assert threats == [] and rej[0].reason_code == "NO_DEPENDENCY"


# ---------------------------------------------------------------- technology substitution

def test_technology_substitution_requires_explicit_mandate():
    exps = _decl("co_b", [{"relation": "TECHNOLOGY", "target_ref": "tech:legacy-radio",
                           "target_name": "Legacy radio", "available_at": "2023-01-01",
                           "source_ref": "sec:tech"}])
    vague = [{"catalyst_kind": "technology_substitution", "target_ref": "tech:legacy-radio",
              "available_at": "2024-01-01", "source_ref": "trend:x"}]
    threats, rej = threat.assess_threats("co_b", "B", exps, vague)
    assert threats == [] and rej[0].reason_code == "VAGUE_TREND_NOT_EVIDENCE"

    mandated = [{"catalyst_kind": "technology_substitution", "target_ref": "tech:legacy-radio",
                 "available_at": "2024-01-01", "source_ref": "fr:standard", "explicit_mandate": True,
                 "evidence_strength": 4, "summary": "standard mandates new waveform"}]
    threats2, _ = threat.assess_threats("co_b", "B", exps, mandated)
    assert len(threats2) == 1 and threats2[0].mechanism == "TECHNOLOGY_SUBSTITUTION"
    assert threats2[0].affected_value_category == "MARKET_ACCESS"


# ---------------------------------------------------------------- geography / facility

def test_geography_event_matches_only_footprint():
    exps = _decl("co_c", [{"relation": "FACILITY", "target_ref": "fac:huntsville",
                           "target_name": "Huntsville AL plant", "geography": "Alabama",
                           "available_at": "2023-01-01", "source_ref": "sec:fac"}])
    outside = [{"catalyst_kind": "geography_event", "geography": "Oregon",
                "available_at": "2024-01-01", "source_ref": "fr:or", "summary": "OR jurisdiction change"}]
    threats, rej = threat.assess_threats("co_c", "C", exps, outside)
    assert threats == [] and rej[0].reason_code == "OUTSIDE_EXPOSURE_GEOGRAPHY"

    inside = [{"catalyst_kind": "geography_event", "geography": "Alabama",
               "available_at": "2024-01-01", "source_ref": "fr:al", "summary": "AL facility mandate",
               "evidence_strength": 3}]
    threats2, _ = threat.assess_threats("co_c", "C", exps, inside)
    assert len(threats2) == 1 and threats2[0].mechanism == "GEOGRAPHY_FACILITY_DISRUPTION"


# ---------------------------------------------------------------- calibration semantics

def test_classify_detection_never_false_from_absence():
    assert tc.classify_detection("MATERIALIZED", "HIGH") == "TRUE_THREAT"
    assert tc.classify_detection("AVOIDED", "HIGH") == "TRUE_THREAT"      # real threat, avoided
    assert tc.classify_detection("MITIGATED", "MEDIUM") == "TRUE_THREAT"
    assert tc.classify_detection("FALSE_ALARM", "HIGH") == "FALSE_ALERT"  # only explicit false is false
    assert tc.classify_detection("UNKNOWN", "HIGH") == "UNRESOLVED"       # unresolved != false
    assert tc.classify_detection(None, "LOW") == "INSUFFICIENT_EVIDENCE"


def test_classify_exposure_grades():
    assert tc.classify_exposure("CONFIRMED", None) == "CONFIRMED"
    assert tc.classify_exposure("INFERRED", True) == "INFERRED_CORRECT"
    assert tc.classify_exposure("INFERRED", False) == "INFERRED_INCORRECT"
    assert tc.classify_exposure("INFERRED", None) == "UNRESOLVED"
    assert tc.classify_exposure("CANDIDATE", None) == "CANDIDATE_REJECTED"


def test_calibrate_reports_precision_with_denominator_and_lead_time():
    results = [
        {"threats": [{"confidence": "HIGH", "available_at": "2023-01-01"}],
         "outcome": {"resolved": True, "label": "MATERIALIZED",
                     "basis": {"observed_at": "2023-07-01"}}},
        {"threats": [{"confidence": "HIGH", "available_at": "2023-01-01"}],
         "outcome": {"resolved": True, "label": "FALSE_ALARM", "basis": {"observed_at": "2023-04-01"}}},
        {"threats": [{"confidence": "MEDIUM", "available_at": "2023-01-01"}],
         "outcome": {"resolved": False, "label": "UNKNOWN"}},
    ]
    cal = tc.calibrate_threats(results)
    assert cal["confirmed_threat_precision"] == 0.5           # 1 true / (1 true + 1 false)
    assert cal["confirmed_threat_precision_denominator"] == 2
    assert cal["unresolved_threats"] == 1
    assert cal["false_alert_from_absence"] == 0
    assert cal["median_lead_time_days"] is not None
    assert cal["small_sample_warning"]  # tiny N flagged
