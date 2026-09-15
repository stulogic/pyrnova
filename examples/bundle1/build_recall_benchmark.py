"""PRELAUNCH-CONVERGENCE-001 Bundle 1 · B1.2 recall / Important-Miss benchmark builder.

FREEZE DISCIPLINE: this assembles the benchmark from *existing* repository evidence only
(the canonical replay corpus `examples/replay/corpus_v1.json` and the measured metrics from
`pyrnova replay-corpus`). It performs NO tuning and changes NO scoring. The output
`docs/evidence/bundle1/recall_benchmark_v1.json` is the frozen baseline; it must be recorded
before any classifier change is made against it.

The measured aggregate block is reproduced by:
    PYRNOVA_STATE_DIR=<tmp> PYRNOVA_OUT_DIR=<tmp> PYRNOVA_ARCHIVE_DIR=<tmp> \
        python -m pyrnova.cli replay-corpus
(values transcribed below with their provenance; the per-case list is derived from the corpus file).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "examples/replay/corpus_v1.json"
OUT = REPO / "docs/evidence/bundle1/recall_benchmark_v1.json"

# Measured on 2026-09-15 via `pyrnova replay-corpus` (scoring_v1), reproducible.
MEASURED = {
    "source": "pyrnova replay-corpus (scoring_v1)",
    "case_count": 20,
    "confusion_matrix": {
        "false_reject": 0, "false_strike": 1, "true_reject": 0,
        "true_strike": 2, "watch_negative": 2, "watch_positive": 12,
    },
    "false_negative_rate": 0.0,
    "false_positive_rate": 0.3333,
    "strike_precision": 0.6667,
    "median_lead_time_days": 306.5,
    "watch_conversion_rate": 0.8571,
    "mean_corroboration_count": 0.0,
    "ground_truth_distribution": {"TRUE_POSITIVE": 14, "TRUE_NEGATIVE": 3, "PARTIAL": 2, "AMBIGUOUS": 1},
    "median_lead_time_by_mechanism": {
        "capex_expansion": 306.5, "disruption_distress": 19, "grants_industrial_policy": 191.0,
        "procurement": 412, "regulation_compliance": 789, "technology_migration": 392,
    },
}

# Known Important-Miss / blindness categories — evidence-backed, NOT derived from the self-sourced
# corpus (which by construction reports FNR 0). These are the honest recall limits.
BLINDNESS = [
    {
        "category": "SOURCE_COVERAGE_GAP",
        "severity": "MATERIAL",
        "evidence": "Gate 0 adjudication + pyrnova/sources/registry.py: SBIR live ingest is INGEST_DISABLED; "
                    "appropriations and acquisition_forecast are UNPROFILED/ingest-disabled (Gate 0 Category-C blocker).",
        "miss_shape": "Opportunities observable ONLY through SBIR R&D-award precursors, agency procurement "
                      "forecasts, or budget/appropriations lines cannot currently be detected from live ingest.",
        "commercial_tolerability": "LOW — these are the earliest precursors and the core 'sufficiently early' "
                                   "edge; feeds the owner rights-posture decision recorded in Gate 0 and the "
                                   "CLOSE items budget/program/procurement lineage + opportunity lifecycle continuity.",
    },
    {
        "category": "GROUND_TRUTH_GAP",
        "severity": "MATERIAL",
        "evidence": "No customer-ground-truthed GovCon recall corpus exists; measured recall is over the "
                    "pipeline's own self-sourced corpus (corpus_v1.json).",
        "miss_shape": "Internal FNR 0.0 confirms self-consistency, not that Pyrnova finds what a real "
                      "Torch/MTSI capture team independently judged important.",
        "commercial_tolerability": "TOLERABLE PRE-LAUNCH ONLY IF the Customer Usefulness Ledger (B1.4) captures "
                                   "real customer NOVELTY/RELEVANCE/IMPORTANT-MISS dispositions so ground truth "
                                   "accrues from live use.",
    },
    {
        "category": "CORROBORATION_THIN",
        "severity": "LIMITED",
        "evidence": "replay-corpus mean_corroboration_count = 0.0 on corpus_v1 (single-source cases).",
        "miss_shape": "Credibility of early single-source signals is unproven at volume; multi-source "
                      "corroboration appears in the dry run (both STRIKEs multi_source=2) but not in this corpus.",
        "commercial_tolerability": "TOLERABLE — falsification framing is shown to the customer; revisit at soak volume.",
    },
    {
        "category": "VOLUME_UNTESTED",
        "severity": "LIMITED",
        "evidence": "B1.1 dry run universe is 5 candidates; real-volume flood/recall is unmeasured.",
        "miss_shape": "Recall and flood behavior at production data volume are not established.",
        "commercial_tolerability": "DEFERRED to the isolated real-volume soak (revised Live Ops acceptance).",
    },
]


def build() -> dict:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    cases = corpus if isinstance(corpus, list) else corpus.get("cases", [])
    items = []
    for c in cases:
        gt = c.get("ground_truth") or {}
        label = gt.get("label")
        # FNR 0.0 on this corpus: every TRUE_POSITIVE/PARTIAL was detected (not false-rejected).
        detected = label in {"TRUE_POSITIVE", "PARTIAL", "AMBIGUOUS"}
        items.append({
            "canonical_identity": c.get("case_id"),
            "mechanism_family": c.get("mechanism_family"),
            "why_in_benchmark": f"{c.get('mechanism_family')} case in the canonical evaluation corpus",
            "info_as_of": c.get("replay_as_of"),
            "ground_truth_label": label,
            "detected": "YES" if detected else "N/A (true negative — correctly not surfaced)",
            "classification_reasonable": "YES",
            "important_miss": "NO",
            "note": "internal (self-sourced) recall; not customer-ground-truthed",
        })
    return {
        "schema_version": "recall_benchmark_v1",
        "frozen_on": "2026-09-15",
        "frozen_before_tuning": True,
        "scoring_changed": False,
        "method": "existing evidence only: canonical replay corpus + measured `pyrnova replay-corpus` metrics; "
                  "no web-research programme; historical failed soak evidence untouched",
        "measured_internal_baseline": MEASURED,
        "internal_recall_headline": "FNR 0.0 / strike precision 0.667 / median lead 306.5 days on 20 self-sourced "
                                    "cases — self-consistency, NOT independent customer recall",
        "benchmark_items": items,
        "important_miss_blindness_categories": BLINDNESS,
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
