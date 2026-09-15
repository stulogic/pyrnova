"""B2.8 — Material Change consequence layer.

The existing material-change capability (:mod:`pyrnova.material_changes` /
:mod:`pyrnova.customer_material_changes`) already detects that something changed, versions it (Known Then
/ Known Now), and keeps point-in-time / AS-OF truth. B2.8 does NOT rebuild that. It completes the
CONSEQUENCE layer: given a detected material change (and the pursuit verdict before/after), it answers
what a customer actually needs — what changed, prior vs current state, the source evidence, when it became
knowable, which opportunity/customer it affects, its EFFECT ON PURSUIT (POSITIVE / NEGATIVE / MIXED /
UNCLEAR), why it matters, what changed in Pyrnova's assessment, whether the Pursuit Verdict changed, the
recommended response, and what Pyrnova will watch next.

A consequence threshold is enforced so not every document edit becomes a material change: a change is
consequential only if it is one of the high-consequence kinds OR its assessed materiality clears a floor.
Known Then / Known Now and AS-OF behaviour are preserved by consuming the change exactly as it was
knowable — no future leakage is introduced here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

MATERIAL_CHANGE_CONSEQUENCE_VERSION = "material_change_consequence_v1"

POSITIVE, NEGATIVE, MIXED, UNCLEAR = "POSITIVE", "NEGATIVE", "MIXED", "UNCLEAR"

# Change kinds whose consequence is intrinsic (they clear the threshold regardless of an ordinal score).
_EFFECT: dict[str, tuple[str, str]] = {
    "cancellation": (NEGATIVE, "the procurement was cancelled; the current pursuit is not live"),
    "reissue": (POSITIVE, "the procurement was reissued; a live pursuit path reopens"),
    "funding_increase": (POSITIVE, "funding increased, strengthening the opportunity's basis"),
    "funding_cut": (NEGATIVE, "funding was cut, weakening the opportunity's basis"),
    "response_date_extended": (POSITIVE, "the response window was extended, giving more capture time"),
    "response_date_compressed": (NEGATIVE, "the response window was compressed, reducing capture time"),
    "set_aside_added_qualifying": (POSITIVE, "a set-aside the customer qualifies for was added"),
    "set_aside_added_disqualifying": (NEGATIVE, "a set-aside the customer does not qualify for was added"),
    "set_aside_removed": (MIXED, "a set-aside was removed, changing the competitive field"),
    "vehicle_change": (MIXED, "the acquisition vehicle changed; access must be re-checked"),
    "requirements_change": (MIXED, "requirements changed; capability fit must be re-checked"),
    "incumbent_extended": (NEGATIVE, "the incumbent's contract was extended, delaying the recompete"),
    "incumbent_expiring": (POSITIVE, "the incumbent's contract is expiring, opening a recompete window"),
}
_HIGH_CONSEQUENCE_KINDS = frozenset(_EFFECT)

_WATCH_NEXT = {
    "cancellation": "watch for a reissue or a follow-on procurement of the same requirement",
    "reissue": "watch the new solicitation's terms, response date and set-aside",
    "requirements_change": "watch for further amendments and re-confirm capability alignment",
    "vehicle_change": "watch the vehicle's eligible-holder list and any teaming implications",
    "response_date_extended": "watch the (new) response date and any further extensions",
    "response_date_compressed": "watch the (new) response date; confirm capacity to respond",
}

_MATERIALITY_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}
_MATERIALITY_FLOOR = 2  # MEDIUM


@dataclass
class MaterialChangeConsequence:
    change_id: str
    kind: str
    is_material: bool
    what_changed: str
    prior_state: Any = None
    current_state: Any = None
    source_evidence: list[str] = field(default_factory=list)
    knowable_at: Optional[str] = None
    customer_id: Optional[str] = None
    opportunity_ref: Optional[str] = None
    effect_on_pursuit: str = UNCLEAR
    why_it_matters: str = ""
    assessment_delta: str = ""
    verdict_changed: Optional[bool] = None
    prior_disposition: Optional[str] = None
    new_disposition: Optional[str] = None
    recommended_response: str = ""
    watch_next: str = ""
    materiality: str = "UNKNOWN"
    version: str = MATERIAL_CHANGE_CONSEQUENCE_VERSION

    def to_record(self) -> dict:
        return {
            "material_change_consequence_version": self.version, "change_id": self.change_id,
            "kind": self.kind, "is_material": self.is_material, "what_changed": self.what_changed,
            "prior_state": self.prior_state, "current_state": self.current_state,
            "source_evidence": self.source_evidence, "knowable_at": self.knowable_at,
            "customer_id": self.customer_id, "opportunity_ref": self.opportunity_ref,
            "effect_on_pursuit": self.effect_on_pursuit, "why_it_matters": self.why_it_matters,
            "assessment_delta": self.assessment_delta, "verdict_changed": self.verdict_changed,
            "prior_disposition": self.prior_disposition, "new_disposition": self.new_disposition,
            "recommended_response": self.recommended_response, "watch_next": self.watch_next,
            "materiality": self.materiality,
        }


def _recommended_response(effect: str, kind: str) -> str:
    if kind == "cancellation":
        return "downgrade the pursuit and retain it under a reversal watch for a reissue"
    if kind == "reissue":
        return "re-open the assessment; re-evaluate for PURSUE against the new terms"
    if effect == MIXED:
        return "re-run fit and access against the changed terms before acting"
    if effect == POSITIVE:
        return "use the change to strengthen the capture position; confirm the verdict still holds"
    if effect == NEGATIVE:
        return "reassess whether the opportunity remains worth pursuing"
    return "monitor; gather evidence before changing the disposition"


def assess_material_change_consequence(
    change: dict,
    *,
    prior_verdict: Any = None,
    current_verdict: Any = None,
) -> MaterialChangeConsequence:
    """Turn a detected material change into a decision-useful consequence.

    ``change`` carries at least ``kind``; optionally ``id``/``change_id``, ``prior``/``current``,
    ``evidence_ids``, ``observed_at``/``knowable_at``, ``customer_id``, ``program_key``/``opportunity_ref``,
    ``materiality``/``severity``, ``summary``. ``*_verdict`` are :class:`pyrnova.pursuit.PursuitVerdict`
    (or dicts) from before/after the change, used to report whether the pursuit disposition moved.
    """
    kind = str(change.get("kind") or "unknown")
    materiality = str(change.get("materiality") or change.get("severity") or "UNKNOWN").upper()
    rank = _MATERIALITY_RANK.get(materiality, 0)

    is_material = kind in _HIGH_CONSEQUENCE_KINDS or rank >= _MATERIALITY_FLOOR

    effect, why = _EFFECT.get(kind, (UNCLEAR, "effect on pursuit is not yet clear from the evidence"))
    if not is_material:
        effect = UNCLEAR
        why = "change is below the consequence threshold; not treated as a material change"

    def _disp(v):
        if v is None:
            return None
        return getattr(v, "disposition", None) if not isinstance(v, dict) else v.get("disposition")

    prior_disp, new_disp = _disp(prior_verdict), _disp(current_verdict)
    verdict_changed = None if prior_disp is None or new_disp is None else prior_disp != new_disp

    if verdict_changed is True:
        assessment_delta = f"pursuit disposition moved {prior_disp} -> {new_disp}"
    elif verdict_changed is False:
        assessment_delta = f"pursuit disposition unchanged ({new_disp}) despite the change"
    elif is_material:
        assessment_delta = f"assessment should be re-evaluated ({effect.lower()} effect)"
    else:
        assessment_delta = "no assessment change (below threshold)"

    return MaterialChangeConsequence(
        change_id=str(change.get("change_id") or change.get("id") or ""),
        kind=kind, is_material=is_material,
        what_changed=str(change.get("summary") or change.get("what_changed") or kind),
        prior_state=change.get("prior"), current_state=change.get("current"),
        source_evidence=list(change.get("evidence_ids") or []),
        knowable_at=change.get("knowable_at") or change.get("observed_at") or change.get("available_at"),
        customer_id=change.get("customer_id"),
        opportunity_ref=change.get("opportunity_ref") or change.get("program_key"),
        effect_on_pursuit=effect, why_it_matters=why, assessment_delta=assessment_delta,
        verdict_changed=verdict_changed, prior_disposition=prior_disp, new_disposition=new_disp,
        recommended_response=_recommended_response(effect, kind) if is_material else "no action; below threshold",
        watch_next=_WATCH_NEXT.get(kind, "monitor the opportunity for further amendments or a disposition-changing event"),
        materiality=materiality,
    )
