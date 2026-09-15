"""B1.5 — opportunity-lifecycle characterization/regression tests.

These pin the *launch-adequate* current behavior (one commercial identity across the capital ->
procurement -> award lifecycle, point-in-time AS-OF history, source-event identity preserved) and
characterize the known intra-stage limitation so a Bundle-2 lineage change updates this file deliberately.
No architecture change is made here; see docs/evidence/bundle1/B1_5_LIFECYCLE_VALIDATION.md.
"""

from pyrnova.chains import resolve_chain, signals_from_records

PK = "disa:cloud-modernization"

# Same program evolving through stages, including intra-PROCUREMENT amendment/cancel/reissue. The four
# PROCUREMENT notices carry native procurement identity (solicitation number) + typed notice roles so
# B2.1 can sequence them: sol1/amd1/cancel share DISA-CLOUD-25-R-0007; the reissue sol2 is a DISTINCT
# instance (DISA-CLOUD-26-R-0002) that explicitly reissues the cancelled one.
SOL_1 = "DISA-CLOUD-25-R-0007"
SOL_2 = "DISA-CLOUD-26-R-0002"
LIFECYCLE = [
    {"source_id": "appropriations", "source_ref": "b1", "stage": "AUTHORIZATION", "program_key": PK,
     "available_at": "2025-02-01", "summary": "budget"},
    {"source_id": "acquisition_forecast", "source_ref": "f1", "stage": "MARKET_ENGAGEMENT", "program_key": PK,
     "available_at": "2025-04-01", "summary": "forecast"},
    {"source_id": "sam_opportunities", "source_ref": "ss1", "stage": "MARKET_ENGAGEMENT", "program_key": PK,
     "available_at": "2025-05-01", "summary": "sources sought"},
    {"source_id": "sam_opportunities", "source_ref": "sol1", "stage": "PROCUREMENT", "program_key": PK,
     "available_at": "2025-07-01", "summary": "solicitation",
     "procurement_id": SOL_1, "notice_type": "solicitation"},
    {"source_id": "sam_opportunities", "source_ref": "sol1-amd1", "stage": "PROCUREMENT", "program_key": PK,
     "available_at": "2025-07-15", "summary": "amendment 1",
     "procurement_id": SOL_1, "notice_type": "amendment"},
    {"source_id": "sam_opportunities", "source_ref": "sol1-cancel", "stage": "PROCUREMENT", "program_key": PK,
     "available_at": "2025-08-20", "summary": "cancellation", "contradicts": True,
     "procurement_id": SOL_1, "notice_type": "cancellation"},
    {"source_id": "sam_opportunities", "source_ref": "sol2", "stage": "PROCUREMENT", "program_key": PK,
     "available_at": "2025-10-01", "summary": "reissue",
     "procurement_id": SOL_2, "notice_type": "reissue", "prior_procurement_id": SOL_1},
    {"source_id": "usaspending", "source_ref": "aw1", "stage": "AWARD", "program_key": PK,
     "available_at": "2026-01-15", "summary": "award"},
]


def _resolve(records, as_of=None):
    return resolve_chain(signals_from_records(records, as_of=as_of), allow_inferred=True)


# --- LAUNCH-ADEQUATE behavior (protected) ------------------------------------------------------

def test_one_commercial_identity_across_the_lifecycle():
    m = _resolve(LIFECYCLE).metrics()
    # The whole lifecycle is ONE program, not fragmented into disconnected notices.
    assert m["program_keys"] == [PK]
    assert set(m["stages_present"]) == {"AUTHORIZATION", "MARKET_ENGAGEMENT", "PROCUREMENT", "AWARD"}
    assert m["relationships_total"] >= 3  # cross-stage links exist


def test_point_in_time_history_is_honest():
    # Only what was knowable by the cutoff is present; later notices do not leak backward.
    early = _resolve(LIFECYCLE, as_of="2025-07-20").metrics()
    assert "AWARD" not in early["stages_present"]
    assert early["unique_signals"] == 5  # budget, forecast, ss, sol1, amd1
    full = _resolve(LIFECYCLE).metrics()
    assert full["unique_signals"] == 8


def test_source_event_identity_is_preserved_and_true_duplicates_collapse():
    # Distinct notices remain distinct signals (source-event identity preserved)...
    procurement = [s for s in _resolve(LIFECYCLE).signals if s.stage == "PROCUREMENT"]
    assert {s.source_ref for s in procurement} == {"sol1", "sol1-amd1", "sol1-cancel", "sol2"}
    # ...but the SAME notice observed twice collapses (no phantom duplicate).
    dup = LIFECYCLE + [dict(LIFECYCLE[3])]  # observe sol1 again
    assert _resolve(dup).metrics()["duplicates_collapsed"] == 1


# --- B2.1 intra-stage procurement lineage (closes the OUTCOME-C gap) ----------------------------

def test_intra_stage_lineage_sequences_amend_cancel_reissue():
    """Amendment / cancellation / reissue are now linked notice-level lineage, not flat peers."""
    res = _resolve(LIFECYCLE)
    preds = {r.predicate for r in res.relationships}
    assert {"AMENDS", "CANCELS", "REISSUES"} <= preds
    # Two distinct procurement instances of one program; source-event identity preserved.
    procurement = [s for s in res.signals if s.stage == "PROCUREMENT"]
    assert {s.source_ref for s in procurement} == {"sol1", "sol1-amd1", "sol1-cancel", "sol2"}
    assert res.metrics()["lineage"]["procurement_instances"] == 2


def test_cancellation_is_consequential_and_reissue_restarts_liveness():
    # After the cancellation but BEFORE the reissue is knowable: the current procurement is dead.
    mid = _resolve(LIFECYCLE, as_of="2025-09-01")
    assert mid.confidence["procurement_live"] is False
    assert mid.confidence["contradicted"] is True
    assert mid.lineage.current_instance(PK).disposition == "cancelled"
    # All-time: the reissue is a distinct, live instance that restarts the pursuit — history retained.
    full = _resolve(LIFECYCLE)
    assert full.confidence["procurement_live"] is True
    cancelled = full.lineage.instance_for(SOL_1)
    assert cancelled.disposition == "cancelled" and cancelled.reissued_by == SOL_2
    assert full.lineage.current_instance(PK).procurement_id == SOL_2


def test_lineage_is_temporally_honest_under_replay():
    # At 2025-07-20 only sol1 + amd1 are knowable: an AMENDS edge exists, no cancellation yet.
    early = _resolve(LIFECYCLE, as_of="2025-07-20")
    preds = {r.predicate for r in early.relationships}
    assert "AMENDS" in preds and "CANCELS" not in preds and "REISSUES" not in preds
    assert early.confidence["procurement_live"] is True


def test_no_procurement_identity_means_no_invented_lineage():
    # Two PROCUREMENT notices of the same program with NO shared native identity form no lineage.
    ambiguous = [
        {"source_id": "sam_opportunities", "source_ref": "x1", "stage": "PROCUREMENT", "program_key": PK,
         "available_at": "2025-07-01", "summary": "solicitation A"},
        {"source_id": "sam_opportunities", "source_ref": "x2", "stage": "PROCUREMENT", "program_key": PK,
         "available_at": "2025-08-01", "summary": "cancellation B", "notice_type": "cancellation"},
    ]
    res = _resolve(ambiguous)
    assert res.metrics()["lineage"]["lineage_relationships"] == 0
    assert res.confidence["procurement_live"] is None
