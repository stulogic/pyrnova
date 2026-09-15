"""B1.5 — ugly opportunity-lifecycle probe (TEST current behavior; change nothing).

Constructs one commercial opportunity (a single program_key) evolving through the full lifecycle —
budget precursor, forecast, sources sought, presolicitation, solicitation, two amendments, a
cancellation, a reissue, award, and a later recompete — and observes how the *existing* chain
resolver (`pyrnova.chains.resolve_chain`) represents it. No architecture change here; this only reports.
"""
from __future__ import annotations

import json

from pyrnova.chains import resolve_chain, signals_from_records

PK = "disa:cloud-modernization"          # one commercial reality
PK_RECOMPETE = "disa:cloud-modernization"  # recompete is the SAME program evolving

RECORDS = [
    # budget precursor / authorization / funding
    {"source_id": "appropriations", "source_ref": "disa-budget-fy26", "stage": "AUTHORIZATION",
     "program_key": PK, "available_at": "2025-02-01", "summary": "DISA cloud budget line"},
    {"source_id": "appropriations", "source_ref": "disa-approp-fy26", "stage": "FUNDING",
     "program_key": PK, "available_at": "2025-03-15", "summary": "DISA cloud appropriation"},
    # forecast + sources sought (market engagement)
    {"source_id": "acquisition_forecast", "source_ref": "disa-forecast-2025", "stage": "MARKET_ENGAGEMENT",
     "program_key": PK, "available_at": "2025-04-01", "summary": "DISA cloud forecast row"},
    {"source_id": "sam_opportunities", "source_ref": "SS-DISA-CLOUD", "stage": "MARKET_ENGAGEMENT",
     "program_key": PK, "available_at": "2025-05-01", "summary": "Sources Sought: DISA cloud"},
    # presolicitation + solicitation + two amendments (procurement)
    {"source_id": "sam_opportunities", "source_ref": "PRESOL-DISA-CLOUD", "stage": "PROCUREMENT",
     "program_key": PK, "available_at": "2025-06-01", "summary": "Presolicitation: DISA cloud"},
    {"source_id": "sam_opportunities", "source_ref": "SOL-DISA-CLOUD", "stage": "PROCUREMENT",
     "program_key": PK, "available_at": "2025-07-01", "summary": "Solicitation: DISA cloud"},
    {"source_id": "sam_opportunities", "source_ref": "SOL-DISA-CLOUD-AMD1", "stage": "PROCUREMENT",
     "program_key": PK, "available_at": "2025-07-15", "summary": "Amendment 1: DISA cloud (Q&A, deadline)"},
    {"source_id": "sam_opportunities", "source_ref": "SOL-DISA-CLOUD-AMD2", "stage": "PROCUREMENT",
     "program_key": PK, "available_at": "2025-08-01", "summary": "Amendment 2: DISA cloud (scope clarification)"},
    # cancellation of the solicitation
    {"source_id": "sam_opportunities", "source_ref": "SOL-DISA-CLOUD-CANCEL", "stage": "PROCUREMENT",
     "program_key": PK, "available_at": "2025-08-20", "summary": "Cancellation: DISA cloud solicitation",
     "contradicts": True},
    # reissue as a new solicitation of the same requirement
    {"source_id": "sam_opportunities", "source_ref": "SOL-DISA-CLOUD-V2", "stage": "PROCUREMENT",
     "program_key": PK, "available_at": "2025-10-01", "summary": "Reissued solicitation: DISA cloud"},
    # award + later recompete of the same program
    {"source_id": "usaspending", "source_ref": "AWARD-DISA-CLOUD", "stage": "AWARD",
     "program_key": PK, "available_at": "2026-01-15", "summary": "Award: DISA cloud"},
    {"source_id": "sam_opportunities", "source_ref": "SOL-DISA-CLOUD-RECOMPETE", "stage": "PROCUREMENT",
     "program_key": PK_RECOMPETE, "available_at": "2030-06-01", "summary": "Recompete solicitation: DISA cloud"},
]


def probe(as_of: str | None = None) -> dict:
    signals = signals_from_records(RECORDS, as_of=as_of)
    res = resolve_chain(signals, allow_inferred=True)
    m = res.metrics()
    procurement_signals = [s for s in res.signals if s.stage == "PROCUREMENT"]
    return {
        "as_of": as_of or "ALL",
        "program_keys": m["program_keys"],
        "single_commercial_identity": len(m["program_keys"]) == 1,
        "unique_signals": m["unique_signals"],
        "duplicates_collapsed": m["duplicates_collapsed"],
        "stages_present": m["stages_present"],
        "relationships_total": m["relationships_total"],
        "contradictions": m["contradictions"],
        "procurement_stage_signal_count": len(procurement_signals),
        "procurement_refs": sorted(s.source_ref for s in procurement_signals),
        "chain_confidence": m["chain_confidence"],
    }


def main() -> int:
    out = {
        "all_time": probe(),
        "as_of_2025_07_20_mid_amendments": probe("2025-07-20"),
        "as_of_2025_09_01_after_cancellation": probe("2025-09-01"),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
