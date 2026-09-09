"""M21 corpus: raw termination flagship + SUBSIDIARY_OF diversity + selectivity, all cases pass,
frozen M15-M20 corpora byte-identical, no propagation explosion, no temporal leakage."""

import hashlib
from pathlib import Path

import pytest

from pyrnova import threat
from pyrnova.sources import ofac

CORPUS = "examples/replay/corpus_m21.json"
DESIGNATIONS = ofac.parse_ofac_csv(Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")

# Every prior threat corpus stays byte-for-byte frozen (M21 extends, never edits).
FROZEN = {
    "examples/replay/corpus_m15.json": "7849beae3282d76a99f7a8e3d00f80665ae5ad4284fc55c8ef499c8d836bd2b4",
    "examples/replay/corpus_m16.json": "8d42c7e9206182dd31e3fad60db59dbab053b8d95e113eb2bc10279e0e9ceb69",
    "examples/replay/corpus_m17.json": "f9ac9458901dcda480ce2b25e9463a8c8ae85dee658b021a8e617dbea5343bb8",
    "examples/replay/corpus_m18.json": "7fdfad85a582861f74457e41578750ac41e49501d4ca6a2d4e88ef570d007004",
    "examples/replay/corpus_m19.json": "60f581c9c573bf6766e4e176e7cbc2b418bc9f5f176c51c57efd64a64ce4baa7",
    "examples/replay/corpus_m20.json": "3b54565d5bc3e8e93f5d0f8d8e43d1761ba9ae1d3462be412e23f1e68281a5b0",
}


@pytest.fixture(scope="module")
def replayed():
    payload = threat.load_threat_corpus(CORPUS)
    return payload, threat.run_threat_corpus(payload, DESIGNATIONS)


def test_m21_extends_frozen_m20_and_all_cases_pass(replayed):
    for path, expected in FROZEN.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    payload, results = replayed
    assert len(payload["threat_cases"]) == 80  # 74 (M20 lineage) + 6 (M21)
    assert sum(1 for r in results if r["case_id"].startswith("m21-")) == 6
    assert not [r["case_id"] for r in results if not r["ok"]]


def test_new_economic_relationship_type_and_raw_termination(replayed):
    _, results = replayed
    summary = threat.summarize_m21(results)
    div = summary["m21_relationship_diversity"]
    assert div["subsidiary_of_exercised"] is True
    assert "SUBSIDIARY_OF" in div["economic_relationship_types_beyond_program_graph"]
    raw = summary["m21_raw_adverse_event"]
    assert raw["raw_authoritative_bytes"] is True
    assert raw["termination_direct_threats"] >= 1
    assert raw["termination_propagated_threats"] >= 1


def test_flagship_chain_deterministic_observed_and_bounded(replayed):
    _, results = replayed
    result = next(r for r in results if r["case_id"] == "m21-real-termination-subsidiary")
    direct = next(t for t in result["threats"] if t["mechanism"] == "PROGRAM_CANCELLATION_OR_DELAY")
    propagated = result["propagation"]["propagated_threats"][0]
    hop = propagated["meta"]["propagation_path"][0]
    assert direct["confidence"] == "HIGH" and direct["severity"] == "LOW"
    assert direct["meta"]["catalyst_class"] == "OBSERVED"
    assert direct["meta"]["exposure_join_class"] == "deterministic"
    assert hop["relation"] == "SUBSIDIARY_OF" and hop["join_method"] == "deterministic_native_id"
    # Confidence never increases across the hop; severity not inflated by graph distance.
    assert propagated["confidence"] == "MEDIUM"
    assert threat.CONFIDENCE_LEVELS.index(propagated["confidence"]) <= threat.CONFIDENCE_LEVELS.index(direct["confidence"])


def test_no_explosion_no_leakage_and_outcome_honestly_unresolved(replayed):
    _, results = replayed
    summary = threat.summarize_m21(results)
    assert summary["propagation_quality"]["propagation_explosion"] is False
    assert summary["propagation_quality"]["confidence_never_increases"] is True
    assert summary["temporal_leakage_violations"] == 0
    # The flagship termination has no forced outcome (days old; no defensible later evidence).
    flagship = next(r for r in results if r["case_id"] == "m21-real-termination-subsidiary")
    assert flagship["outcome"] is None or flagship["outcome"].get("resolved") in (False, None)
    # Broader source/relationship coverage did not create threat explosion: negatives outnumber the
    # single new flagship threat family growth (selectivity preserved).
    m21 = [r for r in results if r["case_id"].startswith("m21-")]
    negatives = sum(1 for r in m21 if not r["threats"] and r["rejections"])
    assert negatives >= 2
