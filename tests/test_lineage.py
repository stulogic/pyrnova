"""B2.1 — focused intra-stage procurement lineage tests (ugly-case coverage)."""

from pyrnova.chains import resolve_chain, signals_from_records
from pyrnova.lineage import resolve_procurement_lineage

PK = "army:radar-sustainment"


def _lineage(records):
    return resolve_procurement_lineage(signals_from_records(records))


def _rec(ref, pid, ntype, when, *, prior=None, contradicts=False):
    r = {"source_id": "sam_opportunities", "source_ref": ref, "stage": "PROCUREMENT",
         "program_key": PK, "available_at": when, "summary": ntype, "procurement_id": pid,
         "notice_type": ntype}
    if prior:
        r["prior_procurement_id"] = prior
    if contradicts:
        r["contradicts"] = True
    return r


def test_multiple_amendments_sequence_within_one_instance():
    lin = _lineage([
        _rec("s", "SOL-A", "solicitation", "2025-01-01"),
        _rec("a1", "SOL-A", "amendment", "2025-01-10"),
        _rec("a2", "SOL-A", "amendment", "2025-02-01"),
    ])
    assert [r.predicate for r in lin.relationships] == ["AMENDS", "AMENDS"]
    inst = lin.instance_for("SOL-A")
    assert inst.disposition == "open" and inst.live is True
    assert len(inst.notice_ids) == 3  # every source event retained


def test_recompete_is_a_distinct_instance_not_a_merge():
    lin = _lineage([
        _rec("s1", "SOL-A", "solicitation", "2024-01-01"),
        _rec("aw", "SOL-A", "award_notice", "2024-06-01"),
        _rec("s2", "SOL-B", "recompete", "2029-01-01", prior="SOL-A"),
    ])
    assert lin.metrics()["procurement_instances"] == 2
    assert any(r.predicate == "RECOMPETES" for r in lin.relationships)
    # The recompete is the current competition; the original is not merged into it.
    assert lin.current_instance(PK).procurement_id == "SOL-B"
    assert lin.instance_for("SOL-A").procurement_id != lin.instance_for("SOL-B").procurement_id


def test_amendment_after_cancellation_reinstates_without_deleting_history():
    lin = _lineage([
        _rec("s", "SOL-A", "solicitation", "2025-01-01"),
        _rec("c", "SOL-A", "cancellation", "2025-02-01", contradicts=True),
        _rec("a", "SOL-A", "amendment", "2025-03-01"),
    ])
    inst = lin.instance_for("SOL-A")
    assert inst.disposition == "open" and inst.live is True   # reinstated by the later amendment
    assert {r.predicate for r in lin.relationships} == {"CANCELS", "AMENDS"}
    assert len(inst.notice_ids) == 3   # the cancellation event is still retained


def test_reissue_referencing_unknown_predecessor_stays_ambiguous():
    lin = _lineage([
        _rec("s2", "SOL-B", "reissue", "2025-05-01", prior="SOL-GHOST"),
    ])
    # No known predecessor => no invented REISSUES edge; the instance still exists and is live.
    assert all(r.predicate != "REISSUES" for r in lin.relationships)
    assert lin.instance_for("SOL-B").live is True
    assert lin.instance_for("SOL-B").reissue_of is None


def test_cancelled_current_instance_marks_program_not_live():
    res = resolve_chain(signals_from_records([
        _rec("s", "SOL-A", "solicitation", "2025-01-01"),
        _rec("c", "SOL-A", "cancellation", "2025-02-01", contradicts=True),
    ]))
    assert res.confidence["procurement_live"] is False
    assert res.lineage.instance_for("SOL-A").cancelled_at == "2025-02-01"
