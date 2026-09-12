"""Integrity checks for the evaluation-only Phase 1.5 industrial replay pack.

These tests validate research fixtures only. They do not import or alter the production
pipeline, scoring policy, source adapters, or Phase 1 replay corpora.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


PACK = Path(__file__).parents[1] / "examples" / "replay" / "industrial_phase1_5"
INVENTORY = PACK / "source_inventory_v1.json"
CORPUS = PACK / "corpus_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def test_source_inventory_is_versioned_hashed_and_rights_bounded():
    inventory = _load(INVENTORY)
    assert inventory["schema_version"] == "industrial_source_inventory_v1"
    assert inventory["extraction_version"] == "manual_structured_fact_v1"
    sources = inventory["sources"]
    assert len(sources) == 27
    assert len({source["source_id"] for source in sources}) == len(sources)

    permitted_retention_states = {
        "RETENTION_ALLOWED",
        "METADATA_REFERENCE_ONLY",
        "METADATA_REFERENCE_AND_STRUCTURED_FACTS",
        "EXCERPT_STRUCTURED_FACTS_ONLY",
        "INTERNAL_ARCHIVAL_PENDING_REVIEW",
        "PROHIBITED_UNAPPROVED",
    }
    for source in sources:
        assert source["canonical_url"].startswith("https://")
        assert source["available_at"]
        assert source["available_at_precision"] in {"DAY", "SECOND"}
        if source["first_observed_at"] is not None:
            assert source["available_at_precision"] == "SECOND"
            assert _instant(source["first_observed_at"]) == _instant(source["available_at"])
        assert source["retrieval_date"] == "2026-09-12"
        assert source["content_hash_scope"] == "UTF-8 retained_evidence_span"
        expected_hash = hashlib.sha256(
            source["retained_evidence_span"].encode("utf-8")
        ).hexdigest()
        assert source["content_sha256"] == expected_hash
        assert source["source_artifact_sha256"] is None
        assert source["rights"]["retention_status"] in permitted_retention_states
        assert source["rights"]["basis"]


def test_corpus_has_seven_ready_cases_and_only_approved_semantics():
    corpus = _load(CORPUS)
    cases = corpus["cases"]
    assert len(cases) == 7
    assert {case["case_id"] for case in cases} == {
        "intel_ohio",
        "tsmc_arizona",
        "micron_new_york",
        "hyundai_georgia",
        "toyota_north_carolina_battery",
        "lilly_lebanon_indiana",
        "novo_nordisk_north_carolina",
    }
    assert all(case["status"] == "REPLAY_READY" for case in cases)

    allowed = corpus["vocabularies"]
    assessment_ids = set()
    for case in cases:
        minimum_cutoffs = 3 if case["tier"] == "PRIMARY" else 2
        assert len(case["cutoff_assessments"]) >= minimum_cutoffs
        assert case["identity"]["facility_basis"]
        for relationship in case["identity"]["relationships"]:
            assert relationship["predicate"] in allowed["relationship"]
            assert relationship["source_ids"]
        for assessment in case["cutoff_assessments"]:
            assert assessment["assessment_id"] not in assessment_ids
            assessment_ids.add(assessment["assessment_id"])
            call = assessment["prospective_call"]
            assert call["direction"] in allowed["direction"]
            assert call["magnitude_band"] in allowed["magnitude_band"]
            assert call["time_horizon"] in allowed["time_horizon"]
            assert call["uncertainties"]
            assert call["falsifiers"]


def test_each_cutoff_excludes_future_evidence_and_freezes_prior_calls():
    inventory = _load(INVENTORY)
    available = {
        source["source_id"]: _instant(source["available_at"])
        for source in inventory["sources"]
    }
    corpus = _load(CORPUS)
    assessment_ids = {
        assessment["assessment_id"]
        for case in corpus["cases"]
        for assessment in case["cutoff_assessments"]
    }
    outcome_ids = set()

    for case in corpus["cases"]:
        for assessment in case["cutoff_assessments"]:
            cutoff = _instant(assessment["as_of"])
            assert set(assessment["visible_source_ids"]).isdisjoint(
                assessment["excluded_future_source_ids"]
            )
            assert all(available[source_id] <= cutoff for source_id in assessment["visible_source_ids"])
            assert all(available[source_id] > cutoff for source_id in assessment["excluded_future_source_ids"])
        for outcome in case["later_outcomes"]:
            assert outcome["outcome_id"] not in outcome_ids
            outcome_ids.add(outcome["outcome_id"])
            assert outcome["resolves_assessment_id"] in assessment_ids
            resolved = next(
                assessment
                for assessment in case["cutoff_assessments"]
                if assessment["assessment_id"] == outcome["resolves_assessment_id"]
            )
            assert _instant(outcome["observed_at"]) > _instant(resolved["as_of"])


def test_negative_controls_cover_required_falsification_classes():
    corpus = _load(CORPUS)
    controls = corpus["negative_controls"]
    assert {control["kind"] for control in controls} == {
        "FUTURE_EVIDENCE_REJECTED",
        "DUPLICATE_UNDERLYING_EVENT",
        "AMENDED_REVISED_ARTIFACT",
        "FACILITY_NAME_COLLISION",
        "COMPANY_NAME_CHANGE_IDENTITY_SURVIVES",
        "LARGE_ANNOUNCEMENT_NO_SELLER_MECHANISM",
        "OUT_OF_PROFILE_GEOGRAPHY",
        "OUT_OF_PROFILE_CAPABILITY",
        "MACRO_AGGREGATE_NOT_COMPANY_EVENT",
        "UNSUPPORTED_SUPPLIER_CUSTOMER_INFERENCE",
        "HEADLINE_VALUE_EXCEEDS_NEAR_TERM_ADDRESSABILITY",
    }
    assert all(control["expected_result"] for control in controls)

    all_relationships = [
        relationship
        for case in corpus["cases"]
        for relationship in case["identity"]["relationships"]
    ]
    assert not any(
        relationship["predicate"] == "SUPPLIES_TO"
        and "synthetic" in (relationship["subject"] + relationship["object"]).lower()
        for relationship in all_relationships
    )


def test_facility_ids_are_stable_and_not_forced_together():
    cases = _load(CORPUS)["cases"]
    facility_ids = [case["identity"]["facility_id"] for case in cases]
    assert len(facility_ids) == len(set(facility_ids))
    assert all(facility_id.startswith("facility:us-") for facility_id in facility_ids)
    assert all(case["identity"]["facility_basis"] for case in cases)
