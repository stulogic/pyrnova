"""M18 — corpus_m18 replay + independence/authority/propagated-calibration metrics + frozen lineage."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pyrnova import threat
from pyrnova.sources import ofac

CORPUS = "examples/replay/corpus_m18.json"
DESIGNATIONS = ofac.parse_ofac_csv(
    Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")

# Frozen upstream corpora must stay byte-for-byte identical (M18 extends, never edits).
_FROZEN = {
    "examples/replay/corpus_m15.json":
        "7849beae3282d76a99f7a8e3d00f80665ae5ad4284fc55c8ef499c8d836bd2b4",
    "examples/replay/corpus_m16.json":
        "8d42c7e9206182dd31e3fad60db59dbab053b8d95e113eb2bc10279e0e9ceb69",
    "examples/replay/corpus_m17.json":
        "f9ac9458901dcda480ce2b25e9463a8c8ae85dee658b021a8e617dbea5343bb8",
}


@pytest.fixture(scope="module")
def replayed():
    payload = threat.load_threat_corpus(CORPUS)
    return payload, threat.run_threat_corpus(payload, DESIGNATIONS)


def test_frozen_corpora_byte_identical():
    for path, want in _FROZEN.items():
        got = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert got == want, f"{path} changed — M18 must extend, never edit a frozen corpus"


def test_all_cases_pass(replayed):
    _, results = replayed
    failed = [r["case_id"] for r in results if not r["ok"]]
    assert not failed, f"failing cases: {failed}"


def test_m18_extends_m17_without_altering_it(replayed):
    payload, _ = replayed
    ids = [c["case_id"] for c in payload["threat_cases"]]
    assert len(ids) == len(set(ids))                          # unique across the merged lineage
    m17 = threat.load_threat_corpus("examples/replay/corpus_m17.json")
    m17_ids = {c["case_id"] for c in m17["threat_cases"]}
    assert m17_ids.issubset(set(ids))                         # every M17 case carried forward
    assert sum(1 for i in ids if i.startswith("m18")) >= 10   # M18 adds its own cases


def test_observed_real_chains_independent_of_saic(replayed):
    """>=2 REAL observed-catalyst propagation chains, using pairs independent of SAIC<->Torch."""
    _, results = replayed
    s = threat.summarize_m18(results)
    assert s["catalyst_authority"]["observed_direct_threats"] >= 3
    assert s["catalyst_authority"]["observed_vs_modeled_distinct"] is True
    # The two flagship real chains (Parsons, Intuitive) each propagate one observed hop to Torch.
    for cid in ("m18-obs-export-control-parsons-torch", "m18-obs-export-control-intuitive-torch"):
        r = next(x for x in results if x["case_id"] == cid)
        pt = r["propagation"]["propagated_threats"]
        assert len(pt) == 1 and pt[0]["subject_ref"] == "co_torch"
        assert pt[0]["meta"]["catalyst_class"] == "OBSERVED"
        assert r["subject_ref"] != "co_saic"


def test_independence_and_diversity_reported(replayed):
    _, results = replayed
    ind = threat.summarize_m18(results)["relationship_independence"]
    assert ind["distinct_chain_company_pairs"] >= 3          # not all one underlying relationship
    assert ind["observed_catalyst_chains"] >= 2
    assert "federal_register" in ind["distinct_source_families"]


def test_no_explosion_and_confidence_never_increases(replayed):
    _, results = replayed
    q = threat.summarize_m18(results)["propagation_quality"]
    assert q["confidence_never_increases"] is True
    assert q["propagation_explosion"] is False
    assert q["max_propagation_depth"] <= 2


def test_negative_and_weak_termination_present(replayed):
    _, results = replayed
    s = threat.summarize_m18(results)
    assert s["negative_cases"] >= 1
    # A real single-occurrence edge terminates propagation end to end.
    ntsi = next(r for r in results if r["case_id"] == "m18-obs-weak-edge-terminates-ntsi")
    assert ntsi["threat_count"] == 1
    assert ntsi["propagation"]["stats"]["propagated_threats"] == 0
    assert ntsi["propagation"]["stats"]["weak_or_exhausted_terminations"] >= 1


def test_propagated_outcome_calibration_begun(replayed):
    _, results = replayed
    cal = threat.summarize_m18(results)["propagated_outcome_calibration"]
    assert cal["resolved_propagated"] >= 1
    assert cal["resolved_direct"] >= 12
    assert cal["false_alert_from_absence"] == 0


def test_resolved_outcomes_grew(replayed):
    _, results = replayed
    cal = threat.summarize_m18(results)["calibration"]
    assert cal["resolved_outcomes"] >= 15                    # M17 closed at 12
    assert cal["confirmed_threat_precision_denominator"] == cal["resolved_outcomes"] or \
        cal["confirmed_threat_precision"] is not None


def test_archived_fr_evidence_integrity():
    """The committed FR evidence content hash matches its own recorded provenance (archive-once)."""
    import json
    payload = json.loads(Path("examples/real_evidence/federal_register_bis_export_controls.json").read_text())
    canon = json.dumps(payload["results"], sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canon).hexdigest() == payload["provenance"]["content_sha256"]
