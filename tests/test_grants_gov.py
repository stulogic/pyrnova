import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyrnova.archive import LocalEvidenceArchive
from pyrnova.normalize import normalize_grant_opportunity
from pyrnova.sources.grants_gov import (
    GrantsGovClient,
    GrantsGovError,
    archive_page,
    build_payload,
    deduplicate_opportunities,
    grant_opportunity_identity,
    sanitize_request_params,
)
from pyrnova.sources.registry import get_spec


FIXTURE = Path(__file__).parent / "fixtures" / "grants_gov_search2.json"


def test_synthetic_replay_fixture_normalizes_without_creating_weak_candidates():
    rows = json.loads(FIXTURE.read_text())["data"]["oppHits"]
    direct, precursor, weak = [normalize_grant_opportunity(row) for row in rows]

    assert direct["grant_signal_class"] == "direct_opportunity"
    assert direct["candidate_eligible"] is True
    assert direct["grant_source_identity"] == "grants.gov:opportunity:G-2026-001"
    assert precursor["grant_signal_class"] == "precursor_funding"
    assert precursor["candidate_eligible"] is False
    assert weak["grant_signal_class"] == "direct_opportunity"
    assert weak["candidate_eligible"] is False


def test_payload_is_bounded_and_excludes_empty_filters():
    assert build_payload(rows=10, start_record_num=2) == {
        "rows": 10,
        "startRecordNum": 2,
        "sortBy": "openDate|desc",
    }
    payload = build_payload(
        keyword=" cyber ", agency_code=" DOD ", opportunity_statuses=["posted", "forecasted"]
    )
    assert payload["keyword"] == "cyber"
    assert payload["agencies"] == "DOD"
    assert payload["oppStatuses"] == "posted|forecasted"
    with pytest.raises(ValueError):
        build_payload(rows=0)
    with pytest.raises(ValueError):
        build_payload(start_record_num=-1)


def test_offline_default_never_makes_a_live_call(monkeypatch):
    monkeypatch.setattr(
        "pyrnova.sources.grants_gov.http.post_json",
        lambda *_args, **_kwargs: pytest.fail("offline client made an HTTP call"),
    )
    with pytest.raises(GrantsGovError, match="OFFLINE"):
        GrantsGovClient().search_opportunities()


def test_success_preserves_raw_bytes_and_sanitized_provenance(monkeypatch, tmp_path):
    raw = FIXTURE.read_bytes()
    parsed = json.loads(raw)
    calls = []

    def fake_post(url, payload, *, source_id):
        assert source_id == "grants_gov"
        calls.append((url, payload))
        return 200, raw, parsed

    monkeypatch.setattr("pyrnova.sources.grants_gov.http.post_json", fake_post)
    client = GrantsGovClient(mode="LIVE-SAFE", request_budget=1)
    page = client.search_opportunities(keyword="cyber", opportunity_statuses=["posted"])
    evidence = archive_page(LocalEvidenceArchive(tmp_path / "archive"), page)

    assert page.raw_response == raw
    assert page.opportunities == parsed["data"]["oppHits"]
    assert page.request_params == {"rows": 25, "startRecordNum": 0, "sortBy": "openDate|desc", "keyword": "cyber", "oppStatuses": "posted"}
    assert page.source_url.endswith("/search2")
    assert page.mode == "LIVE-SAFE"
    assert calls[0][1] == page.request_params
    assert evidence.source_id == "grants_gov"
    assert evidence.retention_tier == "A"
    assert evidence.meta["request_params"] == page.request_params
    assert LocalEvidenceArchive(tmp_path / "archive").get(evidence.content_sha256, "grants_gov") == raw


def test_malformed_success_is_not_reported_or_archived(monkeypatch):
    monkeypatch.setattr(
        "pyrnova.sources.grants_gov.http.post_json",
        lambda *_args, **_kwargs: (200, b'{"notOppHits": []}', {"notOppHits": []}),
    )
    with pytest.raises(GrantsGovError, match="malformed"):
        GrantsGovClient(mode="ACCEPTANCE").search_opportunities()


def test_identity_and_deduplication_are_deterministic_for_reordered_results():
    sparse = {"id": "same", "title": "A"}
    complete = {"id": "same", "title": "A", "agency": "DOD", "openDate": "2026-01-01"}
    fallback = {"number": "NO-ID-1", "title": "Number only"}
    assert grant_opportunity_identity(fallback) == "grants.gov:number:NO-ID-1"
    assert deduplicate_opportunities([sparse, complete, fallback]) == deduplicate_opportunities(
        [fallback, complete, sparse]
    )
    assert deduplicate_opportunities([sparse, complete])[0] == complete


def test_provenance_sanitization_removes_nested_credential_fields():
    assert sanitize_request_params(
        {"keyword": "cyber", "api_key": "nope", "nested": {"accessToken": "nope", "ok": 1}}
    ) == {"keyword": "cyber", "nested": {"ok": 1}}


def test_retry_budget_and_circuit_breaker_behavior(monkeypatch):
    responses = iter([(429, b"slow", None), (200, b'{"data":{"oppHits":[]}}', {"data": {"oppHits": []}})])
    sleeps = []
    now = lambda: datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr("pyrnova.sources.grants_gov.http.post_json", lambda *_args, **_kwargs: next(responses))
    client = GrantsGovClient(
        mode="LIVE-SAFE", request_budget=2, max_retries=1, sleep=sleeps.append, now=now, jitter=lambda _a, _b: 1
    )
    page = client.search_opportunities()
    assert page.attempts == 2
    assert sleeps == [1.0]
    assert client.metrics["calls_made"] == 2

    monkeypatch.setattr("pyrnova.sources.grants_gov.http.post_json", lambda *_args, **_kwargs: (429, b"slow", None))
    blocked = GrantsGovClient(mode="LIVE-SAFE", request_budget=1, max_retries=0, now=now)
    with pytest.raises(GrantsGovError, match="HTTP 429"):
        blocked.search_opportunities()
    with pytest.raises(GrantsGovError, match="circuit open"):
        blocked.search_opportunities()


def test_registry_exposes_grants_as_mutable_m4_source():
    spec = get_spec("grants_gov")
    assert spec.active is True
    assert spec.retention_tier == "A"
