from pathlib import Path

import pytest

from pyrnova.sources.ofac import (
    OfacClient,
    download_url,
    name_candidates,
    parse_ofac_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"
SDN_FIXTURE = (FIXTURES / "ofac_sdn_sample.csv").read_bytes()


def test_download_url_builds_correct_urls_and_rejects_unknown():
    assert download_url("sdn") == "https://www.treasury.gov/ofac/downloads/sdn.csv"
    assert (
        download_url("consolidated")
        == "https://www.treasury.gov/ofac/downloads/consolidated/cons_prim.csv"
    )
    with pytest.raises(ValueError):
        download_url("nonexistent_list")


def test_parse_ofac_csv_exact_keys_and_missing_field_handling():
    designations = parse_ofac_csv(SDN_FIXTURE, list_name="sdn")
    assert len(designations) == 5

    expected_keys = {
        "source_id",
        "source_ref",
        "ent_num",
        "sdn_name",
        "sdn_type",
        "program",
        "title",
        "remarks",
        "list_name",
        "record_kind",
    }
    for d in designations:
        assert set(d.keys()) == expected_keys
        assert d["source_id"] == "sanctions_ofac"
        assert d["list_name"] == "sdn"
        assert d["record_kind"] == "sdn_designation"
        assert isinstance(d["ent_num"], int)

    petrov = designations[0]
    assert petrov["ent_num"] == 10001
    assert petrov["sdn_name"] == "PETROV, Ivan Sergeyevich"
    assert petrov["sdn_type"] == "individual"
    assert petrov["program"] == "RUSSIA-EO14024"
    assert petrov["title"] == "Former Deputy Minister"
    # quoted-comma field parsed intact as a single remarks value
    assert petrov["remarks"] == (
        "Sanctioned pursuant to E.O. 14024; DOB 12 Mar 1971; POB Moscow, Russia"
    )
    assert petrov["source_ref"] == "ofac:sdn:10001"

    kovalenko = designations[4]
    assert kovalenko["title"] is None  # "-0-" -> None
    assert kovalenko["remarks"] is None


def test_parse_ofac_csv_consolidated_record_kind():
    designations = parse_ofac_csv(SDN_FIXTURE, list_name="consolidated")
    assert designations
    assert all(d["record_kind"] == "consolidated_designation" for d in designations)
    assert all(d["list_name"] == "consolidated" for d in designations)


def test_fetch_list_offline_preserves_raw_bytes_and_hash():
    import hashlib

    client = OfacClient()
    snapshot = client.fetch_list("sdn", offline_bytes=SDN_FIXTURE)

    assert snapshot.raw_response == SDN_FIXTURE
    assert snapshot.content_sha256 == hashlib.sha256(SDN_FIXTURE).hexdigest()
    assert snapshot.list_name == "sdn"
    assert snapshot.source_url == "https://www.treasury.gov/ofac/downloads/sdn.csv"
    assert snapshot.fetched_at  # ISO timestamp present

    # round-trips to the same normalization as calling parse_ofac_csv directly
    assert snapshot.designations == parse_ofac_csv(SDN_FIXTURE, list_name="sdn")


def test_name_candidates_matches_planted_entity_as_weak_nonauthoritative():
    designations = parse_ofac_csv(SDN_FIXTURE, list_name="sdn")

    hits = name_candidates(designations, "Global Defense Supply Inc")
    assert len(hits) == 1
    hit = hits[0]
    assert hit["sdn_name"] == "GLOBAL DEFENSE SUPPLY LLC"
    assert hit["authoritative"] is False
    assert hit["match_basis"] == "name_only_weak"

    # idempotent
    hits_again = name_candidates(designations, "Global Defense Supply Inc")
    assert hits_again == hits


def test_name_candidates_rejects_generic_word_only_query():
    designations = parse_ofac_csv(SDN_FIXTURE, list_name="sdn")
    hits = name_candidates(designations, "the company llc")
    assert hits == []
