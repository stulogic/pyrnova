"""SBIR/STTR Awards adapter (offline only, no network)."""

from pathlib import Path

import pytest

from pyrnova.sources import http, sbir


FIXTURES = Path(__file__).parent / "fixtures"
SBIR_AWARDS_BYTES = (FIXTURES / "sbir_awards.json").read_bytes()


def test_build_params_includes_only_supplied_filters():
    params = sbir.build_params(rows=50, start=100)
    assert params == {"start": 100, "rows": 50, "format": "json"}

    params = sbir.build_params(agency="Department of Defense", firm="Torch Technologies",
                                year=2016, keyword="sensor", start=0, rows=25)
    assert params == {
        "start": 0,
        "rows": 25,
        "format": "json",
        "agency": "Department of Defense",
        "firm": "Torch Technologies",
        "year": 2016,
        "keyword": "sensor",
    }


def test_build_params_validates_rows_and_start_bounds():
    with pytest.raises(ValueError, match="rows"):
        sbir.build_params(rows=0)
    with pytest.raises(ValueError, match="rows"):
        sbir.build_params(rows=1001)
    with pytest.raises(ValueError, match="start"):
        sbir.build_params(start=-1)


def test_client_search_awards_parses_top_level_array_and_preserves_provenance(monkeypatch):
    import json

    parsed = json.loads(SBIR_AWARDS_BYTES)
    captured = {}

    def fake_get_json(url, params, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return 200, SBIR_AWARDS_BYTES, parsed

    monkeypatch.setattr(http, "get_json", fake_get_json)

    client = sbir.SbirClient()
    pages = client.search_awards(firm="Torch Technologies", rows=100)

    assert len(pages) == 1
    page = pages[0]
    assert page.raw_response == SBIR_AWARDS_BYTES
    assert page.awards == parsed
    assert page.request_params == captured["params"]
    assert page.source_url == "https://api.www.sbir.gov/public/api/awards"
    assert captured["url"] == page.source_url
    assert page.fetched_at


def test_client_raises_on_non_200(monkeypatch):
    def fake_get_json(url, params, **kwargs):
        return 503, b"", None

    monkeypatch.setattr(http, "get_json", fake_get_json)

    client = sbir.SbirClient()
    with pytest.raises(RuntimeError, match="HTTP 503"):
        client.search_awards()


def test_parse_sbir_awards_returns_chain_ready_records():
    records = sbir.parse_sbir_awards(SBIR_AWARDS_BYTES)
    assert len(records) == 4

    expected_keys = {
        "source_id", "source_ref", "stage", "program_key", "summary", "available_at",
        "agency", "recipient", "recipient_uei", "amount_usd", "record_kind", "confidence",
        "program_identifier",
    }
    for record in records:
        assert set(record.keys()) == expected_keys
        assert record["source_id"] == "sbir"
        assert record["stage"] == "PROGRAM"
        assert record["record_kind"] == "sbir_award"
        assert record["confidence"] == "KNOWN"

    torch_records = [r for r in records if r["recipient"] == "Torch Technologies"]
    assert len(torch_records) == 2
    assert {r["recipient_uei"] for r in torch_records} == {"YA63J5PVEZE6"}
    assert {r["available_at"] for r in torch_records} == {"2014-03-15", "2016-07-01"}
    assert all(r["program_key"].startswith("sbir:") for r in torch_records)
    assert {r["amount_usd"] for r in torch_records} == {149875.0, 999500.0}


def test_parse_sbir_awards_normalizes_date_edge_cases():
    records = sbir.parse_sbir_awards(SBIR_AWARDS_BYTES)
    by_ref = {r["source_ref"]: r for r in records}

    # MM/DD/YYYY normalizes to ISO.
    mm_dd_yyyy = by_ref["N15A-T003-0012"]
    assert mm_dd_yyyy["available_at"] == "2015-06-01"

    # Bare year normalizes to Jan 1 of that year.
    year_only = by_ref["SP4701-19-C-0033"]
    assert year_only["available_at"] == "2019-01-01"
    # Empty award_amount is unparseable -> None.
    assert year_only["amount_usd"] is None
    # Missing agency_tracking_number falls back to contract as source_ref.
    assert year_only["program_identifier"] == "DLA19-001"


def test_parse_sbir_awards_company_name_filter_is_case_insensitive_substring():
    records = sbir.parse_sbir_awards(SBIR_AWARDS_BYTES, company_name="torch technologies")
    assert len(records) == 2
    assert all(r["recipient"] == "Torch Technologies" for r in records)

    records = sbir.parse_sbir_awards(SBIR_AWARDS_BYTES, company_name="helion")
    assert len(records) == 1
    assert records[0]["recipient"] == "Helion Dynamics Inc"

    records = sbir.parse_sbir_awards(SBIR_AWARDS_BYTES, company_name="no such firm")
    assert records == []


def test_parse_sbir_awards_is_idempotent():
    first = sbir.parse_sbir_awards(SBIR_AWARDS_BYTES)
    second = sbir.parse_sbir_awards(SBIR_AWARDS_BYTES)
    assert first == second
