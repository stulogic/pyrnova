"""National brief closes the AU chain to the shared customer product (→ BRIEF) without a country fork."""

from __future__ import annotations

from pyrnova.decision_lead_time import TemporalAnchors
from pyrnova.domains import get_domain
from pyrnova.domains.brief import render_national_brief
from pyrnova.domains.pipeline import (
    NationalEvidence, NationalOpportunity, assess_access, derive_material_change_fixture, to_decision,
)


def _au_decision():
    au = get_domain("AU")
    ev = NationalEvidence("au-ev-003", "au_defence_iip", "2020-08-15", "APPROVAL_GATE", "FMS")
    mc = derive_material_change_fixture(au, ev, as_of="2024-01-01", important_miss_kind="FMS_GTG_MOVEMENT",
                                        mc_id="au-fms-case")
    acc = assess_access(au, access_class="TEAMING_PARTNER", industrial_position="FOREIGN_OWNED_LOCALLY_PRESENT")
    opp = NationalOpportunity(mc, acc, "eval-au")
    anchors = TemporalAnchors("2020-08-15", "2020-08-20", None, None, "2020-09-01", "2022-06-01")
    return au, to_decision(au, opp, anchors=anchors, as_of="2024-01-01")


def test_national_brief_preserves_au_truth():
    au, dec = _au_decision()
    brief = render_national_brief(au, dec, customer_name="Evaluation Target AU")
    # National meaning is present and not flattened into a US ontology.
    assert "Australia (AU)" in brief
    assert "FMS" in brief and "Foreign Military Sales" in brief
    assert "FOREIGN_OWNED_LOCALLY_PRESENT" in brief
    assert "TEAMING_PARTNER" in brief
    # SOURCE FACT vs PYRNOVA DERIVED is stated; DLT from the shared engine is shown.
    assert "PYRNOVA DERIVED" in brief and "SOURCE FACT" in brief
    assert "decision lead time" in brief.lower()
    # Cited national calibration appears (not fabricated inline).
    assert "654.5" in brief and "PYRNOVA-AU-SPEC-001" in brief
    # The distinctions are stated.
    assert "not itself an Opportunity" in brief
