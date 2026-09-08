import json
from pathlib import Path

import pytest

from pyrnova.archive import LocalEvidenceArchive
from pyrnova.sources.appropriations import (
    AppropriationsClient,
    parse_amount,
    parse_appropriations,
    public_artifact_url,
)
from pyrnova.sources.appropriations import archive_observation


FIXTURE = Path(__file__).parent / "fixtures" / "appropriations_sample.json"
ARTIFACT_URL = "https://www.usaspending.gov/artifacts/appropriations.json"


def _parse(**overrides):
    kwargs = dict(
        agency="DISA",
        artifact_url=ARTIFACT_URL,
        observed_at="2026-09-08T12:00:00+00:00",
    )
    kwargs.update(overrides)
    return parse_appropriations(FIXTURE.read_bytes(), **kwargs)


def test_source_identity_is_deterministic_and_stable_on_reparse():
    rows = _parse()
    # 6 rows in fixture, one blank-stage row skipped
    assert len(rows) == 5
    assert rows[0]["source_ref"] == "DOD-INTENT-0091"
    assert rows[1]["source_ref"].endswith("appropriations.json#row=2")
    assert rows == _parse(artifact_url="https://www.usaspending.gov/artifacts/appropriations.json?tracking=x")


def test_available_at_propagates_as_timezone_aware_iso():
    rows = _parse(observed_at="2026-09-08T12:00:00+00:00")
    for row in rows:
        assert row["available_at"] == "2026-09-08T12:00:00+00:00"


def test_stage_distinction_and_blank_stage_skip():
    rows = _parse()
    by_title = {row["title"]: row for row in rows}
    assert by_title["Cloud Modernization Initiative"]["stage"] == "INTENT"
    assert by_title["Network Resilience Program"]["stage"] == "AUTHORIZATION"
    assert by_title["Secure Data Centers Account"]["stage"] == "FUNDING"
    assert by_title["Health IT Modernization Grant Program"]["stage"] == "FUNDING"
    assert "Unlabeled Line Item" not in by_title


def test_program_identifier_prefers_tas_over_cfda_over_program_element():
    rows = _parse()
    by_title = {row["title"]: row for row in rows}

    intent_row = by_title["Cloud Modernization Initiative"]
    assert intent_row["program_identifier"] == "0603760D8Z"
    assert intent_row["program_element"] == "0603760D8Z"
    assert intent_row["treasury_account_symbol"] is None

    tas_and_cfda_row = by_title["Secure Data Centers Account"]
    assert tas_and_cfda_row["program_identifier"] == "097-0100/2027"
    assert tas_and_cfda_row["treasury_account_symbol"] == "097-0100/2027"
    assert tas_and_cfda_row["cfda"] == "12.345"
    assert tas_and_cfda_row["program_key"] == "disa:097-0100/2027".casefold()

    cfda_only_row = by_title["Health IT Modernization Grant Program"]
    assert cfda_only_row["program_identifier"] == "93.778"
    assert cfda_only_row["treasury_account_symbol"] is None


def test_downstream_refs_captured_when_present():
    rows = _parse()
    by_title = {row["title"]: row for row in rows}
    assert by_title["Network Resilience Program"]["downstream_refs"] == ("FA8771-27-R-0001",)
    assert by_title["Cloud Modernization Initiative"]["downstream_refs"] == ()


def test_amount_parsing_handles_currency_multipliers_and_unparseable_values():
    assert parse_amount("$1,200,000") == 1200000.0
    assert parse_amount("1.2M") == 1200000.0
    assert parse_amount("TBD") is None
    assert parse_amount(None) is None
    assert parse_amount("") is None

    rows = _parse()
    by_title = {row["title"]: row for row in rows}
    assert by_title["Cloud Modernization Initiative"]["amount_usd"] == 1200000.0
    assert by_title["Network Resilience Program"]["amount_usd"] == 1200000.0
    assert by_title["Legacy System Sustainment"]["amount_usd"] is None


def test_records_never_candidate_eligible_and_role_is_precursor():
    for row in _parse():
        assert row["candidate_eligible"] is False
        assert row["signal_role"] == "precursor"
        assert row["source_id"] == "appropriations"


def test_artifact_url_requires_https_and_drops_query():
    assert public_artifact_url("https://agency.gov/data.json?token=secret") == "https://agency.gov/data.json"
    with pytest.raises(ValueError):
        public_artifact_url("http://agency.gov/data.json")


def test_malformed_content_handled_gracefully():
    assert parse_appropriations(b"", agency="DISA", artifact_url=ARTIFACT_URL) == []
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_appropriations(b"{not json", agency="DISA", artifact_url=ARTIFACT_URL)
    with pytest.raises(ValueError, match="JSON array"):
        parse_appropriations(json.dumps({"foo": "bar"}).encode(), agency="DISA", artifact_url=ARTIFACT_URL)
    # non-dict rows inside an otherwise valid array are skipped, not fatal
    rows = parse_appropriations(
        json.dumps(["not-a-dict", {"budget_stage": "request", "title": "X", "amount": "$1"}]).encode(),
        agency="DISA",
        artifact_url=ARTIFACT_URL,
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "X"


def test_client_defaults_offline_and_uses_shared_budget(monkeypatch):
    monkeypatch.setattr(
        "pyrnova.sources.appropriations.get_bytes",
        lambda *_args, **_kwargs: pytest.fail("offline mode made a network call"),
    )
    with pytest.raises(RuntimeError, match="OFFLINE"):
        AppropriationsClient().fetch(ARTIFACT_URL, agency="DISA")

    monkeypatch.setattr(
        "pyrnova.sources.appropriations.get_bytes",
        lambda *_args, **_kwargs: (200, FIXTURE.read_bytes()),
    )
    client = AppropriationsClient(mode="LIVE-SAFE", request_budget=1)
    observation = client.fetch(ARTIFACT_URL, agency="DISA")
    assert observation.mode == "LIVE_SAFE"
    assert client.metrics["calls_made"] == 1
    with pytest.raises(RuntimeError, match="budget exhausted"):
        client.fetch(ARTIFACT_URL, agency="DISA")


def test_archive_observation_stores_exact_bytes_with_sanitized_fingerprint(tmp_path):
    monkeypatch_bytes = FIXTURE.read_bytes()
    control = None
    client = AppropriationsClient(mode="LIVE-SAFE", request_budget=1, control=control)

    def fake_get_bytes(*_args, **_kwargs):
        return 200, monkeypatch_bytes

    import pyrnova.sources.appropriations as mod
    original = mod.get_bytes
    mod.get_bytes = fake_get_bytes
    try:
        observation = client.fetch(f"{ARTIFACT_URL}?tracking=discarded", agency="DISA")
    finally:
        mod.get_bytes = original

    evidence = archive_observation(LocalEvidenceArchive(tmp_path / "archive"), observation)
    assert evidence.source_id == "appropriations"
    assert evidence.retention_tier == "A"
    assert evidence.source_url == ARTIFACT_URL
    assert evidence.meta["request_fingerprint"] == observation.request_fingerprint
    assert "tracking" not in json.dumps(evidence.meta)
    assert evidence.content_sha256
