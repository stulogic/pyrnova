# M19 — deterministic OBSERVED exposure + multi-family validation (evidence + acceptance)

_Verified 2026-09-09 in `~/Documents/Pyrnova` on `main`. Spec: `docs/specs/M19_DETERMINISTIC_EXPOSURE.md`._

Reproduce: `PYTHONPATH=. .venv/bin/pytest tests/test_m19_deterministic_exposure.py tests/test_m19_corpus.py`
(honesty gate + corpus) and the full suite `PYTHONPATH=. .venv/bin/pytest` (**457 passed**). Metrics via
`pyrnova.threat.summarize_m19(run_threat_corpus(load_threat_corpus('examples/replay/corpus_m19.json'), DES))`.

## Flagship deterministic chain (real, archived)

```
REAL archived USAspending deobligation  (mod P00256, -$5,152,916.35, 2024-05-06)   [OBSERVED catalyst]
  -> exact prime PIID 47QFSA20F0057
  -> SAIC (UEI MMLKPW9JLX64) is the award recipient        [DETERMINISTIC native-id exposure, CONFIRMED]
  -> PROGRAM_CONTRACTION on SAIC          severity MODERATE, confidence HIGH, family contract_modification
  -> real program-anchored SAIC->Torch sub-award edge on the SAME PIID          [deterministic_native_id]
  -> propagated PROGRAM_CONTRACTION on Torch   confidence HIGH->MEDIUM (degraded, never increased)
```

Evidence archived once at `examples/real_evidence/usaspending_contract_mods_saic_47QFSA20F0057.json`
(3 live USAspending calls; per-response content hashes in-file).

## Acceptance criteria

1. **M18 invariants preserved** — frozen `corpus_m15`…`corpus_m18` byte-identical (test); `scoring_v1`,
   `fit.py`, `replay.py` unchanged. ✔
2. **Deterministic observed exposure semantics explicit + enforced** — `exposure_join_class` (durable on
   every `Threat.meta`); deterministic = CONFIRMED + native-id join (PIID/UEI). ✔
3. **≥1 real observed catalyst with deterministic exposure** — P00256 on 47QFSA20F0057, SAIC UEI join. ✔
4. **≥1 HIGH-confidence direct threat where evidence supports** — flagship PROGRAM_CONTRACTION,
   confidence HIGH (deterministic exposure + observed catalyst). 2 REAL such threats. ✔
5. **≥1 real propagated threat from deterministic observed exposure** — SAIC→Torch, one hop. ✔
6. **All hops retain provenance** — source, evidence ids, `available_at`, join method, catalyst class,
   `exposure_join_class`, relationship path on direct + propagated. ✔
7–8. **Second adverse-event family, materially different** — `contract_modification` (USAspending
   deobligation), distinct source/mechanism/join from BIS/FR export controls. ✔
9. **Multi-family selectivity measured** — `summarize_m19.multi_family_selectivity`:
   `contract_modification` ratio 0.714 vs `regulatory_adverse_event` 0.75 (not noisier). ✔
10. **Deterministic-vs-inferred metrics exist** — exposures 79/13, direct threats 38/8, propagated 13/3,
    resolved deterministic 16 (precision 0.9375), each with denominator. ✔
11–12. **Deterministic identity alone ≠ threat; deterministic no-threat case exists** — `IMMATERIAL`
    (P00281 −$31,616), `NO_EXPOSURE` (wrong award), `EXPOSURE_ENDED` (lapsed incumbency). ✔
13. **Temporal exposure validity enforced** — `valid_to < catalyst` → `EXPOSURE_ENDED`. ✔
14. **Future relationship/evidence excluded** — `m19-det-future-catalyst-excluded` (0 threats at cutoff).✔
15–16. **Direct vs propagated distinct; observed vs modeled distinct** — durable on `Threat.meta`. ✔
17–20. **Confidence non-increasing; depth bounded (≤2); cycles prevented; duplicates suppressed** —
    `summarize_m19.propagation_quality` (no explosion, `confidence_never_increases` True). ✔
21. **Propagated calibration expands** — resolved propagated 1 → 4; precision 1.0 over 4. ✔
22–23. **Unresolved remains valid; absence never a false alert** — `false_alert_from_absence` 0. ✔
24–25. **No threat/propagation explosion** — 46 direct / 16 propagated (`propagated ≤ direct`). ✔
26–28. **`scoring_v1` unchanged; `fit.py` unchanged; previous corpora byte-identical.** ✔
29. **Secret leakage 0** — archives are public-domain USAspending bytes; no `.env`/keys staged. ✔
30–32. **Live calls respectful/minimal; documented** — 3 keyless USAspending calls, archived once; 0
    OFAC/SAM/SEC/SBIR calls. Calls avoided: all replay/development/tests offline. ✔
33–34. **Focused tests pass; one full-suite gate passes** — 12 M19 tests; **457 passed**. ✔
35. **Operations Panel functional** — thin `exposure_join_class`/family surfacing; ops tests pass. ✔
36–37. **Limitations + roadmap/backlog updated** — spec limitations; `05-BACKLOG.md`, roadmap. ✔
38–39. **Every block committed+pushed; final HEAD == origin/main.** ✔

## Metrics snapshot (directional, small sample)

| metric | value |
| --- | --- |
| corpus cases (all pass) | 66 (57 M18 + 9 M19) |
| direct / propagated threats | 46 / 16 (no explosion) |
| adverse-event families | 2 (regulatory_adverse_event, contract_modification) |
| observed-catalyst chains | 7 |
| catalyst authority (direct) | 10 OBSERVED / 36 MODELED |
| deterministic / inferred exposures | 79 / 13 |
| deterministic / inferred direct threats | 38 / 8 |
| real observed-deterministic-HIGH direct threats | 2 (flagship + low-severity) + 3 probe |
| unique company pairs | 14 |
| negative / zero-threat cases | 16 |
| resolved direct outcomes / precision / median lead | 16 / 0.9375 / 342.5 days |
| resolved propagated outcomes / precision | 4 / 1.0 |
| false_alert_from_absence · temporal_leakage_violations | 0 · 0 |
| live API calls | 3 USAspending (keyless, archived once) |
| full suite | 457 passed |
