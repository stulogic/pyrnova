"""B1.5 — opportunity-lifecycle characterization/regression tests.

These pin the *launch-adequate* current behavior (one commercial identity across the capital ->
procurement -> award lifecycle, point-in-time AS-OF history, source-event identity preserved) and
characterize the known intra-stage limitation so a Bundle-2 lineage change updates this file deliberately.
No architecture change is made here; see docs/evidence/bundle1/B1_5_LIFECYCLE_VALIDATION.md.
"""

from pyrnova.chains import resolve_chain, signals_from_records

PK = "disa:cloud-modernization"

# Same program evolving through stages, including intra-PROCUREMENT amendment/cancel/reissue/recompete.
LIFECYCLE = [
    {"source_id": "appropriations", "source_ref": "b1", "stage": "AUTHORIZATION", "program_key": PK,
     "available_at": "2025-02-01", "summary": "budget"},
    {"source_id": "acquisition_forecast", "source_ref": "f1", "stage": "MARKET_ENGAGEMENT", "program_key": PK,
     "available_at": "2025-04-01", "summary": "forecast"},
    {"source_id": "sam_opportunities", "source_ref": "ss1", "stage": "MARKET_ENGAGEMENT", "program_key": PK,
     "available_at": "2025-05-01", "summary": "sources sought"},
    {"source_id": "sam_opportunities", "source_ref": "sol1", "stage": "PROCUREMENT", "program_key": PK,
     "available_at": "2025-07-01", "summary": "solicitation"},
    {"source_id": "sam_opportunities", "source_ref": "sol1-amd1", "stage": "PROCUREMENT", "program_key": PK,
     "available_at": "2025-07-15", "summary": "amendment 1"},
    {"source_id": "sam_opportunities", "source_ref": "sol1-cancel", "stage": "PROCUREMENT", "program_key": PK,
     "available_at": "2025-08-20", "summary": "cancellation", "contradicts": True},
    {"source_id": "sam_opportunities", "source_ref": "sol2", "stage": "PROCUREMENT", "program_key": PK,
     "available_at": "2025-10-01", "summary": "reissue"},
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


# --- CHARACTERIZATION of the known intra-stage gap (Bundle-2 will change these) -----------------

def test_intra_stage_lifecycle_is_currently_flat_known_gap():
    """KNOWN GAP (Bundle 2): amendment / cancellation / reissue are peer PROCUREMENT notices with no
    supersession/amendment linkage between them, and the cancellation is currently inert. This test
    documents present behavior truthfully; it is expected to be updated when intra-stage lineage lands.
    """
    res = _resolve(LIFECYCLE)
    m = res.metrics()
    # The cancellation does not (yet) register as a contradiction or supersede the solicitation.
    assert m["contradictions"] == 0
    assert m["chain_confidence"]["contradicted"] is False
    # No intra-stage (PROCUREMENT->PROCUREMENT) relationship links sol1 -> amd1 -> cancel -> sol2.
    intra = [r for r in res.relationships
             if getattr(r, "predicate", None) in {"AMENDS", "SUPERSEDES", "REISSUES", "CANCELS"}]
    assert intra == []
