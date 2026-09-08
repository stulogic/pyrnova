import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyrnova.archive import LocalEvidenceArchive
from pyrnova.sources.sec_edgar import (
    EdgarClient,
    EdgarRateLimitError,
    archive_observation,
    companyfacts_metadata,
    extract_capex_facts,
    filings_since,
    normalize_cik,
    normalize_filing,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_submission_fixture_is_incremental_and_source_native():
    payload = json.loads((FIXTURES / "sec_submissions_acme.json").read_text())
    rows = filings_since(payload, "0000320193-26-000001")

    assert [row["accessionNumber"] for row in rows] == ["0000320193-26-000002"]
    normalized = normalize_filing(rows[0], cik=payload["cik"], company_metadata=payload)
    assert normalized["filing_identity"] == "sec-edgar:0000320193:0000320193-26-000002"
    assert normalized["signals"] == [
        "material_definitive_agreement",
        "material_financial_obligation",
        "leadership_change",
    ]
    assert normalized["url"].endswith("/000032019326000002/acme8k.htm")


def test_duplicate_source_row_has_the_same_deterministic_identity():
    payload = json.loads((FIXTURES / "sec_submissions_acme.json").read_text())
    row = filings_since(payload)[0]

    assert normalize_filing(row, cik=payload["cik"])["filing_identity"] == normalize_filing(
        dict(row), cik="0000320193"
    )["filing_identity"]


def test_companyfacts_fixture_exposes_only_source_metadata():
    payload = json.loads((FIXTURES / "sec_companyfacts_acme.json").read_text())
    assert companyfacts_metadata(payload) == {
        "cik": "0000320193",
        "entityName": "Acme Defense Systems, Inc.",
        "tickers": ["ACME"],
        "exchanges": ["NYSE"],
    }
    facts = extract_capex_facts(payload)
    assert facts[0]["value_usd"] == 1250000000
    assert facts[0]["signal"] == "reported_capex_cash_flow"
    assert facts[0]["candidate_eligible"] is False
    assert facts[0]["fact_identity"].startswith("sec-edgar:0000320193:capex:")


def test_malformed_cik_and_response_fail_without_archiving_or_network(monkeypatch):
    with pytest.raises(ValueError, match="CIK"):
        normalize_cik("12ABC")

    called = False

    def no_network(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be called")

    monkeypatch.setattr("pyrnova.sources.sec_edgar.http.get_json", no_network)
    with pytest.raises(RuntimeError, match="OFFLINE"):
        EdgarClient(user_agent="Pyrnova research ops@example.test").submissions("320193")
    assert called is False

    client = EdgarClient(user_agent="Pyrnova research ops@example.test", mode="live-safe")
    monkeypatch.setattr(
        "pyrnova.sources.sec_edgar.http.get_json",
        lambda *_args, **_kwargs: (200, b"not-json", None),
    )
    with pytest.raises(RuntimeError, match="HTTP 200"):
        client.submissions("320193")


def test_live_observation_archives_raw_bytes_and_redacts_contact_header(monkeypatch, tmp_path):
    raw = (FIXTURES / "sec_submissions_acme.json").read_bytes()
    payload = json.loads(raw)
    calls = []

    def fake_get(url, params, *, headers):
        calls.append((url, params, headers))
        return 200, raw, payload

    monkeypatch.setattr("pyrnova.sources.sec_edgar.http.get_json", fake_get)
    client = EdgarClient(
        user_agent="Pyrnova Capture Radar contact@example.test",
        mode="live-safe",
        now=lambda: datetime(2026, 9, 8, tzinfo=timezone.utc),
    )
    observation = client.submissions("320193", since_accession="0000320193-26-000001")
    evidence = archive_observation(LocalEvidenceArchive(tmp_path / "archive"), observation)

    assert observation.records[0]["accessionNumber"] == "0000320193-26-000002"
    assert calls[0][1] == {}
    assert calls[0][2]["User-Agent"] == "Pyrnova Capture Radar contact@example.test"
    assert evidence.meta["request_params"] == {"cik": "0000320193", "since_accession": "0000320193-26-000001"}
    assert evidence.meta["request_headers"] == {"user_agent": "configured_not_retained"}
    assert "contact@example.test" not in json.dumps(evidence.meta)
    assert evidence.content_sha256


def test_requires_contact_user_agent_and_rate_limit_prevents_repeat(monkeypatch):
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)
    client = EdgarClient(mode="live-safe", now=lambda: now, cooldown_seconds=30)
    with pytest.raises(RuntimeError, match="User-Agent"):
        client.submissions("320193")

    calls = 0

    def throttled(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return 429, b"too many requests", None

    client = EdgarClient(user_agent="Pyrnova contact@example.test", mode="live-safe", now=lambda: now, cooldown_seconds=30)
    monkeypatch.setattr("pyrnova.sources.sec_edgar.http.get_json", throttled)
    with pytest.raises(EdgarRateLimitError, match="throttled"):
        client.companyfacts("320193")
    with pytest.raises(EdgarRateLimitError, match="next permitted poll"):
        client.companyfacts("320193")
    assert calls == 1
