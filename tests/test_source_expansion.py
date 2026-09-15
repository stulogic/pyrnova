import hashlib
import json
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


def test_sec_edgar_expansion_archive_is_normalized_only_not_raw(tmp_path):
    """sec_edgar is NORMALIZED_ONLY: durable archive must carry reviewed facts +
    hash provenance, never the raw source expression (rights fail-closed)."""
    archive_root = tmp_path / "archive"
    submissions_raw = (FIXTURES / "sec_submissions_acme.json").read_bytes()
    companyfacts_raw = (FIXTURES / "sec_companyfacts_acme.json").read_bytes()
    batch = ingest_source_expansion(
        archive=LocalEvidenceArchive(archive_root),
        observed_at="2026-09-08T12:00:00+00:00",
        sec_submissions_response=submissions_raw,
        sec_companyfacts_response=companyfacts_raw,
    )
    sec_evidence = [ev for ev in batch.evidence if ev.source_id == "sec_edgar"]
    assert len(sec_evidence) == 2
    for ev in sec_evidence:
        assert ev.meta["representation"] == "NORMALIZED_ONLY"
        stored = LocalEvidenceArchive(archive_root).get(ev.content_sha256, "sec_edgar")
        parsed = json.loads(stored)
        assert parsed["representation"] == "NORMALIZED_ONLY"
        # provenance back to the raw page is retained without storing the raw page
        assert parsed["original_content_sha256"] in {
            hashlib.sha256(submissions_raw).hexdigest(),
            hashlib.sha256(companyfacts_raw).hexdigest(),
        }
    # no raw source expression is ever written to durable storage
    for path in archive_root.rglob("*"):
        if path.is_file():
            body = path.read_bytes()
            assert body != submissions_raw and body != companyfacts_raw
            assert b"primaryDocDescription" not in body


def test_malformed_archives_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="malformed Grants"):
        ingest_source_expansion(
            archive=LocalEvidenceArchive(tmp_path / "archive"),
            observed_at="2026-09-08T12:00:00+00:00",
            grants_response=b'{}',
        )
