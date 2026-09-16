"""NZ hard source-rights / GETS enforcement (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, NZ vertical, boundary D).

GETS IS NOT A PYRNOVA INGESTION SOURCE. This proves the hard lock fails closed at BOTH independent
governance layers and that no path can accidentally activate it — national domain (acquisition activation)
and the source-rights registry (transport / derived use / customer display). It also proves the NZ
candidate source families are codified fail-closed (UNKNOWN => DENY), distinguishing access from retention /
commercial use / customer display, with only the lawful historical/replay evidence family permitted for a
derived customer projection (live production still denied).
"""

from __future__ import annotations

import pytest

from pyrnova.domains import get_domain
from pyrnova.domains.base import ProhibitedSourceIngestion, SourceActivation
from pyrnova.domains.fanout import build_national_opportunity_record
from pyrnova.domains.pipeline import (
    NationalEvidence, NationalOpportunity, assess_access,
    derive_material_change, derive_material_change_fixture,
)
from pyrnova.sources.rights import (
    SourceRightsDenied, authorize_derived_projection, authorize_request, gate_customer_display,
)


# --- Layer 1: national domain — GETS is PROHIBITED for acquisition activation ----------------------

def test_gets_hard_lock_national_layer_fails_closed():
    nz = get_domain("NZ")
    assert nz.source("nz_gets").activation is SourceActivation.PROHIBITED
    assert nz.is_ingestible("nz_gets") is False
    with pytest.raises(ProhibitedSourceIngestion):
        nz.assert_ingestible("nz_gets")
    ev = NationalEvidence("g1", "nz_gets", "2020-01-01", "AWARD", "OPEN")
    # Neither the live nor the fixture/replay derive path may touch a prohibited source.
    with pytest.raises(ProhibitedSourceIngestion):
        derive_material_change_fixture(nz, ev, as_of="2021-01-01")
    with pytest.raises((ProhibitedSourceIngestion, PermissionError)):
        derive_material_change(nz, ev, as_of="2021-01-01")


def test_gets_cannot_be_projected_into_the_customer_product():
    """No accidental activation: a GETS-backed opportunity fails closed at the national → tenant bridge."""
    nz = get_domain("NZ")
    # Build a material change from a lawful source, then swap in GETS evidence at the projection edge.
    ev_ok = NationalEvidence("m1", "nz_mod", "2020-01-01", "APPROACH_TO_MARKET", "OPEN")
    mc = derive_material_change_fixture(nz, ev_ok, as_of="2024-01-01", mc_id="nz-mc-guard")
    acc = assess_access(nz, access_class="INCUMBENT", industrial_position="SOVEREIGN_CAPABILITY")
    gets_ev = NationalEvidence("g2", "nz_gets", "2020-01-01", "APPROACH_TO_MARKET", "OPEN",
                              payload={"source_ref": "nz:nz_gets:x"})
    with pytest.raises(ProhibitedSourceIngestion):
        build_national_opportunity_record(nz, NationalOpportunity(mc, acc, "eval-nz"), evidence=[gets_ev],
                                          subject_ref="co_eval_nz", subject_name="x", title="x",
                                          as_of="2024-01-01")


# --- Layer 2: source-rights registry — GETS is hard-denied for transport / derived / display -------

def test_gets_hard_lock_registry_layer_fails_closed():
    # Live transport denied (BLACK class).
    with pytest.raises(SourceRightsDenied) as ei:
        authorize_request("nz_gets", "GET", "https://www.gets.govt.nz/")
    assert ei.value.reason_code == "CLASS_BLACK"
    # Derived projection denied.
    d = authorize_derived_projection({"id": "x", "evidence": {"sources": ["nz_gets"]}})
    assert d.allowed is False and d.reason_code == "CLASS_BLACK"
    # Customer display denied.
    disp = gate_customer_display({"id": "x", "evidence": {"sources": ["nz_gets"]}}, source_ids=["nz_gets"])
    assert disp["source_rights"]["display"] == "BLOCKED"


# --- NZ candidate source families codified fail-closed, access != retention/commercial/display ------

def test_nz_mod_replay_derived_permitted_but_live_denied():
    # Derived customer projection from lawful historical/replay evidence is permitted...
    d = authorize_derived_projection({"id": "x", "evidence": {"sources": ["nz_mod"]}})
    assert d.allowed is True and d.reason_code == "ALLOWED"
    # ...but LIVE transport (production ingestion) is denied: access != production activation.
    with pytest.raises(SourceRightsDenied) as ei:
        authorize_request("nz_mod", "GET", "https://www.defence.govt.nz/")
    assert ei.value.reason_code == "STATE_INGEST_DISABLED"


def test_declared_civil_and_caution_families_fail_closed():
    nz = get_domain("NZ")
    for sid in ("nz_treasury", "nz_linz", "nz_greater_wellington", "nz_police", "nz_nzta"):
        # National layer: DECLARED (UNKNOWN => DENY).
        assert nz.is_ingestible(sid) is False
        # Registry layer: no reviewed rights profile => derived use denied.
        d = authorize_derived_projection({"id": "x", "evidence": {"sources": [sid]}})
        assert d.allowed is False
        # A DECLARED source cannot back a customer projection at the national → tenant bridge.
        ev = NationalEvidence(f"{sid}-e", sid, "2020-01-01", "APPROACH_TO_MARKET", "OPEN")
        mc = derive_material_change_fixture(nz, ev, as_of="2024-01-01", mc_id=f"nz-mc-{sid}")
        acc = assess_access(nz, access_class="NO_ESTABLISHED_ACCESS", industrial_position="ECONOMIC_BENEFIT")
        with pytest.raises(PermissionError):
            build_national_opportunity_record(nz, NationalOpportunity(mc, acc, "eval-nz"), evidence=[ev],
                                              subject_ref="co_eval_nz", subject_name="x", title="x",
                                              as_of="2024-01-01")
