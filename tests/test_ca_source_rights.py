"""CA source-rights state (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, CA vertical, boundary D).

Historical / public accessibility is NOT production authorization. This proves the Canadian source families
are codified fail-closed at BOTH governance layers, that only the CanadaBuys downloadable-dataset family is
permitted for a derived customer projection (live production still denied pending licence verification), and
that the caution families (CanadaBuys portal / DND-CAF web / Canada.ca / DCB / parliamentary / third-party
mirror) fail closed (UNKNOWN => DENY). No live-source activation without explicit rights authority.
"""

from __future__ import annotations

import pytest

from pyrnova.domains import get_domain
from pyrnova.domains.base import SourceActivation
from pyrnova.domains.fanout import build_national_opportunity_record
from pyrnova.domains.pipeline import (
    NationalEvidence, NationalOpportunity, assess_access, derive_material_change_fixture,
)
from pyrnova.sources.rights import SourceRightsDenied, authorize_derived_projection, authorize_request

_FIXTURE = ("ca_canadabuys_dataset",)
_DECLARED = ("ca_canadabuys_portal", "ca_dnd_web", "ca_canada_ca", "ca_dcb", "ca_parliament",
             "ca_thirdparty_mirror")


def test_ca_source_families_codified():
    ca = get_domain("CA")
    for sid in _FIXTURE:
        assert ca.source(sid).activation is SourceActivation.FIXTURE_ONLY
        assert ca.is_ingestible(sid) is False  # FIXTURE_ONLY is not live-ingestible
    for sid in _DECLARED:
        assert ca.source(sid).activation is SourceActivation.DECLARED
        assert ca.is_ingestible(sid) is False


def test_canadabuys_dataset_replay_derived_permitted_but_live_denied():
    for sid in _FIXTURE:
        d = authorize_derived_projection({"id": "x", "evidence": {"sources": [sid]}})
        assert d.allowed is True and d.reason_code == "ALLOWED"
        # Live transport is denied (licence not verified): no live-source activation without rights.
        with pytest.raises(SourceRightsDenied) as ei:
            authorize_request(sid, "GET", "https://canadabuys.canada.ca/")
        assert ei.value.reason_code == "STATE_INGEST_DISABLED"


def test_declared_caution_families_fail_closed_both_layers():
    ca = get_domain("CA")
    for sid in _DECLARED:
        # Registry layer: no reviewed rights profile => derived use denied.
        d = authorize_derived_projection({"id": "x", "evidence": {"sources": [sid]}})
        assert d.allowed is False
        # National → tenant bridge: a DECLARED source cannot back a customer projection.
        ev = NationalEvidence(f"{sid}-e", sid, "2020-01-01", "FORECAST", "OPEN_COMPETITIVE")
        mc = derive_material_change_fixture(ca, ev, as_of="2025-06-01", mc_id=f"ca-mc-{sid}",
                                            consequential_change_kind="OPPORTUNITY_CREATED",
                                            mechanism="COMPETITIVE_OPEN")
        acc = assess_access(ca, access_class="OPEN_COMPETITION", industrial_position="UNKNOWN")
        with pytest.raises(PermissionError):
            build_national_opportunity_record(ca, NationalOpportunity(mc, acc, "eval-ca"), evidence=[ev],
                                              subject_ref="co_eval_ca", subject_name="x", title="x",
                                              as_of="2025-06-01")


def test_portal_scraping_not_presumed_even_though_dataset_is_fixture_permitted():
    # The downloadable-dataset family is FIXTURE_ONLY / replay-derived permitted, but CanadaBuys PORTAL
    # scraping rights are a SEPARATE determination and are NOT presumed (DECLARED => DENY).
    ca = get_domain("CA")
    assert ca.source("ca_canadabuys_dataset").activation is SourceActivation.FIXTURE_ONLY
    assert ca.source("ca_canadabuys_portal").activation is SourceActivation.DECLARED
    d = authorize_derived_projection({"id": "x", "evidence": {"sources": ["ca_canadabuys_portal"]}})
    assert d.allowed is False


def test_unknown_source_denied():
    ca = get_domain("CA")
    assert ca.source("ca_not_a_real_source") is None
    assert ca.is_ingestible("ca_not_a_real_source") is False  # UNKNOWN => DENY
