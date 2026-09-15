import pytest

from pyrnova.sources.usaspending import (
    CONTRACT_TYPE_CODES,
    REQUEST_FIELDS,
    USAspendingClient,
    build_payload,
)


def test_payload_shape_defaults():
    p = build_payload(action_date_start="2020-01-01", action_date_end="2026-01-01")
    assert p["filters"]["award_type_codes"] == CONTRACT_TYPE_CODES
    assert p["filters"]["time_period"] == [{"start_date": "2020-01-01", "end_date": "2026-01-01"}]
    assert "End Date" in p["fields"] and "End Date" in REQUEST_FIELDS
    assert p["sort"] == "Award Amount" and p["order"] == "desc"
    # No optional filters unless provided.
    assert "recipient_search_text" not in p["filters"]
    assert "naics_codes" not in p["filters"]
    assert "agencies" not in p["filters"]


def test_payload_recipient_and_naics():
    p = build_payload(
        recipient_search=["Torch Technologies"],
        naics_codes=["541715"],
        action_date_start="2019-01-01",
        action_date_end="2025-01-01",
        page=2,
        limit=50,
    )
    assert p["filters"]["recipient_search_text"] == ["Torch Technologies"]
    assert p["filters"]["naics_codes"] == ["541715"]
    assert p["page"] == 2 and p["limit"] == 50


def test_payload_rejects_invalid_pagination():
    with pytest.raises(ValueError, match="page"):
        build_payload(action_date_start="2020-01-01", action_date_end="2026-01-01", page=0)
    with pytest.raises(ValueError, match="limit"):
        build_payload(action_date_start="2020-01-01", action_date_end="2026-01-01", limit=101)


def test_recipient_history_preserves_raw_pages(monkeypatch):
    client = USAspendingClient()
    calls = []

    def fake_post(url, payload, *, source_id):
        assert source_id == "usaspending"
        calls.append((url, payload))
        return 200, b'{"results": [{"Award ID": "A-1"}]}', {
            "results": [{"Award ID": "A-1"}], "page_metadata": {"hasNext": False}
        }

    monkeypatch.setattr("pyrnova.sources.usaspending.http.post_json", fake_post)
    pages = client.search_recipient_history(
        recipient_names=["  Acme Federal Systems  ", ""],
        action_date_start="2020-01-01",
        action_date_end="2026-01-01",
    )

    assert pages == [(b'{"results": [{"Award ID": "A-1"}]}', [{"Award ID": "A-1"}])]
    assert calls[0][1]["filters"]["recipient_search_text"] == ["Acme Federal Systems"]


def test_market_history_delegates_filters(monkeypatch):
    client = USAspendingClient()
    captured = {}

    def fake_search(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(client, "search_awards", fake_search)
    assert client.search_market_history(
        naics_codes=["541512"], agency_name="Department of the Army",
        action_date_start="2020-01-01", action_date_end="2026-01-01",
    ) == []
    assert captured["naics_codes"] == ["541512"]
    assert captured["agency_name"] == "Department of the Army"
