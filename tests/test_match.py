from pyrnova.engines.presolicitation import detect_presolicitations
from pyrnova.engines.recompete import detect_recompetes
from pyrnova.match import score_relevance
from pyrnova.normalize import normalize_award, normalize_notice


def test_recompete_relevance_agency_naics_size(award_rows, as_of, profile):
    opps = detect_recompetes([normalize_award(r) for r in award_rows], as_of=as_of, window_days=540)
    acme = next(o for o in opps if o.incumbent == "Acme Federal Systems, Inc.")
    score, reasons, excluded = score_relevance(acme, profile)
    assert not excluded
    # Army agency (0.30) + NAICS 541512 (0.30) + size band (0.15) = 0.75
    assert score >= 0.7
    assert any("agency" in r for r in reasons)
    assert any("NAICS" in r for r in reasons)


def test_presolicitation_capability_keyword_hit(notice_rows, as_of, profile):
    opps = detect_presolicitations([normalize_notice(r) for r in notice_rows], as_of=as_of)
    ss = next(o for o in opps if o.catalyst.kind == "sources_sought")
    score, reasons, _ = score_relevance(ss, profile)
    # C4ISR + network keywords present -> capability component fires.
    assert any("capability keywords" in r for r in reasons)
    assert score >= 0.7


def test_exclusion_zeroes_score(notice_rows, as_of, profile):
    # Craft a notice that trips an exclusion keyword.
    from pyrnova.models import Catalyst, Opportunity

    opp = Opportunity(
        title="Grounds Maintenance and janitorial services",
        catalyst=Catalyst(kind="sources_sought", detected_by="test"),
        agency="Department of the Army",
    )
    score, reasons, excluded = score_relevance(opp, profile)
    assert excluded is True
    assert score == 0.0
    assert reasons and reasons[0].startswith("EXCLUDED")
