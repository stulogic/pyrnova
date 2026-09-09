"""M17 — corpus_m17 replay + calibration + frozen-lineage integrity."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pyrnova import threat
from pyrnova.sources import ofac

CORPUS = "examples/replay/corpus_m17.json"
DESIGNATIONS = ofac.parse_ofac_csv(
    Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")

# Frozen upstream corpora must stay byte-for-byte identical (M17 extends, never edits).
_FROZEN = {
    "examples/replay/corpus_m15.json":
        "7849beae3282d76a99f7a8e3d00f80665ae5ad4284fc55c8ef499c8d836bd2b4",
    "examples/replay/corpus_m16.json":
        "8d42c7e9206182dd31e3fad60db59dbab053b8d95e113eb2bc10279e0e9ceb69",
}


@pytest.fixture(scope="module")
def replayed():
    payload = threat.load_threat_corpus(CORPUS)
    return payload, threat.run_threat_corpus(payload, DESIGNATIONS)


def test_frozen_corpora_byte_identical():
    for path, want in _FROZEN.items():
        got = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert got == want, f"{path} changed — M17 must extend, never edit a frozen corpus"


def test_all_cases_pass(replayed):
    _, results = replayed
    failed = [r["case_id"] for r in results if not r["ok"]]
    assert not failed, f"failing cases: {failed}"


def test_m17_extends_m16_without_altering_it(replayed):
    payload, _ = replayed
    ids = [c["case_id"] for c in payload["threat_cases"]]
    # Every m16 case id survives unchanged, and m17 adds its own.
    assert sum(1 for i in ids if i.startswith("m16-")) == 18
    assert sum(1 for i in ids if i.startswith("m17-")) == 11
    assert len(ids) == len(set(ids))          # no duplicate ids across the merged lineage


def test_two_real_propagation_chains(replayed):
    """Both flagship cases produce a direct threat on SAIC that propagates exactly one hop to Torch,
    with confidence and severity DEGRADED (never increased)."""
    _, results = replayed
    by_id = {r["case_id"]: r for r in results}
    for cid, mech in (("m17-real-propagation-saic-gsa", "PROGRAM_CONTRACTION"),
                      ("m17-real-propagation-saic-army", "PROGRAM_CANCELLATION_OR_DELAY")):
        r = by_id[cid]
        assert r["real_subject"] is True
        assert r["threat_count"] == 1
        direct = r["threats"][0]
        assert direct["mechanism"] == mech
        assert direct["severity"] == "CRITICAL" and direct["confidence"] == "HIGH"
        prop = r["propagation"]
        assert prop["stats"]["propagated_threats"] == 1
        assert prop["stats"]["max_depth_reached"] == 1
        pt = prop["propagated_threats"][0]
        assert pt["subject_ref"] == "co_torch"
        assert pt["mechanism"] == mech               # same mechanism carried downstream
        assert pt["severity"] == "HIGH"              # degraded one band from CRITICAL
        assert pt["confidence"] == "MEDIUM"          # degraded one step from HIGH (never up)
        assert pt["meta"]["propagated"] is True
        assert pt["meta"]["root_threat_id"] == direct["id"]
        assert pt["meta"]["propagation_path"]        # full per-hop provenance retained


def test_calibration_expanded_beyond_five_with_denominator(replayed):
    _, results = replayed
    cal = threat.summarize_m16(results)["calibration"]
    assert cal["resolved_outcomes"] >= 12            # materially beyond M16's 5
    assert cal["confirmed_threat_precision_denominator"] == cal["resolved_outcomes"]
    # An honest FALSE_ALARM keeps precision below a vacuous 1.0.
    assert 0.0 < cal["confirmed_threat_precision"] < 1.0
    assert cal["detection_distribution"].get("FALSE_ALERT") == 1
    assert cal["false_alert_from_absence"] == 0      # invariant: absence is never a false alert
    assert cal["median_lead_time_days"] is not None


def test_future_outcome_excluded(replayed):
    _, results = replayed
    r = next(x for x in results if x["case_id"] == "m17-future-outcome-exclusion")
    assert r["outcome"]["label"] == "UNKNOWN"
    assert r["outcome"]["resolved"] is False
    assert r["outcome"]["future_excluded_count"] == 1
    assert r["detection_quality"] == "UNRESOLVED"     # never retro-resolved by future evidence


def test_no_propagation_or_threat_explosion(replayed):
    _, results = replayed
    s = threat.summarize_m16(results)
    # Propagation stays small and bounded — real edges did not turn the graph into an amplifier.
    assert s["propagated_threats"] <= s["direct_threats"]
    assert s["max_propagation_depth"] <= 2
    assert s["cycles_prevented"] == 0                 # no cycles present to prevent in this corpus
