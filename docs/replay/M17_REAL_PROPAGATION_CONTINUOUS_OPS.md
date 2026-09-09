# M17 — real propagation + continuous operations: replay evidence

_Reproducible evidence for the M17 close (2026-09-09). Spec:
`docs/specs/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md`. All offline; **0 live API calls**._

## Reproduce

```bash
cd ~/Documents/Pyrnova
.venv/bin/python -m pytest          # full suite: 428 passed

# real relationship graph grounded from archived sub-award bytes
.venv/bin/python -m pytest tests/test_m17_relationships.py tests/test_m17_real_propagation.py

# corpus replay + calibration + frozen-lineage integrity
.venv/bin/python -m pytest tests/test_m17_corpus.py tests/test_m17_quality_metrics.py

# continuous selectivity + company threat network view
.venv/bin/python -m pytest tests/test_m17_continuous_selectivity.py tests/test_m17_network_view.py
```

## Real relationship graph (from `examples/real_evidence/usaspending_subawards_torch.json`)

22 real `SUBCONTRACTOR_OF` edges (Torch as subrecipient): **1 program-anchored deterministic (SAIC), 11
authoritative-repeat, 10 single-occurrence weak (terminating)**. SAIC's deterministic anchor is the set
of globally-unique SAIC PIIDs Torch really subcontracts under (`47QFSA20F0057`, `W31P4Q21F0095`,
`W9126020FD504`); the short local order number `"0002"` is rejected as a false anchor.

## Real propagation chains (both program-anchored, deterministic)

| Chain | Real SAIC program | Direct threat (SAIC) | Propagated (Torch) | Real sub-award |
|---|---|---|---|---|
| A | GSA `47QFSA20F0057` ($1.43B) | `PROGRAM_CONTRACTION` CRITICAL/HIGH | HIGH/MEDIUM, depth 1 | `P010277776` |
| B | Army `W31P4Q21F0095` ($825.8M) | `PROGRAM_CANCELLATION_OR_DELAY` CRITICAL/HIGH | HIGH/MEDIUM, depth 1 | `P010270457` |

Severity and confidence degrade one step per hop and never increase (proven per-threat). Corpus edges
are the same edges `ground_subaward_edges` derives from the archived bytes; the cited sub-award ids are
real rows in that evidence (`tests/test_m17_real_propagation.py`).

## Merged corpus metrics (`corpus_m17` = 46 cases, all pass)

- Direct threats **32**; propagated **5** across **4 chains** (2 real SAIC→Torch); beneficiary
  opportunities **2**.
- Propagation: **max depth 2, avg 1.2**, no explosion (`5 ≤ 32`), 0 cycles, 0 duplicate propagations,
  confidence-never-increases **true**.
- Calibration / quality: resolved outcomes **5 → 12**; confirmed-threat precision **0.9167** (denominator
  **12**, one honest FALSE_ALARM); materialized 3, mitigated/avoided 4, delayed 2; **median lead time
  336 days**; `false_alert_from_absence` **0**.
- Per-mechanism precision reported only with its denominator (null where unresolved); source-family
  contribution credits real USAspending evidence with the most resolved-true warnings.

## Continuous selectivity

`SourceScheduler.record_selectivity_run` / `selectivity_report` persist and roll up the exposure→threat
funnel per source run in the durable M12/M13 source-state doc (append-only, bounded, survives reload).
Benign monitored companies against the real OFAC event batch emit **0 threats** (emission rate 0.0);
repeat runs spend 0 calls (served from cache — calls_avoided counted).

## Invariants verified

- `scoring_v1`, `fit.py`, `replay.py` byte-for-byte unchanged; frozen `corpus_m4`…`corpus_m16`
  byte-identical (sha256 gate in `tests/test_m17_corpus.py`).
- Temporal truth: future-dated outcome excluded (`m17-future-outcome-exclusion` stays UNRESOLVED);
  every exposure/catalyst/edge filtered `available_at <= as_of`.
- No secret leakage; **0 live API calls** (0 calls made, N/A avoided beyond the cache-hit demonstration).
- Operations Panel functional; existing views untouched.

## Git

Blocks A–F each committed and pushed to `origin/main` (`1ed84af`, `9e74456`, `d849edd`, `0f3acce`,
`3db60d7`, + this docs/close commit). Working tree clean; `HEAD == origin/main` at close.
