import pytest

from pyrnova.precursors import PRECURSOR_STAGES, ProgramSignal, build_program_chains, stable_signal_id


def _signal(source, ref, stage, program="chips-program"):
    return ProgramSignal(
        source_id=source,
        source_ref=ref,
        stage=stage,
        program_key=program,
        summary=ref,
        available_at="2024-01-01T00:00:00+00:00",
    )


def test_partial_chain_is_ordered_and_deduplicated():
    signals = [
        _signal("sam_opportunities", "notice-1", "MARKET_ENGAGEMENT"),
        _signal("grants_gov", "grant-1", "FUNDING"),
        _signal("grants_gov", "grant-1", "FUNDING"),
        _signal("congress", "law-1", "AUTHORIZATION"),
    ]
    chain = build_program_chains(signals)[0]
    assert chain.stages == ("AUTHORIZATION", "FUNDING", "MARKET_ENGAGEMENT")
    assert len(chain.signals) == 3
    assert chain.is_partial is True


def test_identity_is_deterministic_and_source_native():
    first = stable_signal_id("grants_gov", "OPP-123", "FUNDING")
    assert first == stable_signal_id("grants_gov", "OPP-123", "FUNDING")
    assert first != stable_signal_id("grants_gov", "OPP-124", "FUNDING")


def test_chain_requires_explicit_program_identity_and_known_stage():
    with pytest.raises(ValueError, match="explicit program_key"):
        ProgramSignal("sec_edgar", "filing-1", "INTENT", "", "capex")
    with pytest.raises(ValueError, match="unknown precursor stage"):
        ProgramSignal("sec_edgar", "filing-1", "RUMOR", "issuer-1", "capex")


def test_full_stage_vocabulary_matches_m4_contract():
    assert PRECURSOR_STAGES == (
        "INTENT", "AUTHORIZATION", "FUNDING", "PROGRAM", "MARKET_ENGAGEMENT",
        "PROCUREMENT", "AWARD", "OUTCOME",
    )
