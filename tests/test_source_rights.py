"""Fail-closed source-rights boundary contracts."""

import pytest
import hashlib
import json
from dataclasses import replace

from pyrnova.archive import LocalEvidenceArchive

from pyrnova.sources.registry import (
    REGISTRY,
    RightsClass,
    RightsState,
    SourcePolicy,
    SourceSpec,
    StorageMode,
)
from pyrnova.sources.rights import (
    ProhibitedSourcePayload,
    SourceRightsDenied,
    authorize_model_input,
    authorize_request,
    authorize_source_url,
    authorize_derived_projection,
    gate_customer_display,
    guarded_model_call,
    representation_for_storage,
    screen_payload,
)
from pyrnova.sources import http


def _profile(source_id="corporate_test", *, state=RightsState.CURRENTLY_APPROVED,
             rights_class=RightsClass.GREEN_WITH_CONDITIONS, storage=StorageMode.NORMALIZED_ONLY,
             display="permitted_current_policy_only"):
    return SourcePolicy(
        identity=source_id, domain="corp.example", source_type="corporate_disclosure",
        basis="Owner-approved constrained structured source profile", reviewed_at="2026-01-01",
        review_due_at="2099-01-01", commercial_use="owner_approved_constrained_structured_use",
        automated_access="explicit_domain_profile", raw_storage=storage,
        historical_retention="retain_hash_and_reviewed_representation",
        retention_rule="retain hash and reviewed representation; never delete history",
        fact_use="structured_facts_only", derived_use="permitted_derived_with_attribution",
        excerpt_use="limited_excerpt_with_attribution", excerpt_rule="25 words with URL and attribution",
        fulltext_use="denied", redistribution="denied", attribution="required",
        customer_display=display, model_use="structured_only", model_processing_allowed=True,
        model_constraints=("structured facts or permitted derived content only", "retain attribution"),
        third_party_use="unknown", licence="unknown", rights_class=rights_class, state=state,
        licence_required=False,
        allowed_hosts=("corp.example",), allowed_methods=("GET",), allowed_path_prefixes=("/api/",),
        attribution_text="Corporate source", max_excerpt_words=25,
    )


@pytest.fixture
def corporate_profile(monkeypatch):
    spec = SourceSpec(
        id="corporate_test", name="Corporate test", base_url="https://corp.example/api/v1",
        rights="unknown", retention_tier="A", active=False, source_policy=_profile(),
    )
    monkeypatch.setitem(REGISTRY, "corporate_test", spec)
    return spec


def test_unknown_black_red_and_wrong_endpoint_fail_closed():
    with pytest.raises(SourceRightsDenied) as unknown:
        authorize_request("missing", "GET", "https://example.invalid/anything")
    assert unknown.value.reason_code == "UNKNOWN_SOURCE"
    assert not authorize_request("usaspending", "POST", "https://api.usaspending.gov/api/v2/search/spending_by_award/").allowed is False
    for restricted in ("reuters", "bloomberg", "linkedin", "x"):
        with pytest.raises(SourceRightsDenied):
            authorize_request(restricted, "GET", "https://example.invalid/")
    with pytest.raises(SourceRightsDenied):
        authorize_request("sam_opportunities", "GET", "https://sam.gov/workspace/contract/1")


def test_amber_and_denied_automation_or_commercial_use_never_authorize(monkeypatch):
    amber = _profile("amber_test", rights_class=RightsClass.AMBER)
    monkeypatch.setitem(REGISTRY, "amber_test", SourceSpec(
        id="amber_test", name="Amber", base_url="https://corp.example/api/v1",
        rights="unknown", retention_tier="A", active=False, source_policy=amber,
    ))
    with pytest.raises(SourceRightsDenied) as exc:
        authorize_request("amber_test", "GET", "https://corp.example/api/v1/item")
    assert exc.value.reason_code == "AMBER_RESTRICTED"
    for field in ("commercial_use", "automated_access"):
        values = {"commercial_use": "denied", "automated_access": "denied"}
        bad = _profile("bad_" + field)
        object.__setattr__(bad, field, values[field])
        monkeypatch.setitem(REGISTRY, "bad_" + field, SourceSpec(
            id="bad_" + field, name="Bad", base_url="https://corp.example/api/v1",
            rights="unknown", retention_tier="A", active=False, source_policy=bad,
        ))
        with pytest.raises(SourceRightsDenied):
            authorize_request("bad_" + field, "GET", "https://corp.example/api/v1/item")


