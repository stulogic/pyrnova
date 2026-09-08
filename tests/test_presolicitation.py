from pyrnova.engines.presolicitation import detect_presolicitations
from pyrnova.normalize import normalize_notice
from pyrnova.sources.sam import notice_class_from_type


def _notices(notice_rows):
    return [normalize_notice(r) for r in notice_rows]


def test_notice_class_mapping():
    assert notice_class_from_type("Sources Sought") == "sources_sought"
    assert notice_class_from_type("Presolicitation") == "presolicitation"
    assert notice_class_from_type("Special Notice") == "special_notice"
    assert notice_class_from_type("r") == "sources_sought"
    assert notice_class_from_type("Award Notice") == "award_notice"


def test_wedge_filter_excludes_award_notice(notice_rows, as_of):
    opps = detect_presolicitations(_notices(notice_rows), as_of=as_of)
    kinds = {o.catalyst.kind for o in opps}
    assert "sources_sought" in kinds
    assert "presolicitation" in kinds
    assert "special_notice" in kinds
    # Award notice (grounds maintenance) is not a pre-solicitation wedge signal.
    assert "award_notice" not in kinds
    assert all("Grounds Maintenance" not in o.title for o in opps)


def test_sources_sought_ranked_first(notice_rows, as_of):
    opps = detect_presolicitations(_notices(notice_rows), as_of=as_of)
    assert opps[0].catalyst.kind == "sources_sought"


def test_horizon_from_response_deadline(notice_rows, as_of):
    opps = detect_presolicitations(_notices(notice_rows), as_of=as_of)
    ss = next(o for o in opps if o.catalyst.kind == "sources_sought")
    # deadline 2026-10-15, as-of 2026-09-08 -> 37 days
    assert ss.catalyst.horizon_days == 37
    assert ss.falsification
