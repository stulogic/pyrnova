"""Focused tests for the derived Decision Lead Time model (B1.3)."""

from pyrnova.decision_lead_time import (
    NOT_ESTABLISHED,
    UNKNOWN,
    TemporalAnchors,
    derive_decision_lead_time,
    from_customer_material_change,
)


def test_full_anchors_derive_all_latencies():
    a = TemporalAnchors(
        t0_source_available_at="2026-01-01T00:00:00+00:00",
        t1_acquired_at="2026-01-03T00:00:00+00:00",   # +2d acquisition
        t2_resolved_at="2026-01-04T00:00:00+00:00",
        t3_assessed_at="2026-01-08T00:00:00+00:00",    # +5d analysis (T1->T3)
        t4_customer_ready_at="2026-01-10T00:00:00+00:00",  # +2d readiness
        benchmark_b="2026-04-10T00:00:00+00:00",       # 90d external lead vs ordinary env
    )
    d = derive_decision_lead_time(a)
    assert d["acquisition_latency_days"] == 2.0
    assert d["analysis_latency_days"] == 5.0
    assert d["customer_readiness_latency_days"] == 2.0
    assert d["internal_pipeline_latency_days"] == 9.0  # T0 -> T4
    assert d["external_decision_lead_time_days"] == 90.0
    assert d["external_lead_time_established"] is True
    assert d["anomalies"] == []
    assert d["anchors"]["T3_source"] == "explicit"


def test_benchmark_b_absent_is_not_established_never_fabricated():
    a = TemporalAnchors(
        t0_source_available_at="2026-01-01T00:00:00+00:00",
        t1_acquired_at="2026-01-02T00:00:00+00:00",
        t4_customer_ready_at="2026-01-05T00:00:00+00:00",
    )
    d = derive_decision_lead_time(a)
    assert d["external_decision_lead_time_days"] == NOT_ESTABLISHED
    assert d["external_lead_time_established"] is False
    assert d["anchors"]["B_benchmark"] == NOT_ESTABLISHED


def test_missing_t3_derives_from_t2_and_records_source():
    a = TemporalAnchors(
        t0_source_available_at="2026-01-01T00:00:00+00:00",
        t1_acquired_at="2026-01-02T00:00:00+00:00",
        t2_resolved_at="2026-01-04T00:00:00+00:00",
        t4_customer_ready_at="2026-01-06T00:00:00+00:00",
    )
    d = derive_decision_lead_time(a)
    assert d["anchors"]["T3_assessed_at"] == "2026-01-04T00:00:00+00:00"
    assert d["anchors"]["T3_source"] == "derived_from_T2"
    assert d["analysis_latency_days"] == 2.0  # T1 -> derived T3
    assert d["customer_readiness_latency_days"] == 2.0


def test_missing_endpoint_is_unknown_not_zero():
    d = derive_decision_lead_time(TemporalAnchors(t1_acquired_at="2026-01-02T00:00:00+00:00"))
    assert d["acquisition_latency_days"] == UNKNOWN  # T0 missing
    assert d["internal_pipeline_latency_days"] == UNKNOWN
    assert d["anchors"]["T0_source_available_at"] == UNKNOWN


def test_negative_span_is_flagged_as_anomaly():
    a = TemporalAnchors(
        t0_source_available_at="2026-01-05T00:00:00+00:00",
        t1_acquired_at="2026-01-01T00:00:00+00:00",  # acquired before public availability -> anomaly
        t4_customer_ready_at="2026-01-10T00:00:00+00:00",
    )
    d = derive_decision_lead_time(a)
    assert d["acquisition_latency_days"] == -4.0
    assert "acquisition_latency" in d["anomalies"]


def test_from_customer_material_change_reuses_existing_first_seen_semantics():
    cmc = {
        "intelligence_observed_at": "2026-02-01T00:00:00+00:00",
        "first_relevant_at": "2026-02-03T00:00:00+00:00",
        "delivered_at": "2026-02-04T00:00:00+00:00",
    }
    d = from_customer_material_change(cmc, acquired_at="2026-02-02T00:00:00+00:00")
    assert d["anchors"]["T0_source_available_at"] == "2026-02-01T00:00:00+00:00"
    assert d["anchors"]["T2_resolved_at"] == "2026-02-01T00:00:00+00:00"
    assert d["anchors"]["T4_customer_ready_at"] == "2026-02-04T00:00:00+00:00"
    assert d["acquisition_latency_days"] == 1.0
    assert d["internal_pipeline_latency_days"] == 3.0
    # No benchmark supplied -> external lead time is honestly not established.
    assert d["external_lead_time_established"] is False


def test_from_cmc_falls_back_to_first_relevant_when_undelivered():
    cmc = {"intelligence_observed_at": "2026-02-01T00:00:00+00:00",
           "first_relevant_at": "2026-02-03T00:00:00+00:00"}
    d = from_customer_material_change(cmc)
    assert d["anchors"]["T4_customer_ready_at"] == "2026-02-03T00:00:00+00:00"
