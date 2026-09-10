"""Deterministic demo customer seed (M22-B).

Seeds the SAME two example customers M22-A shipped as committed JSON fixtures (Torch, DAP) into the
PERSISTED customer structures (:mod:`pyrnova.customers`), so the running product operates from persisted
customer state rather than from demo-only configuration. This is a TEST / EXAMPLE / DEMONSTRATION path,
not runtime architecture: the demo identities live here in ``examples/``, never hard-coded into the
``pyrnova`` package's runtime behavior (M22-B doctrine, D-056).

Idempotent and deterministic: onboarding/effective/valid-from timestamps are pinned to fixed dates that
precede each customer's triggering event, so historical replay reconstructs what the customer was
configured to monitor at the cutoff. Re-running is a no-op for a customer already present and produces the
same watchlist ids.

Onboarding dates are pinned before the demo events (Torch/SAIC deobligation knowable 2024-06-01; DAP
termination knowable 2026-08-31) so the demo customers were "already monitoring" when the event landed.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyrnova.customers import (
    WATCH_AGENCY,
    WATCH_ENTITY,
    WATCH_PROGRAM,
    CustomerProfile,
    WatchlistEntry,
    add_watch,
    get_customer,
    upsert_customer,
)

DEMO = Path(__file__).resolve().parent

# Pinned onboarding dates (before each customer's triggering event) — deterministic historical replay.
ONBOARDING = {
    "torch": "2020-01-01T00:00:00+00:00",
    "dap": "2026-01-01T00:00:00+00:00",
}


def _seed_one(store, ctx: dict) -> dict:
    cid = ctx["customer_id"]
    onboarded = ONBOARDING.get(cid, "2020-01-01T00:00:00+00:00")
    created = 0
    if get_customer(store, cid) is None:
        upsert_customer(store, CustomerProfile(
            customer_id=cid,
            name=ctx.get("name", cid),
            entity_refs=list(ctx.get("entity_refs", [])),
            capabilities=list(ctx.get("capabilities", [])),
            agencies=list(ctx.get("agencies", [])),
            sectors=list(ctx.get("sectors", [])),
            provenance="demo_seed",
            effective_from=onboarded,
            created_at=onboarded,
            updated_at=onboarded,
        ))
        created = 1

    watches = 0
    for ref in ctx.get("watched_entity_refs", []):
        add_watch(store, WatchlistEntry(customer_id=cid, object_type=WATCH_ENTITY, ref=ref,
                                        valid_from=onboarded, provenance="demo_seed"))
        watches += 1
    for ref in ctx.get("watched_programs", []):
        add_watch(store, WatchlistEntry(customer_id=cid, object_type=WATCH_PROGRAM, ref=ref,
                                        valid_from=onboarded, provenance="demo_seed"))
        watches += 1
    # Agencies of interest are also persisted as watches so the temporal + private-context model owns
    # every monitoring channel uniformly (the profile also carries them for capability/agency relevance).
    for ref in ctx.get("agencies", []):
        add_watch(store, WatchlistEntry(customer_id=cid, object_type=WATCH_AGENCY, ref=ref,
                                        valid_from=onboarded, provenance="demo_seed"))
        watches += 1
    return {"customer_id": cid, "created": created, "watches": watches}


def seed(store) -> dict:
    """Seed the demo customers into ``store`` (idempotent). Returns a small summary."""
    results = []
    for name in ("torch", "dap"):
        ctx = json.loads((DEMO / f"{name}.json").read_text(encoding="utf-8"))
        results.append(_seed_one(store, ctx))
    return {"seeded": results}


def main() -> int:
    from pyrnova.config import load_config
    from pyrnova.state import StateStore

    cfg = load_config()
    store = StateStore(cfg.state_dir)
    print(seed(store))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
