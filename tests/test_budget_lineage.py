"""B2.9 — Budget -> Program -> Procurement lineage: representative proof + AS-OF integrity."""

from pyrnova.chains import resolve_chain, signals_from_records
from pyrnova.budget_lineage import build_budget_lineage

PK = "disa:cloud-modernization"

# One coherent capital-to-procurement story using now-authorized official sources.
FULL_CHAIN = [
    {"source_id": "appropriations", "source_ref": "approp-FY26-0091", "stage": "AUTHORIZATION",
     "program_key": PK, "available_at": "2025-02-01", "summary": "FY26 appropriation line"},
    {"source_id": "appropriations", "source_ref": "approp-FY26-fund", "stage": "FUNDING",
     "program_key": PK, "available_at": "2025-03-01", "summary": "program funding enacted"},
    {"source_id": "acquisition_forecast", "source_ref": "DISA-2026-001", "stage": "MARKET_ENGAGEMENT",
     "program_key": PK, "available_at": "2025-04-01", "summary": "forecast requirement"},
    {"source_id": "sam_opportunities", "source_ref": "sol-1", "stage": "PROCUREMENT",
     "program_key": PK, "available_at": "2025-07-01", "summary": "solicitation"},
    {"source_id": "usaspending", "source_ref": "award-1", "stage": "AWARD",
     "program_key": PK, "available_at": "2026-01-15", "summary": "award"},
]


def _view(records, as_of=None):
    return build_budget_lineage(resolve_chain(signals_from_records(records, as_of=as_of)))


def test_full_budget_to_award_lineage_is_coherent():
    v = _view(FULL_CHAIN)
    assert v.funding_to_procurement_linked is True and v.is_complete is True
    assert v.funding_anchor["stage"] == "AUTHORIZATION"
    assert v.funding_anchor["source_id"] == "appropriations"
    assert v.award and v.award["source_id"] == "usaspending"
    # Every link carries confidence + knowable time (no invented links).
    assert v.links and all(l.confidence > 0 and l.knowable_at for l in v.links)
    assert "traces to upstream funding evidence appropriations:approp-FY26-0091" in v.summary


def test_as_of_integrity_no_future_award_leaks():
    early = _view(FULL_CHAIN, as_of="2025-05-01")   # before solicitation/award
    assert early.award is None
    assert "PROCUREMENT" not in early.stages_present
    assert early.funding_to_procurement_linked is False
    assert early.earliest_funding_knowable_at == "2025-02-01"


def test_missing_stage_is_recorded_as_coverage_gap_not_invented():
    # Drop the forecast (MARKET_ENGAGEMENT); funding still links straight to procurement.
    records = [r for r in FULL_CHAIN if r["stage"] != "MARKET_ENGAGEMENT"]
    v = _view(records)
    assert v.funding_to_procurement_linked is True
    assert any("missing MARKET_ENGAGEMENT" in g for g in v.coverage_gaps)


def test_unlinked_funding_and_procurement_is_a_gap_not_a_fabricated_link():
    # Funding and procurement belong to DIFFERENT programs -> no shared-identity link.
    records = [
        {"source_id": "appropriations", "source_ref": "a1", "stage": "FUNDING",
         "program_key": "agencyA:progX", "available_at": "2025-01-01", "summary": "funding"},
        {"source_id": "sam_opportunities", "source_ref": "s1", "stage": "PROCUREMENT",
         "program_key": "agencyB:progY", "available_at": "2025-06-01", "summary": "solicitation"},
    ]
    v = _view(records)
    assert v.funding_to_procurement_linked is False
    assert v.is_complete is False
