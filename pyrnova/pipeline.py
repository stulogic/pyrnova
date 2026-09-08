"""Pipeline orchestrator: OBSERVE → ARCHIVE → NORMALIZE → RESOLVE → DETECT → MATCH → REVIEW → STRIKE → OUTCOME.

The OUTCOME stage is graded later (predictions are logged now for future comparison). This module is
source-agnostic: it takes already-fetched raw pages so it runs identically on live pulls and fixtures.
"""

from __future__ import annotations

import json
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from . import scoreboard
from .ai import Reasoner, get_reasoner
from .archive import EvidenceArchive
from .engines.presolicitation import detect_presolicitations
from .engines.recompete import detect_recompetes
from .enrich import connect_event, related_awards, related_precursors
from .match import CapabilityProfile, apply_match, has_domain_signal
from .models import Event, Opportunity, Review, to_record
from .normalize import normalize_award, normalize_notice, normalize_precursor
from .review import apply_review, make_prediction, recommend
from .sources.registry import get_spec
from .state import StateStore


@dataclass
class Report:
    profile_name: str
    as_of: date
    run_id: str = ""
    replay_as_of: str | None = None
    strikes: list[Opportunity] = field(default_factory=list)
    watch: list[Opportunity] = field(default_factory=list)
    rejected: list[Opportunity] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _opportunity_key(opp: Opportunity) -> str:
    if opp.meta.get("award_id"):
        return f"usaspending:award:{opp.meta['award_id']}"
    if opp.meta.get("notice_id"):
        return f"sam:notice:{opp.meta['notice_id']}"
    if opp.meta.get("solicitation_number"):
        return f"sam:solicitation:{opp.meta['solicitation_number']}"
    raw = "|".join([opp.catalyst.kind, opp.agency or "", opp.title])
    return f"derived:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def _deduplicate_candidates(candidates: list[Opportunity]) -> tuple[list[Opportunity], int]:
    unique: dict[str, Opportunity] = {}
    duplicates = 0
    for opp in candidates:
        key = _opportunity_key(opp)
        if key in unique:
            duplicates += 1
            unique[key].meta["duplicate_records"] = unique[key].meta.get("duplicate_records", 1) + 1
            continue
        opp.meta["identity_key"] = key
        opp.id = uuid.uuid5(uuid.NAMESPACE_URL, f"pyrnova:{key}").hex
        unique[key] = opp
    return list(unique.values()), duplicates


def _available_at(record: dict) -> str | None:
    return (
        record.get("available_at")
        or (record.get("_pyrnova_timing") or {}).get("available_at")
        or (record.get("_pyrnova_observation") or {}).get("fetched_at")
    )


def _visible_at(record: dict, cutoff: datetime) -> bool:
    available = _available_at(record)
    if not available:
        return False
    try:
        observed = datetime.fromisoformat(str(available).replace("Z", "+00:00"))
        if observed.tzinfo is None and cutoff.tzinfo is not None:
            observed = observed.replace(tzinfo=cutoff.tzinfo)
        return observed <= cutoff
    except ValueError:
        return False


def _archive_record(
    archive: EvidenceArchive,
    source_id: str,
    record: dict,
    *,
    source_ref: str | None,
    source_url: str | None,
    published_at: str | None,
):
    content = json.dumps(record, sort_keys=True, default=str).encode("utf-8")
    ev = archive.put(
        content,
        source_id=source_id,
        retention_tier=get_spec(source_id).retention_tier,
        media_type="application/json",
        source_ref=str(source_ref or ""),
        source_url=source_url,
        published_at=published_at,
        meta={"raw_source_record": True},
    )
    return ev


