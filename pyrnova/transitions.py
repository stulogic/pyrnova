"""Opportunity evolution / state-transition history (M5).

Records how an opportunity's disposition changed over time and *what evidence caused each change*.
Transitions are derived by replaying the existing scoring policy at each successive point-in-time
cutoff — they are an observability layer over scoring_v1, not a new scoring model, and they never
fabricate a promotion state that the available evidence does not support.

This lets Pyrnova answer, deterministically:

    "First observed 417 days before award. Promoted to WATCH after authorization.
     Promoted to STRIKE after market engagement."
"""

from __future__ import annotations

from .models import OpportunityTransition, to_record
from .replay import ACTIVE_SCORING_VERSION, _dt, run_replay, visible_records


def derive_transitions(
    case: dict,
    *,
    scoring_version: str = ACTIVE_SCORING_VERSION,
    subject_id: str | None = None,
) -> list[OpportunityTransition]:
    """Replay the case disposition at each cutoff where new evidence becomes visible.

    Each distinct ``available_at`` among the applicable records is a cutoff. At every cutoff we run the
    real scoring path over exactly the evidence knowable then; a disposition change is recorded as a
    transition attributed to the record(s) that first became visible at that cutoff.
    """
    subject_id = subject_id or case["case_id"]
    records = case["records"]
    cutoffs = sorted({r["available_at"] for r in records if r.get("available_at")})
    final_cutoff = case["replay_as_of"]
    # Do not consider evidence from beyond the case's own point-in-time horizon.
    cutoffs = [c for c in cutoffs if _dt(c) <= _dt(final_cutoff)]

    transitions: list[OpportunityTransition] = []
    prior_disposition: str | None = None
    prior_visible_refs: set[str] = set()
    for cutoff in cutoffs:
        result = run_replay({**case, "replay_as_of": cutoff}, scoring_version=scoring_version)
        disposition = result["system_disposition"]
        visible = visible_records(records, cutoff)
        new_records = [r for r in visible if r["source_ref"] not in prior_visible_refs]
        prior_visible_refs = {r["source_ref"] for r in visible}
        if disposition == prior_disposition:
            continue
        cause = max(new_records, key=lambda r: (r["available_at"], r["source_ref"]), default=None)
        transition = OpportunityTransition(
            subject_id=subject_id,
            prior_disposition=prior_disposition,
            new_disposition=disposition,
            cause_stage=(cause or {}).get("stage"),
            cause_source_id=(cause or {}).get("source_id"),
            cause_source_ref=(cause or {}).get("source_ref"),
            occurred_at=cutoff,
            scoring_version=scoring_version,
            basis=_basis(prior_disposition, disposition, cause),
            meta={"visible_evidence_count": len(visible), "score": result["score"]},
        )
        transitions.append(transition)
        prior_disposition = disposition
    return transitions


def _basis(prior: str | None, new: str, cause: dict | None) -> str:
    stage = (cause or {}).get("stage")
    kind = (cause or {}).get("record_kind")
    trigger = " and ".join(part for part in (stage, kind) if part) or "new evidence"
    verb = "First disposition" if prior is None else f"Changed from {prior}"
    return f"{verb} to {new} after {trigger}"


def transition_summary(transitions: list[OpportunityTransition]) -> dict:
    """Compact, human-readable trajectory for reports and metrics."""
    return {
        "transition_count": len(transitions),
        "trajectory": [t.new_disposition for t in transitions],
        "promotion_causes": [
            {"to": t.new_disposition, "stage": t.cause_stage, "source_id": t.cause_source_id,
             "at": t.occurred_at, "basis": t.basis}
            for t in transitions
        ],
        "reached_strike": any(t.new_disposition == "STRIKE" for t in transitions),
    }


def persist_transitions(store, transitions: list[OpportunityTransition]) -> None:
    for transition in transitions:
        store.append("opportunity_transitions", to_record(transition))