def test_recursive_payload_screen_is_conservative():
    assert screen_payload({"description": "ordinary CUI word"}).allowed
    with pytest.raises(ProhibitedSourcePayload):
        from pyrnova.sources.rights import validate_source_payload
        validate_source_payload("sam_opportunities", {"nested": {"parent_duns": "1"}})
    with pytest.raises(ProhibitedSourcePayload):
        from pyrnova.sources.rights import validate_source_payload
        validate_source_payload("sam_opportunities", {"handling": "CUI"})


def test_normalized_only_is_allowlisted_and_does_not_store_raw(corporate_profile):
    stored, meta = representation_for_storage(
        "corporate_test", b'{"fulltext":"never store"}',
        normalized={"id": "c1", "name": "Example", "status": "active"},
        metadata={"source_ref": "c1"}, source_url="https://corp.example/api/v1/c1",
        excerpt="A short permitted excerpt", attribution="Corporate source",
    )
    assert b"fulltext" not in stored
    assert meta["representation"] == "NORMALIZED_ONLY"
    with pytest.raises(SourceRightsDenied):
        representation_for_storage("corporate_test", b"{}", normalized={"foo": "bar"}, metadata={})
    with pytest.raises(SourceRightsDenied):
        representation_for_storage("corporate_test", b'{"parent_duns":"x"}', normalized={"id": "c1"})


def test_display_disabled_retains_only_refs_and_history_diagnostic(monkeypatch):
    spec = SourceSpec(
        id="display_disabled_test", name="Display disabled", base_url="https://corp.example/api/v1",
        rights="unknown", retention_tier="A", active=False,
        source_policy=_profile("display_disabled_test", state=RightsState.DISPLAY_DISABLED,
                               display="disabled"),
    )
    monkeypatch.setitem(REGISTRY, "display_disabled_test", spec)
    result = gate_customer_display({
        "id": "mc-1", "title": "source prose", "assessment": {"mechanism": "derived prose"},
        "refs": {"evidence_ids": ["ev-1"]}, "provenance": {"archive_hash": "abc"},
        "source_id": "display_disabled_test",
    })
    assert result["source_rights"]["display"] == "BLOCKED"
    assert result["id"] == "mc-1" and result["refs"] == {"evidence_ids": ["ev-1"]}
    assert "title" not in result and "assessment" not in result


def test_mixed_unknown_source_blocks_source_material():
    result = gate_customer_display({
        "id": "mc-1", "event_summary": "prose", "source_ids": ["usaspending", "unknown"],
        "refs": {"subject_ref": "entity:1"},
    })
    assert result["source_rights"]["display"] == "BLOCKED"
    assert result["id"] == "mc-1" and result["refs"] == {"subject_ref": "entity:1"}
    assert "event_summary" not in result


def test_display_excerpt_is_bounded_and_source_url_must_match():
    too_long = gate_customer_display({
        "id": "mc-1", "source_id": "usaspending", "source_url": "https://api.usaspending.gov/api/v2/search/",
        "attribution": "USAspending", "excerpt": "word " * 200,
    })
    assert too_long["source_rights"]["display"] == "BLOCKED"
    wrong_host = gate_customer_display({
        "id": "mc-1", "source_id": "usaspending", "source_url": "https://example.invalid/",
        "attribution": "USAspending", "excerpt": "short excerpt",
    })
    assert wrong_host["source_rights"]["display"] == "BLOCKED"


def test_model_gate_rejects_raw_and_callback_kwargs_before_invocation():
    called = []
    with pytest.raises(SourceRightsDenied):
        guarded_model_call(lambda *_a, **_k: called.append(True), source_ids=["usaspending"], value=b"raw")
    with pytest.raises(SourceRightsDenied):
        guarded_model_call(lambda *_a, **_k: called.append(True), source_ids=["usaspending"],
                           value={"representation": "NORMALIZED_ONLY", "normalized": {"id": "1"}},
                           source_text="forbidden")
    with pytest.raises(SourceRightsDenied):
        guarded_model_call(lambda *_a, **_k: called.append(True), source_ids=["usaspending"],
                           value={"representation": "NORMALIZED_ONLY", "normalized": {"id": "1"},
                                  "raw_response": "full page"})
    with pytest.raises(SourceRightsDenied):
        guarded_model_call(lambda *_a, **_k: called.append(True), source_ids=["usaspending"],
                           value={"representation": "DERIVED", "derived": {"raw": "full page"},
                                  "evidence_ids": ["ev"]})
    assert called == []
    assert authorize_model_input(["usaspending"], {
        "representation": "NORMALIZED_ONLY", "source_id": "usaspending",
        "normalized": {"id": "1", "amount_usd": 2},
    }).allowed