def run(
    *,
    profile: CapabilityProfile,
    award_rows: Optional[list[dict]] = None,
    notice_rows: Optional[list[dict]] = None,
    precursor_rows: Optional[list[dict]] = None,
    source_observations: Optional[list[dict]] = None,
    archive: EvidenceArchive,
    store: StateStore,
    as_of: date,
    window_days: int = 540,
    relevance_threshold: float = 0.3,
    reviewer: Optional[str] = None,
    reasoner: Optional[Reasoner] = None,
    min_amount: float = 0.0,
    replay_as_of: Optional[str] = None,
) -> Report:
    reasoner = get_reasoner(reasoner)
    award_rows = award_rows or []
    notice_rows = notice_rows or []
    precursor_rows = precursor_rows or []
    source_observations = source_observations or []
    future_records_excluded = 0
    if replay_as_of:
        cutoff = datetime.fromisoformat(replay_as_of.replace("Z", "+00:00"))
        original_count = len(award_rows) + len(notice_rows) + len(precursor_rows)
        award_rows = [r for r in award_rows if _visible_at(r, cutoff)]
        notice_rows = [r for r in notice_rows if _visible_at(r, cutoff)]
        precursor_rows = [r for r in precursor_rows if _visible_at(r, cutoff)]
        future_records_excluded = original_count - len(award_rows) - len(notice_rows) - len(precursor_rows)
        source_observations = [
            o for o in source_observations
            if o.get("fetched_at") and _visible_at({"available_at": o["fetched_at"]}, cutoff)
        ]

    # OBSERVE/ARCHIVE: preserve exact page bytes and safe request provenance before normalization.
    for observation in source_observations:
        source_id = observation["source_id"]
        spec = get_spec(source_id)
        ev = archive.put(
            observation["raw_response"],
            source_id=source_id,
            retention_tier=spec.retention_tier,
            media_type="application/json",
            source_ref=observation.get("source_ref"),
            source_url=observation.get("request_url"),
            meta={
                "observation": True,
                "fetched_at": observation.get("fetched_at"),
                "request_params": observation.get("request_params") or {},
            },
        )
        store.append(
            "observations",
            {
                "source_id": source_id,
                "source_ref": observation.get("source_ref"),
                "request_url": observation.get("request_url"),
                "request_params": observation.get("request_params") or {},
                "fetched_at": observation.get("fetched_at"),
                "content_sha256": ev.content_sha256,
                "archive_uri": ev.archive_uri,
            },
        )

    # NORMALIZE
    awards = [normalize_award(r) for r in award_rows]
    notices = [normalize_notice(r) for r in notice_rows]
    precursors = [normalize_precursor(r) for r in precursor_rows]
    raw_awards = {a.get("_raw_ref"): raw for a, raw in zip(awards, award_rows)}
    raw_notices = {n.get("_raw_ref"): raw for n, raw in zip(notices, notice_rows)}
    raw_precursors = {p.get("_raw_ref"): raw for p, raw in zip(precursors, precursor_rows)}
    evidence_cache = {}

    def archive_source(source_id: str, normalized: dict):
        ref = normalized.get("_raw_ref")
        key = (source_id, ref)
        if key not in evidence_cache:
            raw_map = {
                "usaspending": raw_awards,
                "sam_opportunities": raw_notices,
                "federal_register": raw_precursors,
            }[source_id]
            published = (
                normalized.get("posted_date")
                or normalized.get("publication_date")
            )
            evidence_cache[key] = _archive_record(
                archive,
                source_id,
                raw_map.get(ref, normalized),
                source_ref=ref,
                source_url=normalized.get("url"),
                published_at=str(published) if published else None,
            )
        return evidence_cache[key]

    # DETECT
    raw_candidates: list[Opportunity] = []
    raw_candidates += detect_recompetes(awards, as_of=as_of, window_days=window_days, min_amount=min_amount)
    raw_candidates += detect_presolicitations(notices, as_of=as_of)
    candidates, duplicate_count = _deduplicate_candidates(raw_candidates)

    scoreboard.record(store, "candidate_opportunities", len(candidates), profile=profile.name)
    scoreboard.record(store, "duplicate_opportunities", duplicate_count, profile=profile.name)

    run_basis = json.dumps(
        {
            "profile": profile.name,
            "as_of": as_of.isoformat(),
            "replay_as_of": replay_as_of,
            "awards": sorted(str(a.get("_raw_ref") or "") for a in awards),
            "notices": sorted(str(n.get("_raw_ref") or "") for n in notices),
            "precursors": sorted(str(p.get("_raw_ref") or "") for p in precursors),
        },
        sort_keys=True,
    )
    report = Report(
        profile_name=profile.name,
        as_of=as_of,
        run_id=hashlib.sha256(run_basis.encode("utf-8")).hexdigest()[:20],
        replay_as_of=replay_as_of,
    )
    lead_times: list[int] = []

    for opp in candidates:
        opp.customer_id = profile.name
        # Primary source event. Raw source records, not derived summaries, are archived.
        is_award = opp.catalyst.kind == "recompete_expiry"
        primary = (awards if is_award else notices)
        primary_ref = opp.meta.get("award_id") if is_award else opp.meta.get("notice_id")
        primary_record = next((r for r in primary if r.get("_raw_ref") == primary_ref), None)
        if primary_record:
            source_id = "usaspending" if is_award else "sam_opportunities"
            ev = archive_source(source_id, primary_record)
            opp.evidence.append(ev)
            primary_event = Event(
                kind="award" if is_award else "notice_posted",
                source_id=source_id,
                source_ref=str(primary_ref),
                occurred_at=str(primary_record.get("end_date") if is_award else primary_record.get("posted_date") or "") or None,
                summary=opp.catalyst.summary if is_award else (primary_record.get("title") or opp.title),
                evidence_ids=[ev.id],
                meta={"url": primary_record.get("url")},
            )
            connect_event(
                opp, primary_event, evidence_id=ev.id, predicate="primary_signal", role="primary",
                strength=4 if is_award else 5,
                basis="direct award record" if is_award else "direct SAM opportunity notice",
            )

        # A SAM opportunity is enriched with source-independent award context and upstream documents.
        if not is_award:
            history = related_awards(opp, awards, recipient_names=profile.search_names)
            if history:
                opp.meta["historical_awards"] = []
            for award in history:
                ev = archive_source("usaspending", award)
                if ev not in opp.evidence:
                    opp.evidence.append(ev)
                event = Event(
                    kind="award",
                    source_id="usaspending",
                    source_ref=str(award.get("award_id") or ""),
                    occurred_at=str(award.get("end_date") or "") or None,
                    summary=(
                        f"Historical award to {award.get('recipient_name') or 'unknown recipient'} "
                        f"for {award.get('amount') if award.get('amount') is not None else 'unknown value'}"
                    ),
                    evidence_ids=[ev.id],
                    meta={"url": award.get("url")},
                )
                connect_event(
                    opp, event, evidence_id=ev.id, predicate="historical_buyer_context", role="context",
                    strength=4, basis="direct historical award record",
                )
                opp.meta["historical_awards"].append({
                    "award_id": award.get("award_id"),
                    "recipient_name": award.get("recipient_name"),
                    "amount": award.get("amount"),
                    "end_date": str(award.get("end_date") or "") or None,
                    "url": award.get("url"),
                    "basis": "same buyer plus classification/topic or target history; not proof of upcoming incumbency",
                })

            precursor_links = related_precursors(opp, precursors)
            if precursor_links:
                opp.meta["upstream_precursors"] = []
            for precursor, role, strength, basis in precursor_links:
                ev = archive_source("federal_register", precursor)
                if ev not in opp.evidence:
                    opp.evidence.append(ev)
                event = Event(
                    kind="regulatory_precursor",
                    source_id="federal_register",
                    source_ref=str(precursor.get("precursor_id") or ""),
                    occurred_at=str(precursor.get("publication_date") or "") or None,
                    summary=precursor.get("title") or "Federal Register document",
                    evidence_ids=[ev.id],
                    meta={"url": precursor.get("url"), "official_pdf_url": precursor.get("official_pdf_url")},
                )
                connect_event(
                    opp, event, evidence_id=ev.id, predicate="upstream_precursor", role=role,
                    strength=strength, basis=basis,
                )
                opp.meta["upstream_precursors"].append({
                    "document_number": precursor.get("precursor_id"),
                    "title": precursor.get("title"),
                    "publication_date": str(precursor.get("publication_date") or "") or None,
                    "url": precursor.get("url"),
                    "role": role,
                    "basis": "agency and topic overlap; does not prove procurement intent",
                })

            opp.meta["opportunity_hypothesis"] = (
                f"The {opp.catalyst.kind.replace('_', ' ')} may develop into a relevant procurement "
                f"for {profile.name}; verify scope, acquisition path, and competitive position."
            )
            opp.meta["catalyst_chain"] = [
                {"event_id": event.id, "kind": event.kind, "source_id": event.source_id}
                for event in opp.events
            ]

        # MATCH
        apply_match(opp, profile)
        # AI (optional, non-authoritative)
        opp = reasoner.enrich(opp)
        # DOMAIN GATE: a pre-solicitation notice matching only on a generic NAICS (no agency/capability
        # signal) is not real intelligence for this customer — reject before it can become a STRIKE.
        if opp.catalyst.kind != "recompete_expiry" and not has_domain_signal(opp):
            review = Review(
                opportunity_id=opp.id,
                decision="reject",
                reason="pre-solicitation NAICS-only match; no agency/capability domain signal",
                confidence=opp.confidence,
                reviewer="auto-recommend/v2",
                system_disposition="REJECT",
                score_at_review=opp.relevance_score,
            )
            apply_review(opp, review)
            store.append("reviews", to_record(review))
            store.append("opportunities", {"run_id": report.run_id, **to_record(opp)})
            report.rejected.append(opp)
            continue
        # REVIEW → STRIKE / rejected
        review = recommend(opp, relevance_threshold=relevance_threshold, reviewer=reviewer)
        apply_review(opp, review)
        store.append("reviews", to_record(review))
        store.append("opportunities", {"run_id": report.run_id, **to_record(opp)})

        if opp.is_strike:
            pred = make_prediction(opp, as_of=as_of)
            store.append("predictions", to_record(pred))
            scoreboard.record(store, "predictions_logged", 1, precursor_class=pred.precursor_class)
            if pred.lead_time_days is not None:
                lead_times.append(pred.lead_time_days)
            scoreboard.record(store, "evidence_items", len(opp.evidence))
            if opp.relevance_score >= relevance_threshold:
                scoreboard.record(store, "customer_relevant_strikes", 1)
            report.strikes.append(opp)
        elif opp.state == "reviewing":
            report.watch.append(opp)
        else:
            report.rejected.append(opp)

    # Rank strikes by NOVELTY to the customer (learned from the first live Torch run): pre-solicitation
    # first (earliest, most differentiated, genuinely "not tracked yet"), then competitor recompetes we
    # could capture, then the customer's OWN recompetes (they already know these — context, not a lead).
    # Within a tier: relevance, then attractiveness, then soonest action.
    def _novelty_rank(o: Opportunity) -> int:
        if o.catalyst.kind != "recompete_expiry":
            return 0  # pre-solicitation
        return 2 if o.meta.get("posture") == "defend" else 1  # own defend last, competitor capture mid

    report.strikes.sort(
        key=lambda o: (
            _novelty_rank(o),
            -o.relevance_score,
            -o.attractiveness,
            o.catalyst.horizon_days or 10**9,
        )
    )
    scoreboard.record(store, "strikes_published", len(report.strikes), profile=profile.name)

    report.stats = {
        "run_id": report.run_id,
        "raw_candidates": len(raw_candidates),
        "candidates": len(candidates),
        "duplicate_candidates": duplicate_count,
        "duplicate_opportunity_rate": round(duplicate_count / len(raw_candidates), 4) if raw_candidates else 0.0,
        "future_records_excluded": future_records_excluded,
        "strikes": len(report.strikes),
        "watch": len(report.watch),
        "rejected": len(report.rejected),
        "avg_lead_time_days": round(sum(lead_times) / len(lead_times), 1) if lead_times else None,
        "recompete": sum(1 for o in report.strikes if o.catalyst.kind == "recompete_expiry"),
        "presolicitation": sum(1 for o in report.strikes if o.catalyst.kind != "recompete_expiry"),
        "defend": sum(1 for o in report.strikes if o.meta.get("posture") == "defend"),
        "capture": sum(1 for o in report.strikes if o.meta.get("posture") != "defend"),
        "multi_source": sum(1 for o in report.strikes if len({e.source_id for e in o.evidence}) >= 2),
    }
    return report
