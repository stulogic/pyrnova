from pyrnova.archive import LocalEvidenceArchive
from pyrnova.integrate import attach_program_signal, sec_issuer_entity
from pyrnova.models import Catalyst, Opportunity
from pyrnova.precursors import ProgramSignal


def test_sec_entity_identity_uses_cik_not_name():
    before = sec_issuer_entity(cik="50863", company_name="Intel Corp", tickers=["INTC"])
    renamed = sec_issuer_entity(cik="0000050863", company_name="Intel Corporation", tickers=["INTC"])
    assert before.id == renamed.id
    assert before.meta["sec_cik"] == "0000050863"


def test_program_signal_requires_explicit_join_and_only_enriches(tmp_path):
    opp = Opportunity(
        title="Cloud procurement",
        catalyst=Catalyst(kind="sources_sought", detected_by="test"),
        state="reviewing",
        meta={"program_key": "disa:cloud-modernization", "notice_id": "SAM-1"},
    )
    archive = LocalEvidenceArchive(tmp_path / "archive")
    evidence = archive.put(
        b'{"forecast":"DISA-2027-001"}', source_id="acquisition_forecast",
        retention_tier="A", source_ref="DISA-2027-001",
    )
    unrelated = ProgramSignal(
        "grants_gov", "G-1", "FUNDING", "doe:grid", "Grid funding",
    )
    assert attach_program_signal(opp, unrelated, evidence, strength=5) is False
    assert not opp.events

    forecast = ProgramSignal(
        "acquisition_forecast", "DISA-2027-001", "MARKET_ENGAGEMENT",
        "disa:cloud-modernization", "Cloud modernization forecast", agency="DISA",
    )
    assert attach_program_signal(opp, forecast, evidence, strength=5) is True
    assert opp.state == "reviewing"
    assert opp.events[0].stage == "MARKET_ENGAGEMENT"
    assert opp.evidence_assessments[0].strength == 3
    assert opp.relationships[0].predicate == "program_chain_evidence"
