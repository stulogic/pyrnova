from pathlib import Path

import pytest

from pyrnova.config import Config
from pyrnova.operator import OperatorService, ProfileStore, ReviewStore, RunStore
from pyrnova.state import StateStore


def _service(tmp_path):
    repo = Path(__file__).resolve().parent.parent
    config = Config(
        sam_api_key="",
        archive_backend="local",
        archive_dir=tmp_path / "archive",
        s3_endpoint_url="",
        s3_bucket="",
        s3_access_key_id="",
        s3_secret_access_key="",
        s3_region="auto",
        database_url="",
        state_dir=tmp_path / "state",
        out_dir=tmp_path / "out",
    )
    state = StateStore(config.state_dir)
    return OperatorService(
        config=config,
        profiles=ProfileStore(repo / "examples" / "profiles"),
        runs=RunStore(config.state_dir / "operator_runs"),
        reviews=ReviewStore(state),
        fixtures_dir=repo / "tests" / "fixtures",
    )


def test_fixture_run_has_profiles_sources_summary_and_candidates(tmp_path):
    service = _service(tmp_path)
    ids = {p["id"] for p in service.profiles.list()}
    assert {"torch_technologies", "modern_technology_solutions"} <= ids

    result = service.create_run(
        {"profile_id": "torch_technologies", "mode": "fixtures", "min_amount": 0}
    )
    assert result["status"] == "complete"
    assert {s["source"] for s in result["source_status"]} == {"sam", "usaspending"}
    assert result["summary"]["awards_retrieved"] > 0
    assert result["summary"]["sam_notices_retrieved"] > 0
    assert result["candidates"]
    candidate = result["candidates"][0]
    assert candidate["candidate_id"]
    assert candidate["evidence"][0]["source_id"]
    assert candidate["machine_state"] in {"SUGGESTED_STRIKE", "MACHINE_REJECTED"}


def test_reviews_are_append_only_and_machine_scores_are_preserved(tmp_path):
    service = _service(tmp_path)
    result = service.create_run({"profile_id": "torch_technologies", "mode": "fixtures"})
    candidate = result["candidates"][0]
    original = candidate["attractiveness"]
    common = {
        "candidate_id": candidate["candidate_id"],
        "quality": "POSSIBLE",
        "pursuit_posture": "TEAM",
        "decision": "HOLD",
        "analyst_note": "Needs incumbent check",
        "falsification": "Vehicle access unknown",
        "revised_attractiveness": 0.4,
    }
    service.save_review(result["id"], common)
    service.save_review(result["id"], {**common, "quality": "STRONG", "decision": "APPROVE"})

    reopened = service.get_run(result["id"])
    assert len(reopened["review_history"]) == 2
    assert reopened["latest_reviews"][candidate["candidate_id"]]["decision"] == "APPROVE"
    assert reopened["candidates"][0]["attractiveness"] == original
    assert reopened["latest_reviews"][candidate["candidate_id"]]["machine_scores"]["attractiveness"] == original


def test_brief_contains_only_selected_approved_strikes(tmp_path):
    service = _service(tmp_path)
    result = service.create_run({"profile_id": "torch_technologies", "mode": "fixtures"})
    first, second = result["candidates"][:2]
    for candidate, decision in ((first, "APPROVE"), (second, "HOLD")):
        service.save_review(
            result["id"],
            {
                "candidate_id": candidate["candidate_id"],
                "quality": "STRONG" if decision == "APPROVE" else "POSSIBLE",
                "pursuit_posture": "PRIME",
                "decision": decision,
                "analyst_note": "Reviewed",
                "falsification": candidate["falsification"],
            },
        )

    exported = service.generate_brief(result["id"], [first["candidate_id"]])
    text = Path(exported["path"]).read_text()
    assert first["title"] in text
    assert second["title"] not in text
    assert "PENDING HUMAN REVIEW" not in text
    with pytest.raises(ValueError):
        service.generate_brief(result["id"], [second["candidate_id"]])


def test_stable_candidate_ids_across_equivalent_runs(tmp_path):
    service = _service(tmp_path)
    options = {"profile_id": "torch_technologies", "mode": "fixtures", "as_of": "2025-01-15"}
    first = service.create_run(options)
    second = service.create_run(options)
    assert {c["candidate_id"] for c in first["candidates"]} == {
        c["candidate_id"] for c in second["candidates"]
    }


def test_invalid_adjudication_is_rejected(tmp_path):
    service = _service(tmp_path)
    result = service.create_run({"profile_id": "torch_technologies", "mode": "fixtures"})
    with pytest.raises(ValueError):
        service.save_review(
            result["id"],
            {
                "candidate_id": result["candidates"][0]["candidate_id"],
                "quality": "MAYBE",
                "pursuit_posture": "PRIME",
                "decision": "APPROVE",
            },
        )
