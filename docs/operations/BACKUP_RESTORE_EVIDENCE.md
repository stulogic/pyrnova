# Backup + Isolated Restore — Phase 1 Operational Evidence

**Blocker:** Phase 1 operational — *Backup + isolated restore verification.*
**Final state:** **PASS — BACKUP + ISOLATED RESTORE — VERIFIED / CLOSED** (local isolated destination;
see *Residual dependency* for production off-host storage).
**Branch / worktree:** `backup-restore-001` (isolated git worktree off `source-rights-001` @ `3732d86`,
which carries the authoritative source-rights enforcement and descends from the pinned soak commit
`e7cb2c98`).
**Soak:** untouched. The live Live-Ops soak (PID observed serving `var/phase1_soak/plan.json`) writes to
`var/state`; it was read only via a read-only point-in-time snapshot copy. No restore ever targeted
`var/state`, `var/archive`, or `var/phase1_soak/**`, and the protected evidence directory
`var/phase1_soak/evidence_source_counter_fix_2026-09-12` was never written.

---

## 1. Scope

Prove Pyrnova can (1) create a real backup, (2) verify its integrity, (3) retrieve it independently of
the source runtime, (4) restore it into a clean isolated target, (5) preserve Pyrnova semantics,
(6) *not* resurrect state that current source-rights authority forbids, and (7) document a repeatable
procedure. Implementation is bounded: it extends the existing `StateStore` (append-only JSONL) +
content-addressed `EvidenceArchive` persistence and the existing source-rights gate. No new persistence
architecture, vendor, or platform was introduced. `SOURCE-RIGHTS-001` (`3732d86`) is treated as
committed/closed authority and is **not** reopened.

## 2. Backup contents (durable) vs excluded (regenerable)

Implemented in `pyrnova/backup.py`.

**Captured (canonical, non-regenerable durable state):**

- `StateStore` durable streams under `var/state/*.jsonl`: `customers`, `credentials` (hashes only),
  `customer_watchlist`, `customer_material_changes`, `customer_review_actions`, `reviews`,
  `join_reviews`, `join_review_queue`, `operator_actions`, `opportunities`, `predictions`,
  `fanout_runs` (operational checkpoints / idempotency ledger), `scoreboard`.
- Content-addressed evidence archive `var/archive/**` (immutable objects + `.observations.jsonl`
  provenance sidecars) — the point-in-time evidence and its first-seen timestamps.
- `db/schema.sql` — schema identity / version.

**Excluded because deterministically regenerable from restored canonical state** (recorded in the
manifest `derived_excluded`, recovery behaviour = regenerate, not restore): `replay_results`,
`replay_reports`, `chain_replay_results`, rendered `out/` briefs, and caches. Regeneration is
demonstrated by `regenerate_derived_summary()` (byte-reproducible; rebuilds per-stream/per-customer
counts and a content-addressed archive index from restored bytes).

**Secrets:** the `credentials` stream persists only a salted one-way hash + salt (see `pyrnova/access.py`);
no plaintext secret exists in storage, so none can enter a backup (test asserts the plaintext token is
absent and only `secret_hash` is present). The process `.env` is never part of a backup.

## 3. Procedure (repeatable)

```python
from pyrnova import backup
m   = backup.create_backup(source_root, backup_dir, source_commit="<HEAD>")  # -> MANIFEST.json
res = backup.verify_backup(backup_dir)                # independent integrity check (fail-closed)
# move/copy backup_dir to an independent location, then:
backup.restore_backup(independent_copy, clean_target) # verify -> safe-target -> materialise
report = backup.reconcile_display(clean_target)        # source-rights reconciliation BEFORE display
backup.regenerate_derived_summary(clean_target)        # regenerate excluded derived state
```

The soak’s live `var/state` is backed up via a read-only snapshot copy first (coherent point-in-time
capture without touching the runtime). Restore never targets a protected path — `restore_backup`
refuses any target ending in / containing `var/state`, `var/archive`, or `var/phase1_soak`, and refuses
a non-empty target.

## 4. Backup integrity

`MANIFEST.json` carries: format id (`pyrnova-backup`) + `format_version`, `created_at`, `source_commit`,
`source_root`, explicit `status`, `durable_streams`, `derived_excluded`, a per-file `{path,size,sha256}`
inventory (sorted, deterministic), and a top-level `manifest_sha256` over that inventory. A failed
capture is written with `status="failed"` and re-raised; `verify_backup` fails closed on: wrong
format/version, `status != complete`, `manifest_sha256` mismatch, any missing artifact, and any per-file
size/checksum mismatch.

## 5. Real-data run (live durable state → isolated restore)

