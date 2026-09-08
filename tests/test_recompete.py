from datetime import date

from pyrnova.engines.recompete import detect_recompetes
from pyrnova.normalize import normalize_award


def _awards(award_rows):
    return [normalize_award(r) for r in award_rows]


def test_within_window_detected_and_out_of_window_excluded(award_rows, as_of):
    opps = detect_recompetes(_awards(award_rows), as_of=as_of, window_days=540)
    incumbents = {o.incumbent for o in opps}
    # Acme (ends 2027-01-15) and Globex (ends 2026-12-01) are within 540 days.
    assert "Acme Federal Systems, Inc." in incumbents
    assert "Globex Defense LLC" in incumbents
    # Far-future (2029) and already-expired (2025) are excluded.
    assert "Initech Systems Corporation" not in incumbents
    assert "Umbrella Logistics Inc." not in incumbents


def test_ranked_soonest_first(award_rows, as_of):
    opps = detect_recompetes(_awards(award_rows), as_of=as_of, window_days=540)
    horizons = [o.catalyst.horizon_days for o in opps]
    assert horizons == sorted(horizons)


def test_every_candidate_has_falsification_and_prediction_fields(award_rows, as_of):
    opps = detect_recompetes(_awards(award_rows), as_of=as_of, window_days=540)
    for o in opps:
        assert o.falsification, "falsification note is mandatory"
        assert o.catalyst.kind == "recompete_expiry"
        assert o.expected_action_at
        assert 0.0 <= o.confidence <= 1.0
        assert 0.0 <= o.attractiveness <= 1.0


def test_min_amount_filter(award_rows, as_of):
    opps = detect_recompetes(_awards(award_rows), as_of=as_of, window_days=540, min_amount=5_000_000)
    # Only Acme (12.5M) clears a $5M floor within window; Globex (3.2M) is filtered out.
    assert [o.incumbent for o in opps] == ["Acme Federal Systems, Inc."]


def test_attractiveness_monotonic_in_amount():
    from pyrnova.engines.recompete import _attractiveness_from_amount

    assert _attractiveness_from_amount(100_000) < _attractiveness_from_amount(10_000_000)
    assert _attractiveness_from_amount(0) == 0.0
