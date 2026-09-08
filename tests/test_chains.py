"""M5 cross-source capital-chain resolution."""

import pytest

from pyrnova.chains import CHAIN_RESOLUTION_VERSION, resolve_chain, signals_from_records
from pyrnova.precursors import ProgramSignal


def _sig(source, ref, stage, program, *, at, agency=None, downstream=(), program_identifier=None,
         summary=None, contradicts=False):
    return ProgramSignal(
        source_id=source, source_ref=ref, stage=stage, program_key=program,
        summary=summary or ref, available_at=at, agency=agency,
        downstream_refs=tuple(downstream),
        meta={"program_identifier": program_identifier, "contradicts": contradicts},
    )


def test_deterministic_program_key_join_is_typed_and_provenanced():
    signals = [
        _sig("congress", "law-1", "AUTHORIZATION", "p1", at="2022-01-01T00:00:00+00:00"),
        _sig("grants_gov", "g-1", "FUNDING", "p1", at="2022-06-01T00:00:00+00:00"),
    ]
    resolution = resolve_chain(signals)
    assert len(resolution.relationships) == 1
    rel = resolution.relationships[0]
    assert rel.predicate == "AUTHORIZES"
    assert rel.join_method == "deterministic_program_key"
    assert rel.confidence == 0.95
    assert "program_key" in rel.rationale
    # The relationship is knowable only once the later endpoint is observed.
    assert rel.first_observed_at == "2022-06-01T00:00:00+00:00"


def test_deterministic_native_identifier_crosswalk_links_across_program_keys():
    signals = [
        _sig("acquisition_forecast", "F-1", "MARKET_ENGAGEMENT", "prog-a",
             at="2024-01-01T00:00:00+00:00", downstream=["SOL-9"]),
        _sig("sam_opportunities", "SOL-9", "PROCUREMENT", "prog-b", at="2024-09-01T00:00:00+00:00"),
    ]
    resolution = resolve_chain(signals)
    methods = {r.join_method for r in resolution.relationships}
    assert methods == {"deterministic_native_id"}
    assert resolution.relationships[0].object_id == signals[1].id


def test_inferred_join_requires_explicit_shared_program_identifier():
    signals = [
        _sig("s1", "r1", "FUNDING", "prog-x", at="2023-01-01T00:00:00+00:00",
             agency="Department of Energy", program_identifier="81.086"),
        _sig("s2", "r2", "PROCUREMENT", "prog-y", at="2023-08-01T00:00:00+00:00",
             agency="Department of Energy", program_identifier="81.086"),
    ]
    resolution = resolve_chain(signals)
    assert [r.join_method for r in resolution.relationships] == ["inferred_strong_attribute"]
    assert resolution.relationships[0].confidence == 0.60
    assert not resolution.rejected


def test_weak_topic_only_join_is_rejected_not_materialized():
    signals = [
        _sig("s1", "r1", "MARKET_ENGAGEMENT", "hhs:cloud", at="2024-02-01T00:00:00+00:00",
             agency="Department of Health and Human Services", summary="cloud migration services"),
        _sig("s2", "r2", "MARKET_ENGAGEMENT", "dhs:cloud", at="2024-03-01T00:00:00+00:00",
             agency="Department of Homeland Security", summary="cloud migration services"),
    ]
    resolution = resolve_chain(signals)
    assert resolution.relationships == ()
    assert len(resolution.rejected) == 1
    assert resolution.rejected[0].reason == "topic_overlap_only"


def test_agency_only_match_is_rejected():
    signals = [
        _sig("s1", "r1", "FUNDING", "navy:alpha", at="2024-01-01T00:00:00+00:00",
             agency="Department of the Navy", summary="alpha widgets"),
        _sig("s2", "r2", "PROCUREMENT", "navy:beta", at="2024-06-01T00:00:00+00:00",
             agency="Department of the Navy", summary="beta gadgets"),
    ]
    resolution = resolve_chain(signals)
    assert resolution.relationships == ()
    assert resolution.rejected[0].reason == "agency_name_only"


