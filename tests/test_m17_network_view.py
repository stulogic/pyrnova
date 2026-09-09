"""M17 — the company threat network view answers direct + indirect threat exposure through relationships.

Persists a REAL SAIC->Torch propagation chain (from corpus_m17) into the append-only state, then asks
the Operations Panel: for Torch, what indirect threats reach it and through which relationship? And for
SAIC, what is its outbound network footprint? Read-only, empty-safe.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyrnova.ops import OperatorConsole
from pyrnova.propagation import persist_propagation, propagate_threats
from pyrnova.state import StateStore
from pyrnova.threat import (
    assess_threats,
    incumbency_exposures,
    persist_threats,
    threat_outcome_observation,
)

_CORPUS = json.loads(Path("examples/replay/corpus_m17.json").read_text())


def _chain_case():
    return next(c for c in _CORPUS["threat_cases"] if c["case_id"] == "m17-real-propagation-saic-gsa")


def _console(tmp_path):
    return OperatorConsole(StateStore(tmp_path / "state"), tmp_path / "profiles", tmp_path / "out")


def _persist_real_chain(store):
    case = _chain_case()
    subj = case["subject"]
    as_of = case["replay_as_of"]
    exposures = incumbency_exposures(subj["ref"], subj["name"], subj["uei"],
                                     case["award_records"], as_of=as_of)
    threats, _ = assess_threats(subj["ref"], subj["name"], exposures,
                                case["catalyst_records"], as_of=as_of)
    persist_threats(store, threats)
    prop = propagate_threats(threats, case["relationships"], as_of=as_of)
    persist_propagation(store, prop)
    return threats, prop


def test_torch_sees_the_indirect_threat_and_its_relationship_path(tmp_path):
    console = _console(tmp_path)
    _persist_real_chain(console.store)

    view = console.company_threat_network_view("co_torch")
    assert view["configured"] is True
    assert view["direct_threat_count"] == 0            # Torch is not directly hit — it inherits indirectly
    assert view["inbound_propagated_count"] == 1
    hop = view["inbound_propagated"][0]
    assert hop["subject"] == "Torch Technologies Inc"
    assert hop["mechanism"] == "PROGRAM_CONTRACTION"
    assert hop["depth"] == 1
    # The relationship path names the REAL sub-award edge that carried the threat.
    path = hop["relationship_path"]
    assert path and path[-1]["relation"] == "SUBCONTRACTOR_OF"
    assert path[-1]["from_ref"] == "co_saic" and path[-1]["to_ref"] == "co_torch"
    assert hop["evidence_ids"]


def test_saic_sees_its_outbound_network_footprint(tmp_path):
    console = _console(tmp_path)
    threats, _ = _persist_real_chain(console.store)

    view = console.company_threat_network_view("co_saic")
    assert view["direct_threat_count"] == 1            # SAIC is directly threatened
    assert view["outbound_propagated_count"] == 1      # and that threat propagates to one dependent
    assert view["company_threat_surface"]["active_threat_count"] == 1
    root_id = threats[0].id
    assert view["outbound_network"][0]["root_threat_id"] == root_id


def test_outcome_status_surfaced_when_known(tmp_path):
    console = _console(tmp_path)
    threats, _ = _persist_real_chain(console.store)
    # Record an authoritative outcome for SAIC's direct threat.
    obs = threat_outcome_observation(threats[0].id, "MATERIALIZED", "2025-06-01",
                                     "usaspending", "usa:award-to-other", evidence_strength=4)
    console.store.append("threat_outcomes", obs)

    view = console.company_threat_network_view("co_saic")
    assert view["direct_threats"][0]["outcome"]["label"] == "MATERIALIZED"
    assert view["direct_threats"][0]["outcome"]["resolved"] is True


def test_empty_safe_for_unknown_company(tmp_path):
    view = _console(tmp_path).company_threat_network_view("co_nobody")
    assert view["configured"] is False
    assert view["direct_threat_count"] == 0
    assert view["inbound_propagated"] == []
    assert view["company_threat_surface"] is None
