# Milestone 3 replay baseline

_Status: CLOSED 2026-09-08 · generated from `examples/replay/corpus_v1.json`._

All 15 M3 acceptance criteria passed: corpus size/coverage/balance, future exclusion, determinism,
version persistence, automatic metrics, measurable STRIKE/WATCH/lead-time/evidence behavior, human
adjudication integration, full-corpus policy comparison, no single-case scoring adoption, and explicit
weakness documentation.

## Corpus

- 20 reviewed historical cases.
- Six mechanism families: procurement, grants/industrial policy, regulation/compliance,
  capex/expansion, disruption/distress, and technology migration.
- Ground truth: 14 TRUE_POSITIVE, 3 TRUE_NEGATIVE, 2 PARTIAL, 1 AMBIGUOUS.
- Every canonical case has an explicit UTC replay cutoff, known-at-cutoff evidence, at least one
  excluded later record, outcome, ground-truth confidence, reviewer, and human adjudication.
- Source links are government or first-party corporate records. Direct URL checks were performed;
  some official sites return bot/access-control responses to command-line clients, so the source
  identity and document reference are retained separately from URL reachability.

## `scoring_v1` baseline

- STRIKE precision: **0.6667** (2/3 known-outcome STRIKEs).
- WATCH conversion: **0.8571**.
- False-positive rate: **0.3333**.
- False-negative rate: **0.0**.
- Median measurable lead time: **306.5 days**.
- Human override rate: **0.15**.

The output is persisted as `out/replay_report_e16e390145df214909949b2b.json`; replay results and
report metadata are also appended to local state. The report ID and each replay ID are deterministic.

## Full-corpus scoring comparison

`scoring_v2_candidate` raises only the direct-opportunity STRIKE threshold from 0.30 to 0.80. It was
run against all 20 cases, not selected examples. It demoted one cancelled Army solicitation from
STRIKE to WATCH, moving measured STRIKE precision from 0.6667 to 1.0 and false-positive rate from
0.3333 to 0.0, while WATCH conversion fell from 0.8571 to 0.8.

**Decision: do not adopt.** The apparent improvement is driven by one negative among only three
STRIKE-labelled cases. That is too little evidence and would violate the no-showcase-optimization
rule. `scoring_v1` remains active; both challenger outputs and their version identifiers are retained.
Comparison report: `out/replay_report_e3fc70c8d3b650f270bfb699.json`.

## Known weaknesses

- The initial corpus has only three known-outcome STRIKEs, so precision has a wide uncertainty range.
- TRUE_NEGATIVE representation is adequate to make false positives visible but remains small.
- PARTIAL and AMBIGUOUS cases are excluded from binary precision/error denominators.
- Value calibration has only two cases with comparable predicted and actual values; no general value
  conclusion is justified.
- Several long-horizon WATCH cases measure conversion to a later program action, not customer revenue.
- URL availability can change after review; canonical identity uses source/document references and
  dates rather than treating current URL reachability as historical availability proof.

## Commands

```bash
python -m pyrnova.cli replay --case tests/fixtures/replay_chips_2022.json --scoring-version scoring_v1
python -m pyrnova.cli replay --case tests/fixtures/replay_chips_2022.json --inspect-excluded
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_v1.json
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_v1.json --mechanism procurement
python -m pyrnova.cli compare-scoring --corpus examples/replay/corpus_v1.json
python -m pyrnova.cli metrics --scoring-version scoring_v1
```
