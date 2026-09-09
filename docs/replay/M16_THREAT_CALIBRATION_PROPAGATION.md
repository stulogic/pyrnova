# M16 threat calibration + propagation + selectivity — replay evidence

_Generated 2026-09-09. Semantics: `docs/specs/M16_THREAT_CALIBRATION_PROPAGATION.md` (canonical)._

Reproduce:

```python
from pathlib import Path
from pyrnova import threat, selectivity
from pyrnova.sources import ofac
des = ofac.parse_ofac_csv(Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")
res = threat.run_threat_corpus(threat.load_threat_corpus("examples/replay/corpus_m16.json"), des)
print(threat.summarize_m16(res))   # 35 cases, all pass
```

## Merged corpus metrics (35 cases — directional, small sample)

| Metric | Value |
|---|---|
| cases / passing | 35 / 35 |
| threats emitted | 22 (direct) |
| zero-threat rejections | 11 |
| mechanism distribution | SANCTIONS_EXPOSURE 6, INCUMBENT_DISPLACEMENT 4, PROGRAM_CONTRACTION 3, PROGRAM_CANCELLATION_OR_DELAY 3, + CUSTOMER_CONCENTRATION, ELIGIBILITY_OR_CERTIFICATION_RISK, REGULATORY_COMPLIANCE_EXPOSURE, SUPPLIER_DEPENDENCY_DISRUPTION, TECHNOLOGY_SUBSTITUTION, GEOGRAPHY_FACILITY_DISRUPTION (1 each) — **10 mechanisms** |
| severity distribution | CRITICAL 2, HIGH 16, MODERATE 4 |
| confidence distribution | HIGH 18, MEDIUM 3, LOW 1 (distinct from severity) |
| rejection reasons | WEAK_NAME_MATCH_ONLY 3, NO_EXPOSURE 3, NO_DEPENDENCY 1, VAGUE_TREND_NOT_EVIDENCE 1, OUTSIDE_EXPOSURE_GEOGRAPHY 1, RECOMPETE_NOT_A_THREAT 1, IMMATERIAL 1 |
| exposures | 34 confirmed / 6 inferred / 3 weak rejected |
| dual-sided cases | 2 |

## Propagation (bounded, no explosion)

| Metric | Value |
|---|---|
| propagation cases | 2 |
| direct threats | 22 |
| propagated threats | 3 (≪ direct — no explosion) |
| beneficiary opportunities | 2 |
| max propagation depth | 2 (bounded) |
| cycles prevented / duplicates suppressed | tested in `test_m16_propagation.py` |

Case `m16-propagation-sanctions-supply-chain`: sanctioned supplier → importer A (direct) → B (depth 1)
→ C (depth 2, confidence degraded HIGH→MEDIUM→LOW) + a substitute beneficiary; depth-3 terminates on
confidence exhaustion. Case `m16-propagation-program-cancellation`: cancelled program → incumbent prime
(direct) → subcontractor (propagated) + competitor beneficiary.

## Calibration

| Metric | Value |
|---|---|
| resolved outcomes | 5 |
| detection distribution | TRUE_THREAT 5 |
| confirmed-threat precision | **1.0 (denominator 5)** — directional |
| unresolved threats / rate | 17 / 0.77 (never counted false) |
| materialization rate | 0.4 (of 5 resolved) |
| mitigation/avoidance rate | 0.4 |
| median lead time | **306 days** (sample 5) |
| false_alert_from_absence | 0 (invariant) |

Historical cases exercise MATERIALIZED, AVOIDED, MITIGATED, DELAYED, an UNRESOLVED threat (never false),
and a future-dated outcome excluded at the evaluation cutoff (resolves UNKNOWN).

## Real event-stream selectivity (the guardrail proof)

`tests/test_m16_selectivity.py` (guarded, skips without the git-ignored archive), 19,365 real OFAC SDN
designations × 4 monitored companies with benign counterparties:

| funnel stage | count |
|---|---|
| raw_events | 19,365 |
| exposure_candidates | 4 (weak name overlaps) |
| accepted_exposures | 0 |
| threats_emitted | **0** |
| zero_threat_rejections | 4 |

`threat_emission_rate` 0.0, `weak_rejection_rate` 1.0. A large batch of real events produces no threat
for ordinary companies — selectivity holds at scale.

## Tests & invariants

Focused: `test_m16_families_calibration.py` (9), `test_m16_propagation.py` (9), `test_m16_selectivity.py`
(2), `test_m16_corpus.py` (6), `test_m16_ops_panel.py` (3). Full suite: **400 passed**. `scoring_v1`,
`fit.py`, `replay.py`, and all frozen corpora (incl. `corpus_m15`) byte-for-byte unchanged. 0 live API
calls in M16.
