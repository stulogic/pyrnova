from pyrnova.contribution import SourceContributionLedger, measure_replay_source_contribution


def test_source_contribution_snapshot_keeps_unknowns_and_source_separation():
    ledger = SourceContributionLedger()
    grants = ledger.source("grants_gov")
    grants.raw_records = 3
    grants.normalized_events = 2
    grants.duplicates_removed = 1
    grants.candidates_enriched = 1
    grants.evidence_levels.update({3: 1, 4: 1})
    grants.lead_time_days_gained.extend([30, 60])

    snapshot = ledger.snapshots()["grants_gov"]
    assert snapshot["candidates_created"] == 0
    assert snapshot["median_lead_time_gain_days"] == 45
    assert snapshot["evidence_level_contribution"] == {3: 1, 4: 1}


def test_replay_source_contribution_uses_leave_one_source_out():
    case = {
        "case_id": "source-ablation", "mechanism_family": "procurement",
        "replay_as_of": "2024-02-01T00:00:00+00:00",
        "records": [
            {"source_id": "forecast", "source_ref": "F-1", "record_kind": "forecast",
             "available_at": "2024-01-01T00:00:00+00:00", "strength": 3,
             "source_role": "secondary", "url": "https://agency.gov/f-1", "applies_to_candidate": True},
            {"source_id": "sam", "source_ref": "S-1", "record_kind": "solicitation",
             "available_at": "2024-01-20T00:00:00+00:00", "strength": 5,
             "source_role": "primary", "url": "https://sam.gov/s-1", "applies_to_candidate": True},
        ],
        "candidate": {"hypothesis": "award", "relevance": 0.8, "predicted_buyer": "Agency"},
        "expected_affected_entities": ["vendors"], "expected_buyer_program_owner": "Agency",
        "expected_commercial_mechanism": "contract", "expected_disposition": "STRIKE",
        "actual_outcome": {"occurred": True, "kind": "award", "buyer": "Agency",
                           "occurred_at": "2024-03-01T00:00:00+00:00", "source_ref": "A-1"},
        "ground_truth": {"label": "TRUE_POSITIVE", "confidence": "HIGH"},
        "reviewer": "test", "human_adjudication": {"human_decision": "ACCEPT", "reviewer": "test", "reason": "test"},
    }
    report = measure_replay_source_contribution([case])
    assert report["forecast"]["candidates_enriched"] == 1
    assert report["forecast"]["median_lead_time_gain_days"] == 19
    assert report["sam"]["candidates_created"] == 1
    assert report["sam"]["strike_promotions"] == 1
