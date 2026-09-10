# M22-B — Persisted customer intelligence + Material Change lifecycle

_Status: implemented 2026-09-10 (M22-B) · additive · governed by
`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`, D-041, D-046, D-049, D-055, D-056_

M22-A proved Pyrnova can *present* intelligence customer-specifically, but its customer configuration
lived in committed demo fixtures. M22-B removes that demo seam: it persists the minimum durable customer
model, watchlists, and per-customer Material Change review/lifecycle state, and reconstructs a
point-in-time customer context from persisted state so ordinary reads no longer depend on demo-only
configuration.

M22-B proves Pyrnova can remember **who the customer is, what matters to them, what Pyrnova showed them,
and what they did about it** — the customer-specific exposure/outcome/rejection history that is a Phase 1
moat (D-049/D-052) — without building CRM, IAM, billing, a tenant platform, or a second intelligence
verdict system.

## Components

| Layer | File | Responsibility |
|---|---|---|
| Persisted model | `pyrnova/customers.py` | `CustomerProfile`, `WatchlistEntry`, `ReviewAction`; point-in-time `build_context`; append-only review lifecycle; tenancy checks |
| Streams (dev) | `customers`, `customer_watchlist`, `customer_review_actions` (JSONL via `pyrnova.state.StateStore`) | append-only, customer-private persistence |
| Schema (prod mirror) | `db/schema.sql` | `customer` (extended), `customer_watchlist`, `customer_review_action` |
| Service | `pyrnova/ops.py` (`OperatorConsole`) | persisted-context read path, review overlay, customer CRUD + review actions (tenancy-checked) |
| API | `pyrnova/ops_server.py` | `/api/customers[/{id}[/watchlist[/{watch_id}/retire]]]`, `/api/material-changes/{id}/review`, `/api/material-changes/{id}/review-history` |
| Frontend | `pyrnova/ops_web/material.{html,css,js}` | review-state display + lifecycle actions behind the unchanged M22-A view |
| Demo seed | `examples/material_changes_demo/seed_customers.py`; `pyrnova seed-customers` | deterministic, idempotent seed of Torch/DAP into persisted structures |

## Truth-model decisions (D-056)

1. **Global vs customer-private boundary.** Customer configuration, watchlists, relevance inputs, and
   review/lifecycle state are customer-private and are written ONLY to customer-scoped streams. They are
   never written back into Pyrnova's global intelligence streams
   (`threats`/`propagated_threats`/`exposures`/`relationships`); a customer-private fact can never become
   global truth. (`GLOBAL_INTELLIGENCE_STREAMS` names the protected set; a test enforces disjointness.)
2. **System assessment ≠ customer review state.** The customer lifecycle
   (`NEW → REVIEWED / MONITORING / INVESTIGATING / DISMISSED / RESOLVED`) is an append-only overlay keyed
   by `(customer_id, material_change_id)`. It never mutates the authoritative threat record. A customer
   dismissing a threat does not rewrite Pyrnova's historical assessment. This is not a second verdict
   system — it reuses the existing outcome infrastructure for lineage, not a competing engine.
3. **Tenancy isolation.** Every record is `customer_id`-keyed. A review action is rejected unless the
   Material Change is actually relevant/visible to that customer; a watch retirement is rejected unless
   the watch belongs to that customer. Negative tests cover both.
4. **Temporal truth for configuration.** A `CustomerProfile` version carries `effective_from`; a
   `WatchlistEntry` carries `valid_from`/`valid_to`. `build_context(store, id, as_of=...)` reconstructs
   only the configuration knowable at the cutoff, so a watch added today does not imply the customer was
   monitoring the entity months ago (no retrospective watchlist leakage). Retirement is a `valid_to`
   closure, never a destructive delete, so replay before the closure still sees the watch.
5. **Outcome lineage.** A `RESOLVE` action may carry an `outcome_ref` linking an existing Pyrnova
   outcome, preserving `intelligence → customer saw → reviewed → acted / did not act → outcome`.
   UNRESOLVED (no `outcome_ref`) is a first-class valid state; loss/resolution is never inferred.
6. **No arbitrary canonicalization.** A free-text watch ref is preserved honestly as `resolved: false`
   with a note; it matches literally but is never silently promoted to a canonical Pyrnova entity.

## Read path

`OperatorConsole.material_changes` builds the customer's relevance context from **persisted** state
(profile + temporally-valid watchlists), projects the existing `threats`/`propagated_threats`/
`opportunities` exactly as M22-A did, then overlays each change's current customer review state. The demo
`contexts_dir` JSON remains a fallback only for a customer not yet persisted, so a fresh checkout stays
populated. The response adds `review` (per change) and `by_review_state` (counts) alongside the unchanged
M22-A fields; the OBSERVED/ASSESSMENT separation, point-in-time gate, evidence-independence, ordering, and
isolation are all preserved.

## Auditability

Configuration and review state are append-only and timestamped. Review actions record the transition
(`from_state → to_state`), actor (a placeholder id compatible with later auth), optional structured
reason/note, optional `outcome_ref`, and `at`. `review_history(..., as_of=...)` reconstructs the full
ordered history point-in-time; `current_review_state` folds the log to the current state.

## Demo compatibility (§12)

The M22-A demo remains a reproducible TEST / EXAMPLE / DEMONSTRATION path, not runtime architecture. The
same two customers (Torch, DAP) are seeded into the persisted structures by a deterministic, idempotent
seed whose demo identities live in `examples/` — never hard-coded into the `pyrnova` runtime package (a
test greps the package to enforce this). On a fresh checkout with no persisted customers, the server
seeds them via the example seeder (loaded by file path) so the running product exercises the persisted
path, not a demo JSON.

## Invariants (tested — `tests/test_m22b_customers.py`, 18 cases)

Persisted customer survives restart; watchlist drives deterministic relevance (and retirement removes
it); two customers isolated; one customer's private context never affects another; lifecycle persists and
never alters system assessment; customer-private writes never touch global intelligence streams; review
history is point-in-time reconstructable; outcome linkage preserved with UNRESOLVED first-class; no
future-event leakage on the persisted path; no retrospective watchlist leakage; demo seeds persisted
structures idempotently and is not runtime hard-coding; persisted path matches the M22-A demo-JSON
relevance; cross-customer review/retire rejected; free-text refs marked unresolved; API write endpoints
round-trip.

## Non-goals (deferred; D-048)

No CRM, billing, enterprise SSO/RBAC, tenant schema, task/workflow platform, document ingestion/RAG,
dashboard customization, or visual redesign. Customer-*contributed* private intelligence (documents) is
structurally prepared for (the private/global boundary exists) but not implemented.

## Documented follow-ups (roadmapped, not swallowed)

- **Authentication** attaches to the existing `actor`/`customer_id` boundary (IDs and query boundaries
  are in place; no auth built now — D-048).
- **Persisted live Material Change streams:** wire continuous operations' `threats`/`propagated_threats`
  into a per-tenant `mc_store` (today the read model still reads the shared/demo intelligence streams;
  the customer boundary is enforced at relevance/overlay, not yet at storage partition).
- **Customer-contributed private context** (documents/notes as first-class private intelligence) — the
  global/private boundary is ready; ingestion is deferred.
- **First-class evidence-independence lineage** (carried over from M22-A).
