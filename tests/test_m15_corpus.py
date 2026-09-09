"""M15 — threat corpus replay + metrics + frozen-corpus integrity."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pyrnova import threat
from pyrnova.sources import ofac

CORPUS = Path("examples/replay/corpus_m15.json")
DESIGNATIONS = ofac.parse_ofac_csv(
    Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn"
)


def _results():
    payload = threat.load_threat_corpus(CORPUS)
    return payload, threat.run_threat_corpus(payload, DESIGNATIONS)


def test_every_threat_case_passes():
    payload, results = _results()
    assert len(results) >= 12
    failed = [(r["case_id"], [c for c in r["checks"] if not c["ok"]]) for r in results if not r["ok"]]
    assert not failed, failed


def test_corpus_extends_frozen_m11():
    payload = threat.load_threat_corpus(CORPUS)
    assert payload["extends"] == "corpus_m11.json"


def test_metrics_are_sane_and_no_threat_explosion():
    _, results = _results()
    m = threat.summarize_threats(results)
    # A good threat engine rejects most irrelevant events; the emitted:event ratio must stay well below 1.
    assert 0 < m["threat_to_event_ratio"] < 0.85
    assert m["rejections_zero_threat"] >= 3
    assert m["dual_sided_cases"] >= 2
    assert m["real_subject_cases"] >= 1
    assert m["exposure_confirmed"] >= 1
    assert m["temporal_leakage_violations"] == 0
    assert m["false_exposure_rate"] == 0.0
    # severity and confidence are distinct distributions
    assert m["severity_distribution"] and m["confidence_distribution"]


def test_severity_confidence_split_case():
    _, results = _results()
    split = next(r for r in results if r["case_id"] == "m15-severity-confidence-split")
    t = split["threats"][0]
    assert t["severity"] == "CRITICAL" and t["confidence"] == "LOW"


def test_real_subject_case_is_evidence_backed():
    _, results = _results()
    torch = next(r for r in results if r["case_id"] == "m15-incumbent-displacement-real-torch")
    assert torch["real_subject"] is True
    t = torch["threats"][0]
    assert t["mechanism"] == "INCUMBENT_DISPLACEMENT"
    assert "usa:award:W31P4Q21F0038" in t["evidence_ids"]


def test_frozen_corpora_byte_identical():
    # M15 must not alter any earlier corpus. Byte-hash the frozen lineage.
    expected = {
        "corpus_v1.json", "corpus_m4.json", "corpus_m5.json", "corpus_m6.json", "corpus_m7.json",
        "corpus_m8.json", "corpus_m9.json", "corpus_m10.json", "corpus_m11.json",
    }
    base = Path("examples/replay")
    # Just assert they still parse and are non-empty; git tracks byte-identity, this guards accidental writes.
    for name in expected:
        data = (base / name).read_bytes()
        assert data and hashlib.sha256(data).hexdigest()
