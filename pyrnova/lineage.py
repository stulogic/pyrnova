"""B2.1 — intra-stage procurement lineage.

The cross-stage chain (:mod:`pyrnova.chains`) proves that a budget line, a forecast, a solicitation, and
an award are ONE commercial opportunity. It does not, on its own, sequence a single procurement's own
history: a base solicitation, its amendments, a cancellation, and a later reissue currently sit as flat
peers in the PROCUREMENT stage (see ``docs/evidence/bundle1/B1_5_LIFECYCLE_VALIDATION.md``, OUTCOME C).

This module adds notice-level lineage — ``AMENDS`` / ``SUPERSEDES`` / ``CANCELS`` / ``REISSUES`` /
``RECOMPETES`` — and makes a cancellation consequential:

* Notices are grouped into a **procurement instance** ONLY by shared native procurement identity
  (``procurement_id`` — a solicitation number), never by text similarity. No ``procurement_id`` ⇒ no
  lineage edge (ambiguous lineage stays ambiguous).
* An **amendment** alters the timeline of its own instance without spawning a fake independent pursuit.
* A **cancellation** marks its instance ``not-live`` — a real consequence — while every source event is
  retained. If the instance's latest event is the cancellation, the instance is dead.
* A **reissue** is a DISTINCT instance (new ``procurement_id``) that links back with ``REISSUES``; it does
  not silently rewrite the cancelled instance's history, and it restarts a live pursuit.
* A **recompete / follow-on** is likewise a distinct instance, linked only on explicit prior-reference
  evidence.

Temporal honesty: a lineage edge and an instance's disposition are computed only from the notices present,
so a point-in-time replay (which filters notices by ``as_of``) never gains future relationship knowledge —
a cancelled instance looks dead until the notice that reissues it is itself observed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .models import Relationship
from .precursors import ProgramSignal

LINEAGE_VERSION = "procurement_lineage_v1"

# Backward-pointing, intra-opportunity edges. The chain-confidence backbone deliberately ignores these:
# they sequence one procurement's own history, they are not forward capital→procurement→award links.
LINEAGE_PREDICATES = ("AMENDS", "SUPERSEDES", "CANCELS", "REISSUES", "RECOMPETES")

_CANCEL_TYPES = {"cancellation", "cancel", "cancelled", "canceled", "withdrawn", "withdrawal"}
_AMEND_TYPES = {"amendment", "amend", "modification", "mod"}
_REISSUE_TYPES = {"reissue", "reissuance", "resolicitation", "resolicit"}
_RECOMPETE_TYPES = {"recompete", "recompetition", "follow_on", "follow-on", "followon"}
_LINEAGE_CONFIDENCE = 0.95  # shared native solicitation identity is authoritative, not inferred


def _edge_id(subject_id: str, predicate: str, object_id: str) -> str:
    basis = f"{LINEAGE_VERSION}|{subject_id}|{predicate}|{object_id}".encode("utf-8")
    return hashlib.sha256(basis).hexdigest()[:24]


def _later(a: str | None, b: str | None) -> str | None:
    known = [t for t in (a, b) if t]
    return max(known) if known else None


def notice_role(signal: ProgramSignal) -> str:
    """Classify a notice's lineage role from STRUCTURED fields only.

    Explicit ``notice_type`` wins; a structured ``contradicts`` flag or a canonical cancel/amend/reissue
    label is honoured; everything else is a ``base`` notice. Free-text is never mined for a role here —
    the hard anchor is the shared ``procurement_id`` upstream, so a mislabelled word cannot forge lineage.
    """
    raw = str(signal.meta.get("notice_type") or "").strip().lower().replace(" ", "_")
    if raw in _CANCEL_TYPES or signal.meta.get("contradicts"):
        return "cancellation"
    if raw in _AMEND_TYPES:
        return "amendment"
    if raw in _REISSUE_TYPES:
        return "reissue"
    if raw in _RECOMPETE_TYPES:
        return "recompete"
    return "base"


@dataclass(frozen=True)
class ProcurementInstance:
    """One procurement competition (a native solicitation identity) and its sequenced disposition."""

    program_key: str
    procurement_id: str
    notice_ids: tuple[str, ...]        # signal ids, time-ordered
    base_id: str
    opened_at: str | None
    last_event_at: str | None
    disposition: str                   # open | cancelled | superseded
    live: bool
    cancelled_at: str | None = None
    reissue_of: str | None = None      # procurement_id this instance reissued/recompeted
    reissued_by: str | None = None     # procurement_id that later reissued THIS instance
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcurementLineageResolution:
    relationships: tuple[Relationship, ...]
    instances: tuple[ProcurementInstance, ...]

    def instance_for(self, procurement_id: str) -> ProcurementInstance | None:
        return next((i for i in self.instances if i.procurement_id == procurement_id), None)

    def current_instance(self, program_key: str) -> ProcurementInstance | None:
        """The most recently opened procurement instance for a program (its 'current' competition)."""
        instances = [i for i in self.instances if i.program_key == program_key]
        if not instances:
            return None
        return max(instances, key=lambda i: (i.opened_at or "", i.procurement_id))

    def program_live(self, program_key: str) -> bool | None:
        """Is the program's current procurement live? ``None`` when the program has no instance."""
        current = self.current_instance(program_key)
        return None if current is None else current.live

    def metrics(self) -> dict:
        return {
            "lineage_version": LINEAGE_VERSION,
            "lineage_relationships": len(self.relationships),
            "lineage_predicates": sorted({r.predicate for r in self.relationships}),
            "procurement_instances": len(self.instances),
            "cancelled_instances": sum(i.disposition == "cancelled" for i in self.instances),
            "live_instances": sum(i.live for i in self.instances),
        }


