# Milestone 7 commercial-consequence report

_Verified 2026-09-08 from `examples/replay/corpus_m7.json` under `scoring_v1`._

`corpus_m7.json` extends the frozen 35-case M6 corpus with eight commercial-consequence cases. M2–M6
corpora are byte-for-byte unchanged. Each M7 case declares `expected_consequences` carrying
consequence-level ground truth; precision is graded only where that truth exists.

## Scoring impact (no `scoring_v1` change)

| Corpus | Cases | STRIKE precision | WATCH conversion | FPR | FNR |
|---|---:|---:|---:|---:|---:|
| `corpus_m6` (frozen) | 35 | 0.80 | 0.8889 | 0.1429 | 0.0 |
| `corpus_m7` | 43 | 0.875 | 0.8571 | 0.125 | 0.0 |

Confusion: true_strike 7, false_strike 1 (inherited), false_reject 0. The added STRIKEs are the Navy
radar, CHIPS construction, and directed-energy cases — all true positives with a resolved buyer and a
specific capability. **No STRIKE explosion**: 7 true STRIKEs across 43 cases. FNR stays 0.

## Consequence engine observability

- Catalysts created: **29** (2 duplicate program keys collapsed into their chain component).
- Consequences created: **23**. Zero-consequence catalysts: **6**. Multi-consequence cases: **4**.
- Directness: DIRECT **13**, DOWNSTREAM **7**, SECOND_ORDER **3**.
- Mechanism families exercised: **5** — DIRECT_PROCUREMENT, FUNDED_DOWNSTREAM_DEMAND,
  FORCED_COMPLIANCE_SPEND, CAPITAL_EXPANSION, INDUSTRIAL_CAPACITY_BUILDOUT. (SUPPLY_DISPLACEMENT and
  TECHNOLOGY_MIGRATION are implemented but not yet corpus-exercised.)
- Buyer resolution rate: **0.5652**. Capability resolution rate: **0.5217**.
- Value status: KNOWN **4**, BOUNDED **3**, UNKNOWN **16** — value can and does remain UNKNOWN.
- Rejected consequences: **1** (`internal_self_performance`, fatal).
- Consequence precision: **1.0**; false-consequence rate: **0.0** (graded over the 8 cases with
  declared consequence ground truth). Per-mechanism precision 1.0 where decided. A small-sample
  warning is emitted and never hidden.
- `expected_consequences` checks: **8 / 8 passing**.

## Case findings

| Case | Mechanism / directness | Result |
|---|---|---|
| `m7-direct-strike-navy-radar-2024` | DIRECT_PROCUREMENT / DIRECT | STRIKE; buyer + prime recipient + radar capability; value KNOWN. |
| `m7-downstream-grant-battery-2023` | FUNDED_DOWNSTREAM_DEMAND / DOWNSTREAM | WATCH; beneficiary role; value BOUNDED from program × fraction. |
| `m7-multi-consequence-chips-2022` | multiple | One program → distinct consequences (facility construction STRIKE, capacity buildout, fabricator demand). |
| `m7-zero-consequence-appropriation-2024` | none | Catalyst built, **zero consequences** — no procurement/grant/regulation, so no invented ideas. |
| `m7-killed-internal-selfperf-2024` | DIRECT_PROCUREMENT | REJECTED by `internal_self_performance` fatal falsifier. |
| `m7-compliance-epa-2024` | FORCED_COMPLIANCE_SPEND / DOWNSTREAM | WATCH; regulated-entity role; enforceable obligation with a deadline. |
| `m7-second-order-capex-2024` | CAPITAL_EXPANSION / SECOND_ORDER | WATCH (internal); `speculative_second_order` falsifier retained. |
| `m7-unknown-value-directed-energy-2024` | DIRECT_PROCUREMENT / DIRECT | STRIKE; value UNKNOWN with provenance — not invented. |

## Chain → consequence → STRIKE

The CHIPS case shows one capital program producing several economically distinct consequences; the
Navy radar and directed-energy cases show DIRECT procurement with a resolved buyer and a specific
capability promoted to STRIKE; the appropriation and capex cases show the conservative floor (zero
consequences, or a second-order WATCH held internal).

## Reproduce

```bash
python -m pyrnova.cli replay-corpus      --corpus examples/replay/corpus_m6.json   # frozen baseline
python -m pyrnova.cli replay-corpus      --corpus examples/replay/corpus_m7.json   # scoring_v1 unchanged
python -m pyrnova.cli consequence-corpus --corpus examples/replay/corpus_m7.json --verbose
```

## Limitations

- Consequence precision/false-consequence rates rest on 8 graded cases — directional, not stable.
- SUPPLY_DISPLACEMENT and TECHNOLOGY_MIGRATION mechanisms are implemented but not yet corpus-exercised.
- Capability and value extraction depend on structured NAICS/PSC and explicit amounts; absent those,
  capability resolution and value are correctly UNKNOWN rather than guessed.
- Consequence generation is retrospective; per-cutoff consequence transitions are not yet integrated
  into `derive_transitions`.
- No live API calls were made.
