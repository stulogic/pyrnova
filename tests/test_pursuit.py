"""B2.7 — Pursuit Verdict: canonical, evidence-backed, with reversal conditions."""

from pyrnova.fit_reasoning import Reason, FitReasoning, FOR, AGAINST, UNKNOWN_VERDICT
from pyrnova.pursuit import PURSUE, WATCH, INVESTIGATE, PASS, decide_pursuit
from pyrnova.vehicle_access import assess_vehicle_access


def _reasoning(*, fors=(), againsts=(), unknowns=(), posture="SUPPORT", fit=True):
    return FitReasoning(
        posture=posture, fit=fit, fit_confidence=0.6,
        reasons_for=[Reason("CAPABILITY_FIT", FOR, s, evidence_ids=("e1",), confidence=0.8) for s in fors],
        reasons_against=list(againsts),
        unknowns=[Reason("GEOGRAPHY", UNKNOWN_VERDICT, s) for s in unknowns],
    )


def test_pursue_when_fit_access_and_timing_all_support():
    fr = _reasoning(fors=["radar evidenced", "agency familiarity"])
    access = assess_vehicle_access(acquisition_path="Full and Open")
    v = decide_pursuit(fit_reasoning=fr, access=access, timing={"actionable": True})
    assert v.disposition == PURSUE and v.confidence in ("MEDIUM", "HIGH")
    assert v.decisive_evidence == ["e1"]
    assert any("cancelled" in rc for rc in v.reversal_conditions)
    assert v.next_actions


def test_fatal_blocker_is_pass():
    fr = _reasoning(fors=[], posture="NO_FIT", fit=False,
                    againsts=[Reason("blocker", AGAINST, "no_required_capability", confidence=0.9, decisive=True)])
    v = decide_pursuit(fit_reasoning=fr)
    assert v.disposition == PASS
    assert any("resolved by new evidence" in rc for rc in v.reversal_conditions)


def test_no_access_with_fit_triggers_investigate():
    fr = _reasoning(fors=["strong capability"])
    access = assess_vehicle_access(current_vehicle="Agency IDIQ")  # NO_KNOWN_ACCESS
    v = decide_pursuit(fit_reasoning=fr, access=access)
    assert v.disposition == INVESTIGATE
    assert any("teaming path" in rc or "vehicle" in rc.lower() for rc in v.reversal_conditions)
    assert any("access path" in a for a in v.next_actions)


def test_fit_but_not_actionable_yet_is_watch():
    fr = _reasoning(fors=["capability evidenced"])
    access = assess_vehicle_access(acquisition_path="Full and Open")
    v = decide_pursuit(fit_reasoning=fr, access=access, timing={"actionable": False, "reason": "forecast only"})
    assert v.disposition == WATCH
    assert any("response window" in rc for rc in v.reversal_conditions)


def test_detection_disposition_is_kept_distinct():
    fr = _reasoning(fors=[], unknowns=["no place of performance"])
    v = decide_pursuit(fit_reasoning=fr, detection_disposition="STRIKE")
    # A STRIKE detection does not force PURSUE; missing evidence -> INVESTIGATE.
    assert v.disposition == INVESTIGATE
    assert v.detection_disposition == "STRIKE"


def test_heavy_unknown_investigates_and_lists_evidence_gaps():
    fr = _reasoning(fors=[], unknowns=["capability unproven", "no scale data"])
    v = decide_pursuit(fit_reasoning=fr)
    assert v.disposition == INVESTIGATE
    assert len(v.unknowns) == 2
    assert any("gather evidence" in a for a in v.next_actions)
