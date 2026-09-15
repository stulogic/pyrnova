"""B2.6 — Customer Fit / Past-Performance reasoning.

The M8 fit engine (:func:`pyrnova.fit.evaluate_fit`) already produces an authoritative, evidence-backed
FitResult with POSITIVE / NEGATIVE / UNKNOWN dimensions, a posture, and blockers. B2.6 does NOT re-score
it. It composes an explainable, customer-facing reasoning layer on top that answers, for each meaningful
dimension, WHY: reasons FOR fit, reasons AGAINST fit, and honest UNKNOWNs — every clause linked to the
evidence and provenance behind it.

It folds in the newer intelligence so the reasoning is decision-grade rather than capability-only:
agency familiarity from the Customer Intelligence Profile (B2.2) and the procurement Access verdict
(B2.5), because a strong capability fit with no access is not a strong pursuit. The existing calibrated
scores remain the source of truth; this layer only explains them with evidence. No arbitrary new
composite score is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .customer_intelligence import CustomerIntelligenceProfile, PUBLIC_EVIDENCE, PYRNOVA_DERIVED
from .vehicle_access import AccessAssessment, DIRECT_ACCESS, TEAMING_REQUIRED, NO_KNOWN_ACCESS, UNKNOWN

FIT_REASONING_VERSION = "fit_reasoning_v1"

FOR = "FOR"
AGAINST = "AGAINST"
UNKNOWN_VERDICT = "UNKNOWN"


@dataclass(frozen=True)
class Reason:
    dimension: str
    verdict: str        # FOR | AGAINST | UNKNOWN
    statement: str
    evidence_ids: tuple[str, ...] = ()
    provenance_class: str = PUBLIC_EVIDENCE
    confidence: float = 0.0
    decisive: bool = False

    def to_record(self) -> dict:
        return {
            "dimension": self.dimension, "verdict": self.verdict, "statement": self.statement,
            "evidence_ids": list(self.evidence_ids), "provenance_class": self.provenance_class,
            "confidence": self.confidence, "decisive": self.decisive,
        }


@dataclass
class FitReasoning:
    posture: str
    fit: bool
    fit_confidence: float
    reasons_for: list[Reason] = field(default_factory=list)
    reasons_against: list[Reason] = field(default_factory=list)
    unknowns: list[Reason] = field(default_factory=list)
    decisive_factor: Optional[str] = None
    explanation: str = ""
    version: str = FIT_REASONING_VERSION

    def to_record(self) -> dict:
        return {
            "fit_reasoning_version": self.version, "posture": self.posture, "fit": self.fit,
            "fit_confidence": self.fit_confidence, "decisive_factor": self.decisive_factor,
            "explanation": self.explanation,
            "reasons_for": [r.to_record() for r in self.reasons_for],
            "reasons_against": [r.to_record() for r in self.reasons_against],
            "unknowns": [r.to_record() for r in self.unknowns],
        }


# Human-readable dimension labels (kept small; missing names fall back to the raw name).
_DIM_LABEL = {
    "CAPABILITY_FIT": "capability", "BUYER_RELEVANCE": "agency/buyer familiarity",
    "GEOGRAPHY": "geography", "CERTIFICATION": "certification", "SECURITY": "security clearance",
    "SCALE": "contract scale", "TIMING": "timing", "INCUMBENT": "incumbency", "TEAMING": "teaming",
}


def _label(name: str) -> str:
    return _DIM_LABEL.get(name, str(name).replace("_", " ").lower())


def build_fit_reasoning(
    fit_result: Any,
    *,
    customer_intelligence: Optional[CustomerIntelligenceProfile] = None,
    access: Optional[AccessAssessment] = None,
) -> FitReasoning:
    """Explain a FitResult as evidence-linked reasons FOR / AGAINST / UNKNOWN, folding in access + agency familiarity."""
    reasons_for: list[Reason] = []
    reasons_against: list[Reason] = []
    unknowns: list[Reason] = []

    for dim in getattr(fit_result, "dimensions", []) or []:
        name = dim.get("name", "")
        verdict = dim.get("verdict")
        ev = tuple(dim.get("evidence_ids") or ())
        stmt = f"{_label(name)}: {dim.get('basis') or verdict.lower()}"
        reason = Reason(dimension=name, verdict=FOR if verdict == "POSITIVE" else AGAINST if verdict == "NEGATIVE" else UNKNOWN_VERDICT,
                        statement=stmt, evidence_ids=ev, confidence=dim.get("confidence", 0.0))
        if verdict == "POSITIVE":
            reasons_for.append(reason)
        elif verdict == "NEGATIVE":
            reasons_against.append(reason)
        else:
            unknowns.append(reason)

    # Blockers are decisive reasons against (fatal ones especially).
    decisive_factor = None
    for blk in getattr(fit_result, "blockers", []) or []:
        fatal = bool(blk.get("fatal"))
        r = Reason(dimension="blocker", verdict=AGAINST,
                   statement=f"blocker: {blk.get('code')} — {blk.get('detail') or ''}".strip(" —"),
                   confidence=0.9 if fatal else 0.6, decisive=fatal)
        reasons_against.append(r)
        if fatal and decisive_factor is None:
            decisive_factor = blk.get("code")

    # --- Agency familiarity from the Customer Intelligence Profile (evidence-linked) ------------
    if customer_intelligence is not None:
        for f in customer_intelligence.agencies_served():
            reasons_for.append(Reason("agency_familiarity", FOR,
                                      f"prior work establishes familiarity with {f.value}",
                                      evidence_ids=f.evidence_ids, provenance_class=PYRNOVA_DERIVED,
                                      confidence=f.confidence))
        for f in customer_intelligence.unsupported_claims():
            unknowns.append(Reason("capability_claim", UNKNOWN_VERDICT,
                                   f"capability '{f.key}' is claimed by the customer but not evidenced publicly",
                                   provenance_class=PYRNOVA_DERIVED, confidence=f.confidence))

    # --- Access verdict folded in (a strong fit with no access is not a strong pursuit) ---------
    if access is not None:
        if access.verdict == DIRECT_ACCESS:
            reasons_for.append(Reason("access", FOR, access.summary, provenance_class=PYRNOVA_DERIVED, confidence=0.7))
        elif access.verdict in (TEAMING_REQUIRED, NO_KNOWN_ACCESS):
            r = Reason("access", AGAINST, access.summary, provenance_class=PYRNOVA_DERIVED,
                       confidence=0.7, decisive=access.verdict == NO_KNOWN_ACCESS)
            reasons_against.append(r)
            if access.verdict == NO_KNOWN_ACCESS and decisive_factor is None:
                decisive_factor = "no_known_access"
        elif access.verdict == UNKNOWN:
            unknowns.append(Reason("access", UNKNOWN_VERDICT, access.summary, provenance_class=PYRNOVA_DERIVED))

    # --- Decisive factor + one-line explanation -------------------------------------------------
    posture = getattr(fit_result, "posture", "")
    if decisive_factor is None:
        strongest_for = max(reasons_for, key=lambda r: r.confidence, default=None)
        decisive_factor = strongest_for.dimension if strongest_for else (
            "insufficient_evidence" if unknowns else None)

    for_txt = "; ".join(r.statement for r in sorted(reasons_for, key=lambda r: -r.confidence)[:3]) or "no positive evidence"
    against_txt = "; ".join(r.statement for r in reasons_against[:3])
    explanation = f"Posture {posture}. FOR: {for_txt}."
    if against_txt:
        explanation += f" AGAINST: {against_txt}."
    if unknowns:
        explanation += f" {len(unknowns)} open unknown(s)."

    return FitReasoning(
        posture=posture, fit=bool(getattr(fit_result, "fit", False)),
        fit_confidence=float(getattr(fit_result, "fit_confidence", 0.0)),
        reasons_for=reasons_for, reasons_against=reasons_against, unknowns=unknowns,
        decisive_factor=decisive_factor, explanation=explanation,
    )
