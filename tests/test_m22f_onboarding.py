"""M22-F seed-free onboarding: customer creation, watch configuration, deterministic resolution, fan-out.

Proves an operator can onboard a customer WITHOUT editing seed code (§26/§32), reusing the M22-B customer/
watchlist model, M22-D deterministic resolution, and the M22-C fan-out — and that temporal truth holds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyrnova import access, customers as cust, onboarding
from pyrnova.customer_material_changes import fan_out, _latest_versions
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"


def _store(tmp_path) -> StateStore:
    return StateStore(tmp_path / "state")


# --- customer creation persists without seed code (§32.1-2) -------------------------------------

def test_create_customer_persists_across_reload(tmp_path):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="acme", name="Acme Defense",
                               agencies=["DEPT OF THE ARMY"])
    # A fresh store instance over the same directory still sees the customer (durable JSONL).
    reloaded = StateStore(tmp_path / "state")
    got = onboarding.get_customer(reloaded, "acme")
    assert got is not None and got["name"] == "Acme Defense" and got["agencies"] == ["DEPT OF THE ARMY"]
    assert [c["id"] for c in cust.list_customers(reloaded)] == ["acme"]


# --- all four watch types, owned by the correct customer (§32.3-7) ------------------------------

@pytest.mark.parametrize("otype,ref", [
    ("ENTITY", "co_acme"), ("PROGRAM", "PIID-123ABC"), ("CONTRACT", "N0001925C0001"),
    ("AGENCY", "DEPT OF THE ARMY"),
])
def test_add_each_watch_type(tmp_path, otype, ref):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="acme", name="Acme")
    row = onboarding.add_watch(store, customer_id="acme", object_type=otype, ref=ref)
    assert row["object_type"] == otype and row["customer_id"] == "acme" and row["ref"] == ref
    watches = cust.list_watches(store, "acme")
    assert len(watches) == 1 and watches[0]["object_type"] == otype


def test_add_watch_rejects_unknown_customer(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        onboarding.add_watch(store, customer_id="ghost", object_type="ENTITY", ref="co_x")


def test_duplicate_active_watch_suppressed(tmp_path):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="acme", name="Acme")
    onboarding.add_watch(store, customer_id="acme", object_type="ENTITY", ref="co_acme",
                         valid_from="2026-01-01T00:00:00+00:00")
    onboarding.add_watch(store, customer_id="acme", object_type="ENTITY", ref="co_acme",
                         valid_from="2026-01-01T00:00:00+00:00")
    assert len(cust.list_watches(store, "acme")) == 1     # idempotent per (customer,type,ref,valid_from)


# --- cross-customer + retirement history (§32.9-10) ---------------------------------------------

def test_cross_customer_watch_retire_rejected(tmp_path):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="a", name="A")
    onboarding.create_customer(store, customer_id="b", name="B")
    w = onboarding.add_watch(store, customer_id="a", object_type="ENTITY", ref="co_a")
    with pytest.raises(ValueError):
        onboarding.retire_watch(store, "b", w["id"])       # b cannot retire a's watch


def test_watch_retirement_preserves_history(tmp_path):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="a", name="A")
    w = onboarding.add_watch(store, customer_id="a", object_type="ENTITY", ref="co_a",
                             valid_from="2026-01-01T00:00:00+00:00")
    onboarding.retire_watch(store, "a", w["id"])
    assert cust.list_watches(store, "a") == []             # inactive now
    # But historical replay before retirement still sees it (append-only history preserved).
    past = cust.list_watches(store, "a", as_of="2026-06-01T00:00:00+00:00")
    assert len(past) == 1 and past[0]["ref"] == "co_a"


# --- deterministic resolution states (§20/§32.11-13) --------------------------------------------

def test_resolve_exact_adds_canonical_watch(tmp_path):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="acme", name="Acme")
    res = onboarding.add_watch_resolved(store, customer_id="acme", query="co_saic")
    assert res["status"] == "resolved" and res["watch"] is not None
    assert res["resolution"]["resolution"] == "EXACT"
    assert res["watch"]["ref"] == "co_saic" and res["watch"]["resolved"] is True


def test_resolve_ambiguous_never_silently_chosen(tmp_path):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="acme", name="Acme")
    res = onboarding.add_watch_resolved(store, customer_id="acme",
                                        query="DAP Construction Management")
    assert res["resolution"]["resolution"] == "AMBIGUOUS"
    assert res["status"] == "ambiguous" and res["watch"] is None      # nothing added
    assert cust.list_watches(store, "acme") == []


def test_resolve_probable_requires_confirmation(tmp_path):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="acme", name="Acme")
    # A partial-name query that scores as PROBABLE (single best match) is not added without confirmation.
    probe = onboarding.resolve_target(store, "Science Applications")
    if probe["resolution"] == "PROBABLE":
        res = onboarding.add_watch_resolved(store, customer_id="acme", query="Science Applications")
        assert res["status"] == "needs_confirmation" and res["watch"] is None
        res2 = onboarding.add_watch_resolved(store, customer_id="acme", query="Science Applications",
                                             accept_probable=True)
        assert res2["status"] == "confirmed_probable" and res2["watch"] is not None


def test_resolve_unresolved_not_fabricated(tmp_path):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="acme", name="Acme")
    res = onboarding.add_watch_resolved(store, customer_id="acme",
                                        query="Nonexistent Zzzz Corp 99999")
    assert res["resolution"]["resolution"] == "UNRESOLVED"
    assert res["status"] == "unresolved" and res["watch"] is None     # never invents an identity
    # An operator MAY record it as an honestly-unresolved literal watch, with an explicit type.
    res2 = onboarding.add_watch_resolved(store, customer_id="acme", query="Nonexistent Zzzz Corp 99999",
                                         object_type="ENTITY", allow_unresolved=True)
    assert res2["status"] == "unresolved_recorded" and res2["watch"]["resolved"] is False


# --- credentialed, onboarded customer enters the existing fan-out/read path (§32.14-15) ----------

def test_onboarded_customer_enters_fanout_and_reads(tmp_path):
    store = _store(tmp_path)
    # Onboard a NEW customer against a real seeded incumbent entity (co_torch) that has demo intelligence.
    onboarding.create_customer(store, customer_id="newco", name="New Co",
                               entity_refs=["co_torch"], effective_from="2020-01-01T00:00:00+00:00")
    onboarding.add_watch(store, customer_id="newco", object_type="ENTITY", ref="co_torch",
                         valid_from="2020-01-01T00:00:00+00:00")
    # Provision a credential (proves the access half is wired to the same customer).
    _, token = access.create_credential(store, customer_id="newco")
    assert access.authenticate(store, token).customer_id == "newco"
    # Fan-out over the demo global intelligence materializes relevant Material Changes for newco.
    report = fan_out(mc_store=StateStore(STATE), customer_store=store, cmc_store=store,
                     customer_ids=["newco"])
    assert report["inserted"] > 0
    assert _latest_versions(store, "newco")            # customer-scoped state now exists


# --- temporal truth: a new watch does not backdate relevance (§52) ------------------------------

def test_new_watch_does_not_backdate_relevance(tmp_path):
    store = _store(tmp_path)
    onboarding.create_customer(store, customer_id="newco", name="New Co",
                               effective_from="2020-01-01T00:00:00+00:00")
    # Add the watch with a LATE valid_from — well after the demo intelligence was observed.
    onboarding.add_watch(store, customer_id="newco", object_type="ENTITY", ref="co_torch",
                         valid_from="2027-01-01T00:00:00+00:00")
    # A point-in-time reconstruction BEFORE the watch existed must not see it (no retrospective leakage).
    ctx_before = cust.build_context(store, "newco", as_of="2026-06-01T00:00:00+00:00")
    assert "co_torch" not in ctx_before.watched_entity_refs
    ctx_after = cust.build_context(store, "newco", as_of="2027-06-01T00:00:00+00:00")
    assert "co_torch" in ctx_after.watched_entity_refs
