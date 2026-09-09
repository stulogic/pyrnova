"""M14 — Operations Panel source-mesh + cross-source-chains readout (thin, additive)."""

from __future__ import annotations

from pyrnova.cross_source import persist_chain
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore


def _console(tmp_path):
    store = StateStore(tmp_path / "state")
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    return store, OperatorConsole(store, profiles, tmp_path / "out",
                                  source_state_dir=tmp_path / "srcstate")


def test_panel_groups_sources_into_families(tmp_path):
    _store, console = _console(tmp_path)
    ops = console.source_operations()
    assert ops["configured"] is True
    families = {f["family"] for f in ops["families"]}
    # The broader mesh includes the M14 additions across distinct economic domains.
    assert {"sanctions_trade", "science_rd", "procurement_spend",
            "corporate_intelligence"} <= families
    for f in ops["families"]:
        assert set(f) >= {"family", "sources", "operational", "calls_made", "calls_avoided"}
        assert f["sources"], "each family lists at least one source"


def test_panel_surfaces_recent_cross_source_chains(tmp_path):
    store, console = _console(tmp_path)
    assert console.source_operations()["cross_source_chains"] == []
    persist_chain(
        store,
        {"families": ["sbir", "usaspending"], "cross_family_accepted_joins": [{}, {}],
         "rejected_weak_joins": [{}], "deferred_joins": [],
         "chain_confidence": {"value": 0.6}, "lead_time_days": 2495},
        chain_id="chainA", title="SBIR R&D -> USAspending procurement (Torch)",
    )
    chains = console.source_operations()["cross_source_chains"]
    assert len(chains) == 1
    assert chains[0]["id"] == "chainA"
    assert chains[0]["families"] == ["sbir", "usaspending"]
    assert chains[0]["cross_family_accepted"] == 2
    assert chains[0]["lead_time_days"] == 2495


def test_unconfigured_panel_is_unchanged(tmp_path):
    # No source_state_dir -> the M12 exact-shape contract is preserved (no new keys leak in).
    store = StateStore(tmp_path / "state")
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    console = OperatorConsole(store, profiles, tmp_path / "out")
    assert console.source_operations() == {"configured": False, "source_count": 0, "sources": []}
