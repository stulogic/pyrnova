"""Cross-source capital-chain resolution (M5).

Connects apparently separate source signals into a single economic story **only** on evidence:
explicit shared program identity, or an authoritative native-identifier crosswalk. A conservative
inferred path is available for a strong structured-attribute match; everything weaker
(agency-name-only, topic overlap, chronological proximity) is explicitly *rejected* and counted, never
materialized as a relationship.

Relationships preserve time: a relationship becomes knowable only when its later endpoint is
observed, so replay can answer "when could we first have known this relationship?". This module is
pure with respect to scoring — it never creates a candidate, never promotes a disposition, and never
changes scoring_v1.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .models import Relationship
from .precursors import PRECURSOR_STAGES, ProgramSignal

CHAIN_RESOLUTION_VERSION = "chain_resolution_v1"

_STAGE_ORDER = {stage: index for index, stage in enumerate(PRECURSOR_STAGES)}

# Typed predicate for an edge from an earlier-stage precursor to a later-stage successor of the same
# program. Pairs not listed fall back to the temporal backbone predicate PRECEDES. Each predicate is
# justified by an actual stage transition, not by topic.
PREDICATE_BY_STAGE_PAIR = {
    ("INTENT", "AUTHORIZATION"): "PRECEDES",
    ("AUTHORIZATION", "FUNDING"): "AUTHORIZES",
    ("FUNDING", "PROGRAM"): "FUNDS",
    ("FUNDING", "MARKET_ENGAGEMENT"): "FUNDS",
    ("FUNDING", "PROCUREMENT"): "FUNDS",
    ("PROGRAM", "MARKET_ENGAGEMENT"): "IMPLEMENTS",
    ("PROGRAM", "PROCUREMENT"): "IMPLEMENTS",
    ("MARKET_ENGAGEMENT", "PROCUREMENT"): "PRECEDES",
    ("PROCUREMENT", "AWARD"): "PRECEDES",
    ("AWARD", "OUTCOME"): "PRECEDES",
}

DETERMINISTIC_METHODS = {"deterministic_program_key", "deterministic_native_id"}
_DETERMINISTIC_CONFIDENCE = 0.95
_CORROBORATION_CONFIDENCE = 0.90
_INFERRED_CONFIDENCE = 0.60

_CONTRA_TERMS = {
    "cancel", "cancelled", "cancellation", "canceled", "withdraw", "withdrawn", "rescission",
    "rescinded", "terminated", "termination", "deobligated",
}

# Generic organizational words that must never make two different agencies look identical.
_AGENCY_STOP = {
    "the", "and", "for", "department", "dept", "office", "agency", "administration", "bureau",
    "command", "division", "federal", "national", "united", "states", "government", "service",
    "services",
}


def _tokens(value: str | None) -> set[str]:
    return {t for t in "".join(c.lower() if c.isalnum() else " " for c in (value or "")).split() if len(t) > 2}


def _same_agency(left: str | None, right: str | None) -> bool:
    return bool((_tokens(left) - _AGENCY_STOP) & (_tokens(right) - _AGENCY_STOP))


def _is_contradiction(signal: ProgramSignal) -> bool:
    if signal.meta.get("contradicts"):
        return True
    return bool(_CONTRA_TERMS & {t for t in signal.summary.lower().split()})


def _edge_id(subject_id: str, predicate: str, object_id: str) -> str:
    basis = f"{CHAIN_RESOLUTION_VERSION}|{subject_id}|{predicate}|{object_id}".encode("utf-8")
    return hashlib.sha256(basis).hexdigest()[:24]


def _later(a: str | None, b: str | None) -> str | None:
    """Return the later of two ISO timestamps; None only if both are unknown."""
    known = [t for t in (a, b) if t]
    return max(known) if known else None


@dataclass(frozen=True)
class RejectedJoin:
    """A candidate cross-program link that failed the evidence bar and was not materialized."""

    left_id: str
    right_id: str
    reason: str            # agency_name_only | topic_overlap_only | chronological_proximity_only
    detail: str = ""


@dataclass(frozen=True)
class ChainResolution:
    signals: tuple[ProgramSignal, ...]
    relationships: tuple[Relationship, ...]
    rejected: tuple[RejectedJoin, ...]
    duplicates_collapsed: int
    confidence: dict = field(default_factory=dict)

    @property
    def program_keys(self) -> tuple[str, ...]:
        return tuple(sorted({s.program_key for s in self.signals}))

    @property
    def stages_present(self) -> tuple[str, ...]:
        return tuple(s for s in PRECURSOR_STAGES if s in {sig.stage for sig in self.signals})

    def metrics(self) -> dict:
        deterministic = [r for r in self.relationships if r.join_method in DETERMINISTIC_METHODS]
        inferred = [r for r in self.relationships if r.join_method == "inferred_strong_attribute"]
        return {
            "chain_resolution_version": CHAIN_RESOLUTION_VERSION,
            "signals_in": len(self.signals) + self.duplicates_collapsed,
            "unique_signals": len(self.signals),
            "duplicates_collapsed": self.duplicates_collapsed,
            "relationships_total": len(self.relationships),
            "deterministic_relationships": len(deterministic),
            "inferred_relationships": len(inferred),
            "corroborations": sum(r.predicate == "CORROBORATES" for r in self.relationships),
            "contradictions": sum(r.predicate == "CONTRADICTS" for r in self.relationships),
            "rejected_weak_joins": len(self.rejected),
            "distinct_sources": len({s.source_id for s in self.signals}),
            "program_keys": list(self.program_keys),
            "stages_present": list(self.stages_present),
            "is_partial": len(self.stages_present) < len(PRECURSOR_STAGES),
            "chain_confidence": self.confidence,
        }


def signals_from_records(records: list[dict], *, as_of: str | None = None) -> list[ProgramSignal]:
    """Build ProgramSignals from replay-shaped records that carry explicit program identity.

    Records without a program_key or a known stage are skipped (they cannot join deterministically).
    When ``as_of`` is given, only records knowable at that cutoff are used (point-in-time).
    """
    signals: list[ProgramSignal] = []
    for record in records:
        stage, program_key = record.get("stage"), record.get("program_key")
        if not program_key or stage not in _STAGE_ORDER:
            continue
        available_at = record.get("available_at")
        if as_of is not None and (not available_at or available_at > as_of):
            continue
        signals.append(ProgramSignal(
            source_id=record["source_id"],
            source_ref=record["source_ref"],
            stage=stage,
            program_key=program_key,
            summary=record.get("summary") or record.get("record_kind") or record["source_ref"],
            available_at=available_at,
            agency=record.get("agency"),
            downstream_refs=tuple(record.get("downstream_refs") or ()),
            confidence=str(record.get("confidence") or "UNKNOWN"),
            meta={
                "record_kind": record.get("record_kind"),
                "program_identifier": record.get("program_identifier"),
                "contradicts": bool(record.get("contradicts")),
            },
        ))
    return signals


def _predicate(precursor: ProgramSignal, successor: ProgramSignal) -> str:
    return PREDICATE_BY_STAGE_PAIR.get((precursor.stage, successor.stage), "PRECEDES")


def _relationship(precursor: ProgramSignal, successor: ProgramSignal, *, predicate: str,
                  join_method: str, confidence: float, rationale: str,
                  evidence_by_signal_id: dict[str, str]) -> Relationship:
    knowable = _later(precursor.available_at, successor.available_at)
    evidence_ids = [e for e in (evidence_by_signal_id.get(precursor.id), evidence_by_signal_id.get(successor.id)) if e]
    rel = Relationship(
        subject_id=precursor.id,
        predicate=predicate,
        object_id=successor.id,
        evidence_ids=evidence_ids,
        join_method=join_method,
        confidence=confidence,
        rationale=rationale,
        first_observed_at=knowable,
        available_at=knowable,
        meta={
            "subject_source": f"{precursor.source_id}:{precursor.source_ref}",
            "object_source": f"{successor.source_id}:{successor.source_ref}",
            "subject_stage": precursor.stage,
            "object_stage": successor.stage,
            "program_key": successor.program_key if precursor.program_key == successor.program_key else None,
        },
    )
    rel.id = _edge_id(precursor.id, predicate, successor.id)
    return rel


def _chain_confidence(signals: list[ProgramSignal], relationships: list[Relationship]) -> dict:
    linking = [r for r in relationships if r.predicate != "CONTRADICTS"]
    contradicted = any(r.predicate == "CONTRADICTS" for r in relationships)
    distinct_sources = len({s.source_id for s in signals})
    basis: list[str] = []
    if not linking:
        return {"value": 0.0, "basis": ["no evidence-backed link"], "contradicted": contradicted,
                "source_independence": distinct_sources, "temporal_consistent": True}
    min_link = min(r.confidence for r in linking)
    value = min_link
    basis.append(f"weakest link confidence {min_link:.2f}")
    # A single source cannot corroborate itself across stages.
    if distinct_sources < 2:
        value = min(value, 0.70)
        basis.append("single-source chain capped at 0.70")
    else:
        basis.append(f"{distinct_sources} independent sources")
    # Temporal plausibility: every edge must run forward in knowable time.
    temporal_consistent = True
    for rel in linking:
        subj = next((s for s in signals if s.id == rel.subject_id), None)
        obj = next((s for s in signals if s.id == rel.object_id), None)
        if subj and obj and subj.available_at and obj.available_at and subj.available_at > obj.available_at:
            temporal_consistent = False
    if not temporal_consistent:
        value *= 0.5
        basis.append("penalized: an edge runs backward in time")
    if contradicted:
        value = min(value, 0.30)
        basis.append("penalized: contradiction present")
    return {
        "value": round(value, 3),
        "min_link_confidence": round(min_link, 3),
        "source_independence": distinct_sources,
        "temporal_consistent": temporal_consistent,
        "contradicted": contradicted,
        "basis": basis,
    }


def resolve_chain(
    signals: list[ProgramSignal],
    *,
    as_of: str | None = None,
    evidence_by_signal_id: dict[str, str] | None = None,
    allow_inferred: bool = True,
) -> ChainResolution:
    """Resolve typed, temporal, evidence-backed relationships among source signals.

    Join hierarchy (strongest first): shared explicit program_key, authoritative native-identifier
    crosswalk, then a conservative strong-attribute inference. Weaker matches are rejected, not linked.
    """
    evidence_by_signal_id = evidence_by_signal_id or {}
    # Point-in-time filter and duplicate collapse by source-native stage identity.
    if as_of is not None:
        signals = [s for s in signals if s.available_at and s.available_at <= as_of]
    unique: dict[str, ProgramSignal] = {}
    for signal in signals:
        unique.setdefault(signal.id, signal)
    duplicates_collapsed = len(signals) - len(unique)
    ordered = sorted(
        unique.values(),
        key=lambda s: (_STAGE_ORDER[s.stage], s.available_at or "", s.source_id, s.source_ref),
    )

    relationships: list[Relationship] = []
    seen_pairs: set[tuple[str, str]] = set()

    def add(precursor, successor, *, predicate, join_method, confidence, rationale):
        key = (precursor.id, successor.id)
        if key in seen_pairs:
            return
        seen_pairs.add(key)
        relationships.append(_relationship(
            precursor, successor, predicate=predicate, join_method=join_method,
            confidence=confidence, rationale=rationale, evidence_by_signal_id=evidence_by_signal_id,
        ))

    # 1) Deterministic program-key chains: representative (earliest) signal per (program, stage).
    by_program: dict[str, list[ProgramSignal]] = {}
    for signal in ordered:
        by_program.setdefault(signal.program_key, []).append(signal)
    for program_key, group in sorted(by_program.items()):
        rep_by_stage: dict[str, ProgramSignal] = {}
        for signal in group:
            rep_by_stage.setdefault(signal.stage, signal)  # ordered => earliest wins
        occupied = [s for s in PRECURSOR_STAGES if s in rep_by_stage]
        for earlier, later in zip(occupied, occupied[1:]):
            precursor, successor = rep_by_stage[earlier], rep_by_stage[later]
            if _is_contradiction(successor):
                add(precursor, successor, predicate="CONTRADICTS", join_method="deterministic_program_key",
                    confidence=_DETERMINISTIC_CONFIDENCE,
                    rationale=f"explicit shared program_key {program_key!r}; successor records reversal")
            else:
                add(precursor, successor, predicate=_predicate(precursor, successor),
                    join_method="deterministic_program_key", confidence=_DETERMINISTIC_CONFIDENCE,
                    rationale=f"explicit shared program_key {program_key!r}")
        # Corroboration: independent sources reporting the same program+stage.
        for stage, rep in rep_by_stage.items():
            peers = [s for s in group if s.stage == stage and s.id != rep.id and s.source_id != rep.source_id]
            for peer in peers:
                add(rep, peer, predicate="CORROBORATES", join_method="deterministic_program_key",
                    confidence=_CORROBORATION_CONFIDENCE,
                    rationale=f"independent source corroborates program {program_key!r} at {stage}")

    # 2) Deterministic native-identifier crosswalk (works across program keys).
    by_ref = {s.source_ref: s for s in ordered}
    for signal in ordered:
        for ref in signal.downstream_refs:
            target = by_ref.get(ref)
            if not target or target.id == signal.id:
                continue
            precursor, successor = sorted((signal, target), key=lambda s: (_STAGE_ORDER[s.stage], s.available_at or ""))
            add(precursor, successor, predicate=_predicate(precursor, successor),
                join_method="deterministic_native_id", confidence=_DETERMINISTIC_CONFIDENCE,
                rationale=f"authoritative native-identifier crosswalk via {ref!r}")

    # 3) Conservative inference / explicit rejection for un-linked cross-program pairs.
    linked = seen_pairs | {(b, a) for a, b in seen_pairs}
    rejected: list[RejectedJoin] = []
    for i, left in enumerate(ordered):
        for right in ordered[i + 1:]:
            if left.program_key == right.program_key:
                continue
            if (left.id, right.id) in linked:
                continue
            shared_id = _shared_program_identifier(left, right)
            same_agency = _same_agency(left.agency, right.agency)
            if allow_inferred and shared_id and same_agency:
                precursor, successor = sorted((left, right), key=lambda s: (_STAGE_ORDER[s.stage], s.available_at or ""))
                add(precursor, successor, predicate=_predicate(precursor, successor),
                    join_method="inferred_strong_attribute", confidence=_INFERRED_CONFIDENCE,
                    rationale=f"shared structured program identifier {shared_id!r} and matching agency")
                continue
            # Everything below is too weak to be a relationship — record why it was rejected.
            if same_agency and _tokens(left.summary) & _tokens(right.summary):
                rejected.append(RejectedJoin(left.id, right.id, "agency_name_only",
                                             "same agency and topical overlap, but no shared identifier"))
            elif _tokens(left.summary) & _tokens(right.summary):
                rejected.append(RejectedJoin(left.id, right.id, "topic_overlap_only",
                                             "topical token overlap without identifier or agency match"))
            elif same_agency:
                rejected.append(RejectedJoin(left.id, right.id, "agency_name_only",
                                             "same agency without any shared identifier"))

    confidence = _chain_confidence(list(unique.values()), relationships)
    return ChainResolution(
        signals=tuple(ordered),
        relationships=tuple(relationships),
        rejected=tuple(rejected),
        duplicates_collapsed=duplicates_collapsed,
        confidence=confidence,
    )


def _shared_program_identifier(left: ProgramSignal, right: ProgramSignal) -> str | None:
    """Return a shared *explicit* structured program identifier, else None.

    Inference is deliberately narrow: it requires an authoritative ``program_identifier`` (e.g. a CFDA
    number or an official program code) present and equal on both signals. Program-key text tokens,
    agency names, topic words, and bare years never qualify — those paths are rejected, not inferred.
    """
    left_id, right_id = left.meta.get("program_identifier"), right.meta.get("program_identifier")
    if left_id and right_id and str(left_id).strip().lower() == str(right_id).strip().lower():
        return str(left_id).strip().lower()
    return None
