"""B2.8 — Material Change consequence layer."""

from pyrnova.material_change_consequence import (
    POSITIVE, NEGATIVE, MIXED, UNCLEAR, assess_material_change_consequence,
)
from pyrnova.pursuit import PursuitVerdict, PURSUE, WATCH


def test_cancellation_is_negative_and_material():
    c = assess_material_change_consequence({
        "id": "mc1", "kind": "cancellation", "program_key": "disa:cloud", "customer_id": "mtsi",
        "prior": "open", "current": "cancelled", "evidence_ids": ["sam:cancel-1"],
        "observed_at": "2025-08-20"})
    assert c.is_material and c.effect_on_pursuit == NEGATIVE
    assert c.knowable_at == "2025-08-20" and c.source_evidence == ["sam:cancel-1"]
    assert "reversal watch" in c.recommended_response


def test_reissue_is_positive():
    c = assess_material_change_consequence({"kind": "reissue", "id": "mc2"})
    assert c.effect_on_pursuit == POSITIVE and c.is_material


def test_requirements_change_is_mixed_and_prompts_reassessment():
    c = assess_material_change_consequence({"kind": "requirements_change", "id": "mc3"})
    assert c.effect_on_pursuit == MIXED
    assert "re-run fit" in c.recommended_response


def test_below_threshold_change_is_not_material():
    c = assess_material_change_consequence({"kind": "document_metadata_update", "id": "mc4",
                                            "materiality": "LOW"})
    assert c.is_material is False and c.effect_on_pursuit == UNCLEAR
    assert c.recommended_response == "no action; below threshold"


def test_low_kind_with_high_materiality_clears_threshold():
    c = assess_material_change_consequence({"kind": "narrative_update", "id": "mc5", "materiality": "HIGH"})
    assert c.is_material is True


def test_verdict_change_is_reported():
    prior = PursuitVerdict(disposition=PURSUE, confidence="MEDIUM")
    now = PursuitVerdict(disposition=WATCH, confidence="LOW")
    c = assess_material_change_consequence({"kind": "cancellation", "id": "mc6"},
                                           prior_verdict=prior, current_verdict=now)
    assert c.verdict_changed is True
    assert c.prior_disposition == PURSUE and c.new_disposition == WATCH
    assert "PURSUE -> WATCH" in c.assessment_delta


def test_no_verdicts_leaves_verdict_changed_none():
    c = assess_material_change_consequence({"kind": "vehicle_change", "id": "mc7"})
    assert c.verdict_changed is None and c.effect_on_pursuit == MIXED
