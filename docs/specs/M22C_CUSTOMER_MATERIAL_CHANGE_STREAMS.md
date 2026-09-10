# M22-C — Per-tenant persisted Material Change streams + production read path

_Status: implemented 2026-09-10 (M22-C) · additive · governed by
`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`, D-041, D-046, D-055, D-056, D-057_

M22-A proved Pyrnova can *present* intelligence customer-specifically; M22-B persisted *who the customer
is, what matters to them, and what they did*. Both still computed a customer's Material Changes on the fly
from the SHARED global intelligence streams at read time — customer isolation held at the relevance/overlay
layer, but not at the storage boundary. M22-C closes that seam: it materializes a durable, per-customer
Material Change record so a relevant global change becomes customer-scoped stored state, and ordinary reads
serve that state instead of re-projecting the shared streams.

M22-C proves Pyrnova can maintain a **durable, per-tenant record of what it delivered to each customer,
when it first became relevant, and how that assessment evolved** — the accumulated exposure/outcome history
that is a Phase 1 moat (D-049/D-052) — without duplicating the global intelligence graph as a
customer-owned truth system, without a tenant platform, and without building authentication.

## Components

| Layer | File | Responsibility |
|---|---|---|
| Module | `pyrnova/customer_material_changes.py` | `CustomerMaterialChange` (append-only version); `fan_out`, `rebuild_customer`, `version_history`, `_latest_versions`; content-hash dedupe; became-relevant computation |
| Streams (dev) | `customer_material_changes`, `fanout_runs` (JSONL via `pyrnova.state.StateStore`) | append-only customer-scoped materialized state + per-run observability |
| Schema (prod mirror) | `db/schema.sql` | `customer_material_change`, `fanout_run` |
| Service | `pyrnova/ops.py` (`OperatorConsole`) | optional `cmc_store` + `access_check` seam; first-seen overlay on the read path; `fan_out` / `rebuild_customer_material_changes` / `customer_material_change_versions` |
| API | `pyrnova/ops_server.py` | `POST /api/fanout`; `GET /api/material-changes/{id}/versions?customer=<id>`; `PermissionError → 403` |
| Frontend | `pyrnova/ops_web/material.{html,css,js}` | unchanged M22-A/B view; the read response carries the additive `first_seen` block and `materialized` count |
| CLI | `pyrnova/cli.py` (`pyrnova fanout`) | continuous-operations fan-out over persisted state (`--customers`, `--as-of`) |

## Truth-model decisions (D-057)

1. **Global truth stays global; customer-scoped state stays customer-scoped.** Global intelligence
   (`threats` / `propagated_threats` / `opportunities` / outcomes) is never duplicated as an independent
   customer-owned truth system and is never mutated by a customer. Fan-out writes ONLY the customer-scoped
   streams (`customer_material_changes`, `fanout_runs`); a test asserts the global `threats.jsonl` is
   byte-identical after a run and that the written streams are disjoint from `GLOBAL_INTELLIGENCE_STREAMS`.
2. **A customer record stores references + customer-specific facts, never authoritative prose (§3).** A
   `CustomerMaterialChange` carries `source_refs` (`subject_ref`, `program`, `catalyst_id`,
   `root_change_id`, `evidence_ids`, `source_ref`, `archive_hash`), a compact `assessment_snapshot`
   (`disposition`, `materiality`, `confidence`, `mechanism`, `lifecycle_state`), the customer's
   `relevance_basis`/`relevance_reasons`, the three first-seen times, `outcome_state`/`outcome_ref`, and
   version metadata. The prose projection is reconstructed at read time from the referenced live global
   record — never stored as authoritative truth, evidence bodies never copied.
