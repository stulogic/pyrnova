"""M15 — Operations Panel threat view (thin, additive, read-only, empty-safe)."""

from __future__ import annotations

from pyrnova import threat
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore


def _console(tmp_path):
    store = StateStore(tmp_path / "state")
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    return store, OperatorConsole(store, profiles, tmp_path / "out")


def test_threat_panel_empty_safe(tmp_path):
    _store, console = _console(tmp_path)
    view = console.threat_operations()
    assert view["configured"] is False
    assert view["active_threat_count"] == 0
    assert view["company_threat_surfaces"] == []


def test_threat_panel_surfaces_persisted_threats(tmp_path):
    store, console = _console(tmp_path)
    awards = [{"source_ref": "usa:a", "available_at": "2020-01-01", "recipient_uei": "UEI1",
               "program_key": "prog:x", "program_name": "X", "amount_usd": 30_000_000}]
    exposures = threat.incumbency_exposures("co_sub", "Sub", "UEI1", awards)
    recs = [{"catalyst_kind": "recompete", "program_key": "prog:x", "available_at": "2024-01-01",
             "source_ref": "s", "displacement_signal": "set_aside_change", "evidence_strength": 4}]
    threats, rejections = threat.assess_threats("co_sub", "Sub", exposures, recs)
    threat.persist_exposures(store, exposures)
    threat.persist_threats(store, threats, rejections)

    view = console.threat_operations()
    assert view["configured"] is True
    assert view["active_threat_count"] == 1
    assert view["by_mechanism"]["INCUMBENT_DISPLACEMENT"] == 1
    assert view["by_severity"]["HIGH"] == 1
    assert view["exposure_confirmed"] >= 1
    assert len(view["company_threat_surfaces"]) == 1
    assert view["company_threat_surfaces"][0]["subject_ref"] == "co_sub"
    # operator can see WHY: the threat carries its economic effect + evidence
    assert view["threats"][0]["economic_effect"]
    assert view["threats"][0]["evidence_ids"]


def test_threat_panel_filters_by_subject(tmp_path):
    store, console = _console(tmp_path)
    for ref, uei in (("co_a", "UEIA"), ("co_b", "UEIB")):
        awards = [{"source_ref": f"usa:{ref}", "available_at": "2020-01-01", "recipient_uei": uei,
                   "program_key": f"prog:{ref}", "amount_usd": 30_000_000}]
        exps = threat.incumbency_exposures(ref, ref, uei, awards)
        recs = [{"catalyst_kind": "recompete", "program_key": f"prog:{ref}", "available_at": "2024-01-01",
                 "source_ref": "s", "displacement_signal": "protest", "evidence_strength": 4}]
        t, r = threat.assess_threats(ref, ref, exps, recs)
        threat.persist_threats(store, t, r)
    assert console.threat_operations("co_a")["active_threat_count"] == 1
    assert console.threat_operations()["active_threat_count"] == 2
