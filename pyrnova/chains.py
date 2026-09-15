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
from .lineage import (
    LINEAGE_PREDICATES,
    ProcurementLineageResolution,
    resolve_procurement_lineage,
)
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

# Inferred-join calibration (M6). The *acceptance* threshold is frozen at 0.60 (see 04-DECISIONS
# D-015). M6 refines the inferred path from a rubber-stamp into a weighted, explainable model whose
# computed confidence must actually clear that gate. An "anchor" is an authoritative structured
# identity (shared program identifier, matching entity UEI, or a specific program-number fragment);
# without an anchor a pair is capped below the threshold, so agency + topic + chronology +
# name-similarity can never combine into an accepted join (STRICT INFERENCE RULES 1-4). Pairs that
# clear the DEFER floor but not the accept threshold are queued for human review, not linked.
_INFERRED_ACCEPT_THRESHOLD = 0.60
_INFERRED_DEFER_FLOOR = 0.45
_NO_ANCHOR_CONFIDENCE_CAP = 0.55  # below the accept threshold, by construction

# Entity-level predicates (M6) established only from authoritative structured fields on a record.
ENTITY_PREDICATES = {"AWARDED_TO", "SUBSIDIARY_OF", "LOCATED_AT"}
_ENTITY_FIELD_CONFIDENCE = 0.95

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
    reason: str            # agency_name_only | topic_overlap_only | inference_below_threshold |
                           # inference_contradiction
    detail: str = ""


@dataclass(frozen=True)
class DeferredJoin:
    """An anchored inferred link whose confidence lands in the ambiguous review band.

    It is neither materialized nor discarded: it is handed to the human review queue with its full
    scored rationale so a reviewer's disposition becomes durable calibration evidence.
    """

    left_id: str
    right_id: str
    subject_id: str
    object_id: str
    predicate: str
    confidence: float
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    first_observed_at: str | None = None
    automated_recommendation: str = "DEFER"

    @property
    def relationship_id(self) -> str:
        return _edge_id(self.subject_id, self.predicate, self.object_id)

    def to_queue_record(self) -> dict:
        return {
            "relationship_id": self.relationship_id,
            "left_id": self.left_id,
            "right_id": self.right_id,
            "subject_id": self.subject_id,
            "object_id": self.object_id,
            "predicate": self.predicate,
            "pre_review_confidence": self.confidence,
            "join_method": "inferred_strong_attribute",
            "automated_recommendation": self.automated_recommendation,
            "rationale": self.rationale,
            "evidence_ids": list(self.evidence_ids),
            "first_observed_at": self.first_observed_at,
        }


@dataclass(frozen=True)
class InferenceScore:
    """Explainable, deterministic scoring of one candidate inferred join."""

    confidence: float
    anchored: bool
    disposition: str                 # accept | defer | reject
    factors: tuple[tuple[str, float], ...]
    penalties: tuple[tuple[str, float], ...]
    anchors: tuple[str, ...]
    reject_reason: str | None = None

    @property
    def rationale(self) -> str:
        pos = "; ".join(f"+{name} {weight:+.2f}" for name, weight in self.factors) or "no positive factors"
        neg = "; ".join(f"{name} {weight:+.2f}" for name, weight in self.penalties)
        anchor = f"anchors=[{', '.join(self.anchors)}]" if self.anchors else "no structured anchor"
        parts = [f"inferred confidence {self.confidence:.2f}", anchor, pos]
        if neg:
            parts.append(f"penalties: {neg}")
        return " | ".join(parts)