3. **The read model is the single source of the projected set.** Fan-out uses the SAME
   `build_material_changes` read model M22-A/B use, so the persisted set never diverges from the on-the-fly
   relevant set (a test asserts the fan-out membership equals the console's on-the-fly relevant set).

## Identity (§4)

A customer Material Change is keyed by `(customer_id, material_change_id)`, where `material_change_id` **IS
the source intelligence id** — the stable linkage to global truth and exactly the key M22-B review actions
already use, so the M22-B review-action linkage is unchanged. This key does not churn on refresh,
projection rebuild, lifecycle change, or revisit. The per-version storage identity is
`record_id = cmc_<hash(customer_id, material_change_id, content_version)>` (`_stable_id("cmc", …)`). Two
customers relevant to the same global intelligence share the `material_change_id` linkage but keep
independent customer-scoped rows (independent relevance basis, first-seen times, and versions); a test
asserts the two demo customers' stored `material_change_id` sets are disjoint and every stored row is
stamped with exactly one `customer_id`.

## First-seen semantics (§8)

Three distinct persisted times, never collapsed into a single `created_at`:

- `intelligence_observed_at` — when the underlying intelligence was globally knowable
  (`available_at` / observed-at of the source record).
- `first_relevant_at` — when it became relevant to **this** customer:
  `max(intelligence_observed_at, earliest matching customer-config effective_from)`. Profile-borne channels
  (`DIRECT_SUBJECT`, `CAPABILITY_MATCH`, and profile agency-of-interest) use the profile `effective_from`;
  watch-borne channels (`WATCHED_ENTITY`, `WATCHED_PROGRAM`, `AGENCY_INTEREST` via an agency watch) use the
  matching watch's `valid_from`. When several channels match, the earliest wins. The value is never earlier
  than `intelligence_observed_at`.
- `delivered_at` — when fan-out first materialized the change into the customer's feed.

When the customer *reviewed* it is the SEPARATE M22-B review lifecycle, joined at read time (`review`).
First-seen fields are set on v1 and carried forward immutably across later versions.

## Fan-out and temporal rules (§5/§7)

`fan_out(mc_store, customer_store, cmc_store, customer_ids=None, as_of=None, run_id=None, now=None)` is
deterministic, idempotent, replayable, point-in-time, and per-customer/per-item failure-isolated. For each
customer it builds the M22-B point-in-time relevance context (`build_context(as_of=…)`), projects the same
relevant changes a read would, then upserts one customer-scoped record per relevant change:

- **no existing record** → append v1 (`change_kind=initial`, `delivered_at=now`, `first_relevant_at`
  computed);
- **unchanged content** (identical `content_hash`) → suppressed as a duplicate, nothing written;
- **changed content** → append a new version (`content_version + 1`), carrying first-seen fields forward.

Nothing is written for a customer to whom a change is not relevant. Temporal correctness is inherited from
M22-B `build_context(as_of=…)`: fan-out respects global knowability (`_visible`), profile `effective_from`,
and watch `valid_from`/`valid_to`. Replaying `as_of` a date before the intelligence was knowable
materializes nothing (no future leakage); replaying before a watch was held materializes nothing (no
retrospective watch leakage). Global intelligence that predates the customer profile becomes newly relevant
only at the profile/watch effective_from, and `first_relevant_at` reflects that (never earlier).

## Update / outcome semantics (§11/§12)

The version's `content_hash` is a deterministic sha256 (truncated) over the assessment snapshot, the
customer relevance basis, and the outcome state — so identical inputs re-hash identically (idempotent) and
any material change produces a new version. A content change appends a new version classified
`change_kind=assessment`; when the assessment snapshot and relevance basis are unchanged and only the linked
outcome moved, the appended version is classified `change_kind=outcome`. Prior versions — including the
original assessment snapshot — are retained unchanged, so a future observer sees what Pyrnova originally
said, what the customer did (the separate lifecycle), and what subsequently happened. No duplicate cards;
no in-place rewrite of a prior assessment.

## Rebuild (§10)

`rebuild_customer(...)` re-runs fan-out for a single customer. Because fan-out is content-hash idempotent, a
rebuild over unchanged global truth appends nothing. Customer *actions* (the M22-B review/lifecycle stream,
keyed by the stable `material_change_id`) are a separate stream and are never touched, so rebuilding derived
projections never erases customer history (a test dismisses a change, rebuilds, and asserts the lifecycle
state survives).

## Read path (§9/§13/§16)

`OperatorConsole` gained an OPTIONAL `cmc_store`. When it is set and populated for a customer,
`material_changes()` overlays each change with a `first_seen` block:

- `status: MATERIALIZED` with `intelligence_observed_at`, `first_relevant_at`, `delivered_at`,
  `content_version`, `last_updated_at`, `change_kind`, and `delivered_outcome_state` (the outcome state
  Pyrnova had delivered at the last fan-out — which may lag the current global `outcome_state` still shown
  at top level); or
- `status: PENDING_FANOUT` (relevant now, not yet materialized).

The response also carries a top-level `materialized` count. When `cmc_store` is `None`, the read path
behaves EXACTLY as M22-A/B — no `first_seen` block, `materialized: None` — so the change is fully backward
compatible (a test asserts this). The `first_seen` overlay is kept structurally separate from the M22-B
`review` overlay (system-delivered state vs customer review state are never flattened together).

The running product no longer depends on the demo: `pyrnova/ops_server.py` runs `fan_out()` at startup and
serves the persisted path, and `pyrnova fanout` is the continuous-operations CLI. Fan-out is the ordinary
operations path, not a demo script.

## Tenant boundary + authorization seam (§6/§15)

Isolation is enforced at storage: `_latest_versions` and `version_history` filter by `customer_id`, so a
read for one customer never returns another's rows. `OperatorConsole` also gained an OPTIONAL `access_check`
callable (`access_check(customer_id) -> bool`) — the single authorization chokepoint a later AUTHENTICATED
ACTOR → AUTHORIZED CUSTOMER layer attaches to. `_require_access` raises `PermissionError` for an
unauthorized customer, which the API surfaces as HTTP 403. **Authentication itself is deferred (D-048);
only the seam exists.** When `access_check` is `None` the path is permissive (dev default).

## Observability (§17)

The fan-out report carries `global_items_evaluated`, `customers`, totals (`inserted`, `updated`,
`duplicates_suppressed`, `relevant`, `suppressed_irrelevant`), `failures[]` / `failure_count`, and a
`per_customer[]` breakdown (`evaluated`, `relevant`, `suppressed_irrelevant`, `inserted`, `updated`,
`duplicates_suppressed`). Each run is appended to the `fanout_runs` stream (the observability write is
wrapped so it can never break the fan-out itself) and logged.

## Failure safety (§18)

Failure isolation is per customer and per item: a customer whose context/projection build fails is recorded
in `failures[]` (with `stage`) and skipped; a single bad projected item fails only that item. Neither
corrupts global state nor another customer's state (a test fans out over a non-existent customer alongside a
valid one and asserts the valid customer is fully materialized while the bad one is recorded and empty).

