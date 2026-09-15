# B1.4 — Customer Usefulness Ledger / Decision Memory

PRELAUNCH-CONVERGENCE-001 · Bundle 1 · B1.4. Implementation: `pyrnova/decision_memory.py`.
Tests: `tests/test_decision_memory.py` (14 passed). Deliberately **not** a CRM, pipeline, task system,
or account-management suite; no GUI (the data contract is proven by tests, per the work order).

## Data contract

A customer records a durable, append-only **disposition** on each *delivered* intelligence object, with
explicit vocabularies (every field defaults `UNKNOWN` when genuinely not provided):

| Field | Vocabulary |
|---|---|
| NOVELTY | NEW_TO_CUSTOMER · ALREADY_KNOWN · UNKNOWN |
| RELEVANCE | RELEVANT · NOT_RELEVANT · UNKNOWN |
| PURSUIT | PURSUE · WATCH · PASS · INVESTIGATE · UNKNOWN |
| TIMING | EARLY_ENOUGH · TOO_LATE · UNKNOWN |
| VALUE | ACTIONABLE · INFORMATIVE_ONLY · NO_VALUE · UNKNOWN |
| IMPORTANT MISS | YES · NO · UNKNOWN |
| REASON | bounded set (DUPLICATE_OF_KNOWN, WRONG_AGENCY, WRONG_CAPABILITY, TOO_SMALL, OUT_OF_SCOPE, NOT_ADDRESSABLE, LOW_CONFIDENCE, TIMING, GOOD_LEAD, OTHER, UNKNOWN) + optional length-capped note |
| OUTCOME | PURSUED · DECLINED · BID · NO_BID · AWARD · LOSS · CANCELLED · UNRESOLVED · OTHER · UNKNOWN |

Decision Memory linkage fields — `signal_ref`, `evidence_refs`, `pyrnova_assessment_ref`, `outcome_ref` —
let the chain **SIGNAL → EVIDENCE → CONSEQUENCE → DECISION → ACTION → OUTCOME → LEARNING** be
reconstructed later without building it now.

## Invariants (verified by tests)

- **Customer-private + isolated.** Dispositions live only in the `customer_dispositions` stream; a test
  asserts recording touches **none** of `GLOBAL_INTELLIGENCE_STREAMS`, and reads are tenancy-scoped
  (c2 never sees c1's dispositions).
- **Customer feedback ≠ Pyrnova assessment.** Each row is stamped `origin = "CUSTOMER_FEEDBACK"` and only
  *references* Pyrnova's assessment; recording never mutates any Pyrnova judgment stream.
- **Append-only / auditable / temporal.** A new disposition is a new immutable version; `latest_*` folds
  to the current one, `as_of` reconstructs the effective version at a cutoff, and `disposition_history`
  shows that an earlier customer reaction is preserved, never overwritten.
- **Unknown never becomes a real value.** Unspecified fields stay `UNKNOWN`; invalid vocabulary is
  rejected at construction.

This reuses the M22-B customer-private architecture (`pyrnova.customers`): same StateStore append-only
streams, `_now`/`_parse_dt`/`_stable_id` primitives, and the global-vs-customer-private boundary.

## Verdict

**PASS.** The minimum durable, isolated, append-only disposition/outcome layer exists and is proven by
tests, giving B1.2's GROUND_TRUTH_GAP a mechanism to accrue real customer recall/usefulness evidence from
live use — without CRM/workflow scope creep.
