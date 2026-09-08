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
    # At least the Acme recompete and the Army C4ISR sources-sought should qualify.
    assert report.stats["strikes"] >= 2
    assert report.stats["recompete"] >= 1
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
    defend = [o for o in report.strikes if o.meta.get("posture") == "defend"]
    assert any(o.incumbent and "Acme" in o.incumbent for o in defend)
    # DEFEND items must sort ahead of CAPTURE items.
    postures = [o.meta.get("posture") for o in report.strikes]
    assert postures == sorted(postures, key=lambda p: 0 if p == "defend" else 1)


def test_human_reviewer_upgrades_to_confirmed(tmp_path, profile, award_rows, notice_rows, as_of):
    report, _ = _run(tmp_path, profile, award_rows, notice_rows, as_of, reviewer="stulogic")
    assert report.strikes
    assert all(o.meta.get("review_status") == "human_confirmed" for o in report.strikes)