def test_authorized_usa_spending_raw_structured_response_succeeds():
    raw = b'{"results":[{"Award ID":"A-1"}]}'
    stored, meta = representation_for_storage("usaspending", raw)
    assert stored == raw
    assert meta["representation"] == "RAW_ALLOWED"


def test_public_reference_url_does_not_authorize_html_retrieval():
    assert authorize_source_url(
        "usaspending", "https://www.usaspending.gov/award/A-1"
    ).allowed
    with pytest.raises(SourceRightsDenied):
        authorize_request("usaspending", "GET", "https://www.usaspending.gov/award/A-1")


def test_derived_fanout_requires_known_source_and_rejects_source_content():
    projection = {
        "id": "mc-1", "observed": {"event_summary": "structured fact"},
        "assessment": {"mechanism": "derived"},
        "evidence": {"sources": ["usaspending"], "evidence_ids": ["usaspending:txn:1"]},
    }
    assert authorize_derived_projection(projection).allowed
    denied = authorize_derived_projection({**projection, "fulltext": "page"})
    assert not denied.allowed and denied.reason_code == "SOURCE_CONTENT_DENIED"


def test_shared_http_requires_source_id_before_session(monkeypatch):
    monkeypatch.setattr(http, "_session", lambda: (_ for _ in ()).throw(AssertionError("session called")))
    with pytest.raises(SourceRightsDenied) as exc:
        http.get_json("https://api.usaspending.gov/api/v2/search/spending_by_award/", {})
    assert exc.value.reason_code == "SOURCE_ID_REQUIRED"


def test_archive_persists_normalized_content_and_retrieval_snapshot(corporate_profile, monkeypatch, tmp_path):
    archive = LocalEvidenceArchive(tmp_path)
    raw = json.dumps({"description": "PROHIBITED_COPY_SENTINEL" * 300}).encode()
    ev = archive.put(raw, source_id="corporate_test", retention_tier="A",
                     normalized={"id": "1", "amount_usd": 2},
                     source_url="https://corp.example/api/v1/1")
    stored = archive.get(ev.content_sha256, ev.source_id)
    assert b"PROHIBITED_COPY_SENTINEL" not in b"".join(p.read_bytes() for p in tmp_path.rglob("*") if p.is_file())
    assert hashlib.sha256(stored).hexdigest() == ev.content_sha256
    assert json.loads(stored)["original_content_sha256"] == hashlib.sha256(raw).hexdigest()
    sidecar = json.loads(next(tmp_path.rglob("*.observations.jsonl")).read_text())
    assert sidecar["source_rights_class_at_retrieval"] == ev.source_rights_class_at_retrieval
    assert sidecar["source_policy_version"] == ev.source_policy_version
    assert sidecar["retrieved_at"] == ev.retrieved_at and ev.retrieved_at
    monkeypatch.setitem(REGISTRY, "corporate_test", replace(corporate_profile,
        source_policy=replace(corporate_profile.policy, state=RightsState.DISPLAY_DISABLED)))
    assert archive.get(ev.content_sha256, ev.source_id) == stored
    assert gate_customer_display({"id": "1", "source_id": "corporate_test", "title": "fact"})["source_rights"]["display"] == "BLOCKED"
    assert json.loads(next(tmp_path.rglob("*.observations.jsonl")).read_text()) == sidecar


def test_no_storage_and_restricted_archive_writes_leave_no_material(corporate_profile, monkeypatch, tmp_path):
    monkeypatch.setitem(REGISTRY, "corporate_test", replace(corporate_profile,
        source_policy=replace(corporate_profile.policy, raw_storage=StorageMode.NO_STORAGE)))
    archive = LocalEvidenceArchive(tmp_path)
    for source_id in ("corporate_test", "reuters", "linkedin", "missing"):
        with pytest.raises(SourceRightsDenied):
            archive.put(b'{"id":"1"}', source_id=source_id, retention_tier="A", normalized={"id": "1"})
    assert not list(tmp_path.rglob("*"))