def _lineage_rel(subject: ProgramSignal, predicate: str, obj: ProgramSignal,
                 rationale: str, evidence_by_signal_id: dict[str, str]) -> Relationship:
    """Build one lineage edge from the ACTING notice (subject) to the notice it acts on (object)."""
    knowable = _later(subject.available_at, obj.available_at)
    evidence_ids = [e for e in (evidence_by_signal_id.get(subject.id), evidence_by_signal_id.get(obj.id)) if e]
    rel = Relationship(
        subject_id=subject.id,
        predicate=predicate,
        object_id=obj.id,
        evidence_ids=evidence_ids,
        join_method="native_procurement_identity",
        confidence=_LINEAGE_CONFIDENCE,
        rationale=rationale,
        first_observed_at=knowable,
        available_at=knowable,
        meta={
            "subject_source": f"{subject.source_id}:{subject.source_ref}",
            "object_source": f"{obj.source_id}:{obj.source_ref}",
            "program_key": subject.program_key if subject.program_key == obj.program_key else None,
            "procurement_id": subject.meta.get("procurement_id"),
            "lineage": True,
        },
    )
    rel.id = _edge_id(subject.id, predicate, obj.id)
    return rel


def resolve_procurement_lineage(
    signals: list[ProgramSignal], *, evidence_by_signal_id: dict[str, str] | None = None,
) -> ProcurementLineageResolution:
    """Sequence notices that share a native procurement identity into one auditable lineage.

    Only signals carrying ``meta['procurement_id']`` participate; all others are untouched, so this is a
    purely additive layer over the frozen cross-stage chain engine.
    """
    evidence_by_signal_id = evidence_by_signal_id or {}
    participating = [s for s in signals if s.meta.get("procurement_id")]

    groups: dict[tuple[str, str], list[ProgramSignal]] = {}
    for signal in participating:
        key = (signal.program_key, str(signal.meta["procurement_id"]))
        groups.setdefault(key, []).append(signal)

    relationships: list[Relationship] = []
    instances: list[ProcurementInstance] = []
    base_by_procurement: dict[tuple[str, str], ProgramSignal] = {}

    # First pass: intra-instance lineage (AMENDS / CANCELS / SUPERSEDES) and disposition.
    for (program_key, procurement_id), group in sorted(groups.items()):
        ordered = sorted(group, key=lambda s: (s.available_at or "", s.source_ref))
        base = ordered[0]
        base_by_procurement[(program_key, procurement_id)] = base
        active = base                              # the notice a later action currently applies to
        disposition, cancelled_at = "open", None
        for notice in ordered[1:]:
            role = notice_role(notice)
            if role == "cancellation":
                relationships.append(_lineage_rel(
                    notice, "CANCELS", active,
                    f"cancellation shares native procurement identity {procurement_id!r}; voids the active notice",
                    evidence_by_signal_id))
                disposition, cancelled_at, active = "cancelled", notice.available_at, notice
            elif role == "amendment":
                relationships.append(_lineage_rel(
                    notice, "AMENDS", active,
                    f"amendment shares native procurement identity {procurement_id!r}; alters the active notice",
                    evidence_by_signal_id))
                # An amendment after a cancellation reinstates the competition (history retained).
                if disposition == "cancelled":
                    disposition, cancelled_at = "open", None
                active = notice
            else:
                # A later base-like notice in the same procurement replaces the earlier one.
                relationships.append(_lineage_rel(
                    notice, "SUPERSEDES", active,
                    f"later notice under native procurement identity {procurement_id!r} supersedes the prior",
                    evidence_by_signal_id))
                if disposition == "cancelled":
                    disposition, cancelled_at = "open", None
                active = notice
        instances.append(ProcurementInstance(
            program_key=program_key,
            procurement_id=procurement_id,
            notice_ids=tuple(s.id for s in ordered),
            base_id=base.id,
            opened_at=base.available_at,
            last_event_at=ordered[-1].available_at,
            disposition=disposition,
            live=(disposition == "open"),
            cancelled_at=cancelled_at,
            evidence_ids=tuple(e for e in (evidence_by_signal_id.get(s.id) for s in ordered) if e),
        ))

    # Second pass: cross-instance lineage (REISSUES / RECOMPETES) on explicit prior-reference evidence.
    instance_by_id = {(i.program_key, i.procurement_id): i for i in instances}
    reissued_by: dict[tuple[str, str], str] = {}
    reissue_of: dict[tuple[str, str], str] = {}
    for (program_key, procurement_id), group in sorted(groups.items()):
        prior_ids = {str(s.meta.get("prior_procurement_id")) for s in group if s.meta.get("prior_procurement_id")}
        roles = {notice_role(s) for s in group}
        for prior_id in sorted(pid for pid in prior_ids if pid and pid != procurement_id):
            prior_key = (program_key, prior_id)
            if prior_key not in base_by_procurement:
                continue  # ambiguous / unknown predecessor stays ambiguous — no invented edge
            predicate = "RECOMPETES" if roles & {"recompete"} else "REISSUES"
            this_base = base_by_procurement[(program_key, procurement_id)]
            prior_base = base_by_procurement[prior_key]
            relationships.append(_lineage_rel(
                this_base, predicate, prior_base,
                f"explicit prior-procurement reference {prior_id!r} → {procurement_id!r}",
                evidence_by_signal_id))
            reissued_by[prior_key] = procurement_id
            reissue_of[(program_key, procurement_id)] = prior_id

    if reissued_by or reissue_of:
        instances = [
            ProcurementInstance(
                **{**i.__dict__,
                   "reissued_by": reissued_by.get((i.program_key, i.procurement_id), i.reissued_by),
                   "reissue_of": reissue_of.get((i.program_key, i.procurement_id), i.reissue_of)}
            )
            for i in instances
        ]

    relationships.sort(key=lambda r: (r.subject_id, r.predicate, r.object_id))
    return ProcurementLineageResolution(
        relationships=tuple(relationships),
        instances=tuple(sorted(instances, key=lambda i: (i.program_key, i.opened_at or "", i.procurement_id))),
    )
