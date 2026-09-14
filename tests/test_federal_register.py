import pytest

from pyrnova.sources.federal_register import (
    FederalRegisterClient,
    build_params,
    document_url,
)


def test_build_params_uses_official_filter_names():
    params = build_params(
        agency_ids=["defense-department"],
        document_types=["RULE", "NOTICE"],
        term="cybersecurity",
        publication_date_start="2026-01-01",
        publication_date_end="2026-01-31",
        page=2,
        per_page=25,
    )
    assert params == {
        "conditions[agency_ids][]": ["defense-department"],
        "conditions[type][]": ["RULE", "NOTICE"],
        "conditions[term]": "cybersecurity",
        "conditions[publication_date][gte]": "2026-01-01",
        "conditions[publication_date][lte]": "2026-01-31",
        "page": 2,
        "per_page": 25,
        "order": "newest",
    }


def test_document_url_requires_document_number():
    assert document_url("2026-12345") == "https://www.federalregister.gov/documents/2026-12345"
    assert document_url(None) is None


def test_client_preserves_response_request_and_fetch_provenance(monkeypatch):
    raw = b'{"results":[{"document_number":"2026-12345"}]}'
    calls = []

    def fake_get_json(url, params, *, source_id):
        assert source_id == "federal_register"
        calls.append((url, params))
        return 200, raw, {"results": [{"document_number": "2026-12345"}]}

    monkeypatch.setattr("pyrnova.sources.federal_register.http.get_json", fake_get_json)
    pages = FederalRegisterClient().search_documents(term="acquisition", per_page=10)

    assert len(pages) == 1
    observed = pages[0]
    assert observed.raw_response == raw
    assert observed.documents[0]["document_number"] == "2026-12345"
    assert observed.request_params["conditions[term]"] == "acquisition"
    assert observed.source_url.endswith("/documents.json")
    assert observed.fetched_at.endswith("+00:00")
    assert calls[0][1] == observed.request_params


def test_invalid_pagination_is_rejected():
    with pytest.raises(ValueError):
        build_params(page=0)
    with pytest.raises(ValueError):
        build_params(per_page=1001)