@dataclass(frozen=True)
class ChainResolution:
    signals: tuple[ProgramSignal, ...]
    relationships: tuple[Relationship, ...]
    rejected: tuple[RejectedJoin, ...]
    duplicates_collapsed: int
    confidence: dict = field(default_factory=dict)
    deferred: tuple[DeferredJoin, ...] = ()
    entity_relationships: tuple[Relationship, ...] = ()
    inference_scores: tuple[InferenceScore, ...] = ()  # every anchored candidate pair, for calibration
    lineage: ProcurementLineageResolution | None = None  # B2.1 intra-stage procurement lineage

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
            "deferred_joins": len(self.deferred),
            "corroborations": sum(r.predicate == "CORROBORATES" for r in self.relationships),
            "contradictions": sum(r.predicate == "CONTRADICTS" for r in self.relationships),
            "rejected_weak_joins": len(self.rejected),
            "entity_relationships": len(self.entity_relationships),
            "entity_predicates": sorted({r.predicate for r in self.entity_relationships}),
            "distinct_sources": len({s.source_id for s in self.signals}),
            "program_keys": list(self.program_keys),
            "stages_present": list(self.stages_present),
            "is_partial": len(self.stages_present) < len(PRECURSOR_STAGES),
            "chain_confidence": self.confidence,
            "lineage": self.lineage.metrics() if self.lineage else {
                "lineage_relationships": 0, "procurement_instances": 0,
                "cancelled_instances": 0, "live_instances": 0, "lineage_predicates": [],
            },
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
            geography=record.get("geography") or record.get("place_of_performance"),
            downstream_refs=tuple(record.get("downstream_refs") or ()),
            confidence=str(record.get("confidence") or "UNKNOWN"),
            meta={
                "record_kind": record.get("record_kind"),
                "program_identifier": record.get("program_identifier"),
                "contradicts": bool(record.get("contradicts")),
                "amount_usd": record.get("amount_usd"),
                "entity_uei": record.get("recipient_uei") or record.get("entity_uei"),
                "parent_uei": record.get("parent_uei"),
                "entity_name": record.get("recipient") or record.get("entity_name"),
                "place_of_performance": record.get("place_of_performance"),
                # B2.1 intra-stage procurement lineage anchors (all optional; absence => no lineage).
                "procurement_id": record.get("procurement_id") or record.get("solicitation_number"),
                "notice_type": record.get("notice_type"),
                "prior_procurement_id": record.get("prior_procurement_id"),
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


def _lineage_consequence(confidence: dict, lineage: ProcurementLineageResolution | None) -> dict:
    """Fold intra-stage cancellation consequence into chain confidence (B2.1).

    A program whose CURRENT procurement instance is not live (cancelled, and not restarted by a later
    reissue) is a contradicted, not-live pursuit even when the cross-stage backbone is otherwise strong.
    A reissue restarts liveness, so an all-time view with a live successor is not penalised — the
    consequence tracks the current competition, not the fact that a cancellation ever occurred.
    """
    if lineage is None or not lineage.instances:
        confidence.setdefault("procurement_live", None)
        return confidence
    dead = sorted({i.program_key for i in lineage.instances
                   if (cur := lineage.current_instance(i.program_key)) and not cur.live})
    confidence["procurement_live"] = not dead
    if dead:
        confidence["value"] = round(min(confidence.get("value", 0.0), 0.30), 3)
        confidence["contradicted"] = True
        confidence["not_live_programs"] = dead
        confidence.setdefault("basis", []).append(
            f"penalized: current procurement not live for {', '.join(dead)}")
    return confidence


def _chain_confidence(signals: list[ProgramSignal], relationships: list[Relationship],
                      lineage: ProcurementLineageResolution | None = None) -> dict:
    # Backward-pointing intra-stage lineage edges are not forward chain links; exclude them from the
    # backbone's weakest-link and temporal-consistency computation (their consequence is applied below).
    linking = [r for r in relationships
               if r.predicate != "CONTRADICTS" and r.predicate not in LINEAGE_PREDICATES]
    contradicted = any(r.predicate == "CONTRADICTS" for r in relationships)
    distinct_sources = len({s.source_id for s in signals})
    basis: list[str] = []
    if not linking:
        return _lineage_consequence(
            {"value": 0.0, "basis": ["no evidence-backed link"], "contradicted": contradicted,
             "source_independence": distinct_sources, "temporal_consistent": True},
            lineage)
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
    return _lineage_consequence({
        "value": round(value, 3),
        "min_link_confidence": round(min_link, 3),
        "source_independence": distinct_sources,
        "temporal_consistent": temporal_consistent,
        "contradicted": contradicted,
        "basis": basis,
    }, lineage)


def _norm_text(value: str | None) -> str | None:
    text = " ".join(str(value or "").split()).casefold()
    return text or None


def _significant_tokens(*values: str | None) -> set[str]:
    """Specific alphanumeric identifier tokens (len>=6 containing a digit) usable as a shared
    program/solicitation-number fragment. Short, generic, and bare-year tokens are excluded."""
    out: set[str] = set()
    for value in values:
        for raw in "".join(c if c.isalnum() else " " for c in str(value or "")).split():
            token = raw.upper()
            if len(token) >= 6 and any(ch.isdigit() for ch in token):
                out.add(token)
    return out


def score_inferred_join(left: ProgramSignal, right: ProgramSignal) -> InferenceScore:
    """Deterministically score a candidate inferred join from weighted structured evidence.

    An "anchor" is authoritative structured identity: a shared explicit program identifier, matching
    entity UEI, or a shared specific program/solicitation-number fragment. Without an anchor the
    confidence is capped below the acceptance threshold, so agency + topic + chronology + name
    similarity can never combine into an accepted join. Contradictions (agency conflict, temporal
    impossibility, geographic/funding divergence) subtract and can invalidate an otherwise anchored
    pair. The result is explainable: every factor and penalty is retained.
    """
    factors: list[tuple[str, float]] = []
    penalties: list[tuple[str, float]] = []
    anchors: list[str] = []

    # --- Anchors (authoritative structured identity) ---
    lu, ru = left.meta.get("entity_uei"), right.meta.get("entity_uei")
    if lu and ru and str(lu).strip().upper() == str(ru).strip().upper():
        factors.append(("authoritative_entity_match", 0.45))
        anchors.append(f"entity_uei:{str(lu).strip().upper()}")

    shared_id = _shared_program_identifier(left, right)
    if shared_id:
        factors.append(("shared_program_identifier", 0.45))
        anchors.append(f"program_identifier:{shared_id}")

    shared_fragment = _significant_tokens(left.source_ref, left.meta.get("program_identifier")) & \
        _significant_tokens(right.source_ref, right.meta.get("program_identifier"))
    if shared_fragment and not shared_id:
        factors.append(("program_number_fragment", 0.25))
        anchors.append(f"fragment:{sorted(shared_fragment)[0]}")

    anchored = bool(anchors)

    # --- Non-anchor positive factors ---
    agency_left = _tokens(left.agency) - _AGENCY_STOP
    agency_right = _tokens(right.agency) - _AGENCY_STOP
    agency_known = bool(agency_left) and bool(agency_right)
    agency_overlap = bool(agency_left & agency_right)
    if agency_overlap:
        factors.append(("agency_match", 0.15))

    name_left = _tokens(left.summary) - _AGENCY_STOP
    name_right = _tokens(right.summary) - _AGENCY_STOP
    name_overlap, name_union = name_left & name_right, name_left | name_right
    if name_overlap and name_union:
        jaccard = len(name_overlap) / len(name_union)
        factors.append(("program_name_similarity", round(min(0.15, 0.15 * jaccard), 3)))

    la, ra = left.meta.get("amount_usd"), right.meta.get("amount_usd")
    if isinstance(la, (int, float)) and isinstance(ra, (int, float)) and la > 0 and ra > 0:
        ratio = max(la, ra) / min(la, ra)
        if ratio <= 1.25:
            factors.append(("funding_amount_proximity", 0.10))
        elif ratio >= 10:
            penalties.append(("funding_amount_divergence", 0.15))

    lg = _norm_text(left.geography or left.meta.get("place_of_performance"))
    rg = _norm_text(right.geography or right.meta.get("place_of_performance"))
    if lg and rg:
        factors.append(("geography_match", 0.05)) if lg == rg else penalties.append(("geography_conflict", 0.20))

    # --- Contradiction penalties (gates) ---
    if agency_known and not agency_overlap:
        penalties.append(("agency_conflict", 0.40))
    precursor, successor = sorted((left, right), key=lambda s: (_STAGE_ORDER[s.stage], s.available_at or ""))
    if precursor.available_at and successor.available_at and precursor.available_at > successor.available_at:
        penalties.append(("temporal_impossibility", 0.40))

    confidence = max(0.0, min(0.95, round(sum(w for _, w in factors) - sum(w for _, w in penalties), 3)))
    if not anchored:
        confidence = min(confidence, _NO_ANCHOR_CONFIDENCE_CAP)

    if anchored and confidence >= _INFERRED_ACCEPT_THRESHOLD:
        disposition, reject_reason = "accept", None
    elif anchored and confidence >= _INFERRED_DEFER_FLOOR:
        disposition, reject_reason = "defer", None
    else:
        disposition = "reject"
        reject_reason = ("inference_contradiction" if penalties else "inference_below_threshold") if anchored else None
    return InferenceScore(
        confidence=confidence, anchored=anchored, disposition=disposition,
        factors=tuple(factors), penalties=tuple(penalties), anchors=tuple(anchors),
        reject_reason=reject_reason,
    )


def _entity_rel(subject_id: str, predicate: str, object_id: str, signal: ProgramSignal,
                evidence_ids: list[str], rationale: str) -> Relationship:
    rel = Relationship(
        subject_id=subject_id, predicate=predicate, object_id=object_id,
        evidence_ids=list(evidence_ids), join_method="authoritative_entity_field",
        confidence=_ENTITY_FIELD_CONFIDENCE, rationale=rationale,
        first_observed_at=signal.available_at, available_at=signal.available_at,
        meta={"source": f"{signal.source_id}:{signal.source_ref}", "stage": signal.stage},
    )
    rel.id = _edge_id(subject_id, predicate, object_id)
    return rel


def resolve_entity_relationships(
    signals: list[ProgramSignal], *, evidence_by_signal_id: dict[str, str] | None = None,
) -> list[Relationship]:
    """Derive entity-level predicates (AWARDED_TO, SUBSIDIARY_OF, LOCATED_AT) only from authoritative
    structured fields on a signal — never inferred from topic. Each edge is evidence-backed, temporal,
    and deterministic."""
    evidence_by_signal_id = evidence_by_signal_id or {}
    rels: list[Relationship] = []
    for signal in signals:
        evidence = [e for e in (evidence_by_signal_id.get(signal.id),) if e]
        uei = signal.meta.get("entity_uei")
        if not uei:
            continue
        uei_norm = str(uei).strip().upper()
        entity_node = f"entity:uei:{uei_norm}"
        if signal.stage in ("AWARD", "PROCUREMENT"):
            rels.append(_entity_rel(signal.id, "AWARDED_TO", entity_node, signal, evidence,
                                    f"record names authoritative recipient UEI {uei_norm}"))
        parent = signal.meta.get("parent_uei")
        if parent and str(parent).strip().upper() != uei_norm:
            rels.append(_entity_rel(entity_node, "SUBSIDIARY_OF", f"entity:uei:{str(parent).strip().upper()}",
                                    signal, evidence, "record declares an authoritative parent UEI"))
        place = _norm_text(signal.meta.get("place_of_performance") or signal.geography)
        if place:
            rels.append(_entity_rel(entity_node, "LOCATED_AT", f"place:{place}", signal, evidence,
                                    f"record places entity at {place}"))
    # Deterministic order and de-duplication by edge identity.
    unique: dict[str, Relationship] = {}
    for rel in sorted(rels, key=lambda r: (r.subject_id, r.predicate, r.object_id)):
        unique.setdefault(rel.id, rel)
    return list(unique.values())


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

    # 3) Weighted, explainable inference / deferral / explicit rejection for un-linked cross-program
    #    pairs. An anchored pair is accepted only if its computed confidence clears the (frozen) 0.60
    #    threshold; an anchored pair in [0.45, 0.60) is deferred to human review; everything else is
    #    rejected. Pairs without a structured anchor keep the original categorical weak-join reasons.
    linked = seen_pairs | {(b, a) for a, b in seen_pairs}
    rejected: list[RejectedJoin] = []
    deferred: list[DeferredJoin] = []
    inference_scores: list[InferenceScore] = []
    for i, left in enumerate(ordered):
        for right in ordered[i + 1:]:
            if left.program_key == right.program_key:
                continue
            if (left.id, right.id) in linked:
                continue
            precursor, successor = sorted((left, right), key=lambda s: (_STAGE_ORDER[s.stage], s.available_at or ""))
            score = score_inferred_join(left, right) if allow_inferred else None
            if score and score.anchored:
                inference_scores.append(score)
            if score and score.disposition == "accept":
                add(precursor, successor, predicate=_predicate(precursor, successor),
                    join_method="inferred_strong_attribute", confidence=score.confidence,
                    rationale=score.rationale)
                continue
            if score and score.disposition == "defer":
                predicate = _predicate(precursor, successor)
                evidence_ids = tuple(e for e in (evidence_by_signal_id.get(precursor.id),
                                                 evidence_by_signal_id.get(successor.id)) if e)
                deferred.append(DeferredJoin(
                    left_id=left.id, right_id=right.id, subject_id=precursor.id,
                    object_id=successor.id, predicate=predicate, confidence=score.confidence,
                    rationale=score.rationale, evidence_ids=evidence_ids,
                    first_observed_at=_later(precursor.available_at, successor.available_at),
                ))
                continue
            if score and score.anchored:
                rejected.append(RejectedJoin(left.id, right.id,
                                             score.reject_reason or "inference_below_threshold", score.rationale))
                continue
            # No structured anchor — preserve the original categorical weak-join rejections.
            same_agency = _same_agency(left.agency, right.agency)
            if same_agency and _tokens(left.summary) & _tokens(right.summary):
                rejected.append(RejectedJoin(left.id, right.id, "agency_name_only",
                                             "same agency and topical overlap, but no shared identifier"))
            elif _tokens(left.summary) & _tokens(right.summary):
                rejected.append(RejectedJoin(left.id, right.id, "topic_overlap_only",
                                             "topical token overlap without identifier or agency match"))
            elif same_agency:
                rejected.append(RejectedJoin(left.id, right.id, "agency_name_only",
                                             "same agency without any shared identifier"))

    # 4) Intra-stage procurement lineage (B2.1): additive, gated on native procurement identity.
    #    Notices without meta['procurement_id'] produce no lineage, so the frozen backbone is unchanged.
    lineage = resolve_procurement_lineage(list(unique.values()), evidence_by_signal_id=evidence_by_signal_id)
    for rel in lineage.relationships:
        if (rel.subject_id, rel.object_id) not in seen_pairs:
            seen_pairs.add((rel.subject_id, rel.object_id))
            relationships.append(rel)

    entity_relationships = resolve_entity_relationships(
        list(unique.values()), evidence_by_signal_id=evidence_by_signal_id)
    confidence = _chain_confidence(list(unique.values()), relationships, lineage)
    return ChainResolution(
        signals=tuple(ordered),
        relationships=tuple(relationships),
        rejected=tuple(rejected),
        duplicates_collapsed=duplicates_collapsed,
        confidence=confidence,
        deferred=tuple(deferred),
        entity_relationships=tuple(entity_relationships),
        inference_scores=tuple(inference_scores),
        lineage=lineage,
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
