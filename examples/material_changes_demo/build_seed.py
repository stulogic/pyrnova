"""Deterministic Material Changes demo seed (M22-A; opportunities added M22-E).

Runs the REAL Pyrnova engine paths over REAL archived evidence (no live calls, no fabrication) to produce
the threat / propagated-threat / **opportunity** records the Material Changes read model consumes, and
writes them as tracked, replay-safe JSONL under ``examples/material_changes_demo/state/``. Re-running
reproduces the same fixture byte-for-byte (all engine-assigned ids are pinned deterministically here).

Two customers, proving customer isolation with real data:

* Torch Technologies — a real archived USAspending contract **deobligation** on SAIC's exact PIID
  47QFSA20F0057 (M19) yields a HIGH-confidence PROGRAM_CONTRACTION for SAIC that propagates one hop to
  Torch over the real program-anchored SAIC→Torch sub-award edge (THREAT). M22-E additionally materializes
  Torch's own **recompete opportunities**: the real ``detect_recompetes`` engine over Torch's archived
  USAspending awards surfaces Torch's large incumbent contracts entering their recompete window as
  OPPORTUNITY Material Changes (DIRECT_SUBJECT — Torch is the incumbent).
* DAP Construction Management LLC — a real raw-archived USAspending **terminate-for-convenience** (M21,
  PIID 36C25726N0240) yields a HIGH-confidence PROGRAM_CANCELLATION_OR_DELAY that propagates up to the
  parent over the deterministic SUBSIDIARY_OF native-id edge (THREAT). DAP has no active recompete in the
  archived estate, so it honestly stays threat-only — which also proves the opportunity is isolated to
  Torch.

SAIC's own direct threat is included in the stream but belongs to neither customer — it must not surface
for Torch or DAP, which is exactly the customer-boundary property the read model enforces.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from pyrnova.adverse_events import (
    parse_usaspending_award_termination,
    parse_usaspending_contract_modifications,
    to_contract_contraction_catalyst,
    to_contract_termination_catalyst,
)
from pyrnova.engines.recompete import detect_recompetes
from pyrnova.grounding_subawards import parse_subawards
from pyrnova.models import Evidence, to_record
from pyrnova.normalize import normalize_award
from pyrnova.propagation import propagate_threats
from pyrnova.relationships import (
    exposed_prime_awards_from_subawards,
    ground_subaward_edges,
    ground_subsidiary_edges,
)
from pyrnova.threat import assess_threats, incumbency_exposures

RE = Path("examples/real_evidence")
OUT = Path("examples/material_changes_demo/state")

SAIC = "SCIENCE APPLICATIONS INTERNATIONAL CORPORATION"
SAIC_UEI = "MMLKPW9JLX64"
SAIC_PIID = "47QFSA20F0057"
DAP_PIID = "36C25726N0240"
DAP_UEI = "YR7CLZFGCM95"
PARENT_UEI = "KMSLVW1MZWU9"

# --- M22-E opportunity materialization parameters -------------------------------------------------
# Torch is the tenant ``torch``; its canonical entity is ``co_torch`` (the DIRECT_SUBJECT relevance ref).
TORCH_TENANT = "torch"
TORCH_REF = "co_torch"
TORCH_NAME = "Torch Technologies Inc"
# Pinned recompete scan date so the fixture is deterministic regardless of wall-clock (the engine takes
# ``as_of`` as a parameter). A $100M materiality floor keeps only substantial recompetes for a mid-market
# prime; the 540-day forward window is the engine default.
OPP_AS_OF = date(2026, 9, 1)
OPP_WINDOW_DAYS = 540
OPP_MIN_AMOUNT = 100_000_000.0


def _enrich(threat, *, event, agency, program, source_ref, archive_hash=None):
    """Attach the read-model presentation fields onto the threat record's meta from the real event."""
    rec = to_record(threat)
    meta = dict(rec.get("meta") or {})
    meta.update({
        "event_type": event.get("event_type"),
        "event_time": event.get("action_date") or event.get("available_at"),
        "event_summary": event.get("summary") or event.get("title")
        or f"{event.get('event_type')} on {program}",
        "affected_program": program,
        "agency": agency,
        "source_ref": source_ref,
        "adverse_event_family": "contract_modification",
        "evidence_sources": ["usaspending"],
    })
    if archive_hash:
        meta["archive_hash"] = archive_hash
    rec["meta"] = meta
    return rec


