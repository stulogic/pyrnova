from pyrnova.archive import LocalEvidenceArchive
from pyrnova.brief import render_capture_radar_report, render_signal_brief
from pyrnova.pipeline import run
from pyrnova.scoreboard import totals
from pyrnova.state import StateStore


def _run(tmp_path, profile, award_rows, notice_rows, as_of, **kw):
    archive = LocalEvidenceArchive(tmp_path / "archive")
    store = StateStore(tmp_path / "state")
    report = run(
        profile=profile,
        award_rows=award_rows,
        notice_rows=notice_rows,
        archive=archive,
        store=store,
        as_of=as_of,
        **kw,
    )
    return report, store


def test_pipeline_produces_strikes_and_accumulates(tmp_path, profile, award_rows, notice_rows, as_of):
    report, store = _run(tmp_path, profile, award_rows, notice_rows, as_of)
    # Direct SAM signals may STRIKE; uncorroborated award expiries stay WATCH.
    assert report.stats["strikes"] >= 1
    assert report.stats["recompete"] == 0
    assert report.stats["watch"] >= 2
    assert report.stats["presolicitation"] >= 1

    # Day-1 accumulation: predictions + reviews + scoreboard all written.
    assert store.count("predictions") >= report.stats["strikes"]
    assert store.count("reviews") >= report.stats["candidates"]
    t = totals(store)
    assert t.get("candidate_opportunities", 0) >= report.stats["candidates"]
    assert t.get("strikes_published", 0) >= 1
    assert t.get("predictions_logged", 0) >= 1


def test_confidence_and_attractiveness_are_separate_fields(tmp_path, profile, award_rows, notice_rows, as_of):
    report, _ = _run(tmp_path, profile, award_rows, notice_rows, as_of)
    top = report.strikes[0]
    assert hasattr(top, "confidence") and hasattr(top, "attractiveness")
    # They are independent measures; the top item should have both populated.
    assert top.confidence > 0
    assert top.relevance_score > 0


def test_evidence_attached_to_every_strike(tmp_path, profile, award_rows, notice_rows, as_of):
    report, _ = _run(tmp_path, profile, award_rows, notice_rows, as_of)
    for opp in report.strikes:
        assert opp.evidence, "every STRIKE must carry archived evidence"
        assert opp.evidence[0].content_sha256


def test_brief_renders_expected_sections(tmp_path, profile, award_rows, notice_rows, as_of):
    report, _ = _run(tmp_path, profile, award_rows, notice_rows, as_of)
    brief = render_signal_brief(report)
    assert "Pyrnova Signal Brief" in brief
    assert "Reasons NOT to pursue" in brief
    assert "Recommended next action" in brief
    assert "PENDING HUMAN REVIEW" in brief  # auto-recommend without a human reviewer
    radar = render_capture_radar_report(report)
    assert "Pyrnova Capture Radar" in radar


def test_posture_defend_vs_capture(tmp_path, profile, award_rows, notice_rows, as_of):
    report, _ = _run(tmp_path, profile, award_rows, notice_rows, as_of)
    # Acme is the incumbent on its own recompete -> DEFEND; others -> CAPTURE.
    defend = [o for o in report.watch if o.meta.get("posture") == "defend"]
    assert any(o.incumbent and "Acme" in o.incumbent for o in defend)


def test_novelty_ordering_presol_first_defend_last(tmp_path, profile, award_rows, notice_rows, as_of):
    report, _ = _run(tmp_path, profile, award_rows, notice_rows, as_of)

    def rank(o):
        if o.catalyst.kind != "recompete_expiry":
            return 0
        return 2 if o.meta.get("posture") == "defend" else 1

    ranks = [rank(o) for o in report.strikes]
    assert ranks == sorted(ranks), "pre-sol must lead, the customer's own recompetes must come last"
    # The customer's own DEFEND recompete must not be the headline item when novel items exist.
    assert report.strikes[0].meta.get("posture") != "defend"


def test_reviewer_label_does_not_auto_accept(tmp_path, profile, award_rows, notice_rows, as_of):
    report, _ = _run(tmp_path, profile, award_rows, notice_rows, as_of, reviewer="stulogic")
    assert report.strikes
    assert all(o.meta.get("review_status") == "pending_human" for o in report.strikes)


def test_sam_strike_is_enriched_by_award_and_precursor_evidence(
    tmp_path, profile, award_rows, notice_rows, precursor_rows, as_of
):
    report, _ = _run(
        tmp_path, profile, award_rows, notice_rows, as_of, precursor_rows=precursor_rows
    )
    strike = next(o for o in report.strikes if o.meta.get("notice_id") == "n0001aaaa")
    assert {e.source_id for e in strike.evidence} == {
        "sam_opportunities", "usaspending", "federal_register"
    }
    assert strike.meta["historical_awards"][0]["recipient_name"] == "Acme Federal Systems, Inc."
    assert strike.meta["upstream_precursors"]
    assert {edge.predicate for edge in strike.relationships} >= {
        "primary_signal", "historical_buyer_context", "upstream_precursor"
    }
    assert "supporting" in strike.evidence_roles.values()
    assert "contra" in strike.evidence_roles.values()
    assert strike.meta["review_status"] == "pending_human"
    assert report.stats["multi_source"] >= 1
    rendered = render_signal_brief(report)
    for label in (
        "Opportunity hypothesis", "Historical award / competitor context",
        "Upstream precursor/context", "Evidence roles", "Catalyst chain", "human-review gate",
    ):
        assert label in rendered
