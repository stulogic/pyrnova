# B1.2 — Recall / Important-Miss benchmark (frozen baseline)

PRELAUNCH-CONVERGENCE-001 · Bundle 1 · B1.2. **Frozen before any tuning**; no scoring changed.
Frozen artifact: `docs/evidence/bundle1/recall_benchmark_v1.json` (built by
`examples/bundle1/build_recall_benchmark.py` from existing evidence only). The required output is not
"100% recall" — it is a measured baseline, the known important misses, the categories of blindness, and
whether those misses are commercially tolerable.

## Measured internal baseline (reproducible)

Source: `pyrnova replay-corpus` (scoring_v1) over the canonical 20-case corpus `examples/replay/corpus_v1.json`.

| Metric | Value |
|---|---|
| Cases | 20 (14 TRUE_POSITIVE, 3 TRUE_NEGATIVE, 2 PARTIAL, 1 AMBIGUOUS) |
| False-negative rate (missed true positives) | **0.0** |
| Strike precision | 0.667 (1 false strike) |
| Median lead time | **306.5 days** |
| Median lead by mechanism | procurement 412 d · regulation 789 d · tech-migration 392 d · capex 306.5 d · grants 191 d · disruption 19 d |
| WATCH conversion rate | 0.857 |
| Mean corroboration count | 0.0 (single-source on this corpus) |

**Headline (honest):** on its own corpus Pyrnova misses nothing it was built to find (FNR 0) and warns
very early (median ~10 months). This is **self-consistency, not independent customer recall.** Pyrnova's
selectivity evidence remains stronger than its customer-ground-truthed recall evidence — exactly the gap
this benchmark exists to name.

## Known important misses / categories of blindness

These are the real recall limits. They are **not** derived from the self-sourced corpus (which reports
FNR 0 by construction); they are evidence-backed structural gaps.

1. **SOURCE_COVERAGE_GAP (MATERIAL).** SBIR live ingest is `INGEST_DISABLED`; `appropriations` and
   `acquisition_forecast` are unprofiled/ingest-disabled (Gate 0 Category-C blocker;
   `pyrnova/sources/registry.py`). Opportunities observable **only** through SBIR R&D-award precursors,
   agency procurement forecasts, or budget/appropriations lines cannot currently be detected from live
   ingest. Commercial tolerability: **LOW** — these are the earliest precursors and the core
   "sufficiently early" edge. This directly feeds the recorded owner rights-posture decision and the
   CLOSE items *budget/program/procurement lineage* and *opportunity lifecycle continuity*.
2. **GROUND_TRUTH_GAP (MATERIAL).** No customer-ground-truthed GovCon recall corpus exists. Tolerable
   pre-launch **only if** the Customer Usefulness Ledger (B1.4) captures real customer NOVELTY /
   RELEVANCE / IMPORTANT-MISS dispositions so ground truth accrues from live use.
3. **CORROBORATION_THIN (LIMITED).** `mean_corroboration_count` 0.0 on corpus_v1 (single-source cases);
   multi-source corroboration does appear in the B1.1 dry run (both STRIKEs `multi_source`=2) but is not
   established at volume. Falsification framing is shown to the customer; revisit at soak volume.
4. **VOLUME_UNTESTED (LIMITED).** The B1.1 dry-run universe is 5 candidates; real-volume flood/recall is
   deferred to the isolated real-volume soak (revised Live Ops acceptance rule, §11 of the spec).

## Commercial-tolerability verdict

- The **source-coverage gap is the one materially intolerable miss** for the product's core promise
  (early precursors). It is already captured as a Gate-0 owner decision and as CLOSE items; it must be
  resolved (enable/confirm the disabled precursor sources) before a recall claim is credible.
- The ground-truth gap is tolerable pre-launch **contingent on B1.4** turning live customer feedback into
  accruing recall evidence.
- Corroboration and volume gaps are deferred to the soak.

No classifier behavior was optimized against this benchmark; it is frozen for exactly that reason.