def _saic_torch_chain():
    mods = parse_usaspending_contract_modifications((RE / "usaspending_contract_mods_saic_47QFSA20F0057.json").read_bytes())
    event = next(e for e in mods["events"] if e["modification_number"] == "P00256")
    awards = [{"recipient_uei": SAIC_UEI, "program_key": SAIC_PIID, "amount_usd": 1432695358.81,
               "available_at": "2020-05-05", "period_end": "2025-11-04",
               "source_ref": f"usaspending:award:{SAIC_PIID}"}]
    exposures = incumbency_exposures("co_saic", SAIC, SAIC_UEI, awards, as_of="2024-06-01")
    catalyst = to_contract_contraction_catalyst(event)
    threats, _ = assess_threats("co_saic", SAIC, exposures, [catalyst], as_of="2024-06-01")
    seed = next(t for t in threats if t.mechanism == "PROGRAM_CONTRACTION")

    subawards = parse_subawards((RE / "usaspending_subawards_torch.json").read_bytes(),
                                company_name="TORCH TECHNOLOGIES INC")
    anchors = exposed_prime_awards_from_subawards(subawards, SAIC)
    assert SAIC_PIID in anchors
    edges = ground_subaward_edges(subawards, sub_ref="co_torch", sub_name="Torch Technologies Inc",
                                  prime_refs={SAIC: "co_saic"}, exposed_prime_award_ids={SAIC_PIID})
    edge = next(e for e in edges if e["from_ref"] == "co_saic")
    result = propagate_threats([seed], [edge], as_of="2024-06-01")
    propagated = result["propagated_threats"]

    direct = _enrich(seed, event=event, agency="General Services Administration", program=SAIC_PIID,
                     source_ref=f"usaspending:txn:{SAIC_PIID}:P00256")
    prop_recs = [_enrich(p, event=event, agency="General Services Administration", program=SAIC_PIID,
                         source_ref=f"usaspending:txn:{SAIC_PIID}:P00256") for p in propagated]
    return [direct], prop_recs


def _dap_parent_chain():
    txns = (RE / "usaspending_award_termination_dap.transactions.json").read_bytes()
    prov = json.loads((RE / "usaspending_award_termination_dap.transactions.provenance.json").read_text())
    parsed = parse_usaspending_award_termination(
        txns, piid=DAP_PIID, recipient_uei=DAP_UEI,
        recipient_name="DAP CONSTRUCTION MANAGEMENT LLC", agency="Department of Veterans Affairs")
    event = parsed["events"][0]
    award_record = {
        "recipient_uei": DAP_UEI, "program_key": DAP_PIID, "program_name": f"VA award {DAP_PIID}",
        "available_at": "2026-03-04", "period_start": "2026-03-04", "period_end": None,
        "amount_usd": 3950539.76, "agency": "Department of Veterans Affairs",
        "evidence_id": f"usaspending:award:{DAP_PIID}",
    }
    exposures = incumbency_exposures("co_dap_sub", "DAP CONSTRUCTION MANAGEMENT LLC", DAP_UEI,
                                     [award_record], as_of="2026-08-31")
    catalyst = to_contract_termination_catalyst(event)
    threats, _ = assess_threats("co_dap_sub", "DAP CONSTRUCTION MANAGEMENT LLC",
                                exposures, [catalyst], as_of="2026-08-31")
    seed = next(t for t in threats if t.mechanism == "PROGRAM_CANCELLATION_OR_DELAY")
    edge = ground_subsidiary_edges((RE / "usaspending_recipient_dap.json").read_bytes(),
                                   child_ref="co_dap_sub", available_at="2026-03-04",
                                   valid_from="2026-03-04")[0]
    result = propagate_threats([seed], [edge], as_of="2026-08-31")

    direct = _enrich(seed, event=event, agency="Department of Veterans Affairs", program=DAP_PIID,
                     source_ref=f"usaspending:txn:{DAP_PIID}:P00002", archive_hash=prov["sha256"])
    prop_recs = [_enrich(p, event=event, agency="Department of Veterans Affairs", program=DAP_PIID,
                         source_ref=f"usaspending:txn:{DAP_PIID}:P00002", archive_hash=prov["sha256"])
                 for p in result["propagated_threats"]]
    return [direct], prop_recs


