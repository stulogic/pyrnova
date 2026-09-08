"""Deterministic cross-source linking for commercial context and precursors."""

from __future__ import annotations

import re
from datetime import date

from .models import EvidenceAssessment, Event, Opportunity, Relationship

EVIDENCE_STRENGTH = {
    1: "weak_topical_similarity",
    2: "agency_sector_context",
    3: "named_organizational_program_relationship",
    4: "direct_contracting_budget_award",
    5: "direct_causal_program_evidence",
}

_STOP = {
    "and", "department", "dept", "office", "agency", "administration", "the", "of", "for",
    "services", "service", "support", "united", "states", "federal", "notice", "rule",
    "command", "contracting", "materiel",
}
_CONTRA_TERMS = {"cancel", "cancelled", "cancellation", "delay", "delayed", "rescission", "withdraw", "withdrawn"}


def _tokens(value: str | None) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", (value or "").lower())
        if len(token) > 2 and token not in _STOP
    }


def _agency_related(left: str | None, right: str | None) -> bool:
    return bool(_tokens(left) & _tokens(right))


def related_awards(
    opp: Opportunity,
    awards: list[dict],
    *,
    recipient_names: list[str] | None = None,
    limit: int = 3,
) -> list[dict]:
    """Return buyer+classification or buyer+topic matches, newest/highest-value first."""
    matches = []
    opp_terms = _tokens(" ".join([opp.title, opp.catalyst.summary]))
    target_tokens = [_tokens(name) for name in (recipient_names or [])]
    for award in awards:
        same_code = bool(
            (opp.naics and award.get("naics") and opp.naics == award["naics"])
            or (opp.psc and award.get("psc") and opp.psc == award["psc"])
        )
        topic_match = bool(opp_terms & _tokens(award.get("description")))
        recipient = _tokens(award.get("recipient_name"))
        target_history = any(tokens and tokens <= recipient for tokens in target_tokens)
        award_buyer = " ".join(filter(None, [award.get("agency"), award.get("sub_agency")]))
        if (same_code or topic_match or target_history) and _agency_related(opp.agency, award_buyer):
            matches.append(award)
    matches.sort(key=lambda a: (a.get("end_date") or date.min, a.get("amount") or 0), reverse=True)
    return matches[:limit]


def related_precursors(
    opp: Opportunity, precursors: list[dict], *, limit: int = 2
) -> list[tuple[dict, str, int, str]]:
    """Link agency-aligned Federal Register documents with explicit topical overlap."""
    opp_terms = _tokens(" ".join([opp.title, opp.catalyst.summary, opp.naics or "", opp.psc or ""]))
    matches: list[tuple[dict, str, int]] = []
    for precursor in precursors:
        agency_text = " ".join(precursor.get("agency_names") or [])
        text = " ".join(
            str(precursor.get(k) or "") for k in ("title", "abstract", "search_excerpt", "action")
        )
        if not _agency_related(opp.agency, agency_text) or not (opp_terms & _tokens(text)):
            continue
        role = "contra" if _CONTRA_TERMS & _tokens(text) else "supporting"
        title_score = len((_tokens(opp.title) | _tokens(opp.agency)) & _tokens(precursor.get("title")))
        matches.append((precursor, role, title_score))
    matches.sort(
        key=lambda item: (item[2], item[0].get("publication_date") or date.min), reverse=True
    )
    return [
        (
            precursor,
            role,
            2 if score >= 2 else 1,
            "agency plus title-level topic overlap" if score >= 2 else "agency plus weak topical similarity",
        )
        for precursor, role, score in matches[:limit]
    ]


def connect_event(
    opp: Opportunity,
    event: Event,
    *,
    evidence_id: str,
    predicate: str,
    role: str,
    strength: int,
    basis: str,
) -> None:
    if strength not in EVIDENCE_STRENGTH:
        raise ValueError("evidence strength must be between 1 and 5")
    opp.events.append(event)
    opp.evidence_roles[evidence_id] = role
    opp.evidence_assessments.append(
        EvidenceAssessment(
            evidence_id=evidence_id,
            strength=strength,
            strength_class=EVIDENCE_STRENGTH[strength],
            polarity="contradictory" if role == "contra" else "supporting",
            basis=basis,
        )
    )
    opp.relationships.append(
        Relationship(
            subject_id=opp.id,
            predicate=predicate,
            object_id=event.id,
            evidence_ids=[evidence_id],
            meta={
                "role": role,
                "strength": strength,
                "strength_class": EVIDENCE_STRENGTH[strength],
                "basis": basis,
            },
        )
    )
