"""B2.7 — Pursuit Verdict.

One canonical, evidence-backed pursuit conclusion for a (customer, opportunity) pair. This is the
CUSTOMER's pursuit disposition and is conceptually distinct from Pyrnova's detection classification
(STRIKE / WATCH / REJECT): a strong detection can still be a PASS for a particular customer with no
capability or no access, and a modest detection can be a PURSUE for the customer who owns it.

Dispositions:
    PURSUE      — evidenced fit + a reachable access path + actionable timing.
    WATCH       — a real fit, but not yet actionable (timing early, or access unresolved).
    INVESTIGATE — the decision turns on missing evidence or an unresolved access path worth chasing.
    PASS        — a fatal fit blocker, or weak fit with no path.

Every verdict states why, why not, the decisive evidence, the customer / access / competitive / timing
factors, uncertainty and UNKNOWNs, the next 1–3 evidence-supported capture actions, and — most important —
REVERSAL CONDITIONS: the specific new facts that would change Pyrnova's mind. No fake precision: the
verdict carries a qualitative LOW/MEDIUM/HIGH confidence, not an invented composite score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from .fit_reasoning import AGAINST, FOR, FitReasoning
from .vehicle_access import AccessAssessment, DIRECT_ACCESS, NO_KNOWN_ACCESS, TEAMING_REQUIRED, UNKNOWN

PURSUIT_VERDICT_VERSION = "pursuit_verdict_v1"

PURSUE = "PURSUE"
WATCH = "WATCH"
INVESTIGATE = "INVESTIGATE"
PASS = "PASS"


@dataclass
class PursuitVerdict:
    disposition: str
    confidence: str                     # LOW | MEDIUM | HIGH (qualitative — no fake composite score)
    why: list[str] = field(default_factory=list)
    why_not: list[str] = field(default_factory=list)
    decisive_evidence: list[str] = field(default_factory=list)
    customer_factor: str = ""
    access_factor: str = ""
    competitive_factor: str = ""
    timing_factor: str = ""
    uncertainty: str = ""
    unknowns: list[str] = field(default_factory=list)
    reversal_conditions: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    detection_disposition: Optional[str] = None   # STRIKE/WATCH/REJECT — kept distinct, never overwritten
    version: str = PURSUIT_VERDICT_VERSION

    def to_record(self) -> dict:
        return {
            "pursuit_verdict_version": self.version, "disposition": self.disposition,
            "confidence": self.confidence, "why": self.why, "why_not": self.why_not,
            "decisive_evidence": self.decisive_evidence, "customer_factor": self.customer_factor,
            "access_factor": self.access_factor, "competitive_factor": self.competitive_factor,
            "timing_factor": self.timing_factor, "uncertainty": self.uncertainty,
            "unknowns": self.unknowns, "reversal_conditions": self.reversal_conditions,
            "next_actions": self.next_actions, "detection_disposition": self.detection_disposition,
        }


def _competitive_summary(competitive) -> tuple[str, list[str]]:
    """Return a one-line competitive factor and any reversal conditions it implies."""
    if competitive is None or getattr(competitive, "is_unknown", False):
        return "competitive picture UNKNOWN", []
    inc = getattr(competitive, "incumbent_name", None)
    vulns = competitive.by_dimension("incumbent_vulnerability")
    hyps = competitive.competitor_hypotheses()
    parts = []
    reversals = []
    if inc:
        parts.append(f"incumbent {inc}")
    if vulns:
        parts.append(f"{len(vulns)} incumbent vulnerability(ies)")
        reversals.append("if the incumbent's position strengthens (e.g. contract extended), downgrade")
    if hyps:
        parts.append(f"{len(hyps)} evidenced competitor hypothesis(es)")
        reversals.append("if a strong new competitor is confirmed, re-weight the competitive factor")
    return ("; ".join(parts) or "no competitive evidence"), reversals


def decide_pursuit(
    *,
    fit_reasoning: FitReasoning,
    access: Optional[AccessAssessment] = None,
    competitive: Any = None,
    detection_disposition: Optional[str] = None,
    timing: Optional[dict] = None,
    material_changes: Sequence[Any] = (),
    as_of: Optional[str] = None,
) -> PursuitVerdict:
    """Derive the canonical pursuit verdict by composing fit reasoning, access, competition and timing."""
    fr = fit_reasoning
    reasons_for = fr.reasons_for
    reasons_against = fr.reasons_against
    unknowns = list(fr.unknowns)

    fatal_block = any(r.decisive and r.dimension == "blocker" for r in reasons_against) or (
        fr.posture == "NO_FIT" and not unknowns)
    has_positive = bool(reasons_for)
    heavy_unknown = not has_positive and bool(unknowns)

    access_blocked = access is not None and access.verdict == NO_KNOWN_ACCESS
    access_unknown = access is not None and access.verdict == UNKNOWN
    access_ok = access is None or access.verdict in (DIRECT_ACCESS, TEAMING_REQUIRED)

    timing = timing or {}
    timing_actionable = bool(timing.get("actionable", True))

    # --- Disposition (deterministic precedence) -------------------------------------------------
    if fatal_block:
        disposition = PASS
    elif access_blocked:
        disposition = INVESTIGATE if has_positive else PASS
    elif heavy_unknown:
        disposition = INVESTIGATE
    elif has_positive and access_ok and timing_actionable and not access_unknown:
        disposition = PURSUE
    elif has_positive:
        disposition = WATCH
    else:
        disposition = PASS

    # --- Confidence (qualitative) ---------------------------------------------------------------
    strong_for = [r for r in reasons_for if r.confidence >= 0.7 and r.evidence_ids]
    if disposition in (PURSUE, PASS) and (strong_for or fatal_block):
        confidence = "HIGH" if (len(strong_for) >= 2 or fatal_block) else "MEDIUM"
    elif disposition == INVESTIGATE or access_unknown or unknowns:
        confidence = "LOW"
    else:
        confidence = "MEDIUM"

    # --- Factors --------------------------------------------------------------------------------
    customer_factor = (max(reasons_for, key=lambda r: r.confidence).statement
                       if reasons_for else "no evidenced customer fit")
    access_factor = access.summary if access is not None else "access not assessed"
    competitive_factor, comp_reversals = _competitive_summary(competitive)
    timing_factor = timing.get("reason") or ("actionable now" if timing_actionable else "not yet actionable")

    # --- Why / why-not / decisive evidence ------------------------------------------------------
    why = [r.statement for r in sorted(reasons_for, key=lambda r: -r.confidence)]
    why_not = [r.statement for r in reasons_against]
    if disposition == PASS and not why_not:
        why_not.append("no evidenced fit to support pursuit")
    decisive_evidence = sorted({e for r in reasons_for + reasons_against for e in r.evidence_ids})

    # --- Reversal conditions: what would change Pyrnova's mind ----------------------------------
    reversal_conditions: list[str] = []
    if disposition == PASS or disposition == INVESTIGATE:
        for r in reasons_against:
            if r.dimension == "blocker":
                reversal_conditions.append(f"if the blocker '{r.statement}' is resolved by new evidence, reconsider")
        for u in unknowns:
            reversal_conditions.append(f"if evidence resolves the unknown: {u.statement}")
    if access_blocked:
        req = getattr(access, "required_vehicle", None)
        reversal_conditions.append(
            f"if the customer gains access to {req or 'the operative vehicle'} or a teaming path emerges, revisit")
    if disposition == WATCH and not timing_actionable:
        reversal_conditions.append("if the solicitation posts / the response window opens, re-evaluate for PURSUE")
    if disposition == PURSUE:
        reversal_conditions.append("if the opportunity is cancelled or materially descoped, downgrade")
        if access is not None and access.verdict == TEAMING_REQUIRED:
            reversal_conditions.append(f"if no teammate holding {access.required_vehicle} is secured, downgrade to INVESTIGATE")
    reversal_conditions.extend(comp_reversals)
    for mc in material_changes:
        summ = getattr(mc, "summary", None) or (mc.get("summary") if isinstance(mc, dict) else None)
        if summ:
            reversal_conditions.append(f"if this material change reverses, revisit: {summ}")

    # --- Next actions (1–3, evidence-supported) -------------------------------------------------
    next_actions: list[str] = []
    if disposition == PURSUE:
        next_actions.append("engage the contracting/program POC and confirm requirement alignment")
        if access is not None and access.verdict == TEAMING_REQUIRED:
            next_actions.append(f"secure a teammate/prime holding {access.required_vehicle}")
        next_actions.append("prepare capability evidence mapped to the stated requirement")
    elif disposition == INVESTIGATE:
        if unknowns:
            next_actions.append(f"gather evidence to resolve: {unknowns[0].statement}")
        if access_blocked:
            next_actions.append("identify a vehicle/teaming access path")
        next_actions.append("re-run the verdict once the missing evidence is obtained")
    elif disposition == WATCH:
        next_actions.append("monitor for solicitation posting / amendment / cancellation")
        next_actions.append("watch the response date and any set-aside decision")
    else:  # PASS
        next_actions.append("no action; re-open only if a reversal condition is met")

    unknown_statements = [u.statement for u in unknowns]
    uncertainty = (f"{len(unknowns)} open unknown(s); "
                   f"access {access.verdict if access is not None else 'unassessed'}").strip()

    return PursuitVerdict(
        disposition=disposition, confidence=confidence, why=why, why_not=why_not,
        decisive_evidence=decisive_evidence, customer_factor=customer_factor, access_factor=access_factor,
        competitive_factor=competitive_factor, timing_factor=timing_factor, uncertainty=uncertainty,
        unknowns=unknown_statements, reversal_conditions=reversal_conditions[:6],
        next_actions=next_actions[:3], detection_disposition=detection_disposition,
    )
