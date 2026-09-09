# M15 threat intelligence — replay evidence

_Generated 2026-09-09 from `examples/replay/corpus_m15.json` via `pyrnova.threat.run_threat_corpus` +
`summarize_threats`. Semantics: `docs/specs/M15_THREAT_INTELLIGENCE.md` (canonical)._

Reproduce:

```python
from pathlib import Path
from pyrnova import threat
from pyrnova.sources import ofac
des = ofac.parse_ofac_csv(Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")
payload = threat.load_threat_corpus("examples/replay/corpus_m15.json")
results = threat.run_threat_corpus(payload, des)
print(threat.summarize_threats(results))   # all 17 cases pass
```

## Metrics (17 cases — directional, small sample)

| Metric | Value |
|---|---|
| threats emitted | 11 |
| zero-threat rejections | 4 |
| threat:event ratio | 0.733 (semantic-coverage corpus, not live selectivity) |
| mechanism distribution | SANCTIONS_EXPOSURE 4, PROGRAM_CONTRACTION 2, INCUMBENT_DISPLACEMENT 1, PROGRAM_CANCELLATION_OR_DELAY 1, REGULATORY_COMPLIANCE_EXPOSURE 1, ELIGIBILITY_OR_CERTIFICATION_RISK 1, CUSTOMER_CONCENTRATION 1 |
| severity distribution | CRITICAL 2, HIGH 7, MODERATE 2 |
| confidence distribution | HIGH 7, MEDIUM 3, LOW 1 |
| horizon distribution | IMMEDIATE 4, MEDIUM_TERM 5, NEAR_TERM 2 |
| rejection reasons | WEAK_NAME_MATCH_ONLY 2, NO_EXPOSURE 1, RECOMPETE_NOT_A_THREAT 1 |
| exposures total | 19 (CONFIRMED 15, INFERRED 4) |
| weak candidates rejected | 2 |
| dual-sided cases | 2 |
| real-subject cases | 1 (Torch) |
| synthetic_probe cases | 3 (clearly labelled) |
| false_exposure_rate | 0.0 |
| temporal_leakage_violations | 0 |
| cases passing | 17 / 17 |

Severity and confidence are **distinct distributions** — proven by
`m15-severity-confidence-split` (CRITICAL severity, LOW confidence on the same threat).

## Key cases

- **Sanctions confirmed** (`m15-sanctions-confirmed-supplier`): explicit OFAC `ent_num` =>
  deterministic_identifier, CONFIRMED exposure, SANCTIONS_EXPOSURE, severity HIGH, confidence HIGH.
- **Sanctions dual-sided** (`m15-sanctions-dual-sided`): identity-tuple CONFIRMED threat to the importer
  + a compliant-substitute opportunity sharing the same catalyst (`dual_links` 1).
- **Weak-name reject** (`m15-sanctions-weak-name-reject`): a shared token => `WEAK_NAME_MATCH_ONLY`
  rejection, no threat.
- **Sanctions unknown** (`m15-sanctions-unknown-no-linkage`): no linkage => 0 threats, 0 rejections.
- **Real Torch incumbency** (`m15-incumbent-displacement-real-torch`): real award `W31P4Q21F0038`
  ($623M) => severity CRITICAL, confidence MEDIUM (labelled displacement catalyst).
- **Recompete not a threat** (`m15-recompete-not-a-threat`): incumbency + recompete, no signal =>
  `RECOMPETE_NOT_A_THREAT`.
- **Program cancellation / contraction**: MODERATE ($8M) and HIGH ($40M) severity from known dollar bands.
- **Eligibility + dual** (`m15-eligibility-cert-dual`): ELIGIBILITY risk + compliance-vendor opportunity.
- **Zero-threat irrelevant regulation** (`m15-zero-threat-irrelevant-regulation`): a mandate on a cert
  the subject does not hold => `NO_EXPOSURE`.
- **Future-evidence exclusion** (`m15-future-evidence-exclusion`): catalyst not yet knowable at the
  cutoff => no threat.
- **Threat evolution** (`m15-evolution-t1-weak-candidate` -> `-t2-confirmed-plus-outcome`): weak
  candidate at T1 => rejection; authoritative identifier at T2 => CONFIRMED threat; a MATERIALIZED
  outcome dated after the prediction is excluded at prediction time (resolves UNKNOWN) and resolves
  MATERIALIZED only at a later cutoff (`m15-outcome-materialized-resolved`).

## Real-data check

`tests/test_m15_real_ofac.py` (guarded; skips without the git-ignored `var/m14_archive/`) runs the same
linkage code against the **19,365 real archived SDN designations**: an explicit real `ent_num` =>
CONFIRMED; a benign company sharing only a token with some real designation => never a threat.

## Tests

Focused: `test_m15_exposure.py` (8), `test_m15_threat_engine.py` (13), `test_m15_corpus.py` (6),
`test_m15_ops_panel.py` (3), `test_m15_real_ofac.py` (1). Full suite: **373 passed**. Frozen corpora +
`scoring_v1` + `fit.py` byte-for-byte unchanged.