def _stable_id(prefix: str, payload: dict) -> str:
    """Deterministic id from source-linked fields (engineering doctrine §20; not prose-based)."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"{prefix}_" + hashlib.sha256(blob).hexdigest()[:20]


def _torch_recompete_opportunities() -> list[dict]:
    """Torch's own recompete opportunities via the REAL ``detect_recompetes`` engine (M22-E).

    Uses Torch's archived USAspending awards — no new engine, no live call, no fabrication. Each engine
    field is deterministic; the only engine-assigned ids that default to random uids (opportunity,
    catalyst, evidence) are pinned here from source-linked content so the fixture is byte-reproducible.
    The opportunity carries the CANONICAL subject (``co_torch`` / name) distinct from the tenant
    ``customer_id`` so DIRECT_SUBJECT relevance and investigation links resolve to the real entity.
    """
    raw = (RE / "usaspending_torch.json").read_bytes()
    archive_hash = hashlib.sha256(raw).hexdigest()  # the real archived response the awards came from
    awards = [normalize_award(r) for r in json.loads(raw)["results"]]
    opps = detect_recompetes(awards, as_of=OPP_AS_OF, window_days=OPP_WINDOW_DAYS,
                             min_amount=OPP_MIN_AMOUNT)
    records: list[dict] = []
    for opp in opps:
        award_id = opp.meta.get("award_id")
        opp.id = _stable_id("opp", {"award": award_id, "kind": opp.catalyst.kind, "subject": TORCH_REF})
        opp.catalyst.id = _stable_id("cat", {"award": award_id, "kind": opp.catalyst.kind})
        opp.customer_id = TORCH_TENANT
        opp.state = "candidate"
        opp.evidence = [Evidence(
            source_id="usaspending",
            content_sha256=archive_hash,
            archive_uri="examples/real_evidence/usaspending_torch.json",
            retention_tier="hot",
            source_ref=f"usaspending:award:{award_id}",
            source_url=opp.meta.get("url"),
            id=f"ev_usasp_award_{award_id}",
        )]
        opp.meta.update({
            "subject_ref": TORCH_REF,
            "subject_name": TORCH_NAME,
            "program_key": award_id,
            "source_ref": f"usaspending:award:{award_id}",
            "source_as_of": OPP_AS_OF.isoformat(),  # when Pyrnova could know it entered the recompete window
            "archive_hash": archive_hash,
            "evidence_sources": ["usaspending"],
        })
        records.append(to_record(opp))
    return records


def build() -> dict:
    saic_direct, saic_prop = _saic_torch_chain()
    dap_direct, dap_prop = _dap_parent_chain()
    threats = saic_direct + dap_direct
    propagated = saic_prop + dap_prop
    opportunities = _torch_recompete_opportunities()
    OUT.mkdir(parents=True, exist_ok=True)
    _write(OUT / "threats.jsonl", threats)
    _write(OUT / "propagated_threats.jsonl", propagated)
    _write(OUT / "opportunities.jsonl", opportunities)
    return {"threats": len(threats), "propagated_threats": len(propagated),
            "opportunities": len(opportunities)}


def _write(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    print(build())
