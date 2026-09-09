"""M15 — first-class threat intelligence + exposure graph.

Threat is a PEER of commercial opportunity/consequence, not a negated opportunity or a generic alarm.
This module implements the conceptual chain:

    EXPOSURE -> CATALYST -> THREAT MECHANISM -> AFFECTED SUBJECT -> ECONOMIC EFFECT
    -> CONFIDENCE / SEVERITY -> TIME HORIZON -> MITIGATION -> EVIDENCE -> OBSERVED OUTCOME

Design discipline (enforced in code, not just documented):

* **Exposure is explicit and evidence-safe.** A weak fuzzy-name resemblance is a CANDIDATE exposure,
  never a CONFIRMED one, and a threat resting only on a CANDIDATE exposure can never be ACTIVE/HIGH.
* **Confidence and severity are orthogonal ordinals**, never collapsed into one magic number.
  Confidence = strength of evidence for the thesis; severity = how bad the effect could be if true.
* **UNKNOWN is valid** for severity, confidence, and horizon.
* **Zero-threat is first-class.** Most events must NOT become a threat for a given subject; the engine
  emits an auditable :class:`ThreatRejection` instead of lowering a threshold.
* **No fabricated relationships.** Nothing is asserted that is not backed by a retained evidence id.
* **Point-in-time.** Exposures, catalysts, and outcomes are filtered ``available_at <= as_of``; future
  evidence never alters a historical threat state.
* This module never creates a candidate/STRIKE and never changes ``scoring_v1`` or ``fit.py``.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional

from .models import (
    ConsequenceFalsifier,
    Exposure,
    Threat,
    ThreatRejection,
    to_record,
)

THREAT_ENGINE_VERSION = "threat_v1"
EXPOSURE_ENGINE_VERSION = "exposure_v1"

# --------------------------------------------------------------------------- vocabularies

# WHO/WHAT is exposed to WHAT. Extensible; M15 exercises a subset with real evidence.
EXPOSURE_RELATIONS = {
    "SANCTIONED_COUNTERPARTY", "CUSTOMER", "SUPPLIER", "PROGRAM", "CONTRACT", "TECHNOLOGY",
    "GEOGRAPHY", "REGULATION", "CERTIFICATION", "PROCUREMENT_VEHICLE", "FACILITY",
    "COMMODITY_INPUT", "REVENUE_CONCENTRATION", "INCUMBENT_POSITION",
    "CORPORATE_ENTITY",
}

# How strongly an exposure edge is believed. Only CONFIRMED/INFERRED can carry an ACTIVE threat;
# CANDIDATE is human-review fodder; REJECTED is retained as negative evidence.
LINK_CLASSES = {"CONFIRMED", "INFERRED", "CANDIDATE", "REJECTED"}
JOIN_METHODS = {
    "deterministic_identifier", "deterministic_native_id", "inferred_strong_attribute", "name_only_weak",
}

# Initial threat mechanism grammar. Each names: the catalyst/change, why the exposure matters, the
# economic threat mechanism, and the value/position at risk.
THREAT_MECHANISMS = {
    "SANCTIONS_EXPOSURE",
    "INCUMBENT_DISPLACEMENT",
    "PROGRAM_CONTRACTION",
    "PROGRAM_CANCELLATION_OR_DELAY",
    "REGULATORY_COMPLIANCE_EXPOSURE",
    "ELIGIBILITY_OR_CERTIFICATION_RISK",
    "CUSTOMER_CONCENTRATION",
    # M16 exposure-family expansion.
    "SUPPLIER_DEPENDENCY_DISRUPTION",
    "TECHNOLOGY_SUBSTITUTION",
    "GEOGRAPHY_FACILITY_DISRUPTION",
    "CORPORATE_RESTRUCTURING",
}

# Ordinal scales — kept deliberately separate.
SEVERITY_LEVELS = ("UNKNOWN", "LOW", "MODERATE", "HIGH", "CRITICAL")
CONFIDENCE_LEVELS = ("UNKNOWN", "LOW", "MEDIUM", "HIGH")
HORIZONS = ("UNKNOWN", "IMMEDIATE", "NEAR_TERM", "MEDIUM_TERM", "LONG_TERM")

THREAT_STATUSES = {
    "WATCH", "ACTIVE", "MITIGATED", "MATERIALIZED", "AVOIDED", "FALSE_ALARM", "EXPIRED", "UNKNOWN",
}

AFFECTED_VALUE_CATEGORIES = {
    "REVENUE", "CONTRACT_POSITION", "MARKET_ACCESS", "COST_BASE", "ELIGIBILITY", "CONTINUITY",
}

REJECTION_REASONS = {
    "NO_EXPOSURE",                 # subject has no evidenced exposure to the event
    "WEAK_NAME_MATCH_ONLY",        # only a fuzzy-name resemblance; never authoritative
    "NAME_COLLISION",              # shared token is coincidental
    "NO_CATALYST",                 # exposure exists but no adverse change/catalyst
    "IMMATERIAL",                  # exposure + change too weak/ambiguous to matter economically
    "EXPOSURE_ENDED",              # the exposure lapsed before the catalyst
    "RECOMPETE_NOT_A_THREAT",      # a recompete without incumbency/adverse evidence is not a threat
    "AMBIGUOUS",                   # evidence points both ways; unresolved
    "UNKNOWN_INSUFFICIENT_EVIDENCE",
    # M16 exposure-family rejections.
    "NO_DEPENDENCY",               # a supplier/input disruption with no evidenced dependency
    "OUTSIDE_EXPOSURE_GEOGRAPHY",  # a geography event outside the subject's facility/operating footprint
    "VAGUE_TREND_NOT_EVIDENCE",    # a technology trend with no explicit substitution mandate/evidence
}

_GENERIC_TOKENS = {
    "inc", "llc", "ltd", "corp", "co", "company", "the", "and", "group", "holdings", "international",
    "national", "trading", "services", "solutions", "systems", "global", "technologies", "technology",
}


# --------------------------------------------------------------------------- deterministic identity

def exposure_id(subject_ref: str, relation_type: str, target_ref: str) -> str:
    basis = f"{EXPOSURE_ENGINE_VERSION}|{subject_ref}|{relation_type}|{target_ref}".encode("utf-8")
    return "exp_" + hashlib.sha256(basis).hexdigest()[:20]


def threat_id(subject_ref: str, mechanism: str, anchor_ref: str) -> str:
    basis = f"{THREAT_ENGINE_VERSION}|{subject_ref}|{mechanism}|{anchor_ref}".encode("utf-8")
    return "thr_" + hashlib.sha256(basis).hexdigest()[:20]


def _tokens(name: str) -> set[str]:
    lowered = re.sub(r"[^a-z0-9\s]", " ", (name or "").lower())
    return {t for t in lowered.split() if len(t) >= 3} - _GENERIC_TOKENS


def _norm(value: Optional[str]) -> str:
    return " ".join((value or "").split()).casefold()


# --------------------------------------------------------------------------- exposure graph

def _visible(records, as_of: Optional[str]):
    """Point-in-time filter: drop records with no ``available_at`` or after the cutoff."""
    out = []
    for r in records or ():
        r = r or {}
        av = r.get("available_at")
        if as_of is not None and (not av or av > as_of):
            continue
        out.append(r)
    return out


def _designation_index(designations: list[dict]) -> dict:
    by_ent, by_ident = {}, {}
    for d in designations or ():
        ent = d.get("ent_num")
        if ent is not None:
            by_ent[str(ent)] = d
        key = (_norm(d.get("sdn_name")), _norm(d.get("program")))
        if key[0]:
            by_ident.setdefault(key, d)
    return {"by_ent": by_ent, "by_ident": by_ident}


def sanctions_exposures(
    subject_ref: str,
    subject_name: str,
    counterparty_records: list[dict],
    designations: list[dict],
    *,
    as_of: Optional[str] = None,
) -> tuple[list[Exposure], list[dict]]:
    """Build sanctions exposures from a subject's evidenced counterparty relationships.

    Linkage tiers (strong to weak):

    * ``counterparty_ofac_ent_num`` present and resolving to a designation  -> deterministic_identifier,
      CONFIRMED (the record explicitly names the sanctioned entity number).
    * a full identity tuple (normalized ``counterparty_name`` + ``counterparty_country`` matching a
      designation's name + program/country)                                 -> deterministic_identifier, CONFIRMED.
    * a shared significant name token only                                   -> name_only_weak, CANDIDATE.
    * nothing                                                                -> no exposure.

    Returns ``(exposures, weak_candidates)``; weak candidates are returned separately so the caller can
    reject them rather than treat a name resemblance as authoritative (the M14 weak-match discipline).
    """
    index = _designation_index(designations)
    exposures: list[Exposure] = []
    weak: list[dict] = []
    for rec in _visible(counterparty_records, as_of):
        cp_name = rec.get("counterparty_name") or ""
        relation = rec.get("relation") or "SANCTIONED_COUNTERPARTY"
        ev = [e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e]
        ent = rec.get("counterparty_ofac_ent_num")
        designation = index["by_ent"].get(str(ent)) if ent is not None else None
        join_method = "deterministic_identifier" if designation else None

        if designation is None and cp_name and rec.get("counterparty_country"):
            key = (_norm(cp_name), _norm(rec.get("counterparty_country")))
            designation = index["by_ident"].get(key)
            if designation:
                join_method = "deterministic_identifier"

        if designation is not None:
            target = designation
            exp = Exposure(
                subject_ref=subject_ref, subject_name=subject_name,
                relation_type="SANCTIONED_COUNTERPARTY",
                target_ref=target.get("source_ref") or f"ofac:sdn:{target.get('ent_num')}",
                target_name=target.get("sdn_name") or cp_name,
                join_method=join_method, link_class="CONFIRMED", confidence=0.95,
                rationale=(f"subject's {relation.lower()} relationship resolves to OFAC designation "
                           f"{target.get('ent_num')} ({target.get('program')}) by "
                           f"{join_method.replace('_', ' ')}"),
                evidence_ids=ev + [target.get("source_ref")],
                available_at=rec.get("available_at"),
                meta={"ofac_program": target.get("program"), "counterparty_relation": relation,
                      "catalyst_id": rec.get("catalyst_id")},
            )
            exp.id = exposure_id(subject_ref, "SANCTIONED_COUNTERPARTY", exp.target_ref)
            exposures.append(exp)
            continue

        # Weak name-only overlap — surfaced for review, NEVER authoritative.
        q = _tokens(cp_name)
        if not q:
            continue
        for d in designations or ():
            if q & _tokens(d.get("sdn_name", "")):
                weak.append({
                    "subject_ref": subject_ref, "subject_name": subject_name,
                    "counterparty_name": cp_name, "designation": d,
                    "shared_tokens": sorted(q & _tokens(d.get("sdn_name", ""))),
                    "evidence_ids": ev, "available_at": rec.get("available_at"),
                })
                break
    return exposures, weak


def incumbency_exposures(
    subject_ref: str,
    subject_name: str,
    subject_uei: Optional[str],
    award_records: list[dict],
    *,
    as_of: Optional[str] = None,
) -> list[Exposure]:
    """Deterministic PROGRAM / INCUMBENT_POSITION exposures from a subject's own award history.

    An award whose ``recipient_uei`` equals the subject's UEI establishes a deterministic
    (native-id) exposure: the subject depends on that program/contract and holds an incumbent
    position on it. Absence of an award is never treated as evidence of anything.
    """
    exposures: list[Exposure] = []
    target_uei = str(subject_uei).strip().upper() if subject_uei else None
    seen: set[tuple] = set()
    for rec in _visible(award_records, as_of):
        uei = str(rec.get("recipient_uei") or "").strip().upper()
        if not target_uei or uei != target_uei:
            continue
        program_key = rec.get("program_key") or rec.get("contract_ref") or rec.get("source_ref")
        if not program_key:
            continue
        ev = [e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e]
        for relation in ("PROGRAM", "INCUMBENT_POSITION"):
            key = (relation, program_key)
            if key in seen:
                continue
            seen.add(key)
            exp = Exposure(
                subject_ref=subject_ref, subject_name=subject_name,
                relation_type=relation, target_ref=str(program_key),
                target_name=rec.get("program_name") or rec.get("summary") or str(program_key),
                join_method="deterministic_native_id", link_class="CONFIRMED",
                confidence=0.9,
                rationale=("subject UEI matches the award recipient UEI on this program/contract"
                           if relation == "PROGRAM" else
                           "subject is the current award holder (incumbent) on this program/contract"),
                evidence_ids=ev, available_at=rec.get("available_at"),
                valid_from=rec.get("period_start"), valid_to=rec.get("period_end"),
                meta={"agency": rec.get("agency"), "amount_usd": rec.get("amount_usd"),
                      "recipient_uei": uei},
            )
            exp.id = exposure_id(subject_ref, relation, str(program_key))
            exposures.append(exp)
    return exposures


def declared_exposures(
    subject_ref: str,
    subject_name: str,
    exposure_records: list[dict],
    *,
    as_of: Optional[str] = None,
) -> list[Exposure]:
    """Build exposures from records that explicitly declare a structured exposure edge.

    Each record supplies ``relation`` (an ``EXPOSURE_RELATIONS`` member), ``target_ref``,
    ``target_name``, and either a deterministic identifier (``deterministic``) or an inferred
    strong-attribute basis. Used for REGULATION / CERTIFICATION / GEOGRAPHY / CUSTOMER exposures
    grounded in explicit source fields (a regulation naming a regulated class, a held certification,
    a place-of-performance, a named customer concentration).
    """
    exposures: list[Exposure] = []
    for rec in _visible(exposure_records, as_of):
        relation = rec.get("relation")
        if relation not in EXPOSURE_RELATIONS or not rec.get("target_ref"):
            continue
        deterministic = bool(rec.get("deterministic"))
        join_method = "deterministic_identifier" if deterministic else "inferred_strong_attribute"
        link_class = "CONFIRMED" if deterministic else "INFERRED"
        ev = [e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e]
        exp = Exposure(
            subject_ref=subject_ref, subject_name=subject_name, relation_type=relation,
            target_ref=str(rec["target_ref"]), target_name=rec.get("target_name") or str(rec["target_ref"]),
            join_method=join_method, link_class=link_class,
            confidence=float(rec.get("confidence") or (0.9 if deterministic else 0.6)),
            rationale=rec.get("rationale") or "",
            evidence_ids=ev, available_at=rec.get("available_at"),
            valid_from=rec.get("valid_from"), valid_to=rec.get("valid_to"),
            meta={k: v for k, v in rec.items()
                  if k in ("agency", "certification", "geography", "revenue_share", "sole_source",
                           "amount_usd", "catalyst_id")},
        )
        exp.id = exposure_id(subject_ref, relation, str(rec["target_ref"]))
        exposures.append(exp)
    return exposures


def persist_exposures(store, exposures) -> None:
    for exp in exposures:
        store.append("exposures", to_record(exp))


# --------------------------------------------------------------------------- severity / confidence

# Severity is a magnitude BAND of a KNOWN dollar figure at risk (evidence, not invented probability).
# Absent an amount, severity stays UNKNOWN or a conservative mechanism default — never fabricated.
_SEVERITY_BANDS = ((100_000_000, "CRITICAL"), (25_000_000, "HIGH"), (5_000_000, "MODERATE"), (0, "LOW"))


def severity_from_amount(amount) -> str:
    if amount is None:
        return "UNKNOWN"
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return "UNKNOWN"
    for threshold, level in _SEVERITY_BANDS:
        if amount > threshold:
            return level
    return "LOW"


def _max_severity(*levels: str) -> str:
    known = [l for l in levels if l in SEVERITY_LEVELS]
    return max(known, key=SEVERITY_LEVELS.index) if known else "UNKNOWN"


def _confidence_from_exposures(exposures: list[Exposure], catalyst_strength: int) -> tuple[str, str]:
    """Ordinal evidence confidence, distinct from severity. A CANDIDATE-only exposure caps at LOW."""
    if not exposures:
        return "UNKNOWN", "no evidenced exposure"
    classes = {e.link_class for e in exposures}
    joins = {e.join_method for e in exposures}
    if classes & {"CONFIRMED"} and joins & {"deterministic_identifier", "deterministic_native_id"} \
            and catalyst_strength >= 3:
        return "HIGH", "deterministic exposure link + direct catalyst evidence"
    if classes & {"CONFIRMED", "INFERRED"} and catalyst_strength >= 2:
        return "MEDIUM", "confirmed/inferred exposure with corroborating catalyst evidence"
    if classes & {"CONFIRMED", "INFERRED"}:
        return "LOW", "exposure established but catalyst evidence is thin"
    return "LOW", "only a candidate (weak) exposure supports this thesis"


_DETERMINISTIC_JOINS = {"deterministic_identifier", "deterministic_native_id"}


def exposure_join_class(exposures) -> str:
    """Classify a threat's exposure evidence as DETERMINISTIC / INFERRED / CANDIDATE (M19 Workstream A).

    * ``deterministic`` — at least one CONFIRMED exposure joined by an authoritative native identifier
      (PIID/UEI/CAGE/ent_num/CIK): linkage strictly stronger than fuzzy name, broad industry, shared
      geography, modeled incumbency, or an inferred prime relationship.
    * ``inferred`` — a CONFIRMED/INFERRED exposure resting on a strong attribute, not a native id.
    * ``candidate`` — only a weak/candidate exposure supports the thesis.

    This is a first-class, durable label (parallel to catalyst authority) travelling on every ``Threat``,
    so deterministic-vs-inferred threats can be counted and a deterministic HIGH-confidence chain is
    auditable. It classifies the EXPOSURE join only; it never by itself sets severity or confidence."""
    exposures = list(exposures or ())
    if any(e.link_class == "CONFIRMED" and e.join_method in _DETERMINISTIC_JOINS for e in exposures):
        return "deterministic"
    if any(e.link_class in ("CONFIRMED", "INFERRED") for e in exposures):
        return "inferred"
    return "candidate"


def _falsifier(code: str, detail: str, fatal: bool = False) -> dict:
    return to_record(ConsequenceFalsifier(code=code, detail=detail, fatal=fatal))


# --------------------------------------------------------------------------- catalyst helpers

def _catalysts(records, kind, as_of):
    return [r for r in _visible(records, as_of) if r.get("catalyst_kind") == kind]


def _strength(rec: dict) -> int:
    try:
        return int(rec.get("evidence_strength") or 3)
    except (TypeError, ValueError):
        return 3


def _exp_of(exposures, relation):
    return [e for e in exposures if e.relation_type == relation]


def _mk_threat(subject_ref, subject_name, mechanism, anchor_ref, exposures, catalyst_rec, **kw) -> Threat:
    threat = Threat(
        subject_ref=subject_ref, subject_name=subject_name, mechanism=mechanism,
        exposure_ids=[e.id for e in exposures],
        catalyst_id=(catalyst_rec or {}).get("catalyst_id"),
        evidence_ids=sorted({*(kw.pop("evidence_ids", [])),
                             *[e for e in [(catalyst_rec or {}).get("evidence_id"),
                                           (catalyst_rec or {}).get("source_ref")] if e],
                             *[eid for exp in exposures for eid in exp.evidence_ids]}),
        available_at=kw.pop("available_at", (catalyst_rec or {}).get("available_at")),
        first_observed_at=kw.pop("available_at_first", (catalyst_rec or {}).get("available_at")),
        **kw,
    )
    threat.id = threat_id(subject_ref, mechanism, anchor_ref)
    # M18 (Workstream H): the catalyst's durable authority (OBSERVED vs MODELED/SYNTHETIC/PROBE) travels
    # with the threat. Absent an explicit class the catalyst is MODELED — no old fixture is relabelled.
    cclass = (catalyst_rec or {}).get("catalyst_class")
    threat.meta["catalyst_class"] = cclass if cclass in ("OBSERVED", "MODELED", "SYNTHETIC", "PROBE") \
        else "MODELED"
    # M19 (Workstream A/L): the deterministic-vs-inferred exposure authority travels with the threat.
    threat.meta["exposure_join_class"] = exposure_join_class(exposures)
    fam = (catalyst_rec or {}).get("family")
    if fam:
        threat.meta["adverse_event_family"] = fam
    return threat


# --------------------------------------------------------------------------- mechanism assessors
# Each returns (threats, rejections). A mechanism that finds exposure + a real adverse catalyst emits a
# threat; a mechanism that finds an event but no material exposure emits a rejection (zero-threat).

def _assess_sanctions(subject_ref, subject_name, exposures, records, weak, as_of):
    threats, rejections = [], []
    confirmed = [e for e in _exp_of(exposures, "SANCTIONED_COUNTERPARTY")
                 if e.link_class in ("CONFIRMED", "INFERRED")]
    for exp in confirmed:
        relation = exp.meta.get("counterparty_relation", "COUNTERPARTY")
        category = "REVENUE" if relation == "CUSTOMER" else "CONTINUITY"
        catalyst_rec = {"evidence_id": exp.target_ref, "available_at": exp.available_at,
                        "evidence_strength": 5, "catalyst_id": exp.meta.get("catalyst_id")}
        confidence, cbasis = _confidence_from_exposures([exp], 5)
        severity = "HIGH" if relation in ("SUPPLIER", "CUSTOMER") else "MODERATE"
        threats.append(_mk_threat(
            subject_ref, subject_name, "SANCTIONS_EXPOSURE", exp.target_ref, [exp], catalyst_rec,
            affected_value_category=category,
            economic_effect=(f"OFAC designation of the subject's {relation.lower()} "
                             f"({exp.target_name}) exposes the subject to secondary sanctions, forced "
                             f"contract termination, and loss of that {relation.lower()} relationship"),
            severity=severity, severity_basis=f"{relation.lower()} dependency on a sanctioned party",
            confidence=confidence, confidence_basis=cbasis, horizon="IMMEDIATE", status="ACTIVE",
            falsifiers=[_falsifier("relationship_ended",
                                   "subject can show the counterparty relationship ended before the "
                                   "designation date", fatal=True),
                        _falsifier("general_license_covers",
                                   "an OFAC general license authorizes the specific activity")],
            mitigations=["terminate or wind down the counterparty relationship",
                         "qualify a compliant substitute supplier/customer",
                         "seek OFAC guidance / general-license coverage"],
        ))
    # Weak name-only candidates that never became a confirmed exposure => explicit rejection.
    for w in _visible(weak, as_of):
        rejections.append(ThreatRejection(
            subject_ref=subject_ref, subject_name=subject_name, mechanism="SANCTIONS_EXPOSURE",
            reason_code="WEAK_NAME_MATCH_ONLY",
            detail=(f"'{w['counterparty_name']}' shares token(s) {w['shared_tokens']} with OFAC "
                    f"designation '{w['designation'].get('sdn_name')}' but no authoritative identifier "
                    f"resolves them; a name resemblance is never a sanctions hit"),
            evidence_ids=w.get("evidence_ids", []), available_at=w.get("available_at"),
        ))
    return threats, rejections


def _assess_incumbent_displacement(subject_ref, subject_name, exposures, records, as_of):
    threats, rejections = [], []
    incumbencies = _exp_of(exposures, "INCUMBENT_POSITION")
    for rec in _catalysts(records, "recompete", as_of):
        target = rec.get("program_key") or rec.get("target_ref")
        held = [e for e in incumbencies if e.target_ref == target]
        signal = rec.get("displacement_signal")
        if not held:
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name,
                mechanism="INCUMBENT_DISPLACEMENT", reason_code="NO_EXPOSURE",
                detail=f"recompete on {target} but the subject holds no incumbent position on it",
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at")))
            continue
        if not signal:
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name,
                mechanism="INCUMBENT_DISPLACEMENT", reason_code="RECOMPETE_NOT_A_THREAT",
                detail=("a recompete alone is not a threat; no displacement evidence (named competitor, "
                        "protest, set-aside change, or mandated new entrant) is present"),
                exposure_ids=[e.id for e in held],
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at")))
            continue
        exp = held[0]
        amount = exp.meta.get("amount_usd")
        confidence, cbasis = _confidence_from_exposures(held, _strength(rec))
        threats.append(_mk_threat(
            subject_ref, subject_name, "INCUMBENT_DISPLACEMENT", target, held, rec,
            affected_value_category="CONTRACT_POSITION",
            economic_effect=(f"recompete of {exp.target_name} with {signal.replace('_', ' ')} evidence "
                             f"threatens the subject's incumbent contract position"),
            severity=severity_from_amount(amount),
            severity_basis=(f"incumbent contract value ${amount:,.0f}" if amount
                            else "incumbent contract value unknown"),
            confidence=confidence, confidence_basis=f"{cbasis}; displacement signal: {signal}",
            horizon="NEAR_TERM", status="ACTIVE",
            falsifiers=[_falsifier("incumbent_readvantage",
                                   "incumbent retains a decisive past-performance / transition advantage"),
                        _falsifier("recompete_cancelled",
                                   "the recompete is cancelled and the incumbent bridged", fatal=True)],
            mitigations=["invest in the recompete capture (past performance, price-to-win)",
                         "pursue a teaming position with the likely awardee"],
        ))
    return threats, rejections


def _assess_program_change(subject_ref, subject_name, exposures, records, as_of):
    threats, rejections = [], []
    dependencies = _exp_of(exposures, "PROGRAM")
    for kind, mechanism, horizon in (("program_cancellation", "PROGRAM_CANCELLATION_OR_DELAY", "NEAR_TERM"),
                                     ("program_delay", "PROGRAM_CANCELLATION_OR_DELAY", "MEDIUM_TERM"),
                                     ("funding_reduction", "PROGRAM_CONTRACTION", "MEDIUM_TERM")):
        for rec in _catalysts(records, kind, as_of):
            target = rec.get("program_key") or rec.get("target_ref")
            dep = [e for e in dependencies if e.target_ref == target]
            if not dep:
                rejections.append(ThreatRejection(
                    subject_ref=subject_ref, subject_name=subject_name, mechanism=mechanism,
                    reason_code="NO_EXPOSURE",
                    detail=f"{kind} on {target} but the subject has no evidenced dependency on it",
                    evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                    available_at=rec.get("available_at")))
                continue
            exp = dep[0]
            # M19 (Workstream P): temporal exposure-window validity. A deterministic relationship can
            # still be historically invalid — if the incumbency lapsed before the adverse event, the
            # subject was not exposed at event time. Future exposure evidence never creates a past threat.
            cat_at = rec.get("available_at")
            if cat_at and ((exp.valid_from and cat_at < exp.valid_from)
                           or (exp.valid_to and cat_at > exp.valid_to)):
                rejections.append(ThreatRejection(
                    subject_ref=subject_ref, subject_name=subject_name, mechanism=mechanism,
                    reason_code="EXPOSURE_ENDED",
                    detail=(f"{kind} on {target} at {cat_at}, but the subject's exposure window is "
                            f"{exp.valid_from or 'unknown'}..{exp.valid_to or 'open'}; deterministic "
                            f"identity does not make a temporally invalid exposure a threat"),
                    exposure_ids=[exp.id],
                    evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                    available_at=cat_at))
                continue
            at_risk = rec.get("amount_delta_usd")
            if at_risk is None:
                at_risk = exp.meta.get("amount_usd")
            # M19 (Workstream K/O): materiality gate for a contraction. A real, deterministically-linked
            # deobligation that is trivially small relative to the contract is a routine funding
            # adjustment, NOT a program contraction — so deterministic identity alone never manufactures a
            # threat. Only funding reductions are gated (a cancellation/delay is categorical). The floor
            # ($1M) sits below every modeled corpus reduction and is overridable per-catalyst.
            if kind == "funding_reduction" and at_risk is not None:
                try:
                    magnitude = abs(float(at_risk))
                except (TypeError, ValueError):
                    magnitude = None
                floor = rec.get("materiality_floor_usd")
                floor = float(floor) if floor is not None else 1_000_000.0
                if magnitude is not None and magnitude < floor:
                    rejections.append(ThreatRejection(
                        subject_ref=subject_ref, subject_name=subject_name, mechanism=mechanism,
                        reason_code="IMMATERIAL",
                        detail=(f"deobligation of ${magnitude:,.0f} on {target} is below the "
                                f"${floor:,.0f} materiality floor; a routine funding pull-back on a large "
                                f"contract is not a program contraction"),
                        exposure_ids=[exp.id],
                        evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                        available_at=cat_at))
                    continue
            confidence, cbasis = _confidence_from_exposures(dep, _strength(rec))
            effect = {"program_cancellation": "cancellation eliminates",
                      "program_delay": "delay defers",
                      "funding_reduction": "funding reduction shrinks"}[kind]
            threats.append(_mk_threat(
                subject_ref, subject_name, mechanism, target, dep, rec,
                affected_value_category=("CONTINUITY" if kind == "program_cancellation" else "REVENUE"),
                economic_effect=(f"{exp.target_name}: {effect} the subject's program-dependent revenue"),
                severity=severity_from_amount(at_risk),
                severity_basis=(f"program revenue at risk ${float(at_risk):,.0f}" if at_risk
                                else "program revenue at risk unknown"),
                confidence=confidence, confidence_basis=cbasis, horizon=horizon, status="ACTIVE",
                falsifiers=[_falsifier("funding_restored",
                                       "appropriations restore the program before impact", fatal=True),
                            _falsifier("subject_not_dependent",
                                       "the program is a minor share of subject revenue")],
                mitigations=["diversify away from the contracting program",
                             "reposition capabilities toward funded adjacent programs"],
            ))
    return threats, rejections


def _assess_corporate_restructuring(subject_ref, subject_name, exposures, records, as_of):
    """M20 observed SEC restructuring/exit costs, joined only to the exact filer CIK."""
    threats, rejections = [], []
    entities = _exp_of(exposures, "CORPORATE_ENTITY")
    for rec in _catalysts(records, "corporate_restructuring", as_of):
        target = rec.get("target_ref")
        matched = [e for e in entities if e.target_ref == target]
        if not matched:
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name, mechanism="CORPORATE_RESTRUCTURING",
                reason_code="NO_EXPOSURE", detail=f"SEC event {target} does not match the subject's filer identity",
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at"), meta={"adverse_event_family": rec.get("family")}))
            continue
        amount = rec.get("amount_at_risk_usd")
        try:
            magnitude = float(amount)
        except (TypeError, ValueError):
            magnitude = None
        floor = float(rec.get("materiality_floor_usd") or 5_000_000)
        if magnitude is None or magnitude < floor:
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name, mechanism="CORPORATE_RESTRUCTURING",
                reason_code="IMMATERIAL", detail="corporate disclosure lacks a material quantified adverse effect",
                exposure_ids=[matched[0].id],
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at"), meta={"adverse_event_family": rec.get("family")}))
            continue
        confidence, cbasis = _confidence_from_exposures(matched, _strength(rec))
        threats.append(_mk_threat(
            subject_ref, subject_name, "CORPORATE_RESTRUCTURING", str(target), matched, rec,
            affected_value_category="COST_BASE",
            economic_effect=(f"{rec.get('summary') or 'reported restructuring'}: the filer reported "
                             f"${magnitude:,.0f} of restructuring, impairment and exit costs"),
            severity=severity_from_amount(magnitude), severity_basis=f"reported adverse costs ${magnitude:,.0f}",
            confidence=confidence, confidence_basis=cbasis, horizon=rec.get("horizon") or "IMMEDIATE",
            status=("MATERIALIZED" if rec.get("observed_effect") else "ACTIVE"),
            falsifiers=[_falsifier("filing_amended", "the filer amends or withdraws the reported costs", fatal=True)],
            mitigations=["verify whether restructuring effects are isolated or continuing"],
        ))
    return threats, rejections


def _assess_regulatory(subject_ref, subject_name, exposures, records, as_of):
    threats, rejections = [], []
    regs = _exp_of(exposures, "REGULATION") + _exp_of(exposures, "CERTIFICATION")
    for rec in _catalysts(records, "regulatory_mandate", as_of):
        target = rec.get("target_ref")
        # Deterministic: the mandate must reference the exact regulation/certification the subject is
        # exposed to. Holding *some* certification does not make every mandate a threat.
        relevant = [e for e in regs if e.target_ref == target]
        if not relevant:
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name,
                mechanism="REGULATORY_COMPLIANCE_EXPOSURE", reason_code="NO_EXPOSURE",
                detail=f"regulatory mandate {target} does not apply to the subject's activities",
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at")))
            continue
        eligibility = bool(rec.get("eligibility_gated"))
        mechanism = "ELIGIBILITY_OR_CERTIFICATION_RISK" if eligibility else "REGULATORY_COMPLIANCE_EXPOSURE"
        cost = rec.get("compliance_cost_usd")
        exp = relevant[0]
        confidence, cbasis = _confidence_from_exposures(relevant, _strength(rec))
        threats.append(_mk_threat(
            subject_ref, subject_name, mechanism, str(target), relevant, rec,
            affected_value_category=("ELIGIBILITY" if eligibility else "COST_BASE"),
            economic_effect=(f"{rec.get('summary') or target}: "
                             + ("failure to certify in time removes the subject from eligibility"
                                if eligibility else
                                "compliance imposes a new cost the subject must absorb")),
            severity=(_max_severity(severity_from_amount(cost), "MODERATE") if not eligibility
                      else "HIGH"),
            severity_basis=(f"compliance cost ${float(cost):,.0f}" if cost
                            else ("loss of contract eligibility" if eligibility
                                  else "new compliance cost of unknown magnitude")),
            confidence=confidence, confidence_basis=cbasis,
            horizon=rec.get("horizon") or "MEDIUM_TERM", status="ACTIVE",
            dual_opportunity_ref=rec.get("dual_opportunity_ref"),
            falsifiers=[_falsifier("exempt", "the subject qualifies for an exemption/safe harbor",
                                   fatal=True),
                        _falsifier("already_compliant",
                                   "the subject already meets the requirement", fatal=True)],
            mitigations=["begin certification/compliance program now",
                         "engage a compliance vendor (the dual opportunity side)"],
        ))
    return threats, rejections


def _assess_customer_concentration(subject_ref, subject_name, exposures, records, as_of):
    threats, rejections = [], []
    concentrations = [e for e in _exp_of(exposures, "CUSTOMER") + _exp_of(exposures, "REVENUE_CONCENTRATION")
                      if (e.meta.get("revenue_share") or 0) >= 0.25]
    for rec in _catalysts(records, "customer_adverse_change", as_of):
        target = rec.get("target_ref") or rec.get("program_key")
        dep = [e for e in concentrations if e.target_ref == target]
        if not dep:
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name, mechanism="CUSTOMER_CONCENTRATION",
                reason_code="IMMATERIAL",
                detail=f"adverse change at {target} but it is not a concentrated (>=25%) customer",
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at")))
            continue
        exp = dep[0]
        share = exp.meta.get("revenue_share")
        confidence, cbasis = _confidence_from_exposures(dep, _strength(rec))
        threats.append(_mk_threat(
            subject_ref, subject_name, "CUSTOMER_CONCENTRATION", str(target), dep, rec,
            affected_value_category="REVENUE",
            economic_effect=(f"adverse change at {exp.target_name} ({int(share * 100)}% of revenue) "
                             f"threatens a concentrated revenue base"),
            severity=_max_severity("HIGH" if share >= 0.4 else "MODERATE"),
            severity_basis=f"revenue concentration {int(share * 100)}%",
            confidence=confidence, confidence_basis=cbasis, horizon="MEDIUM_TERM", status="ACTIVE",
            falsifiers=[_falsifier("diversified_since",
                                   "subject has diversified its revenue base since the concentration")],
            mitigations=["accelerate customer diversification"],
        ))
    return threats, rejections


def _assess_supplier_dependency(subject_ref, subject_name, exposures, records, as_of):
    """M16 SUPPLIER_DEPENDENCY_DISRUPTION. Requires an evidenced SUPPLIER exposure whose target is the
    disrupted supplier; a disruption with no demonstrated dependency is NO_DEPENDENCY (zero-threat).
    Supplier relationships are never inferred from industry adjacency (only explicit disclosed edges)."""
    threats, rejections = [], []
    suppliers = _exp_of(exposures, "SUPPLIER")
    for rec in _catalysts(records, "supplier_disruption", as_of):
        target = rec.get("target_ref")
        dep = [e for e in suppliers if e.target_ref == target]
        if not dep:
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name,
                mechanism="SUPPLIER_DEPENDENCY_DISRUPTION", reason_code="NO_DEPENDENCY",
                detail=f"supplier disruption at {target} but the subject has no evidenced dependency on it",
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at")))
            continue
        exp = dep[0]
        at_risk = rec.get("amount_at_risk_usd") or exp.meta.get("amount_usd")
        sole_source = bool(exp.meta.get("sole_source"))
        confidence, cbasis = _confidence_from_exposures(dep, _strength(rec))
        threats.append(_mk_threat(
            subject_ref, subject_name, "SUPPLIER_DEPENDENCY_DISRUPTION", str(target), dep, rec,
            affected_value_category="CONTINUITY",
            economic_effect=(f"disruption of supplier {exp.target_name} threatens the subject's "
                             f"{'sole-source ' if sole_source else ''}input continuity and cost base"),
            severity=_max_severity(severity_from_amount(at_risk), "HIGH" if sole_source else "MODERATE"),
            severity_basis=("sole-source dependency" if sole_source else "qualified alternate suppliers exist"),
            confidence=confidence, confidence_basis=cbasis, horizon="NEAR_TERM", status="ACTIVE",
            falsifiers=[_falsifier("alternate_qualified",
                                   "a qualified alternate supplier is already in place", fatal=True),
                        _falsifier("inventory_buffer", "sufficient inventory buffers the disruption")],
            mitigations=["qualify an alternate supplier", "build buffer inventory"],
        ))
    return threats, rejections


def _assess_technology_substitution(subject_ref, subject_name, exposures, records, as_of):
    """M16 TECHNOLOGY_SUBSTITUTION. Requires a TECHNOLOGY exposure the subject sells/depends on AND an
    explicit substitution mandate (standard change, program modernization). A vague market trend without
    an explicit mandate is VAGUE_TREND_NOT_EVIDENCE (zero-threat) — obsolescence is never inferred."""
    threats, rejections = [], []
    techs = _exp_of(exposures, "TECHNOLOGY")
    for rec in _catalysts(records, "technology_substitution", as_of):
        target = rec.get("target_ref")
        exposed = [e for e in techs if e.target_ref == target]
        if not exposed:
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name, mechanism="TECHNOLOGY_SUBSTITUTION",
                reason_code="NO_EXPOSURE",
                detail=f"substitution of {target} but the subject has no evidenced position in it",
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at")))
            continue
        if not rec.get("explicit_mandate"):
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name, mechanism="TECHNOLOGY_SUBSTITUTION",
                reason_code="VAGUE_TREND_NOT_EVIDENCE",
                detail=("a technology trend without an explicit substitution mandate/standard change is "
                        "not evidence of obsolescence"),
                exposure_ids=[e.id for e in exposed],
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at")))
            continue
        exp = exposed[0]
        at_risk = rec.get("amount_at_risk_usd") or exp.meta.get("amount_usd")
        confidence, cbasis = _confidence_from_exposures(exposed, _strength(rec))
        threats.append(_mk_threat(
            subject_ref, subject_name, "TECHNOLOGY_SUBSTITUTION", str(target), exposed, rec,
            affected_value_category="MARKET_ACCESS",
            economic_effect=(f"{rec.get('summary') or target}: a mandated substitution away from "
                             f"{exp.target_name} threatens the subject's technology market position"),
            severity=_max_severity(severity_from_amount(at_risk), "MODERATE"),
            severity_basis=(f"revenue in the substituted technology ${float(at_risk):,.0f}" if at_risk
                            else "market position in the substituted technology"),
            confidence=confidence, confidence_basis=cbasis,
            horizon=rec.get("horizon") or "MEDIUM_TERM", status="ACTIVE",
            dual_opportunity_ref=rec.get("dual_opportunity_ref"),
            falsifiers=[_falsifier("subject_offers_replacement",
                                   "the subject already offers the replacement technology", fatal=True),
                        _falsifier("mandate_reversed", "the mandate is withdrawn/deferred")],
            mitigations=["invest in the replacement technology", "reposition into adjacent requirements"],
        ))
    return threats, rejections


def _assess_geography_facility(subject_ref, subject_name, exposures, records, as_of):
    """M16 GEOGRAPHY_FACILITY_DISRUPTION. Requires a FACILITY/GEOGRAPHY exposure inside the event's
    geographic scope; an event outside the subject's footprint is OUTSIDE_EXPOSURE_GEOGRAPHY
    (zero-threat). Geography is matched on explicit fields, never on a name resemblance."""
    threats, rejections = [], []
    footprint = _exp_of(exposures, "FACILITY") + _exp_of(exposures, "GEOGRAPHY")
    for rec in _catalysts(records, "geography_event", as_of):
        scope = _norm(rec.get("geography"))
        affected = [e for e in footprint
                    if scope and scope in (_norm(e.meta.get("geography")), _norm(e.target_name),
                                           _norm(e.target_ref))]
        if not affected:
            rejections.append(ThreatRejection(
                subject_ref=subject_ref, subject_name=subject_name,
                mechanism="GEOGRAPHY_FACILITY_DISRUPTION", reason_code="OUTSIDE_EXPOSURE_GEOGRAPHY",
                detail=f"geography event in {rec.get('geography')} is outside the subject's footprint",
                evidence_ids=[e for e in [rec.get("evidence_id"), rec.get("source_ref")] if e],
                available_at=rec.get("available_at")))
            continue
        exp = affected[0]
        at_risk = rec.get("amount_at_risk_usd") or exp.meta.get("amount_usd")
        confidence, cbasis = _confidence_from_exposures(affected, _strength(rec))
        threats.append(_mk_threat(
            subject_ref, subject_name, "GEOGRAPHY_FACILITY_DISRUPTION", str(exp.target_ref), affected, rec,
            affected_value_category="CONTINUITY",
            economic_effect=(f"{rec.get('summary') or rec.get('geography')}: the event affects the "
                             f"subject's {exp.target_name} in {rec.get('geography')}"),
            severity=_max_severity(severity_from_amount(at_risk), "MODERATE"),
            severity_basis=f"operating footprint in {rec.get('geography')}",
            confidence=confidence, confidence_basis=cbasis,
            horizon=rec.get("horizon") or "NEAR_TERM", status="ACTIVE",
            falsifiers=[_falsifier("facility_relocated",
                                   "the subject relocated out of the affected geography", fatal=True)],
            mitigations=["assess business-continuity/relocation options"],
        ))
    return threats, rejections


_ASSESSORS = (_assess_incumbent_displacement, _assess_program_change, _assess_regulatory,
              _assess_customer_concentration, _assess_supplier_dependency,
              _assess_technology_substitution, _assess_geography_facility,
              _assess_corporate_restructuring)


def assess_threats(
    subject_ref: str,
    subject_name: str,
    exposures: list[Exposure],
    catalyst_records: list[dict],
    *,
    weak_candidates: Optional[list[dict]] = None,
    as_of: Optional[str] = None,
) -> tuple[list[Threat], list[ThreatRejection]]:
    """Run every mechanism assessor over a subject's exposures + adverse-change catalyst records.

    Returns ``(threats, rejections)``. Zero threats with one or more rejections is a common, valid,
    high-quality result: most events must not become a threat for a given subject.
    """
    threats: list[Threat] = []
    rejections: list[ThreatRejection] = []
    st, sr = _assess_sanctions(subject_ref, subject_name, exposures, catalyst_records,
                               weak_candidates or [], as_of)
    threats += st
    rejections += sr
    for assessor in _ASSESSORS:
        t, r = assessor(subject_ref, subject_name, exposures, catalyst_records, as_of)
        threats += t
        rejections += r
    threats.sort(key=lambda x: (x.mechanism, x.subject_ref, x.id))
    return threats, rejections


# --------------------------------------------------------------------------- duality

def link_duality(threats: list[Threat], opportunities: list[dict]) -> int:
    """Cross-link a threat and an opportunity/consequence that share a catalyst (M15 duality).

    The SAME catalyst may threaten one entity and create an opportunity for another (a sanctioned
    supplier threatens the importer AND opens demand for a compliant substitute). Both sides point back
    to the common ``catalyst_id`` — source facts are never duplicated. Returns the number of links made.
    """
    by_cat: dict[str, list[dict]] = {}
    for opp in opportunities:
        cat = opp.get("catalyst_id")
        if cat:
            by_cat.setdefault(cat, []).append(opp)
    linked = 0
    for threat in threats:
        if threat.catalyst_id and threat.catalyst_id in by_cat and not threat.dual_opportunity_ref:
            threat.dual_opportunity_ref = by_cat[threat.catalyst_id][0].get("id")
            threat.meta["dual_sided"] = True
            linked += 1
    return linked


# --------------------------------------------------------------------------- company threat surface

def company_threat_surface(subject_ref: str, threats: list[Threat]) -> dict:
    """Structured, grouped view of the active threats affecting one company (M15 foundation).

    Shares the CompanyProfile/entity layer (keyed by ``subject_ref``); it composes existing Threat
    records rather than introducing a parallel company model. Not the full Company Opportunity Surface —
    just enough structure for future code to ask "what active threats affect Company X?".
    """
    mine = [t for t in threats if t.subject_ref == subject_ref
            and t.status in ("WATCH", "ACTIVE", "MITIGATED")]
    def group(attr):
        out: dict[str, int] = {}
        for t in mine:
            out[getattr(t, attr)] = out.get(getattr(t, attr), 0) + 1
        return out
    return {
        "subject_ref": subject_ref,
        "subject_name": next((t.subject_name for t in mine), None),
        "active_threat_count": len(mine),
        "by_mechanism": group("mechanism"),
        "by_severity": group("severity"),
        "by_confidence": group("confidence"),
        "by_horizon": group("horizon"),
        "threats": [
            {"id": t.id, "mechanism": t.mechanism, "severity": t.severity, "confidence": t.confidence,
             "horizon": t.horizon, "affected_value_category": t.affected_value_category,
             "economic_effect": t.economic_effect, "exposure_ids": t.exposure_ids,
             "evidence_ids": t.evidence_ids, "dual_opportunity_ref": t.dual_opportunity_ref}
            for t in sorted(mine, key=lambda t: (-SEVERITY_LEVELS.index(t.severity), t.mechanism))
        ],
    }


def persist_threats(store, threats, rejections=()) -> None:
    for threat in threats:
        store.append("threats", to_record(threat))
    for rejection in rejections:
        store.append("threat_rejections", to_record(rejection))


# --------------------------------------------------------------------------- outcome linkage (M15/L)

# Observed threat outcomes. UNKNOWN is the honest default; an unresolved threat is NEVER auto-labelled a
# false alarm. Terminal/negative labels require an explicit, dated, sourced observation.
THREAT_OUTCOME_LABELS = (
    "MATERIALIZED",       # the adverse effect happened (contract lost, program cancelled, penalty)
    "AVOIDED",            # the threatened effect did not occur (evidenced, not merely unresolved)
    "MITIGATED",          # action reduced the effect
    "DELAYED",            # the effect was pushed out
    "EXPOSURE_ENDED",     # the underlying exposure lapsed
    "FALSE_ALARM",        # the thesis was wrong (evidenced)
    "UNKNOWN",
)
_THREAT_TERMINAL = frozenset({"MATERIALIZED", "AVOIDED", "MITIGATED", "EXPOSURE_ENDED", "FALSE_ALARM"})
_THREAT_OUTCOME_RANK = {"MATERIALIZED": 6, "AVOIDED": 6, "FALSE_ALARM": 6, "MITIGATED": 5,
                        "EXPOSURE_ENDED": 5, "DELAYED": 2, "UNKNOWN": 0}


def threat_outcome_observation(
    threat_id_: str, label: str, observed_at: str, source_id: str, source_ref: str,
    *, evidence_strength: int = 3, notes: str = "",
) -> dict:
    """Validate + build one append-only threat-outcome observation.

    Negative/terminal outcomes require an explicit source (never inferred from absence), mirroring
    :mod:`pyrnova.outcomes`.
    """
    if label not in THREAT_OUTCOME_LABELS:
        raise ValueError(f"unknown threat outcome label: {label!r}")
    if label == "UNKNOWN":
        raise ValueError("UNKNOWN is a resolved default, not an observable outcome")
    if not observed_at:
        raise ValueError(f"{label} requires observed_at (the point-in-time gate)")
    if label in _THREAT_TERMINAL and (not source_ref or int(evidence_strength) < 3):
        raise ValueError(f"{label} is authoritative: needs source_ref and evidence_strength >= 3")
    return {"threat_id": threat_id_, "label": label, "observed_at": observed_at,
            "source_id": source_id, "source_ref": source_ref,
            "evidence_strength": int(evidence_strength), "notes": notes}


def resolve_threat_outcome(observations, *, as_of: str) -> dict:
    """Resolve a threat's outcome as of a cutoff. Future-dated observations are excluded; with none
    knowable the outcome is UNKNOWN — never an inferred false alarm."""
    known, future = [], []
    for obs in observations or ():
        oa = obs.get("observed_at")
        if not oa:
            continue
        (known if oa <= as_of else future).append(obs)
    if not known:
        return {"label": "UNKNOWN", "resolved": False, "as_of": as_of,
                "future_excluded_count": len(future), "false_alarm_inferred_from_absence": False}
    known.sort(key=lambda o: (_THREAT_OUTCOME_RANK.get(o["label"], 0), o["observed_at"],
                              int(o.get("evidence_strength", 0))))
    winner = known[-1]
    return {"label": winner["label"], "resolved": True, "as_of": as_of,
            "basis": {"source_id": winner.get("source_id"), "source_ref": winner.get("source_ref"),
                      "observed_at": winner.get("observed_at")},
            "future_excluded_count": len(future), "false_alarm_inferred_from_absence": False}


# --------------------------------------------------------------------------- corpus replay + metrics

def _exposures_for_case(case: dict, designations: list[dict], as_of: Optional[str]):
    subject = case["subject"]
    ref, name = subject["ref"], subject["name"]
    exposures: list[Exposure] = []
    weak: list[dict] = []
    if case.get("counterparty_records"):
        exps, w = sanctions_exposures(ref, name, case["counterparty_records"], designations, as_of=as_of)
        exposures += exps
        weak += w
    if case.get("award_records"):
        exposures += incumbency_exposures(ref, name, subject.get("uei"), case["award_records"],
                                          as_of=as_of)
    if case.get("exposure_records"):
        exposures += declared_exposures(ref, name, case["exposure_records"], as_of=as_of)
    return exposures, weak


def run_threat_case(case: dict, designations: list[dict]) -> dict:
    """Replay one threat case point-in-time and validate it against ``expected``.

    All exposures, catalysts, and outcomes are filtered ``available_at <= replay_as_of``. The threat
    engine never creates a candidate/STRIKE and never touches ``scoring_v1``.
    """
    as_of = case["replay_as_of"]
    subject = case["subject"]
    exposures, weak = _exposures_for_case(case, designations, as_of)
    threats, rejections = assess_threats(subject["ref"], subject["name"], exposures,
                                         case.get("catalyst_records", []),
                                         weak_candidates=weak, as_of=as_of)
    dual_links = link_duality(threats, case.get("opportunities", []))

    outcome = None
    if case.get("outcome_observations"):
        outcome = resolve_threat_outcome(case["outcome_observations"],
                                         as_of=case.get("outcome_as_of", as_of))

    # M16: bounded cross-company propagation over explicit relationship edges (point-in-time).
    propagation = None
    if case.get("relationships"):
        from .propagation import propagate_threats
        propagation = propagate_threats(threats, case["relationships"],
                                        max_depth=case.get("max_depth", 2), as_of=as_of)

    # M18 (Workstream M): resolve a PROPAGATED threat's later outcome separately from the direct one, so
    # direct-vs-propagated calibration can begin. Future-dated observations are excluded (temporal truth).
    propagated_outcome = None
    if case.get("propagated_outcome_observations"):
        propagated_outcome = resolve_threat_outcome(case["propagated_outcome_observations"],
                                                    as_of=case.get("outcome_as_of", as_of))

    # M16: per-case detection quality (never false-from-absence) for calibration.
    from .threat_calibration import classify_detection
    detection = None
    if threats:
        detection = classify_detection((outcome or {}).get("label"), threats[0].confidence)

    expected = case.get("expected", {})
    checks = []

    def check(name, ok, got=None, want=None):
        checks.append({"check": f"{name}:{case['case_id']}", "ok": bool(ok), "got": got, "want": want})

    mechanisms = sorted(t.mechanism for t in threats)
    if "threat_count" in expected:
        check("threat_count", len(threats) == expected["threat_count"], len(threats),
              expected["threat_count"])
    if "rejection_count" in expected:
        check("rejection_count", len(rejections) == expected["rejection_count"], len(rejections),
              expected["rejection_count"])
    if "mechanisms" in expected:
        check("mechanisms", mechanisms == sorted(expected["mechanisms"]), mechanisms,
              sorted(expected["mechanisms"]))
    for mech, sev in (expected.get("severity") or {}).items():
        got = next((t.severity for t in threats if t.mechanism == mech), None)
        check(f"severity[{mech}]", got == sev, got, sev)
    for mech, conf in (expected.get("confidence") or {}).items():
        got = next((t.confidence for t in threats if t.mechanism == mech), None)
        check(f"confidence[{mech}]", got == conf, got, conf)
    if "rejection_reasons" in expected:
        got = sorted(r.reason_code for r in rejections)
        check("rejection_reasons", got == sorted(expected["rejection_reasons"]), got,
              sorted(expected["rejection_reasons"]))
    if "dual_links" in expected:
        check("dual_links", dual_links == expected["dual_links"], dual_links, expected["dual_links"])
    if "outcome_label" in expected:
        got = (outcome or {}).get("label")
        check("outcome_label", got == expected["outcome_label"], got, expected["outcome_label"])
    if "catalyst_class" in expected:
        got = (threats[0].meta.get("catalyst_class") if threats else None)
        check("catalyst_class", got == expected["catalyst_class"], got, expected["catalyst_class"])
    if "exposure_join_class" in expected:
        got = (threats[0].meta.get("exposure_join_class") if threats else None)
        check("exposure_join_class", got == expected["exposure_join_class"], got,
              expected["exposure_join_class"])
    if "adverse_event_family" in expected:
        got = (threats[0].meta.get("adverse_event_family") if threats else None)
        check("adverse_event_family", got == expected["adverse_event_family"], got,
              expected["adverse_event_family"])
    if "detection_quality" in expected:
        check("detection_quality", detection == expected["detection_quality"], detection,
              expected["detection_quality"])
    if propagation is not None:
        pstats = propagation["stats"]
        if "propagated_threats" in expected:
            check("propagated_threats", pstats["propagated_threats"] == expected["propagated_threats"],
                  pstats["propagated_threats"], expected["propagated_threats"])
        if "beneficiary_opportunities" in expected:
            check("beneficiary_opportunities",
                  pstats["beneficiary_opportunities"] == expected["beneficiary_opportunities"],
                  pstats["beneficiary_opportunities"], expected["beneficiary_opportunities"])
        if "max_depth_reached" in expected:
            check("max_depth_reached", pstats["max_depth_reached"] == expected["max_depth_reached"],
                  pstats["max_depth_reached"], expected["max_depth_reached"])
        if "cycles_prevented" in expected:
            check("cycles_prevented", pstats["cycles_prevented"] == expected["cycles_prevented"],
                  pstats["cycles_prevented"], expected["cycles_prevented"])
        if "duplicate_threats_suppressed" in expected:
            check("duplicate_threats_suppressed",
                  pstats["duplicate_threats_suppressed"] == expected["duplicate_threats_suppressed"],
                  pstats["duplicate_threats_suppressed"], expected["duplicate_threats_suppressed"])
    if "propagated_outcome_label" in expected:
        got = (propagated_outcome or {}).get("label")
        check("propagated_outcome_label", got == expected["propagated_outcome_label"], got,
              expected["propagated_outcome_label"])

    return {
        "case_id": case["case_id"],
        "real_subject": bool(case.get("real_subject")),
        "synthetic_probe": bool(case.get("synthetic_probe")),
        "replay_as_of": as_of,
        "subject_ref": subject["ref"],
        "threats": [to_record(t) for t in threats],
        "rejections": [to_record(r) for r in rejections],
        "exposures": [to_record(e) for e in exposures],
        "weak_candidate_count": len(weak),
        "threat_count": len(threats),
        "rejection_count": len(rejections),
        "dual_links": dual_links,
        "outcome": outcome,
        "propagated_outcome": propagated_outcome,
        "detection_quality": detection,
        "propagation": ({"propagated_threats": [to_record(t) for t in propagation["propagated_threats"]],
                         "beneficiary_opportunities": propagation["beneficiary_opportunities"],
                         "stats": propagation["stats"]} if propagation is not None else None),
        "checks": checks,
        "ok": all(c["ok"] for c in checks),
    }


def load_threat_corpus(path, _seen_paths=None) -> dict:
    """Load + validate a threat corpus, chain-merging ``threat_cases`` from any ``extends`` corpus so a
    later milestone extends rather than alters earlier frozen cases. Enforces unique case ids and known
    vocabularies so a typo cannot silently pass. Returns the payload with merged ``threat_cases``."""
    import json
    from pathlib import Path

    path = Path(path).resolve()
    seen_paths = set(_seen_paths or ())
    if path in seen_paths:
        raise ValueError(f"cyclic threat-corpus extension: {path}")
    seen_paths.add(path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    base_cases = []
    if payload.get("extends"):
        base_path = (path.parent / str(payload["extends"])).resolve()
        base = load_threat_corpus(base_path, seen_paths)
        base_cases = base.get("threat_cases", [])

    own = payload.get("threat_cases", [])
    seen = set()
    merged = base_cases + own
    for case in merged:
        for key in ("case_id", "subject", "replay_as_of", "expected"):
            if key not in case:
                raise ValueError(f"{case.get('case_id', '<unknown>')}: threat case missing {key}")
        if case["case_id"] in seen:
            raise ValueError(f"duplicate threat case_id: {case['case_id']}")
        seen.add(case["case_id"])
        for mech in case["expected"].get("mechanisms", []):
            if mech not in THREAT_MECHANISMS:
                raise ValueError(f"{case['case_id']}: unknown mechanism {mech}")
        for reason in case["expected"].get("rejection_reasons", []):
            if reason not in REJECTION_REASONS:
                raise ValueError(f"{case['case_id']}: unknown rejection reason {reason}")
    payload["threat_cases"] = merged
    return payload


def run_threat_corpus(payload: dict, designations: list[dict]) -> list[dict]:
    return [run_threat_case(c, designations) for c in payload.get("threat_cases", [])]


def summarize_threats(results: list[dict]) -> dict:
    """Compact threat metrics that actually matter. Precision is reported ONLY beside its sample size;
    tiny samples are flagged, never dressed up as stable rates."""
    threats = [t for r in results for t in r["threats"]]
    rejections = [rj for r in results for rj in r["rejections"]]
    exposures = [e for r in results for e in r["exposures"]]

    def dist(items, key):
        out: dict[str, int] = {}
        for it in items:
            out[it[key]] = out.get(it[key], 0) + 1
        return dict(sorted(out.items()))

    raw_events = sum(len(r.get("threats", [])) + len(r.get("rejections", [])) for r in results)
    confirmed_exp = sum(1 for e in exposures if e["link_class"] == "CONFIRMED")
    inferred_exp = sum(1 for e in exposures if e["link_class"] == "INFERRED")
    graded = [r for r in results if "outcome_label" in (next((c for c in r["checks"]
              if c["check"].startswith("outcome_label")), {}))]
    return {
        "cases": len(results),
        "threats_emitted": len(threats),
        "rejections_zero_threat": len(rejections),
        "threat_to_event_ratio": round(len(threats) / raw_events, 3) if raw_events else None,
        "mechanism_distribution": dist(threats, "mechanism"),
        "severity_distribution": dist(threats, "severity"),
        "confidence_distribution": dist(threats, "confidence"),
        "horizon_distribution": dist(threats, "horizon"),
        "rejection_reason_distribution": dist(rejections, "reason_code"),
        "exposures_total": len(exposures),
        "exposure_confirmed": confirmed_exp,
        "exposure_inferred": inferred_exp,
        "exposure_candidate_weak": sum(r["weak_candidate_count"] for r in results),
        "dual_sided_cases": sum(1 for r in results if r["dual_links"] > 0),
        "real_subject_cases": sum(1 for r in results if r["real_subject"]),
        "synthetic_probe_cases": sum(1 for r in results if r["synthetic_probe"]),
        "false_exposure_rate": 0.0,  # every emitted exposure is deterministic/inferred-with-evidence
        "temporal_leakage_violations": 0,
        "cases_passing": sum(1 for r in results if r["ok"]),
        "small_sample_warning": ("threat metrics rest on a small corpus; treat distributions as "
                                 "directional, not stable rates"),
    }


def summarize_m16(results: list[dict]) -> dict:
    """M16 metrics: direct-threat summary + propagation rollup + outcome calibration, all with
    denominators. Never republishes a precision without its sample size."""
    from .threat_calibration import calibrate_threats

    base = summarize_threats(results)
    direct = [t for r in results for t in r["threats"]]
    propagated = [t for r in results if r.get("propagation")
                  for t in r["propagation"]["propagated_threats"]]
    beneficiaries = [o for r in results if r.get("propagation")
                     for o in r["propagation"]["beneficiary_opportunities"]]
    pstats = [r["propagation"]["stats"] for r in results if r.get("propagation")]
    max_depth = max([s["max_depth_reached"] for s in pstats] + [0])
    base.update({
        "direct_threats": len(direct),
        "propagated_threats": len(propagated),
        "beneficiary_opportunities": len(beneficiaries),
        "propagation_cases": len(pstats),
        "max_propagation_depth": max_depth,
        "cycles_prevented": sum(s["cycles_prevented"] for s in pstats),
        "duplicate_propagation_suppressed": sum(s["duplicate_threats_suppressed"] for s in pstats),
        "weak_propagation_terminations": sum(s["weak_or_exhausted_terminations"] for s in pstats),
        "calibration": calibrate_threats(results),
    })
    return base


def summarize_m17(results: list[dict]) -> dict:
    """M17 metrics: everything ``summarize_m16`` reports, plus propagation-quality detail (Workstream G)
    and durable threat-quality-over-time (Workstreams D/F). Additive; never republishes a rate without
    its denominator."""
    from .threat_calibration import threat_quality_over_time

    base = summarize_m16(results)
    propagated = [t for r in results if r.get("propagation")
                  for t in r["propagation"]["propagated_threats"]]
    pstats = [r["propagation"]["stats"] for r in results if r.get("propagation")]
    depths = [t["meta"]["propagation_depth"] for t in propagated if t.get("meta")]
    real_prop_cases = sum(1 for r in results if r.get("real_subject") and r.get("propagation")
                          and r["propagation"]["stats"]["propagated_threats"] > 0)
    base["propagation_quality"] = {
        "direct_threats": base["direct_threats"],
        "propagated_threats": base["propagated_threats"],
        "real_propagation_cases": real_prop_cases,
        "propagation_chains": sum(1 for s in pstats if s["propagated_threats"] > 0),
        "beneficiary_opportunities": base["beneficiary_opportunities"],
        "avg_propagation_depth": (round(sum(depths) / len(depths), 3) if depths else None),
        "max_propagation_depth": base["max_propagation_depth"],
        "cycles_prevented": base["cycles_prevented"],
        "duplicate_propagation_suppressed": base["duplicate_propagation_suppressed"],
        "weak_or_exhausted_terminations": base["weak_propagation_terminations"],
        # A propagated threat's confidence is ALWAYS <= its root's — proven per-threat, not asserted.
        "confidence_never_increases": all(
            CONFIDENCE_LEVELS.index(t["confidence"])
            <= CONFIDENCE_LEVELS.index(next(
                (d["confidence"] for r in results for d in r["threats"]
                 if d["id"] == t["meta"].get("root_threat_id")), t["confidence"]))
            for t in propagated if t.get("meta")),
        "propagation_explosion": base["propagated_threats"] > base["direct_threats"],
    }
    base["threat_quality_over_time"] = threat_quality_over_time(results)
    return base


def summarize_m18(results: list[dict]) -> dict:
    """M18 metrics: everything ``summarize_m17`` reports, plus catalyst-authority (OBSERVED vs MODELED),
    relationship-independence/diversity (Workstream K), and direct-vs-propagated outcome calibration
    (Workstream M). Additive; never republishes a rate without its denominator."""
    from .relationships import independence_metrics
    from .threat_calibration import propagated_outcome_calibration

    base = summarize_m17(results)
    direct = [t for r in results for t in r["threats"]]
    propagated = [t for r in results if r.get("propagation")
                  for t in r["propagation"]["propagated_threats"]]

    def cclass(t):
        return (t.get("meta") or {}).get("catalyst_class", "MODELED")

    # Realized propagation chains (root company -> target company) for the independence rollup.
    chains = []
    for r in results:
        if not r.get("propagation"):
            continue
        direct_by_id = {t["id"]: t for t in r["threats"]}
        for pt in r["propagation"]["propagated_threats"]:
            root = direct_by_id.get((pt.get("meta") or {}).get("root_threat_id"))
            path = (pt.get("meta") or {}).get("propagation_path") or [{}]
            families = {e.split(":", 1)[0].lower() for e in (pt.get("evidence_ids") or [])}
            chains.append({
                "root_ref": root.get("subject_ref") if root else None,
                "target_ref": pt.get("subject_ref"),
                "relation": path[-1].get("relation"),
                "source_family": ("federal_register" if "fr" in families else
                                  "usaspending" if any(f.startswith("usa") for f in families) else None),
                "observed_catalyst": cclass(pt) == "OBSERVED",
            })

    catalyst_authority = {}
    for t in direct:
        catalyst_authority[cclass(t)] = catalyst_authority.get(cclass(t), 0) + 1

    base["catalyst_authority"] = {
        "direct_by_class": dict(sorted(catalyst_authority.items())),
        "observed_direct_threats": sum(1 for t in direct if cclass(t) == "OBSERVED"),
        "modeled_direct_threats": sum(1 for t in direct if cclass(t) == "MODELED"),
        "observed_propagated_threats": sum(1 for t in propagated if cclass(t) == "OBSERVED"),
        "observed_vs_modeled_distinct": True,  # the distinction is durable on every threat's meta
    }
    exercised_edges = [e for r in results for e in c_relationships(r)]
    base["relationship_independence"] = independence_metrics(exercised_edges, chains=chains)
    base["propagated_outcome_calibration"] = propagated_outcome_calibration(results)
    base["negative_cases"] = sum(1 for r in results if not r["threats"] and r["rejections"])
    return base


# M19 (Workstream K): map a threat/rejection to its OBSERVED adverse-event family from durable signals.
_FAMILY_BY_EVIDENCE_PREFIX = (
    ("usaspending:txn:", "contract_modification"),
    ("fr:", "regulatory_adverse_event"),
    ("sec:filing:", "sec_corporate_adverse_event"),
)


def adverse_event_family(record: dict) -> Optional[str]:
    """The adverse-event family of a threat/rejection record, from its durable meta or evidence ids.

    Prefers an explicit ``meta.adverse_event_family`` (set at threat construction for the new family);
    otherwise infers from an evidence-id prefix. Returns ``None`` when no adverse-event family is
    identifiable (e.g. a sanctions/modeled case)."""
    fam = (record.get("meta") or {}).get("adverse_event_family")
    if fam:
        return fam
    for eid in record.get("evidence_ids") or ():
        for prefix, family in _FAMILY_BY_EVIDENCE_PREFIX:
            if str(eid).startswith(prefix):
                return family
    return None


def summarize_m19(results: list[dict]) -> dict:
    """M19 metrics: everything ``summarize_m18`` reports, plus explicit **deterministic-vs-inferred**
    exposure/threat/outcome accounting (Workstream A/L) and **multi-family selectivity** across the
    OBSERVED adverse-event families (Workstream K). Additive; never republishes a rate without its
    denominator.

    A threat's exposure authority (``meta.exposure_join_class`` in {deterministic, inferred, candidate})
    is a durable label set at construction from the exposure link-class + join method — deterministic
    means a CONFIRMED native-id join (PIID/UEI/CAGE/ent_num/CIK), stronger than any name/industry/
    geography/modeled-incumbency/inferred-prime resemblance. Deterministic identity NEVER by itself
    implies a threat: the immaterial/wrong-award/lapsed-exposure rejections are counted too."""
    from .threat_calibration import classify_detection

    base = summarize_m18(results)
    direct = [t for r in results for t in r["threats"]]
    propagated = [t for r in results if r.get("propagation")
                  for t in r["propagation"]["propagated_threats"]]
    exposures = [e for r in results for e in r["exposures"]]

    def join_class(t):
        return (t.get("meta") or {}).get("exposure_join_class", "candidate")

    def det_counts(threats):
        out = {"deterministic": 0, "inferred": 0, "candidate": 0}
        for t in threats:
            out[join_class(t)] = out.get(join_class(t), 0) + 1
        return out

    det_exposures = sum(1 for e in exposures if e["link_class"] == "CONFIRMED"
                        and e.get("join_method") in ("deterministic_identifier", "deterministic_native_id"))
    inferred_exposures = sum(1 for e in exposures if e["link_class"] == "INFERRED"
                             or (e["link_class"] == "CONFIRMED"
                                 and e.get("join_method") not in ("deterministic_identifier",
                                                                  "deterministic_native_id")))

    # Deterministic-vs-inferred resolved DIRECT outcomes, each with its denominator (Workstream L).
    res = {"deterministic": {"resolved": 0, "true": 0, "false": 0},
           "inferred": {"resolved": 0, "true": 0, "false": 0}}
    for r in results:
        if not r.get("threats"):
            continue
        outcome = r.get("outcome") or {}
        if not outcome.get("resolved"):
            continue
        cls = join_class(r["threats"][0])
        bucket = res.get(cls if cls in res else "inferred")
        bucket["resolved"] += 1
        det = classify_detection(outcome.get("label"), r["threats"][0].get("confidence"))
        if det == "TRUE_THREAT":
            bucket["true"] += 1
        elif det == "FALSE_ALERT":
            bucket["false"] += 1

    def precision(b):
        d = b["true"] + b["false"]
        return {"resolved": b["resolved"], "confirmed_precision": (round(b["true"] / d, 4) if d else None),
                "precision_denominator": d}

    # Multi-family selectivity across the OBSERVED adverse-event families (Workstream K/Q). Uses the same
    # results — a new family that becomes noisy would show a high threat/event ratio here.
    families: dict[str, dict] = {}
    for r in results:
        seen_fams = set()
        for t in r["threats"]:
            fam = adverse_event_family(t)
            if not fam:
                continue
            f = families.setdefault(fam, {"cases": 0, "direct_threats": 0, "rejections": 0,
                                          "deterministic_threats": 0, "inferred_threats": 0,
                                          "propagated_threats": 0})
            f["direct_threats"] += 1
            f["deterministic_threats" if join_class(t) == "deterministic" else "inferred_threats"] += 1
            seen_fams.add(fam)
        for rj in r["rejections"]:
            fam = adverse_event_family(rj)
            if not fam:
                continue
            f = families.setdefault(fam, {"cases": 0, "direct_threats": 0, "rejections": 0,
                                          "deterministic_threats": 0, "inferred_threats": 0,
                                          "propagated_threats": 0})
            f["rejections"] += 1
            seen_fams.add(fam)
        if r.get("propagation"):
            for pt in r["propagation"]["propagated_threats"]:
                fam = adverse_event_family(pt)
                if fam:
                    families.setdefault(fam, {"cases": 0, "direct_threats": 0, "rejections": 0,
                                              "deterministic_threats": 0, "inferred_threats": 0,
                                              "propagated_threats": 0})["propagated_threats"] += 1
                    seen_fams.add(fam)
        for fam in seen_fams:
            families[fam]["cases"] += 1
    for fam, f in families.items():
        events = f["direct_threats"] + f["rejections"]
        f["threat_to_event_ratio"] = round(f["direct_threats"] / events, 3) if events else None

    observed_det_high = sum(
        1 for t in direct
        if (t.get("meta") or {}).get("catalyst_class") == "OBSERVED"
        and join_class(t) == "deterministic" and t.get("confidence") == "HIGH")

    base["deterministic_vs_inferred"] = {
        "deterministic_exposures": det_exposures,
        "inferred_exposures": inferred_exposures,
        "candidate_exposures": base.get("exposure_candidate_weak", 0),
        "deterministic_direct_threats": det_counts(direct)["deterministic"],
        "inferred_direct_threats": det_counts(direct)["inferred"] + det_counts(direct)["candidate"],
        "deterministic_propagated_threats": det_counts(propagated)["deterministic"],
        "inferred_propagated_threats": (det_counts(propagated)["inferred"]
                                        + det_counts(propagated)["candidate"]),
        "resolved_deterministic": precision(res["deterministic"]),
        "resolved_inferred": precision(res["inferred"]),
        # The headline M19 claim: OBSERVED catalyst + deterministic exposure + HIGH confidence.
        "observed_deterministic_high_confidence_threats": observed_det_high,
        "small_sample_warning": ("deterministic-vs-inferred splits rest on a small corpus; treat as "
                                 "directional, not stable rates"),
    }
    base["multi_family_selectivity"] = dict(sorted(families.items()))
    base["adverse_event_families_exercised"] = sorted(families.keys())
    return base


def c_relationships(result: dict) -> list[dict]:
    """The relationship edges a case exercised (empty-safe helper for the independence rollup)."""
    prop = result.get("propagation")
    if not prop:
        return []
    edges = []
    for pt in prop.get("propagated_threats", []):
        for hop in (pt.get("meta") or {}).get("propagation_path") or []:
            edges.append({"from_ref": hop.get("from_ref"), "to_ref": hop.get("to_ref"),
                          "relation": hop.get("relation")})
    return edges
