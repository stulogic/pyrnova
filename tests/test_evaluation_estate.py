"""PRODUCT-DEMO-001 — the multinational internal evaluation estate.

Guards the properties that make the estate worth having: it is populated through the REAL customer-product
machinery (no demo-only path), it spans every national domain, it is honest about rights and provenance, it
is deterministic and idempotent, and it never leaks into another tenant.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from pyrnova.customers import CustomerProfile, get_customer, upsert_customer
from pyrnova.decision_memory import list_dispositions
from pyrnova.state import StateStore

ESTATE_DIR = Path("examples/evaluation_estate")


def _estate():
    spec = importlib.util.spec_from_file_location(
        "pyrnova_evaluation_estate", ESTATE_DIR / "build_customer_proof.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def estate():
    return _estate()


@pytest.fixture()
def seeded(tmp_path, estate):
    store = StateStore(tmp_path / "state")
    report = estate.seed(store)
    return store, report


# --- provisioning -----------------------------------------------------------------------------------

def test_provisions_one_lens_with_its_monitoring_configuration(seeded, estate):
    store, report = seeded
    profile = get_customer(store, estate.LENS_ID)
    assert profile is not None
    assert profile.name == estate.LENS_NAME
    # An INTERNAL evaluation lens: provenance says so and no external customer is asserted.
    assert profile.provenance == "internal_evaluation"
    assert profile.capabilities and profile.geography
    assert report["customer"]["watches"] == len(estate.WATCHES)


def test_opportunity_count_floor(seeded):
    """The estate must stay populated: a regression that empties it should fail loudly."""
    _, report = seeded
    assert report["materialized"] >= 20


def test_every_national_domain_is_represented(seeded):
    _, report = seeded
    assert set(report["by_country"]) == {"US", "CA", "GB", "AU", "NZ"}
    assert all(count >= 3 for count in report["by_country"].values())


# --- product breadth --------------------------------------------------------------------------------

def _records(estate):
    return estate.build_opportunity_records()["records"]


def test_dispositions_are_varied_including_negative_states(estate):
    states = {r["state"] for r in _records(estate)}
    # A believable estate is not uniformly attractive: live, flagged-for-review, and downgraded all present.
    assert {"candidate", "reviewing", "cancelled"} <= states


def test_mechanism_and_route_breadth(estate):
    records = _records(estate)
    nat = [r["meta"]["national"] for r in records]
    mechanisms = {n["mechanism"] for n in nat if n.get("mechanism")}
    routes = {n["route"] for n in nat if n.get("route")}
    # Canada's five mechanism families are the widest accepted mechanism vocabulary in the estate.
    assert {"COMPETITIVE_OPEN", "DIRECTED_OEM", "FMS_GTG", "STRATEGIC_SOURCE", "DIGITAL_ICT"} <= mechanisms
    assert len(routes) >= 8


def test_cancellation_reissue_and_post_award_are_present(estate):
    records = _records(estate)
    nat = [r["meta"]["national"] for r in records]
    kinds = {n.get("consequential_change_kind") for n in nat} | {n.get("important_miss_kind") for n in nat}
    assert "PROGRAMME_CANCELLED" in kinds and "PROGRAMME_REISSUED" in kinds
    assert "CANCELLATION" in kinds                      # AU/NZ cancellation vocabulary
    assert any(n.get("post_award") for n in nat)        # award is not terminal
    # A reissue is a FRESH opportunity, never a silent continuation of the cancelled programme.
    cancelled = [r for r in records if (r["meta"]["national"].get("consequential_change_kind")
                                        == "PROGRAMME_CANCELLED")]
    reissued = [r for r in records if (r["meta"]["national"].get("consequential_change_kind")
                                       == "PROGRAMME_REISSUED")]
    assert cancelled and reissued
    assert cancelled[0]["id"] != reissued[0]["id"]
    assert cancelled[0]["state"] == "cancelled" and reissued[0]["state"] == "candidate"


def test_evidence_depth_varies_and_is_never_padded(estate):
    records = _records(estate)
    depths = sorted(len(r["evidence"]) for r in records)
    assert min(depths) == 1                      # legitimately sparse cases exist
    assert max(depths) >= 3                      # evidence-rich chains exist
    # Evidence is never duplicated to inflate a count: ids are unique within a record.
    for r in records:
        ids = [e["id"] for e in r["evidence"]]
        assert len(ids) == len(set(ids))


def test_french_original_evidence_keeps_its_authority(estate):
    fr = [r for r in _records(estate)
          if any(e.get("language") == "fr" for e in r["evidence"])]
    assert fr, "the estate must exercise French-original Canadian evidence"


def test_decision_memory_is_populated_and_marked_internal(seeded, estate):
    store, report = seeded
    assert report["dispositions"] >= 8
    rows = list_dispositions(store, estate.LENS_ID)
    assert rows
    for row in rows:
        # Decision Memory is customer feedback, never a Pyrnova assessment — and here the reviewer is us.
        assert row["origin"] == "CUSTOMER_FEEDBACK"
        assert "Internal Pyrnova evaluation" in (row["note"] or "")


# --- honesty ----------------------------------------------------------------------------------------

def test_rights_blocked_cases_are_reported_never_materialized(seeded):
    store, report = seeded
    blocked = {b["case_id"] for b in report["blocked"]}
    # Sources whose rights are DECLARED => DENY must stay out of the customer product, loudly.
    assert {"au-fms-case-movement", "nz-treasury-civil-blocked"} <= blocked
    materialized = {json.dumps(r) for r in store.read("opportunities")}
    for case_id in blocked:
        assert not any(case_id in rec for rec in materialized)


def test_withheld_us_evidence_is_reported_and_absent(seeded):
    _, report = seeded
    withheld = report["withheld_evidence"]
    assert withheld, "US cases carry records from sources that are not declared US national sources"
    approved = {"usaspending", "sam_opportunities", "federal_register"}
    assert all(w["source_id"] not in approved for w in withheld)


def test_no_live_source_state_is_fabricated(seeded):
    """Every materialized record is replay/fixture-derived and says so in its own provenance."""
    store, _ = seeded
    for rec in store.read("opportunities"):
        for ev in rec.get("evidence") or []:
            assert "examples/" in (ev.get("archive_uri") or ""), ev


def test_estate_asserts_no_external_customer(estate):
    text = (ESTATE_DIR / "build_customer_proof.py").read_text(encoding="utf-8")
    assert "INTERNAL" in text
    assert estate.LENS_NAME.startswith("Pyrnova")     # never a plausible external company


# --- determinism / isolation ------------------------------------------------------------------------

def test_projection_is_deterministic(estate):
    first = estate.build_opportunity_records()["records"]
    second = estate.build_opportunity_records()["records"]
    assert [r["id"] for r in first] == [r["id"] for r in second]
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_seeding_is_idempotent_at_the_product_level(tmp_path, estate):
    store = StateStore(tmp_path / "state")
    first = estate.seed(store)
    second = estate.seed(store)
    assert first["materialized"] == second["materialized"]
    # Streams are append-only by design; the PRODUCT view dedupes to one record per stable id.
    latest = {r["id"] for r in store.read("opportunities")}
    assert len(latest) == first["materialized"]
    assert second["customer"]["created"] == 0        # the lens is not re-created


def test_estate_does_not_leak_into_another_tenant(tmp_path, estate):
    store = StateStore(tmp_path / "state")
    upsert_customer(store, CustomerProfile(customer_id="other-tenant", name="Other Tenant",
                                           entity_refs=["co_other"]))
    estate.seed(store)
    for rec in store.read("opportunities"):
        assert rec["customer_id"] == estate.LENS_ID
        assert rec["meta"]["subject_ref"] == estate.LENS_REF
    assert not list_dispositions(store, "other-tenant")


# --- shared read model / local launch path ----------------------------------------------------------

def test_list_view_passes_national_truth_through(seeded, estate):
    """The opportunity list must carry national meaning, or an international row renders as Unknown."""
    from pyrnova.ops import OperatorConsole
    store, _ = seeded
    console = OperatorConsole(store, Path("examples/profiles"), Path("out"),
                              mc_store=store, customer_store=store, cmc_store=store)
    console.fan_out()
    rows = console.customer_opportunities(estate.LENS_ID, as_of=estate.ESTATE_AS_OF)["opportunities"]
    assert rows
    for row in rows:
        national = row["national"]
        assert national and national["domain"] in {"US", "CA", "GB", "AU", "NZ"}
        assert national["route"]


def test_us_ontology_records_carry_no_national_block(tmp_path):
    """A record without national truth keeps its payload unchanged (``national`` is None, not invented)."""
    from pyrnova.ops import OperatorConsole
    store = StateStore(tmp_path / "state")
    console = OperatorConsole(store, Path("examples/profiles"), Path("out"),
                              mc_store=store, customer_store=store, cmc_store=store)
    us_record = {
        "id": "opp_x", "title": "US record", "agency": "Department of the Navy",
        "evidence": [{"id": "ev-1", "source_id": "usaspending",
                      "source_url": "https://www.usaspending.gov/award/CONT_AWD_X"}],
        "meta": {"evidence_sources": ["usaspending"]},
    }
    summary = console._opportunity_summary(us_record)
    assert summary["source_rights"]["display"] != "BLOCKED"
    assert summary["national"] is None


def test_demo_global_seeding_is_idempotent_and_local_only(tmp_path):
    """The local launch path imports demo intelligence once, and never into an enforced deployment."""
    from pyrnova import ops_server
    demo = Path("examples/material_changes_demo")
    store = StateStore(tmp_path / "state")
    first = ops_server._seed_demo_global_intelligence(demo, store)
    assert first > 0
    assert ops_server._seed_demo_global_intelligence(demo, store) == 0   # idempotent per record id
    counts = {s: len(list(store.read(s))) for s in ops_server._DEMO_GLOBAL_STREAMS}
    assert sum(counts.values()) == first

    # An enforced (credentialed / non-local) posture must never receive demo intelligence.
    enforced = StateStore(tmp_path / "enforced")
    policy = ops_server.AccessPolicy(host="0.0.0.0", require_auth=True, expose_operator=False)

    class _Cfg:
        state_dir = tmp_path / "enforced"
        out_dir = tmp_path / "out"

    ops_server._build_console(_Cfg(), enforced, policy)
    assert not any(list(enforced.read(s)) for s in ops_server._DEMO_GLOBAL_STREAMS)


def test_provisioned_estate_is_not_hidden_by_the_demo_seed(tmp_path, estate):
    """Regression: provisioning the estate first must not stop the demo intelligence importing, and the
    demo import must not displace the estate. Order-independent."""
    from pyrnova import ops_server
    store = StateStore(tmp_path / "state")
    estate.seed(store)
    ops_server._seed_demo_global_intelligence(Path("examples/material_changes_demo"), store)
    by_customer = {}
    for rec in store.read("opportunities"):
        by_customer.setdefault(rec["customer_id"], set()).add(rec["id"])
    assert len(by_customer[estate.LENS_ID]) >= 20
    assert set(by_customer) - {estate.LENS_ID}, "demo tenants' intelligence must survive alongside it"


def test_titles_are_drawn_from_the_fixtures_not_invented(estate):
    """A title is a quotation of the accepted corpus, so the estate cannot introduce new claims."""
    titles = estate._fixture_titles("ca_replay")
    corpus = json.loads(Path("examples/ca_replay/corpus.json").read_text(encoding="utf-8"))
    notes = {c["case_id"]: (c.get("note") or "") for c in corpus["cases"]}
    for case_id, title in titles.items():
        subject = title.split(" — ", 1)[1]
        assert subject and subject in notes[case_id]
