"""B4.12 / B4.14 — exact-candidate commercial rehearsal + MTSI/Torch RC proof capture.

Drives the REAL OperatorConsole (Bundle-3 product + Bundle-2 decision chain, B4.1 recompute) end to
end against the persisted, tracked demo state — no fabricated opportunities, no seeded fake data, no
external delivery. MTSI is Customer #1; Torch supplies additional populated proof. The script fails
loudly if any truthfulness invariant breaks, and writes a JSON capture next to itself.

Run from the worktree root:
    PYTHONPATH=. <venv>/python docs/evidence/bundle4/rehearsal_capture.py

This is a REHEARSAL against candidate state. It sends no prospect communication, starts no soak, and
claims no soak pass. Delivery uses an in-memory RecordingTransport (records, never sends externally).
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

from pyrnova.alerts import RecordingTransport
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

REPO = Path(__file__).resolve().parents[3]
DEMO = REPO / "examples/material_changes_demo"
STATE = DEMO / "state"
PROFILES = REPO / "examples/profiles"

# The locked commercial authority (owner-provided). Presented verbatim; not sent, not a legal offer.
LOCKED_OFFER = {
    "product": "PYRNOVA LIVE INTELLIGENCE",
    "engagement_fee_usd": 15000,
    "term_days": 60,
    "scope": "one Customer Lens · bounded intelligence surface · up to 10 Named Users",
    "billing": "100% invoiced after signature · Net 15 default · activation normally after cleared payment",
    "continuation": "$18,000 quarterly prepaid",
    "optional_annual": "$72,000",
    "no_free_pilot": True,
    "no_default_discount": True,
    "obsolete_do_not_use": "The $2,500 Intelligence Sprint is obsolete and must not appear.",
}
CUSTOMER_SEQUENCE = ["mtsi", "torch", "celestar", "shorepoint", "hyertek"]


def _console(workdir: Path) -> OperatorConsole:
    store = StateStore(workdir / "state")
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)  # torch + dap (accepted committed fixtures)
    return OperatorConsole(
        store, PROFILES, workdir / "o", mc_store=StateStore(STATE), contexts_dir=DEMO,
        customer_store=store, cmc_store=StateStore(workdir / "cmc"),
        delivery_store=CustomerDeliveryStore(workdir / "deliveries"),
    )


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"REHEARSAL FAILED — truthfulness invariant broken: {msg}")


def _capture_customer(console: OperatorConsole, cid: str) -> dict:
    lens = console.customer_lens(cid)
    _require(lens["customer"]["id"] == cid, f"{cid} lens identity")
    opps = console.customer_opportunities(cid)
    out: dict = {
        "customer_id": cid,
        "lens_identity": lens["customer"],
        "opportunity_count": opps["count"],
        "opportunities": [],
        "empty_state": opps["count"] == 0,
    }
    for o in opps["opportunities"]:
        dec = console.opportunity_decision(cid, o["id"])
        dc = dec["decision_chain"]
        ev = dc["evidence"]
        # Evidence Inspector on the first evidence item.
        inspector = None
        if ev:
            inspector = console.opportunity_evidence(cid, o["id"], ev[0]["id"])
        out["opportunities"].append({
            "id": o["id"],
            "title": o.get("title"),
            "incumbent": o.get("incumbent"),
            "why_now": o.get("why_now"),
            "recommended_action": o.get("recommended_action"),
            "pursuit": {"verdict": dc["pursuit"]["verdict"],
                        "confidence": dc["pursuit"]["confidence"],
                        "recommended_action": dc["pursuit"]["recommended_action"]},
            "evidence_sources": sorted({e.get("source_id") for e in ev if e.get("source_id")}),
            "evidence_archives": sorted({e.get("archive_uri") for e in ev if e.get("archive_uri")}),
            "evidence_inspector_ok": bool(inspector),
        })
    return out


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        console = _console(workdir)

        # Customer #1 = MTSI. Onboard from its accepted profile, carrying its canonical entity ref only.
        console.create_customer(
            customer_id="mtsi", name="Modern Technology Solutions", entity_refs=["co_mtsi"],
            capabilities=["systems engineering", "modeling and simulation"],
            agencies=["Missile Defense Agency", "Space Force", "General Services Administration"],
        )

        mtsi = _capture_customer(console, "mtsi")
        torch = _capture_customer(console, "torch")

        # --- Truthfulness invariants (fail loudly) --------------------------------------------------
        # MTSI must be genuinely populated from its OWN real archive (B4.2 fan-out), never fabricated.
        _require(mtsi["opportunity_count"] > 0, "MTSI should surface its real persisted recompetes")
        for o in mtsi["opportunities"]:
            _require("MODERN TECHNOLOGY SOLUTIONS" in (o["incumbent"] or "").upper(),
                     "MTSI incumbent identity")
            _require(all("usaspending_mtsi.json" in a for a in o["evidence_archives"]),
                     "MTSI evidence must come from usaspending_mtsi.json, not Torch")
        _require(torch["opportunity_count"] > 0, "Torch populated proof")

        # Tenant isolation: no shared opportunity ids across the two lenses.
        mtsi_ids = {o["id"] for o in mtsi["opportunities"]}
        torch_ids = {o["id"] for o in torch["opportunities"]}
        _require(mtsi_ids.isdisjoint(torch_ids), "tenant isolation (disjoint opportunity ids)")

        # AS-OF: before the opportunities' first_seen (2026-09-01) the MTSI lens is honestly empty.
        as_of_before = console.customer_opportunities("mtsi", as_of="2026-08-01")

        # Disposition -> Decision Memory (persisted, re-readable).
        first = mtsi["opportunities"][0]["id"]
        disp = console.record_opportunity_disposition(
            "mtsi", first, relevance="RELEVANT", pursuit="INVESTIGATE",
            note="rehearsal disposition (not a customer instruction)",
        )

        # Brief: deterministic, rights-aware, and free of obsolete Intelligence Sprint language.
        brief = console.build_customer_brief("mtsi", first)
        _require("Intelligence Sprint" not in brief["body"], "brief must not contain obsolete Sprint copy")
        _require(brief["rights_display"] in ("ALLOWED", "PARTIAL"), "brief rights disposition")

        # Authorized delivery-state path with an in-memory transport (NO external send).
        console.authorize_delivery_recipient("mtsi", "capture.rehearsal@example.test")
        transport = RecordingTransport()
        delivery = console.deliver_customer_brief(
            "mtsi", first, recipients=["capture.rehearsal@example.test"], transport=transport,
        )
        _require(delivery["status"] == "DELIVERED" and len(transport.sent) == 1,
                 "recorded (non-external) delivery-state path")

        capture = {
            "note": "Exact-candidate rehearsal against tracked demo state. No fabricated data. "
                    "No external send. No soak started or claimed passed.",
            "customer_sequence": CUSTOMER_SEQUENCE,
            "customer_1": "mtsi",
            "locked_commercial_offer": LOCKED_OFFER,
            "capability_status_legend": {
                "IMPLEMENTED/TESTED": "product capability proven by candidate code + tests",
                "PRODUCTION/LIVE-OPS-ACCEPTED": "requires the final replacement soak — NOT claimed here",
            },
            "mtsi": mtsi,
            "torch_populated_proof": torch,
            "as_of_before_first_seen": {"as_of": "2026-08-01",
                                        "mtsi_opportunity_count": as_of_before["count"]},
            "disposition_to_decision_memory": {"opportunity_id": first,
                                               "relevance": disp.get("relevance"),
                                               "pursuit": disp.get("pursuit")},
            "brief": {"rights_display": brief["rights_display"],
                      "content_sha256": brief.get("content_sha256"),
                      "contains_obsolete_sprint": "Intelligence Sprint" in brief["body"]},
            "delivery_state": {"status": delivery["status"],
                               "delivery_id": delivery["delivery_id"],
                               "transport": "in-memory RecordingTransport (records, never sends externally)",
                               "recorded_sends": len(transport.sent)},
        }
        out_path = Path(__file__).with_name("rehearsal_capture.json")
        out_path.write_text(json.dumps(capture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "REHEARSAL": "PASS",
            "mtsi_opportunities": mtsi["opportunity_count"],
            "torch_opportunities": torch["opportunity_count"],
            "tenant_isolated": True,
            "as_of_2026-08-01_mtsi_count": as_of_before["count"],
            "brief_has_obsolete_sprint": "Intelligence Sprint" in brief["body"],
            "delivery_status": delivery["status"],
            "capture": str(out_path.relative_to(REPO)),
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
