from pyrnova.sources.usaspending import build_payload, REQUEST_FIELDS, CONTRACT_TYPE_CODES


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
