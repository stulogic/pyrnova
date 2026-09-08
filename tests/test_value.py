"""Tests for pyrnova.value — evidence-backed value-estimation foundation (M7)."""

from __future__ import annotations

from pyrnova.value import ValueEstimate, estimate_value, parse_amount


def test_explicit_amount_known():
    est = estimate_value(explicit_amount="$1,200,000", evidence_ids=("ev1",))
    assert est.status == "KNOWN"
    assert est.amount_usd == 1_200_000
    assert est.low_usd == est.amount_usd == est.high_usd
    assert est.method == "explicit_procurement_amount"
    assert est.confidence >= 0.9
    assert est.provenance == ("ev1",)


def test_parse_amount_variants():
    assert parse_amount("$1,200,000") == 1_200_000
    assert parse_amount("1.2M") == 1_200_000
    assert parse_amount("$48 million") == 48_000_000
    assert parse_amount(45000000) == 45_000_000.0
    assert parse_amount("") is None
    assert parse_amount("n/a") is None
    assert parse_amount(None) is None


def test_comparable_awards_median():
    est = estimate_value(
        comparable_awards=["$1,000,000", "2,000,000", "3000000"],
        evidence_ids=("evA", "evB", "evC"),
    )
    assert est.status == "ESTIMATED"
    assert est.amount_usd == 2_000_000
    assert est.low_usd == 1_000_000
    assert est.high_usd == 3_000_000
    assert est.method == "comparable_awards_median"
    assert est.provenance == ("evA", "evB", "evC")


def test_single_comparable_reduced_confidence():
    multi = estimate_value(comparable_awards=["1000000", "2000000"], evidence_ids=("e1",))
    single = estimate_value(comparable_awards=["1000000"], evidence_ids=("e1",))
    assert single.status == "ESTIMATED"
    assert single.confidence < multi.confidence


def test_appropriation_with_project_fraction_bounded():
    est = estimate_value(
        appropriation_amount="$100,000,000",
        project_fraction=(0.02, 0.10),
        evidence_ids=("ev-app",),
    )
    assert est.status == "BOUNDED"
    assert est.amount_usd is None
    assert est.low_usd == 2_000_000
    assert est.high_usd == 10_000_000
    assert est.method == "appropriation_fraction_range"
    assert est.provenance == ("ev-app",)


def test_bare_program_amount_upper_bound():
    est = estimate_value(program_amount="50000000", evidence_ids=("ev-prog",))
    assert est.status == "BOUNDED"
    assert est.amount_usd is None
    assert est.low_usd is None
    assert est.high_usd == 50_000_000
    assert est.method == "program_ceiling_upper_bound"
    assert est.confidence < 0.45


def test_no_evidence_unknown():
    est = estimate_value()
    assert est.status == "UNKNOWN"
    assert est.amount_usd is None
    assert est.low_usd is None
    assert est.high_usd is None
    assert est.confidence == 0.0
    assert est.method == "unknown"
    assert est.provenance == ()


def test_provenance_reflects_evidence_ids():
    est = estimate_value(explicit_amount="5000", evidence_ids=("x", "y", "z"))
    assert est.provenance == ("x", "y", "z")


def test_deterministic_same_inputs():
    kwargs = dict(
        appropriation_amount="10000000",
        project_fraction=(0.05, 0.15),
        evidence_ids=("e1", "e2"),
    )
    est1 = estimate_value(**kwargs)
    est2 = estimate_value(**kwargs)
    assert est1 == est2
    assert isinstance(est1, ValueEstimate)