@pytest.mark.parametrize("field", ["parentDuns", "DUNSNumber", "dnbUltimateParent"])
def test_legacy_camel_case_fields_are_denied(field):
    from pyrnova.sources.rights import validate_source_payload
    with pytest.raises(ProhibitedSourcePayload):
        validate_source_payload("sam_opportunities", {"nested": {field: "123"}})


@pytest.mark.parametrize("delta", [
    {"state": RightsState.RIGHTS_DEGRADED}, {"state": RightsState.LICENSE_EXPIRED},
    {"review_due_at": "2000-01-01"},
    {"licence_required": True, "licence": "test licence", "licence_reference": "test",
     "licence_valid_until": "2000-01-01"},
])
def test_degraded_expired_and_overdue_rights_block_all_uses(corporate_profile, monkeypatch, delta):
    monkeypatch.setitem(REGISTRY, "corporate_test", replace(corporate_profile,
        source_policy=replace(corporate_profile.policy, **delta)))
    with pytest.raises(SourceRightsDenied):
        authorize_request("corporate_test", "GET", "https://corp.example/api/v1")
    assert gate_customer_display({"id": "1", "source_id": "corporate_test", "title": "fact"})["source_rights"]["display"] == "BLOCKED"
    assert not authorize_derived_projection({"id": "1", "source_id": "corporate_test"}).allowed
    assert not authorize_model_input(["corporate_test"], {
        "source_id": "corporate_test", "representation": "NORMALIZED_ONLY", "normalized": {"id": "1"}}).allowed


def test_model_unknown_boolean_and_nested_source_content_deny_callback(corporate_profile, monkeypatch):
    called = []
    value = {"source_id": "corporate_test", "representation": "NORMALIZED_ONLY", "normalized": {"id": "1"}}
    monkeypatch.setitem(REGISTRY, "corporate_test", replace(corporate_profile,
        source_policy=replace(corporate_profile.policy, model_processing_allowed="false")))
    with pytest.raises(SourceRightsDenied):
        guarded_model_call(lambda *_a, **_kw: called.append(True), source_ids=["corporate_test"], value=value)
    monkeypatch.setitem(REGISTRY, "corporate_test", corporate_profile)
    with pytest.raises(SourceRightsDenied):
        guarded_model_call(lambda *_a, **_kw: called.append(True), source_ids=["corporate_test"], value={
            "source_id": "corporate_test", "representation": "DERIVED", "evidence_ids": ["ev"],
            "derived": {"assessment_code": {"raw_response": "copied document"}}})
    assert called == []


def test_approved_connectors_pass_identity_to_real_http_gate(monkeypatch):
    from types import SimpleNamespace
    from pyrnova.sources.usaspending import USAspendingClient
    from pyrnova.sources.ofac import OfacClient
    from pyrnova.sources.sam import SamClient
    calls = []
    class Session:
        def post(self, url, **kw):
            calls.append((url, kw))
            return SimpleNamespace(status_code=200, content=b'{"results":[]}', headers={})
        def get(self, url, **kw):
            calls.append((url, kw))
            raw = b'{"opportunitiesData":[]}' if "sam.gov" in url else b''
            return SimpleNamespace(status_code=200, content=raw, headers={})
    monkeypatch.setattr(http, "_session", Session)
    USAspendingClient().search_awards(action_date_start="2026-01-01", action_date_end="2026-01-02")
    OfacClient().fetch_list()
    SamClient("fixture-key").search_observations(posted_from="01/01/2026", posted_to="01/02/2026")
    assert len(calls) == 3 and all(kw["allow_redirects"] is False for _, kw in calls)
    with pytest.raises(SourceRightsDenied):
        http.get_json("https://sam.gov/opp/1", {}, source_id="sam_opportunities")
    assert len(calls) == 3


def test_customer_raw_and_unbounded_expression_cannot_use_attribution_to_bypass(corporate_profile, monkeypatch):
    base = {"id": "1", "source_id": "corporate_test", "source_url": "https://corp.example/api/v1/1",
            "attribution": "Corporate source"}
    for content in ({"raw_response": "copied page"}, {"description": "word " * 200}):
        assert gate_customer_display({**base, **content})["source_rights"]["display"] == "BLOCKED"
    monkeypatch.setitem(REGISTRY, "corporate_test", replace(corporate_profile,
        source_policy=replace(corporate_profile.policy, customer_display="permitted_unknown_scope")))
    assert gate_customer_display({**base, "excerpt": "brief fact"})["source_rights"]["display"] == "BLOCKED"
