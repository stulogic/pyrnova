"""Supported, seed-free customer onboarding (M22-F).

Before M22-F, creating/configuring a customer meant editing the demo seed script
(``examples/material_changes_demo/seed_customers.py``). That is fine for a committed demo identity but
unacceptable as the normal path for a real design customer (§17/§18/§26). This module is the thin domain
layer a competent operator drives — via the CLI (``pyrnova customer``/``pyrnova watch``) — to onboard a
customer WITHOUT editing Python or JSONL by hand.

It is not a CRM (§17). It only establishes enough structured customer context for Pyrnova's existing
relevance/fan-out to work, and it does so by REUSING what Pyrnova already has:

* customer identity + configuration → M22-B :mod:`pyrnova.customers` (``CustomerProfile``, append-only,
  temporal, auditable);
* watchlists → M22-B :class:`~pyrnova.customers.WatchlistEntry` (ENTITY / PROGRAM / CONTRACT / AGENCY,
  ``valid_from``/``valid_to`` temporal truth, honest ``resolved`` flag, cross-customer-safe retirement);
* entity/program resolution → M22-D deterministic :func:`pyrnova.investigation.search`
  (EXACT / PROBABLE / AMBIGUOUS / UNRESOLVED) — no second resolver, no runtime LLM (§20);
* materialization into the customer-facing product → M22-C fan-out (unchanged).

Resolution is explicit, never magic (§54): EXACT can be selected; PROBABLE requires explicit confirmation;
AMBIGUOUS is never silently chosen; UNRESOLVED is never fabricated. An operator may deliberately record a
watch as unresolved (a first-class honest state) rather than force an identity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import customers as cust
from .investigation import (
    RESOLUTION_AMBIGUOUS,
    RESOLUTION_EXACT,
    RESOLUTION_PROBABLE,
    RESOLUTION_UNRESOLVED,
    build_estate,
    search,
)
from .state import StateStore


# ------------------------------------------------------------------ customer creation

def create_customer(store, *, customer_id: str, name: str, entity_refs=None, capabilities=None,
                    agencies=None, sectors=None, geography=None, provenance: str = "operator",
                    effective_from: Optional[str] = None) -> dict:
    """Create/replace a persisted customer profile version (append-only, auditable) — reuses M22-B.

    This is the seed-free replacement for editing ``seed_customers.py``: it writes the SAME
    :class:`~pyrnova.customers.CustomerProfile` structure the demo seed writes, into the SAME persisted
    stream the product reads — there is no parallel customer model (§18).
    """
    profile = cust.CustomerProfile(
        customer_id=customer_id, name=name, entity_refs=list(entity_refs or []),
        capabilities=list(capabilities or []), agencies=list(agencies or []),
        sectors=list(sectors or []), geography=list(geography or []),
        provenance=provenance, effective_from=effective_from)
    return cust.upsert_customer(store, profile)


def get_customer(store, customer_id: str, *, as_of: Optional[str] = None) -> Optional[dict]:
    profile = cust.get_customer(store, customer_id, as_of=as_of)
    if profile is None:
        return None
    out = profile.to_record()
    out["watchlist"] = cust.list_watches(store, customer_id, as_of=as_of)
    return out


# ------------------------------------------------------------------ deterministic estate for resolution

def load_estate(store, *, demo_dir: str = "examples/material_changes_demo", as_of: Optional[str] = None):
    """Build the point-in-time investigation estate the same way the server and ``pyrnova search`` do.

    Reads the configured global intelligence streams, falling back to the tracked demo state on a fresh
    checkout, so onboarding resolution sees exactly what the running product sees (one canonical pattern).
    """
    demo_state = Path(demo_dir) / "state"
    mc_store = store
    if not (Path(store.root) / "threats.jsonl").exists() and (demo_state / "threats.jsonl").exists():
        mc_store = StateStore(demo_state)

    def _read(s, name):
        try:
            return list(s.read(name))
        except Exception:  # noqa: BLE001 — degrade gracefully if a collection is absent
            return []

    def _latest(rows):
        by_id = {}
        for r in rows:
            rid = r.get("id")
            if rid:
                by_id[str(rid)] = r
        return list(by_id.values())

    return build_estate(
        threats=_latest(_read(mc_store, "threats")),
        propagated_threats=_latest(_read(mc_store, "propagated_threats")),
        opportunities=_latest(_read(store, "opportunities")),
        relationships=_read(store, "relationships"),
        as_of=as_of)


# ------------------------------------------------------------------ resolution-gated watch configuration

# Map a resolved search result "type" to the watchlist object type.
_TYPE_TO_WATCH = {"COMPANY": cust.WATCH_ENTITY, "PROGRAM": cust.WATCH_PROGRAM}


def resolve_target(store, query: str, *, demo_dir: str = "examples/material_changes_demo",
                   as_of: Optional[str] = None) -> dict:
    """Deterministically resolve a free-text onboarding target using M22-D search (no new resolver)."""
    estate = load_estate(store, demo_dir=demo_dir, as_of=as_of)
    return search(estate, query or "")


def add_watch(store, *, customer_id: str, object_type: str, ref: str, label: str = "",
              valid_from: Optional[str] = None, provenance: str = "operator") -> dict:
    """Add a watchlist entry literally (M22-B semantics). The ref's ``resolved`` flag is computed honestly.

    Rejects an unknown customer so an operator cannot attach a watch to a non-existent tenant.
    """
    if cust.get_customer(store, customer_id) is None:
        raise ValueError(f"customer not found: {customer_id}")
    entry = cust.WatchlistEntry(customer_id=customer_id, object_type=object_type, ref=ref,
                                label=label, valid_from=valid_from, provenance=provenance)
    return cust.add_watch(store, entry)


def add_watch_resolved(store, *, customer_id: str, query: str, object_type: Optional[str] = None,
                       accept_probable: bool = False, allow_unresolved: bool = False,
                       demo_dir: str = "examples/material_changes_demo",
                       label: str = "", provenance: str = "operator") -> dict:
    """Resolve ``query`` against the estate, then add the resulting watch under explicit resolution rules.

    Rules (§20/§54 — resolution is explicit, never magic):

    * **EXACT** → add the resolved canonical ref (COMPANY→ENTITY watch, PROGRAM→PROGRAM watch).
    * **PROBABLE** → add ONLY when ``accept_probable`` (explicit operator confirmation); else refuse and
      surface the ranked candidates.
    * **AMBIGUOUS** → never silently choose; refuse and surface the candidates for the operator to pick.
    * **UNRESOLVED** → never fabricate; refuse unless ``allow_unresolved`` (add the literal query as an
      honestly-unresolved watch — a first-class state), and then only when ``object_type`` is given.

    Returns ``{"status": ..., "resolution": <search result>, "watch": <record|None>}``.
    """
    if cust.get_customer(store, customer_id) is None:
        raise ValueError(f"customer not found: {customer_id}")
    result = resolve_target(store, query, demo_dir=demo_dir)
    resolution = result.get("resolution")
    results = result.get("results") or []

    def _add_from_result(res: dict) -> dict:
        otype = _TYPE_TO_WATCH.get(res.get("type"))
        if otype is None:
            raise ValueError(f"cannot watch a resolved object of type {res.get('type')!r}")
        return add_watch(store, customer_id=customer_id, object_type=otype,
                         ref=res.get("key"), label=label or res.get("canonical_name", ""),
                         provenance=provenance)

    if resolution == RESOLUTION_EXACT and results:
        return {"status": "resolved", "resolution": result, "watch": _add_from_result(results[0])}
    if resolution == RESOLUTION_PROBABLE:
        if accept_probable and results:
            return {"status": "confirmed_probable", "resolution": result,
                    "watch": _add_from_result(results[0])}
        return {"status": "needs_confirmation", "resolution": result, "watch": None}
    if resolution == RESOLUTION_AMBIGUOUS:
        return {"status": "ambiguous", "resolution": result, "watch": None}
    # UNRESOLVED
    if allow_unresolved:
        if not object_type:
            raise ValueError("an unresolved watch requires an explicit --type")
        watch = add_watch(store, customer_id=customer_id, object_type=object_type, ref=query,
                          label=label, provenance=provenance)
        return {"status": "unresolved_recorded", "resolution": result, "watch": watch}
    return {"status": "unresolved", "resolution": result, "watch": None}


def retire_watch(store, customer_id: str, watch_id: str) -> dict:
    """Retire a watch (append-only closure; preserves history; cross-customer safe) — reuses M22-B."""
    return cust.retire_watch(store, customer_id, watch_id)


__all__ = [
    "create_customer", "get_customer",
    "load_estate", "resolve_target",
    "add_watch", "add_watch_resolved", "retire_watch",
]
