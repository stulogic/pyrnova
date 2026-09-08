"""Capability fit and opportunity personalization (M8).

Given a validated `CommercialConsequence` and a specific company's evidence-backed capability profile,
determine whether that company has a *credible, evidence-supported path* to capture the opportunity —
and, if so, in what capture posture (PRIME / SUPPORT / TEAM / DEFEND), or NO_FIT.

Fit is grounded in explicit capability/evidence overlap, never in generic sector reasoning:

    NO agency-name-only fit. NO NAICS-only fit. NO keyword-overlap-only fit. NO semantic-similarity-only
    fit. Unknown stays unknown; a company with no capability evidence is not a PRIME.

Fit is kept strictly separate from `scoring_v1`: fit confidence measures a company's capture path, not
opportunity quality. A strong opportunity can be a poor fit; a strong fit can sit on a weak opportunity.
This module never changes scoring.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, date

from .models import to_record

FIT_ENGINE_VERSION = "capability_fit_v1"

POSTURES = {"PRIME", "SUPPORT", "TEAM", "DEFEND", "NO_FIT"}
VERDICTS = {"POSITIVE", "NEGATIVE", "UNKNOWN"}
FIT_DIMENSIONS = (
    "CAPABILITY_FIT", "BUYER_RELEVANCE", "GEOGRAPHY", "CERTIFICATION",
    "SECURITY", "SCALE", "TIMING", "INCUMBENT_POSITION", "TEAMING_POTENTIAL",
)

# Blocker codes; `fatal` blockers forbid any fit (NO_FIT). Soft blockers forbid PRIME but permit a
# lesser posture, or mark an unknown that cannot establish a credible path.
FATAL_BLOCKERS = {
    "no_required_capability", "insufficient_certification", "security_clearance_mismatch",
    "geographic_exclusion", "timing_passed", "historically_failed_capability",
    "explicit_source_contradiction",
}
SOFT_BLOCKERS = {
    "insufficient_capability_evidence", "scale_mismatch", "wrong_contract_vehicle",
    "unsupported_team_dependence",
}


def _later(*times: str | None) -> str | None:
    known = [t for t in times if t]
    return max(known) if known else None


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class FitDimension:
    name: str
    verdict: str          # POSITIVE | NEGATIVE | UNKNOWN — never forced to a neutral 0.5
    confidence: float
    evidence_ids: tuple = ()
    basis: str = ""


@dataclass(frozen=True)
class FitBlocker:
    code: str
    detail: str = ""
    fatal: bool = False


@dataclass
class FitResult:
    consequence_id: str
    company_id: str
    posture: str                       # PRIME | SUPPORT | TEAM | DEFEND | NO_FIT
    fit: bool
    fit_confidence: float              # confidence in the posture assessment — distinct from scoring
    capability_match: list = field(default_factory=list)   # matched capability labels
    dimensions: list = field(default_factory=list)         # list[FitDimension as dict]
    strongest_evidence: str | None = None
    weakest_dimension: str | None = None
    blockers: list = field(default_factory=list)           # list[FitBlocker as dict]
    assumptions: list = field(default_factory=list)
    rationale: str = ""
    is_unknown: bool = False
    evidence_ids: list = field(default_factory=list)
    first_supportable_at: str | None = None
    id: str = ""
    meta: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- helpers

def _labels(capability_classes) -> set[str]:
    out = set()
    for c in capability_classes or ():
        label = c.get("label") if isinstance(c, dict) else getattr(c, "label", None)
        if label:
            out.add(label)
    return out


def _participants(consequence, roles: set[str]) -> list[dict]:
    out = []
    for p in getattr(consequence, "participants", None) or ():
        role = p.get("role") if isinstance(p, dict) else getattr(p, "role", None)
        if role in roles:
            out.append(p if isinstance(p, dict) else to_record(p))
    return out


def _casefold_set(values) -> set[str]:
    return {str(v).strip().casefold() for v in (values or ()) if str(v).strip()}


# --------------------------------------------------------------------------- dimensions

def _capability_dimension(req_caps, profile):
    co_caps = {e.label for e in profile.capabilities}
    exclusions = _casefold_set(profile.exclusions)
    matched = req_caps & co_caps
    excluded = {c for c in req_caps if c.casefold() in exclusions}
    ev = tuple(e.source_ref for e in profile.capabilities if e.label in matched)
    if not req_caps:
        return FitDimension("CAPABILITY_FIT", "UNKNOWN", 0.0, (),
                            "consequence declares no specific capability requirement"), set(), set()
    if excluded and not (matched - excluded):
        return FitDimension("CAPABILITY_FIT", "NEGATIVE", 0.6, (),
                            f"required capability {sorted(excluded)} is on the company's exclusion list"), matched, excluded
    if matched:
        conf = max((e.confidence for e in profile.capabilities if e.label in matched), default=0.6)
        full = req_caps <= co_caps
        return FitDimension("CAPABILITY_FIT", "POSITIVE", round(conf, 3), ev,
                            f"{'full' if full else 'partial'} capability match: {sorted(matched)}"), matched, excluded
    if co_caps:
        return FitDimension("CAPABILITY_FIT", "NEGATIVE", 0.6, (),
                            f"required {sorted(req_caps)} not among the company's evidenced capabilities"), matched, excluded
    return FitDimension("CAPABILITY_FIT", "UNKNOWN", 0.0, (),
                        "no capability evidence exists for this company"), matched, excluded


def _buyer_dimension(consequence, profile):
    buyers = _casefold_set(p.get("name") for p in _participants(consequence, {"BUYER", "PROGRAM_OWNER"}))
    history = profile.contract_history or []
    if not history:
        return FitDimension("BUYER_RELEVANCE", "UNKNOWN", 0.0, (), "no contract history on file"), False, False
    matches, prime = [], False
    spend = str(getattr(consequence, "likely_spend_category", "") or "").casefold()
    for h in history:
        agency = str(h.get("agency") or "").casefold()
        code_hit = spend and (str(h.get("naics") or "").startswith(spend[:6]) or str(h.get("psc") or "").casefold() == spend)
        if (buyers and any(b in agency or agency in b for b in buyers if agency)) or code_hit:
            matches.append(h.get("award_ref") or h.get("agency"))
            prime = prime or h.get("role") == "prime"
    if matches:
        return FitDimension("BUYER_RELEVANCE", "POSITIVE", 0.8 if prime else 0.6, tuple(m for m in matches if m),
                            f"prior {'prime ' if prime else ''}work with the buying agency / matching code"), True, prime
    return FitDimension("BUYER_RELEVANCE", "UNKNOWN", 0.0, (), "no prior work with this buyer / code"), False, False


def _geography_dimension(consequence, profile, requirements):
    restriction = requirements.get("geography")
    co_geo = _casefold_set(profile.geography) | _casefold_set(
        f.get("location") for f in (profile.facilities or []))
    if restriction:
        req = _casefold_set(restriction if isinstance(restriction, (list, tuple)) else [restriction])
        if co_geo & req or any(any(r in g or g in r for g in co_geo) for r in req):
            return FitDimension("GEOGRAPHY", "POSITIVE", 0.7, (), f"company meets geographic restriction {sorted(req)}")
        return FitDimension("GEOGRAPHY", "NEGATIVE", 0.7, (), f"geographic restriction {sorted(req)} not met")
    geo = str(getattr(consequence, "geography", "") or "").casefold()
    if geo and co_geo and any(part in geo or geo in part for part in co_geo):
        return FitDimension("GEOGRAPHY", "POSITIVE", 0.5, (), "company operates in the opportunity's geography")
    return FitDimension("GEOGRAPHY", "UNKNOWN", 0.0, (), "no geographic restriction or match established")


def _certification_dimension(profile, requirements):
    required = _casefold_set(requirements.get("certifications"))
    if not required:
        return FitDimension("CERTIFICATION", "UNKNOWN", 0.0, (), "no certification requirement declared")
    held = _casefold_set(profile.certifications)
    missing = sorted(required - held)
    if missing:
        return FitDimension("CERTIFICATION", "NEGATIVE", 0.9, (), f"missing required certification(s): {missing}")
    return FitDimension("CERTIFICATION", "POSITIVE", 0.8, (), "all required certifications held")


def _security_dimension(profile, requirements):
    required = requirements.get("clearance")
    if not required:
        return FitDimension("SECURITY", "UNKNOWN", 0.0, (), "no clearance requirement declared")
    held = _casefold_set(profile.clearances)
    if str(required).casefold() not in held:
        return FitDimension("SECURITY", "NEGATIVE", 0.9, (), f"required clearance {required} not held")
    return FitDimension("SECURITY", "POSITIVE", 0.8, (), "required clearance held")


def _scale_dimension(consequence, profile):
    value = getattr(consequence, "value", {}) or {}
    amount = value.get("amount_usd") or value.get("high_usd")
    cap = (profile.scale or {}).get("max_contract_usd")
    if not amount or not cap:
        return FitDimension("SCALE", "UNKNOWN", 0.0, (), "opportunity or company scale unknown")
    if amount > cap * 3:
        return FitDimension("SCALE", "NEGATIVE", 0.6, (),
                            f"opportunity ~${amount:,.0f} materially exceeds company ceiling ${cap:,.0f}")
    return FitDimension("SCALE", "POSITIVE", 0.6, (), "opportunity within a plausible scale band")


def _timing_dimension(consequence, requirements, as_of):
    if requirements.get("timing_passed"):
        return FitDimension("TIMING", "NEGATIVE", 0.8, (), "capture window has already passed")
    return FitDimension("TIMING", "UNKNOWN", 0.0, (), "no timing block established")


def _incumbent_dimension(consequence, profile, requirements):
    program = requirements.get("incumbent_program_key") or getattr(consequence, "program_key", None)
    incumbent_refs = [h.get("award_ref") for h in (profile.contract_history or [])
                      if h.get("program_key") and h["program_key"] == program]
    if incumbent_refs or program in _casefold_set(profile.meta.get("incumbent_of")):
        return FitDimension("INCUMBENT_POSITION", "POSITIVE", 0.85, tuple(r for r in incumbent_refs if r),
                            "company is the incumbent on this program"), True
    return FitDimension("INCUMBENT_POSITION", "UNKNOWN", 0.0, (), "no incumbency evidence"), False


def _teaming_dimension(profile, matched_partial):
    if matched_partial and profile.partners:
        return FitDimension("TEAMING_POTENTIAL", "POSITIVE", 0.5, (),
                            "partial capability plus known teaming partners")
    return FitDimension("TEAMING_POTENTIAL", "UNKNOWN", 0.0, (), "no teaming evidence")


# --------------------------------------------------------------------------- engine

def evaluate_fit(consequence, profile, *, requirements: dict | None = None, as_of: str | None = None) -> FitResult:
    """Explainable, evidence-backed fit for one (consequence, company). Zero fit is valid."""
    requirements = requirements or {}
    req_caps = _labels(getattr(consequence, "capability_classes", None))

    cap_dim, matched, excluded = _capability_dimension(req_caps, profile)
    buyer_dim, buyer_pos, prime_history = _buyer_dimension(consequence, profile)
    geo_dim = _geography_dimension(consequence, profile, requirements)
    cert_dim = _certification_dimension(profile, requirements)
    sec_dim = _security_dimension(profile, requirements)
    scale_dim = _scale_dimension(consequence, profile)
    timing_dim = _timing_dimension(consequence, requirements, as_of)
    incumbent_dim, is_incumbent = _incumbent_dimension(consequence, profile, requirements)
    matched_all = bool(req_caps) and req_caps <= {e.label for e in profile.capabilities}
    matched_partial = bool(matched) and not matched_all
    team_dim = _teaming_dimension(profile, matched_partial)

    dimensions = [cap_dim, buyer_dim, geo_dim, cert_dim, sec_dim, scale_dim, timing_dim, incumbent_dim, team_dim]

    blockers: list[FitBlocker] = []
    if cap_dim.verdict == "NEGATIVE":
        code = "historically_failed_capability" if excluded else "no_required_capability"
        blockers.append(FitBlocker(code, cap_dim.basis, fatal=True))
    if cert_dim.verdict == "NEGATIVE":
        blockers.append(FitBlocker("insufficient_certification", cert_dim.basis, fatal=True))
    if sec_dim.verdict == "NEGATIVE":
        blockers.append(FitBlocker("security_clearance_mismatch", sec_dim.basis, fatal=True))
    if geo_dim.verdict == "NEGATIVE":
        blockers.append(FitBlocker("geographic_exclusion", geo_dim.basis, fatal=True))
    if timing_dim.verdict == "NEGATIVE":
        blockers.append(FitBlocker("timing_passed", timing_dim.basis, fatal=True))
    if requirements.get("contract_vehicle") and requirements["contract_vehicle"] not in (profile.meta.get("contract_vehicles") or []):
        blockers.append(FitBlocker("wrong_contract_vehicle",
                                   f"requires vehicle {requirements['contract_vehicle']}", fatal=False))
    if scale_dim.verdict == "NEGATIVE":
        blockers.append(FitBlocker("scale_mismatch", scale_dim.basis, fatal=False))
    unknown_capability = cap_dim.verdict == "UNKNOWN" and bool(req_caps) and not matched
    if unknown_capability:
        blockers.append(FitBlocker("insufficient_capability_evidence",
                                   "no evidenced capability establishes a credible path", fatal=False))

    fatal = [b for b in blockers if b.fatal]
    posture, is_unknown, rationale = _decide_posture(
        fatal, unknown_capability, cap_dim, matched_all, matched_partial,
        is_incumbent, buyer_pos, prime_history, scale_dim, cert_dim, sec_dim,
        consequence, team_dim,
    )

    fit_confidence = _fit_confidence(posture, is_unknown, cap_dim, buyer_dim, dimensions, blockers)
    positives = [d for d in dimensions if d.verdict == "POSITIVE"]
    strongest = max(positives, key=lambda d: d.confidence, default=None)
    weakest = _weakest_dimension(dimensions)
    cap_ev = [e for e in profile.capabilities if e.label in matched]
    first_supportable = _later(getattr(consequence, "first_supportable_at", None),
                               *[e.available_at for e in cap_ev]) if posture != "NO_FIT" or is_unknown else None

    result = FitResult(
        consequence_id=getattr(consequence, "id", ""),
        company_id=profile.company_id,
        posture=posture,
        fit=posture != "NO_FIT",
        fit_confidence=fit_confidence,
        capability_match=sorted(matched),
        dimensions=[to_record(d) for d in dimensions],
        strongest_evidence=(strongest.basis if strongest else None),
        weakest_dimension=(weakest.name if weakest else None),
        blockers=[to_record(b) for b in blockers],
        assumptions=_assumptions(posture, matched_partial, unknown_capability),
        rationale=rationale,
        is_unknown=is_unknown,
        evidence_ids=sorted({e for d in dimensions for e in d.evidence_ids}),
        first_supportable_at=first_supportable,
        meta={"engine_version": FIT_ENGINE_VERSION, "directness": getattr(consequence, "directness", None)},
    )
    result.id = "fit_" + hashlib.sha256(
        f"{result.consequence_id}|{result.company_id}|{FIT_ENGINE_VERSION}".encode()).hexdigest()[:20]
    return result


def _decide_posture(fatal, unknown_capability, cap_dim, matched_all, matched_partial,
                    is_incumbent, buyer_pos, prime_history, scale_dim, cert_dim, sec_dim,
                    consequence, team_dim):
    if fatal:
        return "NO_FIT", False, "fatal blocker(s): " + ", ".join(b.code for b in fatal)
    if unknown_capability:
        return "NO_FIT", True, "insufficient capability evidence to establish a credible capture path"
    if cap_dim.verdict != "POSITIVE":
        return "NO_FIT", True, "no positive capability evidence"
    if is_incumbent:
        return "DEFEND", False, "company is the incumbent; posture is retention/defense, not new capture"
    directness = getattr(consequence, "directness", "DIRECT")
    eligibility_ok = cert_dim.verdict != "NEGATIVE" and sec_dim.verdict != "NEGATIVE"
    scale_ok = scale_dim.verdict != "NEGATIVE"
    if matched_partial:
        if team_dim.verdict == "POSITIVE":
            return "TEAM", False, "partial capability is stronger through teaming"
        return "SUPPORT", False, "company can cover part of the requirement in a support role"
    # matched_all, capability POSITIVE. PRIME requires demonstrated prior PRIME-role performance —
    # a code/agency match as a subcontractor is a support signal, not a prime signal.
    if directness == "DIRECT" and eligibility_ok and scale_ok and prime_history:
        return "PRIME", False, "full capability, eligible, credible scale, and prior prime performance"
    if directness in ("DOWNSTREAM", "SECOND_ORDER"):
        return "SUPPORT", False, "downstream consequence fits a subcontract/supplier role"
    return "SUPPORT", False, "capability fits but the prime/scale/history signal is insufficient for PRIME"


def _fit_confidence(posture, is_unknown, cap_dim, buyer_dim, dimensions, blockers):
    if posture == "NO_FIT":
        if is_unknown:
            return 0.1  # low: we cannot establish fit, not a confident "no"
        return round(min(0.95, 0.6 + 0.1 * len([b for b in blockers if b.fatal])), 3)  # confident no
    base = cap_dim.confidence
    base += 0.05 * sum(1 for d in dimensions if d.verdict == "POSITIVE" and d.name != "CAPABILITY_FIT")
    base -= 0.1 * sum(1 for b in blockers if not b.fatal)
    return round(max(0.05, min(0.95, base)), 3)


def _weakest_dimension(dimensions):
    negatives = [d for d in dimensions if d.verdict == "NEGATIVE"]
    if negatives:
        return min(negatives, key=lambda d: -d.confidence)
    unknowns = [d for d in dimensions if d.verdict == "UNKNOWN"]
    return unknowns[0] if unknowns else None


def _assumptions(posture, matched_partial, unknown_capability):
    out = []
    if matched_partial:
        out.append("teaming/subcontract path assumed to cover the unmatched capability")
    if posture == "SUPPORT":
        out.append("capture depends on a prime awarding subcontract/supplier work")
    if unknown_capability:
        out.append("no capability evidence on file; fit could change if a capability statement is added")
    return out


# --------------------------------------------------------------------------- human review (reuses StateStore)

FIT_DECISIONS = {"ACCEPT_FIT", "REJECT_FIT", "DEFER"}


def enqueue_fit_review(store, fit_result: FitResult) -> dict:
    record = {
        "fit_id": fit_result.id, "consequence_id": fit_result.consequence_id,
        "company_id": fit_result.company_id, "automated_posture": fit_result.posture,
        "pre_review_confidence": fit_result.fit_confidence, "status": "pending",
    }
    existing = {r["fit_id"] for r in _fit_queue_state(store).values() if r.get("status") == "pending"}
    if fit_result.id not in existing:
        store.append("fit_review_queue", record)
    return record


def _fit_queue_state(store) -> dict:
    latest: dict[str, dict] = {}
    for row in store.read("fit_review_queue"):
        if row.get("fit_id"):
            latest[row["fit_id"]] = row
    return latest


def pending_fit_reviews(store) -> list[dict]:
    return [r for r in _fit_queue_state(store).values() if r.get("status") == "pending"]


def adjudicate_fit(store, fit_id: str, *, decision: str, reviewer: str, reason: str = "") -> dict:
    decision = decision.strip().upper()
    if decision not in FIT_DECISIONS:
        raise ValueError("decision must be ACCEPT_FIT, REJECT_FIT, or DEFER")
    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer is required")
    pending = _fit_queue_state(store).get(fit_id)
    if not pending or pending.get("status") != "pending":
        raise ValueError(f"no pending fit review for {fit_id}")
    review = {
        "id": hashlib.sha256(f"{fit_id}|{reviewer}|{decision}".encode()).hexdigest()[:20],
        "fit_id": fit_id, "consequence_id": pending.get("consequence_id"),
        "company_id": pending.get("company_id"), "decision": decision, "reviewer": reviewer.strip(),
        "reason": reason, "automated_posture": pending.get("automated_posture"),
        "pre_review_confidence": pending.get("pre_review_confidence"),
        "reviewed_at": datetime.utcnow().isoformat(),
    }
    store.append("fit_reviews", review)
    store.append("fit_review_queue", {**pending, "status": "resolved", "review_id": review["id"]})
    return review
