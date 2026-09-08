# Milestone 4 source-contribution report

_Verified 2026-09-08 from `examples/replay/corpus_m4.json` under `scoring_v1`._

The M4 corpus extends, rather than edits, the frozen 20-case M3 corpus. It adds three reviewed cases:
one Grants.gov industrial-policy NOFO, one SEC EDGAR capex disclosure, and one unresolved official
agency procurement forecast. All later evidence remains excluded at each replay cutoff.

## Expanded corpus result

- 23 cases; all six mechanism families remain represented.
- STRIKE precision: **0.6667**.
- WATCH conversion: **0.8667**.
- False-positive rate: **0.3333**.
- False-negative rate: **0.0**.
- Median measurable lead time: **297.5 days**.
- No new STRIKEs and no scoring change.

## New-source contribution

| Source | Raw records | Visible normalized evidence | WATCH promotions under ablation | STRIKE promotions | Precision delta | Finding |
|---|---:|---:|---:|---:|---:|---|
| Grants.gov | 1 | 1 | 1 | 0 | 0.0 | Named funding opportunity supports earlier WATCH; it is not procurement proof. |
| SEC EDGAR | 2 | 1 | 1 | 0 | 0.0 | Attributable issuer capex disclosure supports WATCH; timing/downstream demand remain contingent. |
| Agency procurement forecast | 1 | 1 | 1 | 0 | 0.0 | Named forecast supports monitoring, but unresolved/non-binding status blocks promotion. |

The source-specific cases contain no duplicate records and no records classified as noise at their
cutoffs. The sample is intentionally small: these results prove conservative contribution and absence
of selectivity regression, not general predictive lift. Run:

```bash
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_m4.json
python -m pyrnova.cli source-contribution --corpus examples/replay/corpus_m4.json
```
