# M20 replay evidence — generalized adverse events and relationships

_Verified 2026-09-09 in `~/Documents/Pyrnova` on `main`._

Reproduce focused: `PYTHONPATH=. .venv/bin/pytest -q tests/test_m20_real_event_relationship.py
tests/test_m20_corpus_ops.py tests/test_m19_corpus.py tests/test_m18_selectivity_ops.py
tests/test_m16_propagation.py tests/test_m17_real_propagation.py` (**30 passed**).

Final suite: `PYTHONPATH=. .venv/bin/pytest -q` (**464 passed, 1 skipped**; 465 collected).

## Flagship chain

```text
SEC 10-K accession 0001571123-26-000029, filed 2026-03-16
  -> $35M restructuring, impairment and exit costs                    OBSERVED
  -> exact SAIC CIK 0001571123 exposure                               DETERMINISTIC
  -> CORPORATE_RESTRUCTURING                                          HIGH / HIGH
  -> exact SAIC recipient-id + PIID W31P4Q21F0095 prime edge          COMPANY_TO_PROGRAM
  -> Army program indirect delivery/continuity risk                   MODERATE / MEDIUM
```

The direct event is already materialized cost. The propagated record is explicitly indirect and does
not assert that program performance failed.

## Merged corpus metrics

| Metric | Value |
|---|---:|
| Cases passing | 74 / 74 |
| Direct / propagated threats | 51 / 17 |
| Adverse-event families | 3 |
| Real relationship types | COMPANY_TO_PROGRAM, SUBCONTRACTOR_OF |
| Relationship chain counts | COMPANY_TO_PROGRAM 1; SUBCONTRACTOR_OF 14; probe DEPENDS_ON 2 |
| Unique entity pairs | 15 |
| OBSERVED / MODELED / PROBE direct | 12 / 36 / 3 |
| Deterministic / inferred exposures | 87 / 13 |
| Negative cases | 18 |
| HIGH/CRITICAL total / resolved / unresolved | 38 / 14 / 24 |
| HIGH/CRITICAL materialized / mitigated / avoided / false | 6 / 1 / 2 / 1 |
| Resolved direct / precision | 17 / 0.9412 (N=17) |
| Resolved propagated / precision | 4 / 1.0 (N=4, directional) |
| Median direct lead | 337 days (N=17) |
| Max depth / confidence non-increasing | 2 / true |
| Threat / propagation explosion | none / none |
| Temporal leakage / absence-derived false alerts | 0 / 0 |

Family selectivity (direct threats / classified events): contract modification 5/7 (0.714), Federal
Register regulatory adverse 12/16 (0.750), SEC corporate adverse 5/7 (0.714). M20 test cases repeat the
same real event to exercise boundaries, so these are corpus diagnostics, not population rates.

## Acquisition accounting

One budgeted SEC full-submission retrieval was attempted and returned HTTP 403; it was not retried.
The committed compact filing extract is attributable to the official filing URL and cross-checked to
the already-retained raw SEC submissions snapshot. All USAspending relationship evidence was already
archived. Source API calls: SEC 1 attempted / 0 successful; all others 0. Offline replays avoided at
least 8 repeat source calls.
