"""Tests for pyrnova.grounding: USAspending award bytes -> evidence-backed facts."""

import json
import os

import pytest

from pyrnova.grounding import detect_vehicles, parse_amount, parse_usaspending_awards

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "real_evidence",
)
TORCH_PATH = os.path.join(FIXTURE_DIR, "usaspending_torch.json")
MTSI_PATH = os.path.join(FIXTURE_DIR, "usaspending_mtsi.json")


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


CONTRACT_KEYS = {
    "company_name",
    "source_id",
    "recipient_names",
    "awards",
    "contract_history",
    "capability_records",
    "scale",
    "vehicles",
    "buyer_agencies",
    "award_count",
}

AWARD_KEYS = {
    "award_ref",
    "generated_internal_id",
    "source_url",
    "agency",
    "sub_agency",
    "buyer_agency",
    "amount_usd",
    "start_date",
    "end_date",
    "award_type",
    "description",
    "naics",
    "psc",
    "role",
    "available_at",
    "observed_at",
}

CONTRACT_HISTORY_KEYS = {
    "agency",
    "naics",
    "psc",
    "value_usd",
    "role",
    "award_ref",
    "program_key",
    "description",
    "available_at",
}

CAPABILITY_RECORD_KEYS = {
    "source_id",
    "source_ref",
    "available_at",
    "description",
    "naics",
    "psc",
}


def test_torch_fixture():
    raw = _read_bytes(TORCH_PATH)
    result = parse_usaspending_awards(raw, company_name="Torch Technologies")

    assert set(result.keys()) == CONTRACT_KEYS
    assert "TORCH TECHNOLOGIES INC" in result["recipient_names"]
    assert result["award_count"] >= 15
    assert result["scale"]["max_contract_usd"] > 500_000_000
    assert any("HWIL" in (a["description"] or "") for a in result["awards"])
    assert "GSA OASIS SB" in result["vehicles"]
    assert "Department of the Army" in result["buyer_agencies"]
    assert all(a["available_at"] for a in result["awards"])

    for award in result["awards"]:
        assert set(award.keys()) == AWARD_KEYS
        assert award["role"] == "prime"
    for entry in result["contract_history"]:
        assert set(entry.keys()) == CONTRACT_HISTORY_KEYS
    for entry in result["capability_records"]:
        assert set(entry.keys()) == CAPABILITY_RECORD_KEYS


def test_mtsi_fixture():
    raw = _read_bytes(MTSI_PATH)
    result = parse_usaspending_awards(raw, company_name="Modern Technology Solutions")

    assert "MODERN TECHNOLOGY SOLUTIONS, INC." in result["recipient_names"]
    assert any(a["buyer_agency"] == "Missile Defense Agency" for a in result["awards"])

    future_awards = [a for a in result["awards"] if (a["available_at"] or "").startswith("2025")]
    assert future_awards, "expected a 2025-dated award (ARCWERX ARTEMIS) to be preserved"
    assert any(a["award_ref"] == "47QFSA25F0011" for a in future_awards)


def test_detect_vehicles():
    assert detect_vehicles("GSA OASIS SB POOL 5B") == ["GSA OASIS SB"]
    assert detect_vehicles("no vehicle here") == []
    assert detect_vehicles("") == []
    assert detect_vehicles(None) == []


def test_detect_vehicles_multiple_and_variants():
    assert detect_vehicles("Awarded via NASA SEWP under an IDIQ") == ["IDIQ", "NASA SEWP"]
    assert detect_vehicles("OASIS SMALL BUSINESS pool") == ["GSA OASIS SB"]
    assert detect_vehicles("plain OASIS award") == ["GSA OASIS"]
    # OASIS SB should not also register the plain "GSA OASIS" vehicle
    result = detect_vehicles("GSA OASIS SB task order")
    assert "GSA OASIS" not in result
    assert "GSA OASIS SB" in result
    assert "GSA schedule" not in result

    # a standalone GSA mention elsewhere in the text still registers
    result2 = detect_vehicles("GSA schedule contract, separately under IDIQ")
    assert "GSA schedule" in result2


