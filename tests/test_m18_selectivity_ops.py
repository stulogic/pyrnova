"""M18 — the new OBSERVED adverse-event source feeds the SAME selectivity funnel, and the panel surfaces
it. Workstreams N (continuous selectivity), O (call/yield), Q (operations panel). No live calls."""

from __future__ import annotations

from pathlib import Path

from pyrnova.adverse_events import (
    parse_federal_register_adverse,
    regulation_target_ref,
    summarize_adverse_events,
    to_regulatory_catalyst,
)
from pyrnova.ops import OperatorConsole
from pyrnova.relationships import independence_metrics
from pyrnova.selectivity import run_selectivity, source_run_funnel

_FR = Path("examples/real_evidence/federal_register_bis_export_controls.json")


def _observed_catalyst():
    parsed = parse_federal_register_adverse(_FR.read_bytes())
    event = next(e for e in parsed["events"] if e["event_id"] == "2026-17231")
    return parsed, event, to_regulatory_catalyst(event)


def test_export_control_events_flow_through_the_same_selectivity_funnel():
    """A real BIS rule threatens ONLY the monitored company with an evidenced exposure to it; the funnel
    shows the drop from raw events to threats emitted (standards measured, never lowered)."""
    parsed, event, catalyst = _observed_catalyst()
    tref = regulation_target_ref(event)
    monitored = [
        {"ref": "co_parsons", "name": "Parsons Government Services Inc.",
         "exposure_records": [{"relation": "REGULATION", "target_ref": tref, "target_name": "EAR",
                               "deterministic": False, "available_at": "2024-09-17",
                               "source_ref": "usa:subaward:PO-0011221"}]},
        {"ref": "co_unrelated", "name": "Unrelated Widgets Inc.",
         "exposure_records": [{"relation": "REGULATION", "target_ref": "EAR:0694-UNRELATED",
                               "target_name": "unrelated", "deterministic": False,
                               "available_at": "2024-01-01", "source_ref": "x"}]},
    ]
    result = run_selectivity(monitored, catalyst_records=[catalyst],
                             raw_event_count=len(parsed["events"]), as_of="2026-09-01",
                             stream_name="federal_register_export_controls")
    funnel = result["funnel"]
    assert funnel["raw_events"] == 8
    assert funnel["threats_emitted"] == 1           # only the evidenced-exposure company
    assert funnel["zero_threat_rejections"] >= 1    # the unrelated company is a zero-threat rejection

    # Workstream O: decorate with call/yield accounting (archive-once: 1 call made, the rest avoided).
    run = source_run_funnel(result, source_id="federal_register", run_id="m18-fr-1",
                            calls_made=1, calls_avoided=7, records_received=8, changed_records=8)
    assert run["source_id"] == "federal_register"
    assert run["calls_made"] == 1 and run["calls_avoided"] == 7
    assert run["funnel"]["threats_emitted"] == 1


def test_adverse_event_summary_and_panel_view():
    """Workstream Q: the panel surfaces archived OBSERVED catalysts + independence counts (thin)."""
    parsed, _, _ = _observed_catalyst()
    summary = summarize_adverse_events(parsed)
    assert summary["events_total"] == 8
    assert summary["observed_events"] == 8
    assert "Industry and Security Bureau" in summary["by_agency"]

    independence = independence_metrics(
        [{"from_ref": "co_parsons", "to_ref": "co_torch", "relation": "SUBCONTRACTOR_OF"},
         {"from_ref": "co_intuitive", "to_ref": "co_torch", "relation": "SUBCONTRACTOR_OF"}])
    view = OperatorConsole.adverse_catalyst_view(parsed, independence)
    assert view["source_id"] == "federal_register"
    assert view["observed_catalyst_count"] == 8
    assert view["catalysts"][0]["catalyst_class"] == "OBSERVED"
    assert view["relationship_independence"]["unique_company_pairs"] == 2

    # Empty-safe.
    empty = OperatorConsole.adverse_catalyst_view({})
    assert empty["observed_catalyst_count"] == 0
