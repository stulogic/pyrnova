"""A single live source failing (timeout / 5xx / transport error) must DEGRADE that pass, not crash
the whole capture-radar run. Regression guard for the primary (USAspending) path, which previously
let a bare requests exception propagate and abort the run (observed as a real HTTP 502 / ReadTimeout
against api.usaspending.gov). SAM and Federal Register already degraded this way; the anchor source
must behave consistently so partial intelligence is still produced and any empty is EXPLAINED."""

from __future__ import annotations

from datetime import date

from pyrnova import cli
from pyrnova.config import load_config
from pyrnova.match import CapabilityProfile


def test_usaspending_failure_degrades_and_does_not_crash(monkeypatch, capsys):
    def _boom(*a, **k):
        raise RuntimeError("USAspending search failed: HTTP 502")

    monkeypatch.setattr("pyrnova.sources.usaspending.USAspendingClient.search_awards", _boom)
    # No SAM key and no precursor terms -> only the USAspending passes run; all fail.
    monkeypatch.delenv("SAM_API_KEY", raising=False)
    monkeypatch.delenv("PYRNOVA_SAM_API_KEY", raising=False)

    profile = CapabilityProfile(name="Eval Target", naics=["541715"], recipient_names=["Eval Target"])
    award_rows, notice_rows, precursor_rows, source_obs = cli._live_rows(
        load_config(), profile, date(2026, 9, 16), window_days=540)

    # The run returned normally with empty award intelligence...
    assert award_rows == []
    # ...and the empty is EXPLAINED as source degradation, never silent.
    err = capsys.readouterr().err
    assert "USAspending DEGRADED" in err
