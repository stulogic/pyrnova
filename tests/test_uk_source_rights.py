"""UK source-rights state (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, UK vertical, boundary D).

Historical accessibility is NOT production authorization. This proves the UK source families are codified
fail-closed at BOTH governance layers, that only the OGL/structured replay-evidence families are permitted
for a derived customer projection (live production still denied), and that the specific caution families
(DSP / SSRO / NAO / attachments-VDR / supplier material / archive-mirror) fail closed (UNKNOWN => DENY).
"""

from __future__ import annotations

import pytest

from pyrnova.domains import get_domain
from pyrnova.domains.base import SourceActivation
from pyrnova.domains.fanout import build_national_opportunity_record
from pyrnova.domains.pipeline import (
    NationalEvidence, NationalOpportunity, assess_access, derive_material_change_fixture,
)
from pyrnova.sources.rights import (
    SourceRightsDenied, authorize_derived_projection, authorize_request,
)

_FIXTURE = ("uk_contracts_finder", "uk_gov_uk")
_DECLARED = ("uk_dsp", "uk_ssro", "uk_nao", "uk_vdr_attachments", "uk_supplier_material", "uk_archive_mirror")


def test_uk_source_families_codified():
    uk = get_domain("GB")
    for sid in _FIXTURE:
        assert uk.source(sid).activation is SourceActivation.FIXTURE_ONLY
        assert uk.is_ingestible(sid) is False  # FIXTURE_ONLY is not live-ingestible
    for sid in _DECLARED:
        assert uk.source(sid).activation is SourceActivation.DECLARED
        assert uk.is_ingestible(sid) is False


def test_ogl_replay_derived_permitted_but_live_denied():
    for sid in _FIXTURE:
        d = authorize_derived_projection({"id": "x", "evidence": {"sources": [sid]}})
        assert d.allowed is True and d.reason_code == "ALLOWED"
        with pytest.raises(SourceRightsDenied) as ei:
            authorize_request(sid, "GET", f"https://www.gov.uk/" if sid == "uk_gov_uk"
                              else "https://www.find-tender.service.gov.uk/")
        assert ei.value.reason_code == "STATE_INGEST_DISABLED"


def test_declared_caution_families_fail_closed_both_layers():
    uk = get_domain("GB")
    for sid in _DECLARED:
        # Registry layer: no reviewed rights profile => derived use denied.
        d = authorize_derived_projection({"id": "x", "evidence": {"sources": [sid]}})
        assert d.allowed is False
        # National → tenant bridge: a DECLARED source cannot back a customer projection.
        ev = NationalEvidence(f"{sid}-e", sid, "2020-01-01", "TENDER", "OPEN")
        mc = derive_material_change_fixture(uk, ev, as_of="2024-01-01", mc_id=f"gb-mc-{sid}",
                                            consequential_change_kind="OPPORTUNITY_CREATED")
        acc = assess_access(uk, access_class="OPEN_COMPETITION", industrial_position="UK_PRIME")
        with pytest.raises(PermissionError):
            build_national_opportunity_record(uk, NationalOpportunity(mc, acc, "eval-uk"), evidence=[ev],
                                              subject_ref="co_eval_uk", subject_name="x", title="x",
                                              as_of="2024-01-01")


def test_attachments_do_not_inherit_notice_rights():
    # A tender-attachment / VDR family is DECLARED and denied even though the notice index is FIXTURE_ONLY:
    # attachments do NOT inherit notice rights automatically.
    uk = get_domain("GB")
    assert uk.source("uk_contracts_finder").activation is SourceActivation.FIXTURE_ONLY
    assert uk.source("uk_vdr_attachments").activation is SourceActivation.DECLARED
    d = authorize_derived_projection({"id": "x", "evidence": {"sources": ["uk_vdr_attachments"]}})
    assert d.allowed is False
