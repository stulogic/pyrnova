import pytest

from pyrnova.sources.sam import SamClient, build_params


def test_observation_preserves_raw_rows_and_safe_request_provenance(monkeypatch):
    raw = b'{"opportunitiesData":[{"noticeId":"abc"}]}'
    calls = []

    def fake_get_json(url, params, *, source_id):
        assert source_id == "sam_opportunities"
        calls.append((url, params))
        return 200, raw, {"opportunitiesData": [{"noticeId": "abc"}], "totalRecords": 1}

    monkeypatch.setattr("pyrnova.sources.sam.http.get_json", fake_get_json)
    observed = SamClient("secret-key").search_observations(
        posted_from="01/01/2026", posted_to="01/31/2026", ptype="p", naics="541512"
    )[0]

    assert observed.raw_response == raw
    assert observed.rows == [{"noticeId": "abc"}]
    assert observed.request_url.endswith("/search")
    assert observed.request_params == {
        "postedFrom": "01/01/2026",
        "postedTo": "01/31/2026",
        "limit": 100,
        "offset": 0,
        "ptype": "p",
        "ncode": "541512",
    }
    assert "api_key" not in observed.request_params
    assert observed.fetched_at.endswith("+00:00")
    assert calls[0][1]["api_key"] == "secret-key"


def test_observation_paginates_with_distinct_safe_offsets(monkeypatch):
    def fake_get_json(_url, params, *, source_id):
        assert source_id == "sam_opportunities"
        rows = [{"noticeId": str(params["offset"])}]
        return 200, b"{}", {"opportunitiesData": rows, "totalRecords": 3}

    monkeypatch.setattr("pyrnova.sources.sam.http.get_json", fake_get_json)
    pages = SamClient("secret-key").search_observations(
        posted_from="01/01/2026", posted_to="01/31/2026", limit=1, max_pages=3
    )

    assert [page.request_params["offset"] for page in pages] == [0, 1, 2]
    assert all("api_key" not in page.request_params for page in pages)


def test_pagination_validation_and_legacy_search_compatibility(monkeypatch):
    with pytest.raises(ValueError):
        build_params(posted_from="01/01/2026", posted_to="01/31/2026", limit=0)
    with pytest.raises(ValueError):
        build_params(posted_from="01/01/2026", posted_to="01/31/2026", offset=-1)
    with pytest.raises(ValueError):
        SamClient("secret-key").search_observations(
            posted_from="01/01/2026", posted_to="01/31/2026", max_pages=0
        )

    monkeypatch.setattr(
        "pyrnova.sources.sam.http.get_json",
        lambda _url, _params, **_kwargs: (200, b'{"opportunitiesData":[]}', {"opportunitiesData": []}),
    )
    raw, rows = SamClient("secret-key").search(
        posted_from="01/01/2026", posted_to="01/31/2026"
    )
    assert raw == b'{"opportunitiesData":[]}'
    assert rows == []
