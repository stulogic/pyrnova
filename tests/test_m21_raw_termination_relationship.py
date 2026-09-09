"""M21 honesty gate: RAW authoritative contract termination + deterministic exposure +
new SUBSIDIARY_OF economic relationship + bounded propagation. All offline over archived raw bytes."""

import hashlib
import json
from pathlib import Path

from pyrnova.adverse_events import (
    parse_usaspending_award_termination,
    to_contract_termination_catalyst,
)
from pyrnova.propagation import propagate_threats
from pyrnova.relationships import ground_subsidiary_edges
from pyrnova.threat import assess_threats, incumbency_exposures

RE = Path("examples/real_evidence")
TXNS = RE / "usaspending_award_termination_dap.transactions.json"
AWARD = RE / "usaspending_award_termination_dap.award.json"
RECIP = RE / "usaspending_recipient_dap.json"

PIID = "36C25726N0240"
CHILD_UEI = "YR7CLZFGCM95"
PARENT_UEI = "KMSLVW1MZWU9"
CATALYST_DATE = "2026-08-31"


def _termination_event():
    return parse_usaspending_award_termination(
        TXNS.read_bytes(), piid=PIID, recipient_uei=CHILD_UEI,
        recipient_name="DAP CONSTRUCTION MANAGEMENT LLC", agency="Department of Veterans Affairs",
    )["events"][0]


def test_raw_termination_bytes_are_authoritative_and_hash_matches_provenance():
    raw = TXNS.read_bytes()
    prov = json.loads((RE / "usaspending_award_termination_dap.transactions.provenance.json").read_text())
    # The archived body's hash is the exact sha256 of the raw response bytes (immutable evidence).
    assert hashlib.sha256(raw).hexdigest() == prov["sha256"]
    assert prov["request_url"].startswith("https://api.usaspending.gov")
    ev = _termination_event()
    assert ev["event_type"] == "CONTRACT_TERMINATION"
    assert ev["termination_kind"] == "TERMINATE_FOR_CONVENIENCE"  # action_type F
    assert ev["action_type"] == "F" and ev["modification_number"] == "P00002"
    assert ev["piid"] == PIID and ev["recipient_uei"] == CHILD_UEI
    assert ev["federal_action_obligation"] == -3908263.25
    assert ev["amount_delta_usd"] == 3908263.25
    assert ev["action_date"] == CATALYST_DATE and ev["available_at"] == CATALYST_DATE
    assert ev["catalyst_class"] == "OBSERVED"
    assert ev["archive_hash"] == prov["sha256"]  # hash over the same raw bytes


def test_termination_is_positively_evidenced_not_inferred_from_absence():
    # A funding-only deobligation row (no TERMINAT, action_type C) must NOT be read as a termination.
    payload = {"results": [
        {"id": "x", "action_type": "C", "action_type_description": "FUNDING ONLY ACTION",
         "modification_number": "P00001", "description": "FUNDING ONLY.", "action_date": "2026-05-01",
         "federal_action_obligation": -1000.0},
    ]}
    out = parse_usaspending_award_termination(json.dumps(payload), piid=PIID, recipient_uei=CHILD_UEI)
    assert out["events"] == []


def test_subsidiary_edge_is_exact_native_id_and_self_parent_filtered():
    edges = ground_subsidiary_edges(RECIP.read_bytes(), child_ref="co_dap_sub",
                                    available_at="2026-03-04", valid_from="2026-03-04")
    assert len(edges) == 1
    e = edges[0]
    assert e["relation"] == "SUBSIDIARY_OF"
    assert e["join_method"] == "deterministic_native_id" and e["link_class"] == "CONFIRMED"
    assert e["from_ref"] == "co_dap_sub" and e["to_ref"] == f"co_uei_{PARENT_UEI}"
    assert e["provenance"]["child_uei"] == CHILD_UEI and e["provenance"]["parent_uei"] == PARENT_UEI
    # A recipient whose only "parent" is itself yields NO subsidiary edge (name is not identity).
    self_only = json.dumps({"uei": "AAAA1111BBBB", "parent_uei": "AAAA1111BBBB",
                            "name": "X", "parent_name": "X", "recipient_id": "r-C"})
    assert ground_subsidiary_edges(self_only, child_ref="co_x") == []