## Invariants (tested — `tests/test_m22c_customer_material_changes.py`, 20 cases)

Using the real M22-A/B archived-evidence demo (Torch, DAP) plus small synthetic global records for
update/outcome/temporal cases:

- fan-out materializes relevant changes and writes nothing for an irrelevant/unknown customer; the
  materialized set equals the on-the-fly read model relevant set;
- `material_change_id` IS the source intelligence id; fan-out is idempotent (a re-run inserts/updates
  nothing, all suppressed as duplicates) and record identity does not churn;
- storage-level cross-customer isolation: the two customers' `material_change_id` sets are disjoint, every
  row carries exactly one customer, and a single-customer fan-out never writes another customer's rows;
- the `access_check` seam rejects a mismatched customer on both the read path and the versions accessor;
- fan-out writes only the customer-scoped streams — the global `threats` stream is byte-identical and the
  written streams are disjoint from `GLOBAL_INTELLIGENCE_STREAMS`;
- first-seen has three distinct times; `first_relevant_at` respects a late watch (never earlier than the
  watch);
- no future leakage and no retrospective watch leakage on point-in-time fan-out;
- an assessment change appends a new version without losing first-seen fields, and the customer review
  lifecycle survives a derived-state update;
- a later outcome attaches as a new `outcome`-kind version while the original assessment version is
  retained unchanged;
- rebuild preserves customer actions and is idempotent;
- the production-shaped read path serves persisted `first_seen` (all `MATERIALIZED`, `materialized == count`);
  and without a `cmc_store` the read path is backward compatible (`materialized: None`, no `first_seen`);
- a bad customer is isolated and recorded in `failures[]` while a valid customer is unaffected;
- the report carries the observability counters and each run is persisted to `fanout_runs`;
- the `POST /api/fanout` and `GET /api/material-changes/{id}/versions` endpoints round-trip; an unauthorized
  customer is rejected 403.

Additive only: `scoring_v1`/`fit.py`/`replay.py`/severity bands and frozen corpora byte-identical; M22-A/B
read and API behavior compatible. Full suite **532 passed** (was 512; +20 M22-C).

## Non-goals (deferred; D-048)

No authentication/SSO/RBAC (only the `access_check` seam exists), no tenant-graph duplication of the
intelligence model, no CRM/billing, no document ingestion/RAG, no agents, no broad frontend redesign, and
no new intelligence sources. Global intelligence remains the single authoritative truth; customer-scoped
state is derived, referential, and never promoted back into the global graph.

## Documented follow-ups (roadmapped, not swallowed)

- **Authentication** attaches to the existing `access_check(customer_id)` seam and the `actor`/`customer_id`
  boundary; no auth is built now (D-048).
- **Customer-contributed private context** (documents/notes as first-class private intelligence) — the
  global/private boundary is ready; ingestion remains deferred (carried from M22-B).
- **First-class evidence-independence lineage** (carried from M22-A/B).
- **Streaming/incremental fan-out** beyond a full deterministic pass — deferred until real customer volume
  justifies it (premature streaming infrastructure is an explicit non-goal, D-048).
