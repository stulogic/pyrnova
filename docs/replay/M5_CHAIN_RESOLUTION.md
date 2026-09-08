# Milestone 5 chain-resolution report

_Verified 2026-09-08 from `examples/replay/corpus_m5.json` under `scoring_v1`._

`corpus_m5.json` extends the frozen 23-case M4 corpus with four reviewed cross-source chain cases. The
M4 scoring baseline is unchanged; M5 adds cross-source relationship reconstruction, opportunity
evolution, and chain observability on top of it.

## Scoring impact (no `scoring_v1` change)

| Corpus | Cases | STRIKE precision | WATCH conversion | FPR | FNR | Median lead |
|---|---:|---:|---:|---:|---:|---:|
| `corpus_m4` (frozen) | 23 | 0.6667 | 0.8667 | 0.3333 | 0.0 | 297.5 |
| `corpus_m5` | 27 | 0.75 | 0.875 | 0.25 | 0.0 | 297.5 |

The single additional STRIKE is the hand-reviewed Navy C5ISR lifecycle — a true positive with a
forecast, a matching SAM solicitation, and the USAspending award sharing program identity and native
identifiers. No false positive was added; precision rises and FPR falls purely from correctly
adjudicated cases. `scoring_v1` was not modified.

## Cross-source chain observability

Across the seven corpus cases that carry explicit program identity (four M5 chain cases plus three
M4 cases whose records already declared stages):

- Cross-source relationships: **7**, all **deterministic** (program-key or native-identifier). Inferred: **0**.
- Rejected weak joins: **1** (topic-overlap-only; the HHS/DHS cloud false join).
- Duplicate signals collapsed: **0**. Contradictions: **0**. Corroborations: **0**.
- Promotion events observed: **8**, caused at stages — MARKET_ENGAGEMENT 4, FUNDING 2, INTENT 1, PROCUREMENT 1.
- Median chain lead time: **434 days**.
- Expected-chain assertions: **4 of 4 passing**.

## Case findings

| Case | Chain type | Result |
|---|---|---|
| `chain-navy-c5isr-lifecycle-2023` | forecast → solicitation → award | Full deterministic lifecycle; trajectory WATCH→STRIKE (promoted at the solicitation); 434-day lead; chain confidence 0.95. |
| `chain-doe-battery-hub-downstream-2022` | grant → program → downstream award | Deterministic `FUNDS`/`PRECEDES` chain; stays WATCH at NOFO time — a grant is funding, not an automatic STRIKE. |
| `chain-false-join-hhs-dhs-cloud-2024` | tempting false join | Rejected as topic-overlap-only; zero relationships; disposition REJECT (true negative). |
| `chain-faa-tracon-unresolved-2024` | partial / unresolved | Single-stage partial chain with a dangling downstream reference; remains WATCH; no invented edge. |

## Reproduce

```bash
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_m4.json   # frozen baseline unchanged
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_m5.json   # +1 true-positive STRIKE
python -m pyrnova.cli chain-corpus  --corpus examples/replay/corpus_m5.json
```

## Limitations

- The chain corpus is intentionally small (four reviewed cases); it demonstrates that resolution is
  deterministic, evidence-gated, and rejects weak joins — not broad predictive lift.
- All accepted joins here are deterministic. The conservative `inferred_strong_attribute` path is
  implemented and tested but not yet exercised by a corpus case.
- Entity-level predicates (`AWARDED_TO`, `SUBSIDIARY_OF`, `LOCATED_AT`) and budget/appropriation
  precursor stages are represented in the vocabulary/schema but await reviewed primary evidence.