def test_dedupe_keeps_highest_amount():
    payload = {
        "results": [
            {
                "Award ID": "ABC123",
                "Recipient Name": "TEST CO",
                "Start Date": "2020-01-01",
                "End Date": "2021-01-01",
                "Award Amount": 100.0,
                "Awarding Agency": "Agency A",
                "Awarding Sub Agency": "Sub A",
                "Contract Award Type": "DELIVERY ORDER",
                "Description": "first row",
                "NAICS Code": None,
                "PSC Code": None,
                "generated_internal_id": "GID1",
            },
            {
                "Award ID": "ABC123",
                "Recipient Name": "TEST CO",
                "Start Date": "2020-01-01",
                "End Date": "2021-01-01",
                "Award Amount": 500.0,
                "Awarding Agency": "Agency A",
                "Awarding Sub Agency": "Sub A",
                "Contract Award Type": "DELIVERY ORDER",
                "Description": "second row, higher amount",
                "NAICS Code": None,
                "PSC Code": None,
                "generated_internal_id": "GID2",
            },
        ]
    }
    raw = json.dumps(payload).encode("utf-8")
    result = parse_usaspending_awards(raw, company_name="Test Co")

    assert result["award_count"] == 1
    assert len(result["awards"]) == 1
    assert result["awards"][0]["amount_usd"] == 500.0
    assert result["awards"][0]["description"] == "second row, higher amount"


def test_deterministic_parsing():
    raw = _read_bytes(TORCH_PATH)
    result1 = parse_usaspending_awards(raw, company_name="Torch Technologies")
    result2 = parse_usaspending_awards(raw, company_name="Torch Technologies")
    assert result1 == result2


def test_row_missing_award_id_is_skipped():
    payload = {
        "results": [
            {
                "Recipient Name": "TEST CO",
                "Start Date": "2020-01-01",
                "Award Amount": 100.0,
                "Description": "no award id",
            },
            {
                "Award ID": "XYZ999",
                "Recipient Name": "TEST CO",
                "Start Date": "2020-01-01",
                "Award Amount": 50.0,
                "Description": "has award id",
            },
        ]
    }
    raw = json.dumps(payload).encode("utf-8")
    result = parse_usaspending_awards(raw, company_name="Test Co")
    assert result["award_count"] == 1
    assert result["awards"][0]["award_ref"] == "XYZ999"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("623310899.16", 623310899.16),
        (1000, 1000.0),
        (1000.5, 1000.5),
        ("", None),
        (None, None),
        ("not a number", None),
        ("1,000", 1000.0),
        ("  42  ", 42.0),
        ("$1,000.50", 1000.50),
    ],
)
def test_parse_amount(value, expected):
    assert parse_amount(value) == expected


def test_source_url_none_without_generated_internal_id():
    payload = {
        "results": [
            {
                "Award ID": "NOID1",
                "Recipient Name": "TEST CO",
                "Start Date": "2020-01-01",
                "Award Amount": 10.0,
                "Description": "no generated internal id",
            }
        ]
    }
    raw = json.dumps(payload).encode("utf-8")
    result = parse_usaspending_awards(raw, company_name="Test Co")
    assert result["awards"][0]["source_url"] is None


def test_capability_records_only_for_nonempty_description():
    payload = {
        "results": [
            {
                "Award ID": "NODESC1",
                "Recipient Name": "TEST CO",
                "Start Date": "2020-01-01",
                "Award Amount": 10.0,
                "Description": "",
            },
            {
                "Award ID": "HASDESC1",
                "Recipient Name": "TEST CO",
                "Start Date": "2020-01-01",
                "Award Amount": 10.0,
                "Description": "a real description",
            },
        ]
    }
    raw = json.dumps(payload).encode("utf-8")
    result = parse_usaspending_awards(raw, company_name="Test Co")
    assert len(result["capability_records"]) == 1
    assert result["capability_records"][0]["source_ref"] == "HASDESC1"


def test_source_id_default_and_override():
    raw = _read_bytes(TORCH_PATH)
    default_result = parse_usaspending_awards(raw, company_name="Torch Technologies")
    assert default_result["source_id"] == "usaspending"

    custom_result = parse_usaspending_awards(
        raw, company_name="Torch Technologies", source_id="usaspending_v2"
    )
    assert custom_result["source_id"] == "usaspending_v2"
    assert custom_result["capability_records"][0]["source_id"] == "usaspending_v2"
