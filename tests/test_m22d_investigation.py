"""M22-D honesty gate: company/program investigation + deterministic entity search.

Covers the M22-D acceptance priorities (see ``docs/specs/M22D_INVESTIGATION_SEARCH.md`` §24): exact
identifier resolution; ambiguous name handling with no silent canonicalization; canonical-object linkage;
Material Change → entity/program navigation; relationship temporal validity; evidence-reference
preservation; customer-overlay isolation; no outcome future leakage; deterministic search ordering;
sparse-entity honest rendering; company/program read-projection correctness; and that no runtime LLM is
invoked for ordinary search/pages.

Uses the REAL M22-A/B/C archived-evidence demo fixture (SAIC, Torch, DAP + its native-id parent) plus a
small synthetic estate for the two-same-named-entities (ambiguity) and CIK/CAGE identifier cases — no
fabrication of intelligence into the tracked corpus.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from pyrnova import investigation as inv
from pyrnova.investigation import (
    build_estate,
    company_intelligence,
    program_intelligence,
    search,
)
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"


def _load(name):
    return [json.loads(l) for l in (STATE / name).read_text().splitlines() if l.strip()]


@pytest.fixture
def estate():
    return build_estate(threats=_load("threats.jsonl"),
                        propagated_threats=_load("propagated_threats.jsonl"))


def _load_seeder():
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _console(tmp_path, *, access_check=None):
    cstore = StateStore(tmp_path / "cust")
    _load_seeder().seed(cstore)
    mc = StateStore(STATE)
    return OperatorConsole(StateStore(tmp_path / "s"), tmp_path / "p", tmp_path / "o",
                           mc_store=mc, customer_store=cstore, access_check=access_check)


# ---- a small synthetic estate for ambiguity + CIK/CAGE (no fabrication into the tracked corpus) ----

def _synthetic_estate():
    def thr(tid, ref, name, program, agency, evidence):
        return {"id": tid, "subject_ref": ref, "subject_name": name, "mechanism": "PROGRAM_CONTRACTION",
                "severity": "MODERATE", "confidence": "HIGH", "status": "ACTIVE",
                "available_at": "2025-01-01", "evidence_ids": evidence,
                "meta": {"affected_program": program, "agency": agency, "catalyst_class": "MODELED"}}
    threats = [
        thr("t_a1", "co_acme_defense", "Acme Corporation", "AAA111PROG", "Army", ["cik:0000111111"]),
        thr("t_a2", "co_acme_marine", "Acme Corporation", "BBB222PROG", "Navy", ["cage:1ABC2"]),
    ]
    return build_estate(threats=threats)


# ================================================================ (1) exact identifier resolution

def test_exact_pyrnova_entity_id(estate):
    r = search(estate, "co_saic")
    assert r["resolution"] == inv.RESOLUTION_EXACT
    assert r["match_basis"] == inv.MATCH_ENTITY_ID
    assert r["results"][0]["link"] == {"company": "co_saic"}


def test_exact_uei_resolves_native_parent_and_child(estate):
    parent = search(estate, "KMSLVW1MZWU9")
    child = search(estate, "YR7CLZFGCM95")
    assert parent["resolution"] == inv.RESOLUTION_EXACT and parent["match_basis"] == inv.MATCH_UEI
    assert parent["results"][0]["key"] == "co_uei_KMSLVW1MZWU9"
    assert child["results"][0]["key"] == "co_dap_sub"  # child UEI came from the SUBSIDIARY_OF provenance


def test_exact_contract_id_resolves_to_program(estate):
    r = search(estate, "47QFSA20F0057")
    assert r["resolution"] == inv.RESOLUTION_EXACT
    assert r["match_basis"] == inv.MATCH_PROGRAM_ID
    assert r["results"][0]["type"] == inv.KIND_PROGRAM


def test_exact_cik_and_cage(_=None):
    est = _synthetic_estate()
    cik = search(est, "0000111111")
    cage = search(est, "1ABC2")
    assert cik["resolution"] == inv.RESOLUTION_EXACT and cik["match_basis"] == inv.MATCH_CIK
    assert cage["resolution"] == inv.RESOLUTION_EXACT and cage["match_basis"] == inv.MATCH_CAGE


def test_exact_identifier_search_uses_no_llm(estate, monkeypatch):
    # Deterministic search must never import/invoke the LLM helper. Poison it and confirm search is clean.
    import pyrnova.ai as ai
    for attr in dir(ai):
        if callable(getattr(ai, attr, None)) and not attr.startswith("__"):
            monkeypatch.setattr(ai, attr, lambda *a, **k: (_ for _ in ()).throw(AssertionError("LLM invoked")))
    assert search(estate, "co_saic")["resolution"] == inv.RESOLUTION_EXACT
    assert search(estate, "Torch Technologies")["resolution"] == inv.RESOLUTION_EXACT


# ================================================================ (2) ambiguity + no silent canonicalization

def test_ambiguous_name_shows_all_never_merges():
    est = _synthetic_estate()
    r = search(est, "Acme Corporation")
    assert r["resolution"] == inv.RESOLUTION_AMBIGUOUS
    keys = {x["key"] for x in r["results"]}
    assert keys == {"co_acme_defense", "co_acme_marine"}  # two Acmes -> two results, distinct canonical refs


def test_real_dap_name_variants_are_ambiguous(estate):
    # The real DAP child and its native-id parent carry near-identical names; they are two canonical
    # entities and must be surfaced as two, not silently merged.
    r = search(estate, "DAP Construction Management")
    assert r["resolution"] == inv.RESOLUTION_AMBIGUOUS
    assert {x["key"] for x in r["results"]} == {"co_dap_sub", "co_uei_KMSLVW1MZWU9"}


def test_alias_exact_match(estate):
    # The parent entity's stored name has a comma variant; matching it exactly still resolves.
    r = search(estate, "DAP CONSTRUCTION MANAGEMENT, LLC")
    assert r["resolution"] in (inv.RESOLUTION_EXACT, inv.RESOLUTION_AMBIGUOUS)


def test_nonexistent_and_malformed_are_unresolved(estate):
    assert search(estate, "no-such-entity-xyz")["resolution"] == inv.RESOLUTION_UNRESOLVED
    assert search(estate, "")["resolution"] == inv.RESOLUTION_UNRESOLVED
    assert search(estate, "   ")["resolution"] == inv.RESOLUTION_UNRESOLVED
    assert search(estate, "!!!")["resolution"] == inv.RESOLUTION_UNRESOLVED


def test_search_ordering_is_deterministic(estate):
    a = search(estate, "DAP Construction Management")
    b = search(estate, "DAP Construction Management")
    assert [x["key"] for x in a["results"]] == [x["key"] for x in b["results"]]


# ================================================================ (4) canonical linkage

def test_results_point_to_canonical_objects(estate):
    for q in ("co_saic", "KMSLVW1MZWU9", "47QFSA20F0057"):
        r = search(estate, q)
        for res in r["results"]:
            link = res["link"]
            key = link.get("company") or link.get("program")
            assert key in estate.entities or key in estate.programs


# ================================================================ (3)(11)(12) read-projection correctness

def test_company_page_sections_present(estate):
    page = company_intelligence(estate, "co_saic")
    assert page["identity"]["canonical_name"] == "SCIENCE APPLICATIONS INTERNATIONAL CORPORATION"
    assert page["current_intelligence"]["count"] == 1
    assert any(g["program_key"] == "47QFSA20F0057" for g in page["government_activity"])
    assert any(r["relation"] == "SUBCONTRACTOR_OF" and r["related_ref"] == "co_torch"
               for r in page["relationships"])
    assert page["evidence"] and page["material_history"]


def test_program_page_lists_evidenced_companies(estate):
    page = program_intelligence(estate, "47QFSA20F0057")
    refs = {c["ref"] for c in page["companies"]}
    assert refs == {"co_saic", "co_torch"}
    assert page["program_identity"]["agency"] == "General Services Administration"


def test_unknown_ref_raises_keyerror(estate):
    with pytest.raises(KeyError):
        company_intelligence(estate, "co_nope")
    with pytest.raises(KeyError):
        program_intelligence(estate, "NOPROG")


# ================================================================ (12) sparse / UNKNOWN honest rendering

def test_sparse_entity_states_unknowns_honestly(estate):
    page = company_intelligence(estate, "co_saic")  # SAIC has no UEI/CAGE/CIK stored in the demo
    gaps = " ".join(page["intelligence_gaps"]).lower()
    assert "no uei" in gaps and "cage" in gaps and "cik" in gaps
    assert page["identity"]["identifiers"] == {}  # honestly empty, never fabricated


def test_evidence_is_reference_only(estate):
    page = company_intelligence(estate, "co_saic")
    for e in page["evidence"]:
        assert set(e) == {"evidence_id", "source", "type"}  # references, not bodies


# ================================================================ (7)(10) temporal truth

def test_future_intelligence_not_shown_historically():
    # The DAP termination (and the SUBSIDIARY_OF edge it exercises) is knowable 2026-08-31; before that
    # neither the change nor the edge appears.
    est = build_estate(propagated_threats=_load("propagated_threats.jsonl"), as_of="2026-01-01")
    assert inv._edges_touching(est, "co_uei_KMSLVW1MZWU9", as_of="2026-01-01") == []
    est2 = build_estate(propagated_threats=_load("propagated_threats.jsonl"), as_of="2026-09-01")
    assert any(e["relation"] == "SUBSIDIARY_OF"
               for e in inv._edges_touching(est2, "co_uei_KMSLVW1MZWU9", as_of="2026-09-01"))


def test_relationship_validity_window_respected(estate):
    # A relationship whose validity has not begun (or has ended) at the cutoff is not shown.
    estate.entities.setdefault("co_x", {"canonical_name": "X"})
    estate.entities.setdefault("co_y", {"canonical_name": "Y"})
    estate.edges = [{"relation": "SUBCONTRACTOR_OF", "from_ref": "co_x", "to_ref": "co_y",
                     "valid_from": "2030-01-01", "valid_to": None, "evidence_ids": []}]
    assert inv._edges_touching(estate, "co_x", as_of="2025-01-01") == []      # not yet in effect
    assert inv._edges_touching(estate, "co_x", as_of="2031-01-01")            # in effect later
    estate.edges[0].update(valid_from="2020-01-01", valid_to="2022-01-01")
    assert inv._edges_touching(estate, "co_x", as_of="2025-01-01") == []      # already ended


def test_entity_not_knowable_before_its_event_absent_from_search():
    est = build_estate(threats=_load("threats.jsonl"), as_of="2020-01-01")
    # SAIC's threat is knowable 2024-05-06; DAP's 2026-08-31 — neither entity exists in a 2020 estate.
    assert search(est, "co_saic")["resolution"] == inv.RESOLUTION_UNRESOLVED


# ================================================================ (5)(6) Material Change -> investigation

def test_material_change_carries_investigation_links(tmp_path):
    console = _console(tmp_path)
    feed = console.material_changes("torch")["material_changes"]
    assert feed
    for c in feed:
        nav = c["investigation"]
        assert nav["company"]["ref"] in console._build_estate().entities
        if nav["program"]:
            assert nav["program"]["key"] in console._build_estate().programs


def test_console_search_and_pages(tmp_path):
    console = _console(tmp_path)
    assert console.search("co_saic")["resolution"] == inv.RESOLUTION_EXACT
    page = console.company_intelligence("co_torch")
    assert page["identity"]["ref"] == "co_torch"
    prog = console.program_intelligence("47QFSA20F0057")
    assert prog["program_identity"]["program_key"] == "47QFSA20F0057"


# ================================================================ (9) customer-overlay isolation

def test_customer_overlay_isolated_and_authorized(tmp_path):
    console = _console(tmp_path)
    page = console.company_intelligence("co_torch", customer="torch")
    cc = page["customer_context"]
    assert cc["customer_id"] == "torch" and cc["watched"] and cc["relation"] == "DIRECT_SUBJECT"
    # A global request (no customer) exposes NO customer context at all.
    assert "customer_context" not in console.company_intelligence("co_torch")


def test_company_page_never_leaks_another_customers_state(tmp_path):
    console = _console(tmp_path)
    # co_saic is Torch's WATCHED entity but is not DAP's. DAP's overlay must not show Torch's changes.
    dap_view = console.company_intelligence("co_saic", customer="dap")
    torch_ids = set(console.company_intelligence("co_saic", customer="torch")["customer_context"]["related_material_change_ids"])
    dap_ids = set(dap_view["customer_context"]["related_material_change_ids"])
    assert dap_ids.isdisjoint(torch_ids) or not dap_ids  # DAP sees none of Torch's private related changes


def test_access_check_blocks_unauthorized_customer_overlay(tmp_path):
    console = _console(tmp_path, access_check=lambda cid: cid == "torch")
    # Authorized customer overlay works.
    assert console.company_intelligence("co_torch", customer="torch")["customer_context"]["watched"]
    # An unauthorized customer overlay is rejected at the access seam (§23).
    with pytest.raises(PermissionError):
        console.company_intelligence("co_torch", customer="dap")


# ================================================================ (14) prior behavior unaffected

def test_global_pages_have_no_customer_context_by_default(estate):
    assert "customer_context" not in company_intelligence(estate, "co_saic")
    assert "customer_context" not in program_intelligence(estate, "47QFSA20F0057")
