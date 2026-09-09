"""M11 — production opportunity lifecycle + append-only outcome learning.

Authoritative, point-in-time outcomes for opportunities/predictions. This module is **additive** and
never changes ``scoring_v1``: it observes what actually happened, pairs it with the preserved prediction,
and produces calibration evidence. Challenger scorers may be *evaluated* against this ledger but never
promoted here — ``scoring_v1`` stays production.

Hard rules (enforced in code, not just documented):

1. **Never infer loss from absence.** A missing observation resolves to ``UNKNOWN``, never ``LOST`` /
   ``AWARD_TO_OTHER``. A negative outcome must be recorded from an explicit, dated, sourced observation.
2. **Strict future-outcome exclusion.** ``resolve_outcome(..., as_of)`` drops every observation whose
   ``observed_at`` is after the cutoff, exactly like point-in-time evidence. No future knowledge leaks
   into a historical reconstruction.
3. **Predictions are preserved, never mutated.** The learning ledger references a prediction snapshot;
   it does not edit it. Outcomes are an append-only stream keyed to the opportunity/prediction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional

# ------------------------------------------------------------------ outcome vocabulary

# Authoritative point-in-time outcome labels. UNKNOWN is the honest default; it is NEVER a silent loss.
OUTCOME_LABELS = (
    "WON",
    "LOST",
    "PARTICIPATED",
    "NO_BID",
    "AWARD_TO_OTHER",
    "CANCELLED",
    "EXPIRED",
    "DELAYED",
    "PARTIAL_CAPTURE",
    "SUBCONTRACT_CAPTURE",
    "INCUMBENT_RETENTION",
    "UNKNOWN",
)

# Outcomes that assert a *capture* for us (used for capture-rate observability only, not scoring).
CAPTURE_POSITIVE = frozenset(
    {"WON", "PARTIAL_CAPTURE", "SUBCONTRACT_CAPTURE", "INCUMBENT_RETENTION"}
)
# Outcomes that assert a competitive *non-capture* for us. These must come from an explicit observation.
CAPTURE_NEGATIVE = frozenset({"LOST", "AWARD_TO_OTHER"})
# Terminal outcomes where the opportunity ended without a resolved capture contest.
TERMINAL_NULL = frozenset({"CANCELLED", "EXPIRED"})
# Still-open / not-yet-resolved states.
OPEN_STATES = frozenset({"PARTICIPATED", "NO_BID", "DELAYED", "UNKNOWN"})

# Labels that may never be produced by inference — only by a sourced, dated observation.
REQUIRES_EXPLICIT_SOURCE = CAPTURE_POSITIVE | CAPTURE_NEGATIVE | TERMINAL_NULL

# Higher wins when two authoritative observations exist as-of the same cutoff. Later observed_at breaks
# ties; this ranking only decides which *resolved* label to surface, never edits the append-only log.
_AUTHORITY_RANK = {
    "WON": 6,
    "PARTIAL_CAPTURE": 6,
    "SUBCONTRACT_CAPTURE": 6,
    "INCUMBENT_RETENTION": 6,
    "LOST": 6,
    "AWARD_TO_OTHER": 6,
    "CANCELLED": 5,
    "EXPIRED": 5,
    "PARTICIPATED": 3,
    "NO_BID": 3,
    "DELAYED": 2,
    "UNKNOWN": 0,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _stable_id(payload: dict, length: int = 24) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()[:length]


# ------------------------------------------------------------------ observation model

@dataclass(frozen=True)
class OutcomeObservation:
    """One authoritative, dated, sourced observation of what happened to an opportunity.

    ``observed_at`` is the point-in-time gate (when the outcome first became knowable). Negative and
    terminal outcomes require an explicit ``source_ref`` — they can never be inferred from absence.
    """

    opportunity_id: str
    label: str
    observed_at: str
    source_id: str
    source_ref: str
    evidence_strength: int = 3
    confidence: float = 0.9
    awarded_to: Optional[str] = None
    value_usd: Optional[float] = None
    prediction_id: Optional[str] = None
    provenance: str = ""
    notes: str = ""
    recorded_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if self.label not in OUTCOME_LABELS:
            raise ValueError(f"unknown outcome label: {self.label!r}")
        if self.label == "UNKNOWN":
            raise ValueError("UNKNOWN is a resolved default, not an observable outcome; do not record it")
        if not str(self.opportunity_id).strip():
            raise ValueError("opportunity_id is required")
        if not str(self.observed_at).strip():
            raise ValueError(f"{self.label} requires observed_at (the point-in-time gate)")
        _parse_dt(self.observed_at)  # validates format/timezone
        if not str(self.source_id).strip() or not str(self.source_ref).strip():
            raise ValueError(f"{self.label} requires source_id and source_ref (never inferred)")
        if self.label in REQUIRES_EXPLICIT_SOURCE and int(self.evidence_strength) < 3:
            raise ValueError(
                f"{self.label} is authoritative and needs evidence_strength >= 3, "
                f"got {self.evidence_strength}"
            )
        if not 1 <= int(self.evidence_strength) <= 5:
            raise ValueError("evidence_strength must be 1..5")

    @property
    def id(self) -> str:
        return "outc_" + _stable_id(
            {"o": self.opportunity_id, "l": self.label, "at": self.observed_at, "ref": self.source_ref}
        )


def observation_from_dict(data: dict) -> OutcomeObservation:
    fields = {
        k: data[k]
        for k in (
            "opportunity_id", "label", "observed_at", "source_id", "source_ref",
            "evidence_strength", "confidence", "awarded_to", "value_usd",
            "prediction_id", "provenance", "notes",
        )
        if k in data
    }
    return OutcomeObservation(**fields)


def record_observation(store, observation: OutcomeObservation) -> str:
    """Append an outcome observation to the append-only ``outcome_observations`` stream (idempotent)."""
    row = to_record(observation)
    existing = {r.get("id") for r in store.read("outcome_observations")}
    if row["id"] not in existing:
        store.append("outcome_observations", row)
    return row["id"]


# ------------------------------------------------------------------ point-in-time resolution

def resolve_outcome(
    observations: Iterable[dict | OutcomeObservation],
    *,
    as_of: str,
) -> dict:
    """Resolve the authoritative outcome for one opportunity **as of a cutoff**.

    Future-dated observations (``observed_at`` > ``as_of``) are excluded. If no authoritative
    observation is knowable at the cutoff, the outcome is ``UNKNOWN`` — never an inferred loss.
    """
    cutoff = _parse_dt(as_of)
    rows = [asdict(o) if isinstance(o, OutcomeObservation) else dict(o) for o in observations]
    known, excluded_future = [], []
    for r in rows:
        if not r.get("observed_at"):
            continue
        if _parse_dt(r["observed_at"]) <= cutoff:
            known.append(r)
        else:
            excluded_future.append(r)

    if not known:
        return {
            "label": "UNKNOWN",
            "resolved": False,
            "as_of": as_of,
            "basis": None,
            "observation_count": 0,
            "future_excluded_count": len(excluded_future),
            "future_excluded_refs": sorted(r.get("source_ref") for r in excluded_future),
            "loss_inferred_from_absence": False,  # invariant: absence never becomes a loss
        }

    known.sort(
        key=lambda r: (
            _AUTHORITY_RANK.get(r.get("label"), 0),
            _parse_dt(r["observed_at"]),
            int(r.get("evidence_strength", 0)),
        )
    )
    winner = known[-1]
    return {
        "label": winner["label"],
        "resolved": True,
        "as_of": as_of,
        "basis": {
            "id": winner.get("id"),
            "source_id": winner.get("source_id"),
            "source_ref": winner.get("source_ref"),
            "observed_at": winner.get("observed_at"),
            "evidence_strength": winner.get("evidence_strength"),
            "awarded_to": winner.get("awarded_to"),
            "value_usd": winner.get("value_usd"),
        },
        "observation_count": len(known),
        "future_excluded_count": len(excluded_future),
        "future_excluded_refs": sorted(r.get("source_ref") for r in excluded_future),
        "loss_inferred_from_absence": False,
    }


# ------------------------------------------------------------------ learning ledger

def build_learning_record(
    prediction: dict,
    observations: Iterable[dict | OutcomeObservation],
    *,
    as_of: str,
) -> dict:
    """Pair a **preserved** prediction snapshot with the point-in-time resolved outcome.

    The prediction dict is copied verbatim into ``prediction`` and never mutated. Correctness is a
    calibration read only; it does not feed back into scoring.
    """
    resolved = resolve_outcome(observations, as_of=as_of)
    label = resolved["label"]
    predicted_positive = bool(prediction.get("predicted_capture", True))

    if label == "UNKNOWN":
        correctness = "PENDING"
    elif label in CAPTURE_POSITIVE:
        correctness = "CONFIRMED" if predicted_positive else "MISSED_POSITIVE"
    elif label in CAPTURE_NEGATIVE:
        correctness = "OVERCALLED" if predicted_positive else "CORRECT_NEGATIVE"
    else:  # terminal-null / still-open participation states
        correctness = "INDETERMINATE"

    return {
        "id": "learn_" + _stable_id(
            {"p": prediction.get("id"), "o": prediction.get("opportunity_id"), "as_of": as_of}
        ),
        "opportunity_id": prediction.get("opportunity_id"),
        "prediction_id": prediction.get("id"),
        "prediction": dict(prediction),  # preserved verbatim, never mutated
        "resolved_outcome": resolved,
        "outcome_label": label,
        "correctness": correctness,
        "as_of": as_of,
        "scoring_version": "scoring_v1",  # production scorer is unchanged by outcome learning
    }


def summarize_learning(records: list[dict]) -> dict:
    """Calibration observability over the outcome ledger (no scoring impact)."""
    total = len(records)
    labels = {lbl: sum(1 for r in records if r["outcome_label"] == lbl) for lbl in OUTCOME_LABELS}
    resolved = [r for r in records if r["outcome_label"] != "UNKNOWN"]
    capture = [r for r in records if r["outcome_label"] in CAPTURE_POSITIVE]
    contested = [r for r in records if r["outcome_label"] in (CAPTURE_POSITIVE | CAPTURE_NEGATIVE)]

    def rate(n, d):
        return round(n / d, 4) if d else None

    return {
        "ledger_size": total,
        "outcome_distribution": {k: v for k, v in labels.items() if v},
        "resolved_count": len(resolved),
        "unknown_count": total - len(resolved),
        "resolution_rate": rate(len(resolved), total),
        "capture_count": len(capture),
        "win_rate_among_contested": rate(len(capture), len(contested)),
        "confirmed": sum(1 for r in records if r["correctness"] == "CONFIRMED"),
        "overcalled": sum(1 for r in records if r["correctness"] == "OVERCALLED"),
        "correct_negative": sum(1 for r in records if r["correctness"] == "CORRECT_NEGATIVE"),
        "pending": sum(1 for r in records if r["correctness"] == "PENDING"),
        # Invariant surfaced explicitly: no resolved LOST/AWARD_TO_OTHER came from absence.
        "loss_inferred_from_absence": sum(
            1 for r in records if r["resolved_outcome"].get("loss_inferred_from_absence")
        ),
        "future_outcomes_excluded": sum(
            r["resolved_outcome"].get("future_excluded_count", 0) for r in records
        ),
        "small_sample_warning": (
            "outcome learning rests on very few resolved outcomes; treat as directional"
            if len(resolved) < 20 else None
        ),
    }


# ------------------------------------------------------------------ challenger evaluation (eval-only)

def evaluate_challenger(records: list[dict], *, challenger: str, predicted_positive) -> dict:
    """Score a **challenger** predictor against the resolved outcome ledger — evaluation only.

    ``predicted_positive`` is a callable ``prediction_dict -> bool``. This computes the challenger's
    precision/recall against authoritative outcomes but NEVER changes production: ``scoring_v1`` stays
    the active scorer. The result carries ``promoted=False`` and ``production_scoring_version`` so the
    separation is unmissable.
    """
    contested = [r for r in records if r["outcome_label"] in (CAPTURE_POSITIVE | CAPTURE_NEGATIVE)]
    tp = fp = fn = tn = 0
    for r in contested:
        actual_pos = r["outcome_label"] in CAPTURE_POSITIVE
        pred_pos = bool(predicted_positive(r["prediction"]))
        if pred_pos and actual_pos:
            tp += 1
        elif pred_pos and not actual_pos:
            fp += 1
        elif not pred_pos and actual_pos:
            fn += 1
        else:
            tn += 1

    def rate(n, d):
        return round(n / d, 4) if d else None

    return {
        "challenger": challenger,
        "promoted": False,  # evaluation-only, hard invariant
        "production_scoring_version": "scoring_v1",
        "contested_cases": len(contested),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": rate(tp, tp + fp),
        "recall": rate(tp, tp + fn),
        "small_sample_warning": (
            "challenger evaluation rests on very few contested outcomes; directional only"
            if len(contested) < 20 else None
        ),
    }


def to_record(obj) -> dict:
    if isinstance(obj, OutcomeObservation):
        d = asdict(obj)
        d["id"] = obj.id
        return d
    return dict(obj)


# ------------------------------------------------------------------ outcome corpus

def load_outcome_corpus(path) -> dict:
    """Load an outcome-learning corpus. Validates each observation via ``OutcomeObservation`` and every
    prediction snapshot carries an id + opportunity_id. Returns the parsed payload (``outcome_cases`` +
    the ``extends`` pointer so the M10 lifecycle base stays explicit and frozen)."""
    from pathlib import Path

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    seen = set()
    for case in payload.get("outcome_cases", []):
        for key in ("case_id", "opportunity_id", "replay_as_of", "prediction", "expected"):
            if key not in case:
                raise ValueError(f"{case.get('case_id', '<unknown>')}: outcome case missing {key}")
        if case["case_id"] in seen:
            raise ValueError(f"duplicate outcome case_id: {case['case_id']}")
        seen.add(case["case_id"])
        _parse_dt(case["replay_as_of"])
        pred = case["prediction"]
        if not pred.get("id") or not pred.get("opportunity_id"):
            raise ValueError(f"{case['case_id']}: prediction snapshot needs id + opportunity_id")
        for obs in case.get("observations", []):
            observation_from_dict(obs)  # raises on any invalid/inferred negative outcome
    return payload


def run_outcome_case(case: dict) -> dict:
    """Resolve one outcome case point-in-time and build its preserved-prediction learning record."""
    as_of = case["replay_as_of"]
    observations = case.get("observations", [])
    record = build_learning_record(case["prediction"], observations, as_of=as_of)
    record["case_id"] = case["case_id"]
    expected = case["expected"]
    checks = [{
        "check": f"label:{case['case_id']}",
        "ok": record["outcome_label"] == expected["label"],
        "got": record["outcome_label"], "want": expected["label"],
    }]
    if "correctness" in expected:
        checks.append({
            "check": f"correctness:{case['case_id']}",
            "ok": record["correctness"] == expected["correctness"],
            "got": record["correctness"], "want": expected["correctness"],
        })
    record["checks"] = checks
    record["ok"] = all(c["ok"] for c in checks)
    return record


def run_outcome_corpus(payload: dict) -> list[dict]:
    return [run_outcome_case(c) for c in payload.get("outcome_cases", [])]
