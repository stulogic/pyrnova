# B1.5 — Ugly opportunity-lifecycle validation

PRELAUNCH-CONVERGENCE-001 · Bundle 1 · B1.5. **Current behavior was tested before any architecture
change.** Reproducible probe: `examples/bundle1/lifecycle_probe.py`. Regression/characterization tests:
`tests/test_opportunity_lifecycle.py` (4 passed).

Governing question: *does Pyrnova represent one commercial opportunity evolving through time, or does it
fragment the same commercial reality into disconnected notices/events?*

## What was tested

One program (`disa:cloud-modernization`) evolving through the full lifecycle — budget/authorization →
funding → forecast → sources sought → presolicitation → solicitation → amendment 1 → amendment 2 →
cancellation → reissue → award → later recompete — resolved through the existing
`pyrnova.chains.resolve_chain`, at all-time and at two point-in-time cutoffs.

## Findings

**Launch-adequate (works today):**

1. **One commercial identity across stages.** All 12 lifecycle signals resolve to a single
   `program_keys = ["disa:cloud-modernization"]`. The opportunity is represented as one reality evolving
   across AUTHORIZATION → FUNDING → MARKET_ENGAGEMENT → PROCUREMENT → AWARD — **not fragmented** into
   disconnected programs. Cross-stage relationships link the capital → procurement → award chain.
2. **Point-in-time history is honest.** AS-OF cutoffs expose only what was knowable then (5 signals at
   2025-07-20, 9 at 2025-09-01, 12 all-time); later notices never leak backward.
3. **Source-event identity preserved; true duplicates collapse.** Distinct notices stay distinct signals;
   the same notice observed twice collapses (`duplicates_collapsed`), so there are no phantom duplicates.

**Known gaps (the "ugly" part):**

1. **Intra-stage lifecycle is flat.** All seven PROCUREMENT notices (presol, solicitation, amendment 1,
   amendment 2, cancellation, reissue, recompete) sit as **peers in one stage with no
   predecessor/successor linkage between them.** There is no `AMENDS` / `SUPERSEDES` / `REISSUES` /
   `CANCELS` predicate: the chain knows they are the same program but not that AMD1 amends the
   solicitation, that the cancellation voids it, or that the reissue restarts it.
2. **Cancellation is inert.** A notice flagged `contradicts` in the PROCUREMENT stage produced
   `contradictions = 0` and `chain_confidence.contradicted = false`. Contradiction is evaluated only on
   *formed* relationships, and intra-stage peers form none — so a cancelled solicitation currently does
   not suppress or flag the live opportunity. **This is the highest-priority sub-item.**
3. **Recompete conflated with the original.** The 2030 recompete reuses the program_key and folds into
   the same PROCUREMENT bucket as the closed 2025 procurement, rather than being a distinct procurement
   instance of the same program.

## Verdict — OUTCOME C (bounded design requirement, deferred; no late-session redesign)

Cross-stage opportunity continuity is **launch-adequate and is not rebuilt.** The intra-stage
procurement lifecycle is a real, bounded limitation whose correct fix is a model addition, not a small
patch; improvising it late in this session is explicitly out of scope. It is documented here with
evidence and pinned by tests, and carried to Bundle 2.

### Bounded design requirement for Bundle 2

- Introduce **notice-level lineage within a stage**: `AMENDS`, `SUPERSEDES`, `CANCELS`, `REISSUES`
  predicates linking notices that share program identity and native solicitation identity, so a
  procurement's own history (issue → amend → cancel → reissue) is one sequenced lineage.
- Make **cancellation consequential**: a `CANCELS`/contradiction must lower chain confidence and mark
  the current procurement instance not-live, without deleting the source events.
- Separate a **recompete as a distinct procurement instance** of the same program (new competition,
  new lead time) rather than merging it into the original procurement bucket.
- Preserve original source-event identity and evidence; do not collapse distinct procurements merely
  because they look similar.
- Add focused regression tests; the characterization test in `test_opportunity_lifecycle.py` is expected
  to be updated (intentionally) when this lands.

A clean commit/resume point is preserved for Bundle 2. The historical failed soak evidence was untouched.
