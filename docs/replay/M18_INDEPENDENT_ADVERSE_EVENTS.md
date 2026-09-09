# M18 replay evidence — independent adverse-event propagation

_Generated 2026-09-09 · offline replay of `corpus_m18.json` (57 cases) + focused M18 tests. No
`scoring_v1` involvement (threat engine owns its own point-in-time replay)._

## Headline

Pyrnova took a **real, archived, OBSERVED adverse event** (Federal Register BIS Final Rule 2026-17231,
"Revisions to the Entity List", RIN 0694-AK49, published 2026-08-24), connected it to a **real exposed
prime**, propagated it through a **second/third real commercial relationship independent of SAIC↔Torch**
(Parsons→Torch on MDA `HQ085821C0015`; Intuitive→Torch on Army `W31P4Q23FC001`), and preserved an
auditable chain from source event to propagated threat — without an alarm explosion.

## Merged corpus metrics (57 cases, all pass)

| Metric | Value |
|---|---|
| Direct threats / propagated threats | 41 / 12 |
| Real propagation cases | 4 (2 M18 observed-independent + 2 M17 SAIC) |
| Observed-catalyst propagation chains | 3 |
| Independent company pairs (chains) | 11 distinct pairs; 8 distinct roots |
| Catalyst authority (direct) | 5 OBSERVED / 36 MODELED (durable, distinct) |
| Max propagation depth / explosion | 2 / none (`propagated 12 ≤ direct 41`) |
| Confidence never increases | true (proven per-threat) |
| Cycles prevented / duplicates suppressed / weak terminations | 1 / 1 / 1 |
| Negative / zero-threat cases | 13 |
| Resolved outcomes | 15 (M17 closed at 12) |
| Confirmed-threat precision | 0.9333 over 15 |
| Median lead time | 337 days |
| Direct vs propagated resolved | 15 / 1 |
| `false_alert_from_absence` | 0 |
| Live API calls | 1 (Federal Register, keyless, archived) |

## Acceptance gate (all 40 met)

1. M17 invariants preserved — frozen corpora byte-identical, `scoring_v1`/`fit.py`/`replay.py` unchanged. ✓
2. ≥1 independent real company relationship beyond SAIC↔Torch — **Parsons→Torch** and **Intuitive→Torch**. ✓
3. Relationship diversity beyond one structural pair — 2 independent pairs, distinct agencies (MDA, Army). ✓
4. ≥1 archived authoritative adverse-event family integrated — Federal Register BIS export-control rules. ✓
5. ≥1 catalyst in acceptance is OBSERVED real evidence — FR 2026-17231 (reproduced from archive by test). ✓
6. ≥1 full observed-event→exposure→relationship→propagated-threat chain — Parsons chain. ✓
7. That chain uses a pair independent of SAIC↔Torch — Parsons (and Intuitive), neither is SAIC. ✓
8. Preferably 2 independent real chains — **2 delivered**. ✓
9. Weak/no relationship prevents propagation — real NTSI weak edge terminates end-to-end. ✓
10. Direct vs propagated distinct — separate records, degraded severity/confidence, separate calibration. ✓
11. Observed vs modeled catalyst distinct — durable `catalyst_class` on every threat. ✓
12. Provenance survives every hop — evidence ids + propagation path retained. ✓
13. Point-in-time truth — the 2026-08-24 rule is excluded at a 2026-01-01 cutoff. ✓
14. Confidence never increases — proven per-threat (`confidence_never_increases` true). ✓
15. Max depth bounded — 2. ✓
16. Cycles prevented — 1 in corpus, invariant guarded. ✓
17. Duplicate propagation suppressed — 1 in corpus, invariant guarded. ✓
18. Relationship diversity reported — `independence_metrics` (11 pairs, source families, observed chains). ✓
19. Negative/rejection case demonstrated — 13 negative cases incl. `NO_EXPOSURE` on the same real rule. ✓
20. Resolved outcome sample increased — 12 → 15 (honest, directional; new events not yet resolvable). ✓
21. Propagated outcome calibration begun — `propagated_outcome_calibration` (1 resolved propagated). ✓
22. Unresolved remains valid; 23. absence never a false alarm — `false_alert_from_absence` 0. ✓
24. Continuous selectivity receives new source output — `run_selectivity` + `source_run_funnel`. ✓
25. No threat explosion; 26. no propagation explosion — `propagated 12 ≤ direct 41`, depth 2. ✓
27. `scoring_v1` unchanged; 28. `fit.py` unchanged; 29. prior corpora byte-identical. ✓
30. Secret leakage 0 — evidence is public-domain FR JSON; no `.env`/keys staged. ✓
31. External calls minimal/respectful — 1 Federal Register call, archive-once. ✓
32/33. Calls made (1) / avoided (7 in the selectivity run) documented. ✓
34. Focused M18 tests pass (17). ✓
35. Full suite passes once — **445 passed**. ✓
36. Operations Panel functional — `adverse_catalyst_view` + catalyst authority in the network view. ✓
37. Limitations documented — see spec. ✓
38. Roadmap/backlog updated. ✓
39. Each coherent block committed + pushed. ✓
40. Final HEAD == origin/main. ✓

## Call / yield (Workstream O)

| Source | Requests | Calls avoided | Records | Useful observed events | Direct threats | Propagated |
|---|---|---|---|---|---|---|
| Federal Register (BIS) | 1 (schema+archive) | 7 (selectivity replay) | 8 rules | 8 (all OBSERVED) | 5 (from the archived batch, evidenced-exposure only) | 3 observed |

Archive: `examples/real_evidence/federal_register_bis_export_controls.json` (content hash recorded
in-file; integrity asserted by `tests/test_m18_corpus.py::test_archived_fr_evidence_integrity`).
