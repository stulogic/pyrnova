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
                meta={"ofac_program": target.get("program"), "counterparty_relation": relation},
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
                  if k in ("agency", "certification", "geography", "revenue_share")},
        )
        exp.id = exposure_id(subject_ref, relation, str(rec["target_ref"]))
        exposures.append(exp)
    return exposures


def persist_exposures(store, exposures) -> None:
    for exp in exposures:
        store.append("exposures", to_record(exp))