Point-in-time snapshot of the live runtime (`source_commit a19a799…`, pinned soak `e7cb2c98`):

- **Backup created:** `status=complete`, **15 files**, `manifest_sha256 = 97e4fb15364cff2196…860effa4`.
- **Verified** on the source backup dir (15/15) **and** on the independent copy (15/15).
- **Restored** the independent copy into a clean isolated target: 15/15 files, byte-identical
  (`customer_material_changes.jsonl` verified equal).
- Largest captured artifact `state/opportunities.jsonl` (290,583 bytes,
  `sha256 9de97e01…6fbfdee`); evidence object
  `archive/sam_opportunities/57/574813de…350a08` (21,192 bytes, self-verifying content address).

Full manifest is reproduced by re-running the procedure; a copy is retained with the run artifacts.

## 6. Acceptance checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| A | Canonical identity | PASS | `record_id`/`material_change_id`/opportunity `id` + `first_seen_at` restore identically; ids are content-addressed (`_stable_id`), no regeneration/collision. |
| B | Customer/tenant separation | PASS | Application-layer isolation (every record keyed by `customer_id`) preserved; no cross-tenant leakage; `torch`/`dap` records stay partitioned. |
| C | Provenance | PASS | `source_refs` (SOURCE FACT / evidence ids / hashes) and `disposition` (PYRNOVA DERIVED) survive byte-identically; assessment snapshots intact. |
| D | Temporal / AS-OF | PASS | `intelligence_observed_at`, `first_relevant_at`, `valid_from` unchanged by restore — no shift of historical state into present-day knowledge. |
| E | Checkpoints / idempotency | PASS | `fanout_runs` cursors + ids restore exactly; restored `record_id`s unique → no duplicate processing / replay-from-zero. |
| F | Safe derived regeneration | PASS | `regenerate_derived_summary()` deterministic and rebuilds derived counts + content-addressed archive index from restored canonical bytes. |
| G | Source-rights reconciliation | PASS | `reconcile_display()` runs every restored customer record through the authoritative `rights.gate_customer_display`; display is authorised **only** where current policy permits — restore alone does not grant display. |
| H | Non-resurrection (negative) | PASS | A backed-up record attributed to a now-restricted source (`reuters`, class BLACK) remains in restored durable state (history retained) but reconciliation returns display **BLOCKED** (`reason_code CLASS_BLACK`) and the gate emits only a minimal reference-only projection — historical evidence preserved, not resurrected. |

**Source-rights reconciliation on real data:** 5 restored `customer_material_changes` → 4 permitted
(all `usaspending`, GREEN, current policy), 1 blocked fail-closed (`UNKNOWN_SOURCE`: a soak-synthetic
record `subject_ref soak-ironmountain-solutions` whose `evidence_ids` bears no attributable source
prefix — correct fail-closed posture). No live source was rights-restricted (live sources are all
approved gov sources); the BLACK-class non-resurrection case is proven with the controlled fixture in
the test suite, exercising the same authoritative gate.

## 7. Fail-closed behaviour (verified)

Restore/verify fail closed on: checksum mismatch, size mismatch, missing artifact, `manifest_sha256`
tamper, incompatible format/version, unsafe/non-isolated target (protected path or non-empty), and a
reconciliation the gate cannot decide (`SourceRightsReconciliationError`). A corrupt backup aborts
restore before any file is materialised (no partial restore).

## 8. Tests run

- `tests/test_backup_restore.py` — **18 passed** (integrity/format, fail-closed corruption/missing/
  format/unsafe-target, isolated round-trip via independent copy, and acceptance checks A–H incl. the
  negative non-resurrection test).
- Regression guard: `-k "rights or access or customer_material or source_rights or state"` — **75 passed**
  (source-rights, access/auth, customer material-change, and state semantics unaffected; the change is
  purely additive). No full-suite run was required — the change adds a module + tests and does not alter
  existing persistence or rights code.

## 9. Residual operational dependency

Off-host / off-machine storage is demonstrated with an **independent local copy** (SOURCE → BACKUP
ARTIFACT → INDEPENDENT COPY → CLEAN RESTORE TARGET). A production backup destination/provider (e.g. the
existing `S3EvidenceArchive` path or an object store) has **not** been selected or provisioned. This is
**production-hardening follow-up, not a Phase 1 blocker**: the backup artifact is provider-agnostic
(a directory + manifest) and the retrieval/restore path already consumes an independent copy rather than
the live source. Wiring a remote destination is an operational deployment step, not a change to the
verified procedure.

## 10. Final state

**PASS — BACKUP + ISOLATED RESTORE — VERIFIED / CLOSED.** Soak untouched; source-rights authority not
weakened; non-resurrection proven; procedure documented and repeatable.