def _direct_threat():
    award_record = {
        "recipient_uei": CHILD_UEI, "program_key": PIID, "program_name": f"VA award {PIID}",
        "available_at": "2026-03-04", "period_start": "2026-03-04", "period_end": None,
        "amount_usd": 3950539.76, "agency": "Department of Veterans Affairs",
        "evidence_id": f"usaspending:award:{PIID}",
    }
    exposures = incumbency_exposures("co_dap_sub", "DAP CONSTRUCTION MANAGEMENT LLC", CHILD_UEI,
                                     [award_record], as_of=CATALYST_DATE)
    catalyst = to_contract_termination_catalyst(_termination_event())
    threats, rejections = assess_threats("co_dap_sub", "DAP CONSTRUCTION MANAGEMENT LLC",
                                         exposures, [catalyst], as_of=CATALYST_DATE)
    return exposures, threats, rejections


def test_direct_threat_is_deterministic_observed_high_confidence():
    _, threats, rejections = _direct_threat()
    direct = [t for t in threats if t.mechanism == "PROGRAM_CANCELLATION_OR_DELAY"]
    assert len(direct) == 1
    t = direct[0]
    assert t.confidence == "HIGH"
    assert t.affected_value_category == "CONTINUITY"
    assert t.meta["catalyst_class"] == "OBSERVED"
    assert t.meta["exposure_join_class"] == "deterministic"
    # Severity honestly follows the frozen dollar bands ($3.91M -> LOW band); confidence, not severity,
    # is what the categorical termination raises.
    assert t.severity == "LOW"


def test_termination_propagates_up_to_parent_over_subsidiary_edge():
    _, threats, _ = _direct_threat()
    seed = next(t for t in threats if t.mechanism == "PROGRAM_CANCELLATION_OR_DELAY")
    edge = ground_subsidiary_edges(RECIP.read_bytes(), child_ref="co_dap_sub",
                                   available_at="2026-03-04", valid_from="2026-03-04")[0]
    result = propagate_threats([seed], [edge], as_of=CATALYST_DATE)
    assert result["stats"]["propagated_threats"] == 1
    pt = result["propagated_threats"][0]
    assert pt.subject_ref == f"co_uei_{PARENT_UEI}"
    assert pt.confidence == "MEDIUM"  # HIGH degraded one step across a CONFIRMED edge (never increases)
    hop = pt.meta["propagation_path"][0]
    assert hop["relation"] == "SUBSIDIARY_OF"
    assert hop["provenance"]["parent_uei"] == PARENT_UEI
    assert pt.meta["exposure_join_class"] == "deterministic"


def test_relationship_and_exposure_temporal_validity():
    _, threats, _ = _direct_threat()
    seed = next(t for t in threats if t.mechanism == "PROGRAM_CANCELLATION_OR_DELAY")
    base = ground_subsidiary_edges(RECIP.read_bytes(), child_ref="co_dap_sub",
                                   available_at="2026-03-04", valid_from="2026-03-04")[0]
    # An edge whose validity begins AFTER the event is not traversed (relationship temporal termination).
    future = {**base, "valid_from": "2026-09-15"}
    result = propagate_threats([seed], [future], as_of=CATALYST_DATE)
    assert result["propagated_threats"] == []
    assert result["stats"]["relationship_temporal_terminations"] == 1
    # A genuinely LAPSED incumbency (exposure valid_to before the event) is EXPOSURE_ENDED, not a threat.
    lapsed_award = {
        "recipient_uei": CHILD_UEI, "program_key": PIID, "available_at": "2026-03-04",
        "period_start": "2026-03-04", "period_end": "2026-06-01", "amount_usd": 3950539.76,
        "evidence_id": f"usaspending:award:{PIID}",
    }
    exposures = incumbency_exposures("co_dap_sub", "DAP", CHILD_UEI, [lapsed_award], as_of=CATALYST_DATE)
    catalyst = to_contract_termination_catalyst(_termination_event())
    threats, rejections = assess_threats("co_dap_sub", "DAP", exposures, [catalyst], as_of=CATALYST_DATE)
    assert not threats
    assert "EXPOSURE_ENDED" in [r.reason_code for r in rejections]
