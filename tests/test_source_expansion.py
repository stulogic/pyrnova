from pathlib import Path

import pytest

from pyrnova.archive import LocalEvidenceArchive
from pyrnova.source_expansion import ingest_source_expansion


FIXTURES = Path(__file__).parent / "fixtures"


def test_offline_source_expansion_archives_normalizes_resolves_and_chains(tmp_path):
    batch = ingest_source_expansion(
        archive=LocalEvidenceArchive(tmp_path / "archive"),
        observed_at="2026-09-08T12:00:00+00:00",
        grants_response=(FIXTURES / "grants_gov_search2.json").read_bytes(),
        sec_submissions_response=(FIXTURES / "sec_submissions_acme.json").read_bytes(),
        sec_companyfacts_response=(FIXTURES / "sec_companyfacts_acme.json").read_bytes(),
        forecast_response=(FIXTURES / "acquisition_forecast.csv").read_bytes(),
        forecast_agency="DISA",
        forecast_url="https://example.mil/forecast.csv",
    )
    assert set(batch.normalized) == {"grants_gov", "sec_edgar", "acquisition_forecast"}
    assert {signal.stage for signal in batch.signals} >= {"INTENT", "FUNDING", "MARKET_ENGAGEMENT"}
    assert len(batch.chains) == len({signal.program_key for signal in batch.signals})
    assert batch.entities[0].meta["sec_cik"] == "0000320193"
    assert len(batch.evidence) == 4
    assert all(signal.id in batch.evidence_by_signal_id for signal in batch.signals)
    assert batch.source_contribution["grants_gov"]["raw_records"] == 3
    assert batch.source_contribution["acquisition_forecast"]["candidates_created"] == 0


def test_malformed_archives_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="malformed Grants"):
        ingest_source_expansion(
            archive=LocalEvidenceArchive(tmp_path / "archive"),
            observed_at="2026-09-08T12:00:00+00:00",
            grants_response=b'{}',
        )
