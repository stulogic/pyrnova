# B1.1 — Real-cohort dry run (MTSI + Torch)

PRELAUNCH-CONVERGENCE-001 · Bundle 1 · deliverable B1.1. This is **validation evidence, not a
commercial claim** (N=2). It is truthful product observation of the *existing* pipeline; no scoring,
threshold, or source coverage was tuned for this exercise.

## Method (reproducible)

`python -m examples.bundle1.dry_run_cohort` runs `pyrnova.pipeline.run` (scoring_v1) offline over the
**shared** bundled `_fixture_rows()` candidate universe (4 awards / 4 notices / 2 precursors), once per
capability lens (`examples/profiles/torch_technologies.json`,
`examples/profiles/modern_technology_solutions.json`), `as_of 2026-09-08`, threshold 0.3, into isolated
temp archive/state. Deterministic output is committed at `docs/evidence/bundle1/dry_run_metrics.json`
(run_id `a7f661c08f2bc7d4dd63`). The historical failed soak evidence was not touched or used.

## Observed outputs

| Lens | candidates | STRIKE (recompete/presol) | WATCH | REJECT | duplicates | multi-source STRIKEs | avg lead | top relevance |
|---|---|---|---|---|---|---|---|---|
| Torch Technologies | 5 | 2 (0 / 2) | 2 | 1 | 0 | 2 | 29.5 d | 0.60 |
| Modern Technology Solutions | 5 | 2 (0 / 2) | 2 | 1 | 0 | 2 | 29.5 d | 0.73 |

STRIKEs (both lenses): *Sources Sought: Army C4ISR Network Modernization Support* and *Special Notice:
Industry Day: Air Force Cloud Modernization* — both **pre-solicitation** (market-research stage, ahead of
any solicitation), both **corroborated by ≥2 sources**, both carrying customer-fit reasoning, explicit
falsification ("a Sources Sought/RFI is market research, not a commitment to procure"), and a recommended
next action. WATCH (both lenses): two incumbent recompete watches (Acme Federal Systems ends 2027-01-15;
Globex Defense LLC ends 2026-12-01).

## Findings against the B1.1 checklist

- **Total material outputs:** 5 candidates/lens.
- **STRIKE / WATCH / REJECT:** 2 / 2 / 1 per lens — selective, not degenerate.
- **Material Change types:** pre-solicitation capture STRIKEs + incumbent recompete WATCHes.
- **Duplicates / near-duplicates:** 0 (`duplicate_candidates`=0).
- **Clearly irrelevant output:** none surfaced as STRIKE; 1 candidate correctly rejected below threshold.
- **Obvious useful output:** both STRIKEs are early, corroborated, capability-matched pre-solicitation
  signals with a next action — decision-useful for a capture executive.
- **Zero-result risk:** not triggered (2 STRIKEs each). **Flood/noise risk:** not triggered (5 candidates).
- **Lens differentiation is real:** identical universe, but MTSI scores the C4ISR case 0.73 vs Torch 0.60
  (MTSI's profile carries C4ISR/systems-engineering capabilities), confirming relevance tracks capability
  fit rather than being uniform.
- **Obvious missed known opportunities:** none *within this fixture universe* — but the universe is a small
  demo set (5 candidates). This dry run therefore **cannot** measure real-volume recall or flood; that is
  precisely what B1.2 (recall/Important-Miss benchmark) and the deferred real-volume soak exist to answer.

## Verdict

**PASS as validation evidence.** On the shared fixture universe both lenses are selective (no zero-result,
no flood), produce corroborated early pre-solicitation STRIKEs with decision-useful framing, suppress
duplicates, and differentiate by capability fit. The binding open question — recall and flood at real
data volume — is explicitly deferred to B1.2 and the isolated soak, and is not claimed here.