def test_duplicate_signals_are_collapsed_and_edges_are_idempotent():
    signals = [
        _sig("grants_gov", "g-1", "FUNDING", "p1", at="2022-06-01T00:00:00+00:00"),
        _sig("grants_gov", "g-1", "FUNDING", "p1", at="2022-06-01T00:00:00+00:00"),
        _sig("sam_opportunities", "s-1", "PROCUREMENT", "p1", at="2022-09-01T00:00:00+00:00"),
    ]
    first = resolve_chain(signals)
    second = resolve_chain(signals)
    assert first.duplicates_collapsed == 1
    assert [r.id for r in first.relationships] == [r.id for r in second.relationships]
    assert len(first.relationships) == 1


def test_point_in_time_filter_excludes_future_signals():
    signals = [
        _sig("acquisition_forecast", "F-1", "MARKET_ENGAGEMENT", "p1", at="2024-01-01T00:00:00+00:00"),
        _sig("usaspending", "A-1", "AWARD", "p1", at="2025-01-01T00:00:00+00:00"),
    ]
    early = resolve_chain(signals, as_of="2024-06-01T00:00:00+00:00")
    assert [s.stage for s in early.signals] == ["MARKET_ENGAGEMENT"]
    assert early.relationships == ()


def test_contradiction_is_typed_and_penalizes_confidence():
    signals = [
        _sig("sam_opportunities", "s-1", "PROCUREMENT", "p1", at="2024-01-01T00:00:00+00:00"),
        _sig("sam_opportunities", "s-2", "AWARD", "p1", at="2024-06-01T00:00:00+00:00",
             contradicts=True, summary="solicitation cancelled"),
    ]
    resolution = resolve_chain(signals)
    assert resolution.relationships[0].predicate == "CONTRADICTS"
    assert resolution.confidence["contradicted"] is True
    assert resolution.confidence["value"] <= 0.30


def test_single_source_chain_confidence_is_capped():
    signals = [
        _sig("sec_edgar", "f-1", "INTENT", "p1", at="2023-01-01T00:00:00+00:00"),
        _sig("sec_edgar", "f-2", "OUTCOME", "p1", at="2024-01-01T00:00:00+00:00"),
    ]
    resolution = resolve_chain(signals)
    assert resolution.confidence["source_independence"] == 1
    assert resolution.confidence["value"] == 0.70


def test_corroboration_edge_for_independent_same_stage_sources():
    signals = [
        _sig("grants_gov", "g-1", "FUNDING", "p1", at="2022-06-01T00:00:00+00:00"),
        _sig("usaspending", "u-1", "FUNDING", "p1", at="2022-07-01T00:00:00+00:00"),
    ]
    resolution = resolve_chain(signals)
    assert [r.predicate for r in resolution.relationships] == ["CORROBORATES"]
    assert resolution.relationships[0].confidence == 0.90


def test_signals_from_records_skips_missing_identity_and_dangling_refs_are_safe():
    records = [
        {"source_id": "s", "source_ref": "ok", "stage": "FUNDING", "program_key": "p",
         "available_at": "2024-01-01T00:00:00+00:00", "downstream_refs": ["NOT-PRESENT"]},
        {"source_id": "s", "source_ref": "no-stage", "program_key": "p",
         "available_at": "2024-01-01T00:00:00+00:00"},
        {"source_id": "s", "source_ref": "no-program", "stage": "AWARD",
         "available_at": "2024-01-01T00:00:00+00:00"},
    ]
    signals = signals_from_records(records)
    assert len(signals) == 1
    # A dangling downstream reference must not raise or invent an edge.
    assert resolve_chain(signals).relationships == ()


def test_evidence_ids_flow_into_relationship_provenance():
    signals = [
        _sig("congress", "law-1", "AUTHORIZATION", "p1", at="2022-01-01T00:00:00+00:00"),
        _sig("grants_gov", "g-1", "FUNDING", "p1", at="2022-06-01T00:00:00+00:00"),
    ]
    evidence = {signals[0].id: "ev-a", signals[1].id: "ev-b"}
    resolution = resolve_chain(signals, evidence_by_signal_id=evidence)
    assert sorted(resolution.relationships[0].evidence_ids) == ["ev-a", "ev-b"]
    assert resolution.metrics()["chain_resolution_version"] == CHAIN_RESOLUTION_VERSION
