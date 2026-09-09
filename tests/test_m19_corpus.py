"""M19 — corpus_m19 replay + deterministic-vs-inferred / multi-family metrics + frozen lineage."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pyrnova import threat
from pyrnova.sources import ofac

CORPUS = "examples/replay/corpus_m19.json"
DESIGNATIONS = ofac.parse_ofac_csv(
    Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")

# Frozen upstream corpora must stay byte-for-byte identical (M19 extends, never edits).
_FROZEN = {
    "examples/replay/corpus_m15.json":
        "7849beae3282d76a99f7a8e3d00f80665ae5ad4284fc55c8ef499c8d836bd2b4",
    "examples/replay/corpus_m16.json":
        "8d42c7e9206182dd31e3fad60db59dbab053b8d95e113eb2bc10279e0e9ceb69",
    "examples/replay/corpus_m17.json":
        "f9ac9458901dcda480ce2b25e9463a8c8ae85dee658b021a8e617dbea5343bb8",
    "examples/replay/corpus_m18.json":
        "7fdfad85a582861f74457e41578750ac41e49501d4ca6a2d4e88ef570d007004",
}


@pytest.fixture(scope="module")
def replayed():
    payload = threat.load_threat_corpus(CORPUS)
    return payload, threat.run_threat_corpus(payload, DESIGNATIONS)


def test_frozen_corpora_byte_identical():
    for path, want in _FROZEN.items():
        got = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert got == want, f"{path} changed — M19 must extend, never edit a frozen corpus"


def test_all_cases_pass(replayed):
    _, results = replayed
    failed = [r["case_id"] for r in results if not r["ok"]]
    assert not failed, f"failing cases: {failed}"


def test_m19_extends_m18_without_altering_it(replayed):
    payload, _ = replayed
    ids = [c["case_id"] for c in payload["threat_cases"]]
    assert len(ids) == len(set(ids))                          # unique across the merged lineage
    m18 = threat.load_threat_corpus("examples/replay/corpus_m18.json")
    m18_ids = {c["case_id"] for c in m18["threat_cases"]}
    assert m18_ids.issubset(set(ids))                         # every M18 case carried forward
    assert sum(1 for i in ids if i.startswith("m19")) >= 8    # M19 adds its own cases


def test_second_adverse_event_family_is_integrated(replayed):
    """A second OBSERVED adverse-event family (contract_modification) is exercised and is materially
    different from the BIS/Federal Register export-control family."""
    _, results = replayed
    s = threat.summarize_m19(results)
    fams = s["adverse_event_families_exercised"]
    assert "contract_modification" in fams and "regulatory_adverse_event" in fams
    # The new family is not noisier than the incumbent one (it stays selective).
    cm = s["multi_family_selectivity"]["contract_modification"]
    assert cm["direct_threats"] >= 1 and cm["rejections"] >= 1


def test_real_deterministic_observed_high_confidence_chain(replayed):
    """At least one REAL observed catalyst has a deterministic exposure and a HIGH-confidence direct
    threat, and it propagates one hop to a real relationship (confidence degrades, never increases)."""
    _, results = replayed
    r = next(x for x in results if x["case_id"] == "m19-det-contraction-saic-torch")
    assert r["real_subject"] is True
    t = r["threats"][0]
    assert t["mechanism"] == "PROGRAM_CONTRACTION"
    assert t["confidence"] == "HIGH"
    assert t["meta"]["catalyst_class"] == "OBSERVED"
    assert t["meta"]["exposure_join_class"] == "deterministic"
    pt = r["propagation"]["propagated_threats"]
    assert len(pt) == 1 and pt[0]["subject_ref"] == "co_torch"
    assert pt[0]["meta"]["catalyst_class"] == "OBSERVED"
    assert pt[0]["meta"]["exposure_join_class"] == "deterministic"
    # confidence degraded across the hop (HIGH -> MEDIUM), never increased.
    order = ("UNKNOWN", "LOW", "MEDIUM", "HIGH")
    assert order.index(pt[0]["confidence"]) < order.index(t["confidence"])


def test_deterministic_identity_alone_is_not_a_threat(replayed):
    """Deterministic no-threat cases exist: immaterial, wrong-award, lapsed-exposure."""
    _, results = replayed
    by = {r["case_id"]: r for r in results}
    assert by["m19-det-contraction-immaterial-negative"]["rejections"][0]["reason_code"] == "IMMATERIAL"
    assert by["m19-det-wrong-award-no-exposure"]["rejections"][0]["reason_code"] == "NO_EXPOSURE"
    assert by["m19-temporal-exposure-ended"]["rejections"][0]["reason_code"] == "EXPOSURE_ENDED"
    for cid in ("m19-det-contraction-immaterial-negative", "m19-det-wrong-award-no-exposure",
                "m19-temporal-exposure-ended", "m19-det-future-catalyst-excluded"):
        assert by[cid]["threats"] == []


def test_deterministic_vs_inferred_and_propagated_calibration(replayed):
    """Deterministic-vs-inferred exposure metrics exist; propagated-outcome calibration expanded."""
    _, results = replayed
    s = threat.summarize_m19(results)
    dvi = s["deterministic_vs_inferred"]
    assert dvi["deterministic_exposures"] > 0 and dvi["inferred_exposures"] > 0
    assert dvi["deterministic_direct_threats"] > 0
    assert dvi["observed_deterministic_high_confidence_threats"] >= 1
    # At least one REAL deterministic observed HIGH-confidence direct threat.
    real_obs_det_high = [
        t for r in results if r.get("real_subject")
        for t in r["threats"]
        if t["confidence"] == "HIGH" and (t.get("meta") or {}).get("catalyst_class") == "OBSERVED"
        and (t.get("meta") or {}).get("exposure_join_class") == "deterministic"]
    assert len(real_obs_det_high) >= 1
    # Resolved propagated outcomes expanded beyond M18's 1 (Workstream M) with diversity.
    poc = s["propagated_outcome_calibration"]
    assert poc["resolved_propagated"] >= 3
    assert poc["false_alert_from_absence"] == 0
    labels = {r["propagated_outcome"]["label"] for r in results
              if r.get("propagated_outcome") and r["propagated_outcome"].get("resolved")}
    assert {"MATERIALIZED", "MITIGATED", "AVOIDED"}.issubset(labels)


def test_no_threat_or_propagation_explosion(replayed):
    _, results = replayed
    s = threat.summarize_m19(results)
    assert s["propagation_quality"]["propagation_explosion"] is False
    assert s["propagation_quality"]["confidence_never_increases"] is True
    assert s["temporal_leakage_violations"] == 0
