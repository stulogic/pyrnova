"""Pipeline orchestrator: OBSERVE → ARCHIVE → NORMALIZE → RESOLVE → DETECT → MATCH → REVIEW → STRIKE → OUTCOME.

The OUTCOME stage is graded later (predictions are logged now for future comparison). This module is
source-agnostic: it takes already-fetched raw pages so it runs identically on live pulls and fixtures.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from . import scoreboard
from .ai import Reasoner, get_reasoner
from .archive import EvidenceArchive
from .engines.presolicitation import detect_presolicitations
from .engines.recompete import detect_recompetes
from .match import CapabilityProfile, apply_match, has_domain_signal
from .models import Opportunity, Review, to_record
from .normalize import normalize_award, normalize_notice
from .review import apply_review, make_prediction, recommend
from .state import StateStore


@dataclass
class Report:
    profile_name: str
    as_of: date
    strikes: list[Opportunity] = field(default_factory=list)
    rejected: list[Opportunity] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _stable_opportunity_id(opp: Opportunity) -> str:
    """Stable source-derived identity for rerun review/history joins."""
    source = str(opp.meta.get("source") or "unknown")
    source_ref = str(opp.meta.get("award_id") or opp.meta.get("notice_id") or "")
    identity = "|".join((source, source_ref, str(opp.expected_action_at or ""), opp.title))
    return f"{source}:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"


def _archive_record(archive: EvidenceArchive, source_id: str, record: dict, opp: Opportunity):
    content = json.dumps(record, sort_keys=True, default=str).encode("utf-8")
    ev = archive.put(
        content,
        source_id=source_id,
        retention_tier="A",  # both USAspending and SAM records are version-sensitive
        media_type="application/json",
        source_ref=str(record.get("_raw_ref") or ""),
        source_url=opp.meta.get("url"),
        published_at=str(record.get("posted_date") or record.get("end_date") or "") or None,
        meta={"engine": opp.catalyst.detected_by},
    )
    opp.evidence.append(ev)
    return ev


def run(
    *,
    profile: CapabilityProfile,
    award_rows: Optional[list[dict]] = None,
    notice_rows: Optional[list[dict]] = None,
    archive: EvidenceArchive,
    store: StateStore,
    as_of: date,
    window_days: int = 540,
    relevance_threshold: float = 0.3,
    reviewer: Optional[str] = None,
    reasoner: Optional[Reasoner] = None,
    min_amount: float = 0.0,
) -> Report:
    reasoner = get_reasoner(reasoner)
    award_rows = award_rows or []
    notice_rows = notice_rows or []

    # NORMALIZE
    awards = [normalize_award(r) for r in award_rows]
    notices = [normalize_notice(r) for r in notice_rows]

    # DETECT
    candidates: list[Opportunity] = []
    candidates += detect_recompetes(awards, as_of=as_of, window_days=window_days, min_amount=min_amount)
    candidates += detect_presolicitations(notices, as_of=as_of)

    scoreboard.record(store, "candidate_opportunities", len(candidates), profile=profile.name)

    report = Report(profile_name=profile.name, as_of=as_of)
    lead_times: list[int] = []

    for opp in candidates:
        opp.id = _stable_opportunity_id(opp)
        opp.customer_id = profile.name
        # ARCHIVE (per-item evidence, content-addressed) — moat accumulation starts here.
        src = "usaspending" if opp.catalyst.kind == "recompete_expiry" else "sam_opportunities"
        # A compact, content-addressed record for provenance (raw pages are archived at OBSERVE too).
        archive_record = {
            "_raw_ref": opp.meta.get("award_id") or opp.meta.get("notice_id"),
            "title": opp.title,
            "agency": opp.agency,
            "incumbent": opp.incumbent,
            "naics": opp.naics,
            "value_usd": opp.value_usd,
            "expected_action_at": opp.expected_action_at,
            "url": opp.meta.get("url"),
            "posted_date": opp.catalyst.meta.get("posted_date"),
            "end_date": opp.catalyst.meta.get("end_date"),
        }
        _archive_record(archive, src, archive_record, opp)

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
                reviewer=reviewer or "auto-recommend/v1",
            )
            apply_review(opp, review)
            store.append("reviews", to_record(review))
            report.rejected.append(opp)
            continue
        # REVIEW → STRIKE / rejected
        review = recommend(opp, relevance_threshold=relevance_threshold, reviewer=reviewer)
        apply_review(opp, review)
        store.append("reviews", to_record(review))

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
        "candidates": len(candidates),
        "strikes": len(report.strikes),
        "rejected": len(report.rejected),
        "avg_lead_time_days": round(sum(lead_times) / len(lead_times), 1) if lead_times else None,
        "recompete": sum(1 for o in report.strikes if o.catalyst.kind == "recompete_expiry"),
        "presolicitation": sum(1 for o in report.strikes if o.catalyst.kind != "recompete_expiry"),
        "defend": sum(1 for o in report.strikes if o.meta.get("posture") == "defend"),
        "capture": sum(1 for o in report.strikes if o.meta.get("posture") != "defend"),
    }
    return report
