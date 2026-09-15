# PRELAUNCH-CONVERGENCE-001 — mandatory pre-release work order

Status: **MANDATORY PRE-RELEASE WORK ORDER — OPEN.** Owner-authorized. Codified 2026-09-15.
This spec is canonical for the pre-launch convergence gate. The authority files
(`02-EXECUTION.md`, `03-CURRENT-STATE.md`, `04-DECISIONS.md`) point here and are not duplicated.

## 1. Release-gate status

Pyrnova may **not** be declared PRE-LAUNCH COMPLETE, CUSTOMER #1 PRODUCTION READY, or activated for
production Customer #1 while any mandatory CLOSE item (§5) is materially incomplete. NARROW items must
meet their defined launch floor. REMAIN items are intentionally deferred and do not block release.

This work order does **not** reopen Phase One strategy, the commercial offer, the Customer #1 order,
website doctrine, payment doctrine, source-rights doctrine, the Trust Pack, Company Ready, or accepted
temporal/provenance semantics.

## 2. The intelligence decision chain

The product chain to be completed and made coherent end to end:

```text
SIGNAL
-> OPPORTUNITY
-> BUYER
-> INCUMBENT
-> ACCESS
-> CUSTOMER FIT
-> PURSUIT DECISION
-> MATERIAL CHANGE
-> CUSTOMER ACTION
-> OUTCOME
-> LEARNING
```

This refines, and does not replace, the accepted intelligence lineage in `03-CURRENT-STATE.md`
(SOURCE → EVIDENCE ARTIFACT → ASSERTION → ASSESSMENT → CUSTOMER CONSEQUENCE → MATERIAL CHANGE →
INVESTIGATION/REVIEW → ACTION → OUTCOME).

## 3. Governing acceptance measure — customer usefulness

The governing pre-launch acceptance question is:

> **"Does Pyrnova reliably show a capture executive something consequential, credible and sufficiently
> early that it changes what they do?"**

Selectivity evidence alone is insufficient; measured customer usefulness (recall, lead time, important
misses, disposition/outcome capture) governs acceptance.

## 4. CLOSE / NARROW / REMAIN doctrine

- **CLOSE** — mandatory; must reach the defined launch floor before release.
- **NARROW** — required, but only to a bounded launch floor, not full build-out.
- **REMAIN** — deliberately deferred; explicitly out of scope for pre-launch and does not block release.

## 5. Mandatory CLOSE items

- authoritative release lineage
- soak-to-release acceptance provenance for the final RC
- known recall / Important-Miss baseline
- Customer Usefulness / disposition capture
- opportunity lifecycle continuity
- vehicle/access analysis
- Pursuit Verdict
- customer-visible Material Change consequence
- functional core customer product experience
- customer intelligence delivery
- customer brief download
- safe Phase 1 persistence concurrency/durability
- deterministic release/install/rollback
- production trust verification
- commercial-path rehearsal

## 6. NARROW items (bounded launch floor)

- buyer/agency intelligence
- incumbent/competitor intelligence
- customer past-performance intelligence
- budget/program/procurement lineage
- people/relationship intelligence
- search/export breadth

## 7. REMAIN items (deliberately deferred — do not block release)

teaming marketplace; full partner discovery; pricing/labor database; CRM replacement; proposal
generation; broad capture workflow; Slack/M365 integration suite; SLED; FOIA service; giant contact
database; FedRAMP High / IL5 / CUI; unnecessary SSO/SCIM; multi-region/platform scale; Postgres
migration absent measured need; broad non-GovCon expansion.

## 8. Pre-launch work bundles

Delivery proceeds in owner-authorized bundles. Current authorization covers **Gate 0 + Bundle 1 only**;
proceeding past Bundle 1 requires explicit owner authorization and remaining session budget.

- **Gate 0 — repository/authority closure.** Verify integration lineage, adjudicate the known failing
  baseline (see `docs/operations/GATE0_TEST_ADJUDICATION.md`), codify this spec, establish one
  authoritative development lineage.
- **Bundle 1 — customer value proof + decision memory.** Real-cohort dry run; recall / Important-Miss
  benchmark (frozen before tuning); Decision Lead Time; Customer Usefulness Ledger / Decision Memory;
  ugly opportunity-lifecycle validation.
- Later bundles: authorized separately.

## 9. Competitive launch expectations

Pyrnova must, at launch, show a capture executive something consequential, credible, and early enough to
change action — earlier and more decision-usefully than the incumbent workflow (manual SAM/USAspending
watching and generic alerting). The bar is decision usefulness and lead time, not feature count. See
`docs/strategy/COMPETITIVE_DOCTRINE.md`.

## 10. Explicit release prohibition

No production Customer #1 activation, no "pre-launch complete" or "production ready" declaration, and no
release promotion while any CLOSE item is materially incomplete. This prohibition is independent of, and
in addition to, all existing commercial and readiness gates.

## 11. Revised final Live Ops acceptance rule

Final Live Ops acceptance is **deferred** until substantial pre-launch runtime work is complete. When it
runs, it must use:

- an **immutable pinned release/worktree, isolated from active development** — the mutable canonical
  development checkout must never again be the acceptance runtime root;
- **72 consecutive unattended hours**, spanning at least **3 business days**, with no unexplained
  interruption;
- deterministic exercises covering: restart/recovery; durable checkpoints; archive-first recovery;
  source degradation/recovery; duplicate suppression/idempotency; customer isolation/fan-out;
  long-interval scheduling semantics; failure visibility.

Historical failed-soak evidence
(`var/phase1_soak/evidence_source_counter_fix_2026-09-12`) is immutable and must never be restarted,
repaired, reseeded, migrated, rewritten, deleted, signalled, or used as mutable test state. No
replacement soak is authorized in the current session.
