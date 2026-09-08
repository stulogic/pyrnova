"""Regression contracts for deterministic provenance, review, and state behavior."""

from __future__ import annotations

from copy import deepcopy

import pytest

from pyrnova.archive import LocalEvidenceArchive
from pyrnova.enrich import EVIDENCE_STRENGTH, related_precursors
from pyrnova.models import Catalyst, Opportunity
from pyrnova.pipeline import run
from pyrnova.review import adjudicate, apply_review
from pyrnova.state import StateStore


def _run(tmp_path, profile, award_rows, notice_rows, as_of, precursor_rows=None):
    return run(
        profile=profile,
        award_rows=award_rows,
        notice_rows=notice_rows,
        precursor_rows=precursor_rows,
        archive=LocalEvidenceArchive(tmp_path / "archive"),
        store=StateStore(tmp_path / "state"),
        as_of=as_of,
    )


def test_pipeline_deduplicates_duplicate_awards_and_notices_deterministically(
    tmp_path, profile, award_rows, notice_rows, as_of
):
    baseline = _run(tmp_path / "baseline", profile, award_rows, notice_rows, as_of)
    duplicated = _run(
        tmp_path / "duplicated",
        profile,
        list(reversed(deepcopy(award_rows) + deepcopy(award_rows))),
        list(reversed(deepcopy(notice_rows) + deepcopy(notice_rows))),
        as_of,
    )

    baseline_ids = {opp.meta["identity_key"]: opp.id for opp in baseline.strikes + baseline.watch + baseline.rejected}
    duplicated_opps = duplicated.strikes + duplicated.watch + duplicated.rejected
    assert {opp.meta["identity_key"]: opp.id for opp in duplicated_opps} == baseline_ids
    assert len(duplicated_opps) == len(baseline_ids)
    assert duplicated.stats["duplicate_candidates"] == duplicated.stats["raw_candidates"] - duplicated.stats["candidates"]
    assert duplicated.stats["duplicate_candidates"] > 0


def test_evidence_strength_hierarchy_and_federal_register_context_cap(
    tmp_path, profile, notice_rows, precursor_rows, as_of
):
    assert EVIDENCE_STRENGTH == {
        1: "weak_topical_similarity",
        2: "agency_sector_context",
        3: "named_organizational_program_relationship",
        4: "direct_contracting_budget_award",
        5: "direct_causal_program_evidence",
    }
    assert list(EVIDENCE_STRENGTH) == [1, 2, 3, 4, 5]

    report = _run(
        tmp_path, profile, [], notice_rows, as_of, precursor_rows=precursor_rows
    )
    federal_assessments = [
        assessment
        for opp in report.strikes + report.watch + report.rejected
        for event, assessment in zip(opp.events, opp.evidence_assessments)
        if event.source_id == "federal_register"
    ]
    assert federal_assessments
    assert all(assessment.strength <= 2 for assessment in federal_assessments)
    assert all(assessment.strength_class == EVIDENCE_STRENGTH[assessment.strength] for assessment in federal_assessments)


@pytest.mark.parametrize(
    ("decision", "state", "review_status"),
    [
        ("ACCEPT", "strike", "human_confirmed"),
        ("WATCH", "reviewing", "human_watch"),
        ("REJECT", "rejected", "human_rejected"),
    ],
)
def test_human_adjudication_validates_and_drives_lifecycle(decision, state, review_status):
    opportunity = Opportunity(title="Test signal", catalyst=Catalyst(kind="rfi", detected_by="test"))
    review = adjudicate(opportunity, decision=decision, reviewer="reviewer-1", reason="verified")

    assert review.human_decision == decision
    assert review.reviewer == "reviewer-1"
    assert apply_review(opportunity, review).state == state
    assert opportunity.meta["review_status"] == review_status


@pytest.mark.parametrize("decision", ["", "STRIKE", "approve"])
def test_adjudication_rejects_unknown_decision_and_missing_reviewer(decision):
    opportunity = Opportunity(title="Test signal", catalyst=Catalyst(kind="rfi", detected_by="test"))
    if decision:
        with pytest.raises(ValueError, match="decision must be ACCEPT, WATCH, or REJECT"):
            adjudicate(opportunity, decision=decision, reviewer="reviewer-1")
    with pytest.raises(ValueError, match="reviewer is required"):
        adjudicate(opportunity, decision="ACCEPT", reviewer="   ")


def test_state_store_latest_returns_last_matching_record(tmp_path):
    store = StateStore(tmp_path / "state")
    store.append("reviews", {"id": "one", "decision": "watch"})
    store.append("reviews", {"id": "two", "decision": "reject"})
    store.append("reviews", {"id": "one", "decision": "accept"})

    assert store.latest("reviews", "one")["decision"] == "accept"
    assert store.latest("reviews", "two")["decision"] == "reject"
    assert store.latest("reviews", "missing") is None


def test_raw_source_observation_and_safe_provenance_survive_pipeline(
    tmp_path, profile, as_of
):
    raw = b'{"opportunitiesData":[]}'
    archive = LocalEvidenceArchive(tmp_path / "archive")
    store = StateStore(tmp_path / "state")
    run(
        profile=profile,
        archive=archive,
        store=store,
        as_of=as_of,
        source_observations=[{
            "source_id": "sam_opportunities",
            "source_ref": "search:p:0",
            "request_url": "https://api.sam.gov/opportunities/v2/search",
            "request_params": {"postedFrom": "09/01/2026", "postedTo": "09/08/2026"},
            "fetched_at": "2026-09-08T10:00:00+00:00",
            "raw_response": raw,
        }],
    )
    observation = next(store.read("observations"))
    assert "api_key" not in observation["request_params"]
    assert archive.get(observation["content_sha256"], "sam_opportunities") == raw


def test_context_without_direct_opportunity_creates_no_candidate(
    tmp_path, profile, precursor_rows, as_of
):
    report = _run(tmp_path, profile, [], [], as_of, precursor_rows=precursor_rows)
    assert report.stats["candidates"] == 0
    assert report.stats["strikes"] == 0
