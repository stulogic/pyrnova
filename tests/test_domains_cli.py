"""Operator visibility of national domains via the CLI (international operability, Phase 7/14)."""

from __future__ import annotations

import json

from pyrnova.cli import main


def test_domains_list_reports_operational_posture(capsys):
    assert main(["domains", "list"]) == 0
    rows = json.loads(capsys.readouterr().out)
    by_code = {r["code"]: r for r in rows}
    assert by_code["US"]["operational"] is True and by_code["AU"]["operational"] is True
    assert by_code["GB"]["operational"] is False  # seam only
    # NZ GETS activation is visible to the operator as PROHIBITED.
    assert by_code["NZ"]["sources"]["nz_gets"] == "PROHIBITED"


def test_domains_show_au_exposes_national_truth(capsys):
    assert main(["domains", "show", "AU"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["routes"]["FMS"] != d["routes"]["GTG"]
    assert d["dlt_calibration"]["median_dlt_to_market_days"] == 654.5
    assert "AIC_ALIGNED" in d["industrial_position_classes"]
