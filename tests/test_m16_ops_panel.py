"""M16 — Operations Panel propagation + selectivity views (thin, additive, empty-safe)."""

from __future__ import annotations

from pyrnova import propagation, selectivity, threat
from pyrnova.models import Threat
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore
from pyrnova.threat import threat_id


def _console(tmp_path):
    store = StateStore(tmp_path / "state")
    (tmp_path / "profiles").mkdir()
    return store, OperatorConsole(store, tmp_path / "profiles", tmp_path / "out")


def test_propagation_view_empty_safe(tmp_path):
    _store, console = _console(tmp_path)
    view = console.threat_propagation_view()
    assert view["configured"] is False
    assert view["propagated_threat_count"] == 0


def test_propagation_view_surfaces_paths(tmp_path):
    store, console = _console(tmp_path)
    seed = Threat(subject_ref="co_a", subject_name="A", mechanism="PROGRAM_CANCELLATION_OR_DELAY",
                  confidence="HIGH", severity="HIGH", evidence_ids=["ev:root"], catalyst_id="cat")
    seed.id = threat_id("co_a", "PROGRAM_CANCELLATION_OR_DELAY", "root")
    edges = [{"from_ref": "co_a", "to_ref": "co_b", "to_name": "B", "relation": "SUBCONTRACTOR_OF",
              "link_class": "CONFIRMED", "evidence_ids": ["ev:a-b"], "available_at": "2024-01-01"},
             {"from_ref": "co_a", "to_ref": "co_c", "to_name": "C", "relation": "SUBSTITUTE_FOR",
              "link_class": "CONFIRMED", "evidence_ids": ["ev:a-c"], "available_at": "2024-01-01"}]
    res = propagation.propagate_threats([seed], edges)
    propagation.persist_propagation(store, res)

    view = console.threat_propagation_view()
    assert view["configured"] is True
    assert view["propagated_threat_count"] == 1
    assert view["beneficiary_opportunity_count"] == 1
    assert view["max_propagation_depth"] == 1
    assert view["propagated_threats"][0]["path"]      # provenance visible
    assert view["propagated_threats"][0]["root_threat_id"] == seed.id


def test_selectivity_view_passthrough():
    monitored = [{"ref": "co", "name": "Co", "counterparty_records": [
        {"source_ref": "r", "available_at": "2023-01-01", "relation": "SUPPLIER",
         "counterparty_name": "Ordinary Widgets"}]}]
    res = selectivity.run_selectivity(monitored, raw_event_count=1000, stream_name="s")
    view = OperatorConsole.selectivity_view(res)
    assert view["funnel"]["raw_events"] == 1000
    assert view["funnel"]["threats_emitted"] == 0
    assert view["stream"] == "s"
