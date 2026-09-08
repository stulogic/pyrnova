# Evaluation of the Adjudication Feedback

> **Research and decision provenance, not current implementation authority.** Durable adopted decisions
> are recorded in `01-PROJECT-AUTHORITY.md` and `04-DECISIONS.md`.

**Status:** Historical analysis. Companion to `docs/archive/EXECUTION_AUTHORITY_30D_V1.md`.
**What this is:** a hostile evaluation of the feedback received on the original red team — NOT an
adoption of it. Requested standard: *evaluate, don't just accept.*

---

## Headline

The adjudication is directionally sound; its frame — "accept the commercial compression, reject the
strategic amputation" — is fair. But **four of its five reversals re-expand scope**, and two of those
are semantic agreements dressed as disagreements. Each is individually cheap. **In aggregate they
rebuild the exact substrate-first temptation the adjudication claims to reject** — death by a thousand
"it's cheap to keep" decisions. Only one reversal has real teeth, and it is the one to reject.

## Ruling on each reversal

| # | Reversal | Ruling | Why |
|---|----------|--------|-----|
| 1 | Keep 3 pipelines canonical in schema; only BOP builds | **ACCEPT — not actually a reversal** | Forward-compatible schema is ~zero cost and was never contested. "Roadmap not build target" and "canonical in schema not build target" are the same operational outcome. Live danger: "retain the data necessary" must mean cheap raw archival of bytes already fetched, not new normalization/ingestion. **Bounded** in Authority §2. |
| 2 | STRIKE stays canonical | **ACCEPT — minor** | Cheap; "you'll reinvent the word" is right. But it's a lifecycle-state decision (candidate→qualified), implementable as one table + status enum, not a second graph. |
| 3 | Moat = the combination, not outcome labels alone | **CONCEDE — founder right, I overstated** | Point-in-time capture of amended/deleted/restated records + first-observation time + resolved graph + rejected predictions is genuinely hard to reconstruct. **But** the moat *test* holds: only real if it yields demonstrable predictive lift a competitor can't cheaply match. Storage ≠ moat. Both kept in Authority §10. |
| 4 | Precursors (OMB/Congress/budget) enter weeks 3–6 | **REJECT the plan, ACCEPT the concern — replaced** | The one materially wrong move. See below. |
| 5 | Don't publicly trap Pyrnova as "GovCon capture intelligence" | **ACCEPT** | Costs nothing; branding debt is real. Caveat: audience-segment the positioning — buyer sees concrete Capture Radar, investor sees the platform. |

**Revenue reframe** ($1m = bounty/attack target; engineer around $100k): **fully endorsed.** The most
important correction, accepted by the founder. Residual risk: "bounty" language must not creep back into
operating assumptions.

## The reversal that is wrong (#4)

**Strategic point (correct):** recompetes alone ≈ HigherGov/GovWin parity; "we see the capital chain
before procurement" is the real differentiator; precursors can't be deferred forever.

**Plan (wrong):** ingesting OMB/Congress/budget-justification pipelines in weeks 3–6 —
- competes for the scarce founder-hours that should be **closing the first Sprints** (weeks 3–4 are the
  selling weeks); and
- front-loads the **hardest, highest-hallucination** part of the system (precursor→procurement CONNECT),
  risking a wrong precursor claim on the very first brief.

**Both the red team and the adjudication missed the cheaper answer:** the best precursors are already in
the P0 kernel. **SAM.gov already carries Sources Sought, RFI, Special Notice, and Presolicitation notice
types** — literal pre-procurement demand — at zero new-source cost. USAspending option-years and IDV
ceilings are precursors too. The adjudication reached for OMB/Congress when the nearest, highest-signal
precursor is a notice-type filter on a source already being ingested.

**Replacement (now in Authority §8, Week 3):**
1. Exploit precursors already in SAM/USAspending first.
2. Prove OMB/Congress-style precursors manually in the retrospective casebook (analyst, one chain per
   example) — buys "we see before procurement" at ~zero pipeline cost.
3. Automate one external precursor only on paying-customer pull (Week-4 rule).

## Two sharpenings both documents missed

1. **Point-in-time moat is source-dependent.** Strong where records churn — SAM (amendments,
   cancellations, deletions) and USAspending (restatements). Near-worthless on **Federal Register**
   (permanent immutable public archive). Concentrate the discipline; don't claim uniform moat weight.
   (Authority §10.)
2. **Retrospective proof must over-index on precursor cases, not recompetes.** A recompete "we could
   have known" is trivially true (end dates are public) → weak proof. The compelling casebook item is
   the precursor chain (budget line → months later → solicitation) — which also delivers precursor
   differentiation without building the precursor pipeline. (Authority §9.)

## The governance gap the adjudication lacked

Added as the **Anti-accumulation rule** (Authority §2.1): every "keep it / retain it / it's cheap"
decision is free only as raw archival or schema shape; the moment it needs active engineering,
normalization, or founder-hours during the selling window, it is deferred by default and must earn its
place against the $100k target. This rule is what stands between the adjudication and quietly becoming
the substrate-first plan again.

## Net

Adopt reversals 1, 2, 3, 5 (1 & 2 with bounding notes; 3 keeping the lift-test). Reject reversal 4's
plan, keep its concern, replace with precursors-already-in-SAM + manual casebook proof +
automate-on-customer-pull. Add the anti-accumulation rule and the source-specific moat note. The
resulting 30-day plan is preserved in `docs/archive/EXECUTION_AUTHORITY_30D_V1.md`.
