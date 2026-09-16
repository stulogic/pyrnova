"""Operator visibility of national domains via the CLI (international operability, Phase 7/14)."""

from __future__ import annotations

import json

from pyrnova.cli import main


def test_domains_list_reports_operational_posture(capsys):
    assert main(["domains", "list"]) == 0
    rows = json.loads(capsys.readouterr().out)
    by_code = {r["code"]: r for r in rows}
    assert by_code["US"]["operational"] is True and by_code["AU"]["operational"] is True
    # NZ is now operational (validated + owner build authority).
    assert by_code["NZ"]["operational"] is True and by_code["NZ"]["dlt_calibrated"] is True
    # UK (GB) is now operational, but with NO numeric DLT threshold (n=3 strict-qualifying).
    assert by_code["GB"]["operational"] is True and by_code["GB"]["dlt_calibrated"] is False
    # NZ GETS activation is visible to the operator as PROHIBITED; the replay evidence family is FIXTURE_ONLY.
    assert by_code["NZ"]["sources"]["nz_gets"] == "PROHIBITED"
    assert by_code["NZ"]["sources"]["nz_mod"] == "FIXTURE_ONLY"


def test_domains_show_nz_exposes_national_truth_incl_thin_prime(capsys):
    assert main(["domains", "show", "NZ"]) == 0
    d = json.loads(capsys.readouterr().out)
    # NZ routes are NZ meanings; DIRECT_SOURCE and PANEL are distinct entries.
    assert d["routes"]["DIRECT_SOURCE"] != d["routes"]["PANEL"]
    assert d["dlt_calibration"]["median_dlt_to_market_days"] == 491.0
    # Thin Prime is an ACCESS class only, never an Industrial Position.
    assert "THIN_PRIME" in d["access_classes"]
    assert "THIN_PRIME" not in d["industrial_position_classes"]
    assert "ECONOMIC_BENEFIT" in d["industrial_position_classes"]


def test_domains_sources_nz_shows_gets_prohibited(capsys):
    assert main(["domains", "sources", "NZ"]) == 0
    status = json.loads(capsys.readouterr().out)
    by_id = {s["id"]: s for s in status["sources"]}
    assert by_id["nz_gets"]["national_activation"] == "PROHIBITED"
    assert by_id["nz_gets"]["live_activatable"] is False
    assert by_id["nz_mod"]["replay_derived_permitted"] is True


def test_domains_show_au_exposes_national_truth(capsys):
    assert main(["domains", "show", "AU"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["routes"]["FMS"] != d["routes"]["GTG"]
    assert d["dlt_calibration"]["median_dlt_to_market_days"] == 654.5
    assert "AIC_ALIGNED" in d["industrial_position_classes"]
