# B4.16 — US Phase 1 RC evidence package + authority reconciliation

Controlling owner gate: **PYRNOVA-US-RC-GATE-001**. This is the exact-candidate reconciliation. No
"probably / mostly / almost / should be fine" language is used: each gate is PASS, FAIL, or EVIDENCE
MISSING against exact-candidate evidence.

## Final acceptance package (exact candidate)

1. **Branch:** `prelaunch-convergence-001`
2. **Code-complete HEAD SHA:** `50e1b7a` (this package doc is committed on top and adds documentation
   only — no code changes after `50e1b7a`).
3. **Working tree:** CLEAN (`git status --porcelain` empty at `50e1b7a`).
4. **B4 commit inventory (`main..HEAD`):** B4.1 `d35cf33` · B4.2 `1c15bae` · B4.3 `371e749` ·
   B4.4 `7f425d8` · B4.5 `ff50261` · B4.6 `2d627f8` · B4.7 `5316e93` · B4.8 `9f4f638` · B4.9 `fdd9c78` ·
   B4.10–11 `3bf16fd` · B4.12+B4.14 `ffa7f0c` · B4.13 `3ce6c72` · B4.15 `a283cf3` ·
   B4.16 SMTP `ddda203` · B4.16 fixture `50e1b7a`. `origin/main` unchanged at `7bd36c2`; **main not
   merged/promoted.**
5. **Product / customer proof:** `docs/evidence/bundle4/B4_12_COMMERCIAL_REHEARSAL.md` +
   `rehearsal_capture.json` (regenerable, fails loudly on any fabrication).
6. **MTSI proof:** `B4_14_MTSI_TORCH_RC_PROOF.md`; `test_b3_mtsi_torch_proof.py`, `test_b4_mtsi_fanout.py`
   — 2 real recompetes from `usaspending_mtsi.json`, incumbent MTSI, PURSUE/MEDIUM, tenant-isolated.
7. **Torch proof:** same docs/tests — 6 real recompetes from `usaspending_torch.json`, accepted populated
   capability intact.
8. **Real customer-delivery evidence:** wiring `test_b4_customer_delivery_wiring.py` +
   **production-equivalent real-SMTP transmit** `test_b4_production_equivalent_smtp.py::test_customer_delivery_transmits_over_real_smtp`
   (real EHLO/MAIL/RCPT/DATA on a loopback sink; brief body on the wire). Real EXTERNAL send to a real
   inbox = credential/infra dependency (§ external dependencies).
9. **Real operator-alert evidence:** `test_operator_alerts.py`, `test_b4_alerts_wiring.py` +
   `test_b4_production_equivalent_smtp.py::test_operator_alert_transmits_over_real_smtp` (CRITICAL alert
   delivered over real SMTP; dead-man watcher + severity doctrine). Same external-send caveat.
10. **Backup/restore evidence:** `docs/operations/BACKUP_RESTORE_RC.md`, `test_backup_restore.py`,
    `test_b4_backup_release.py` (SHA linkage, backup-during-writes consistency, restore post-hardening).
11. **Immutable release evidence:** `docs/operations/RELEASE_RUNBOOK.md`, `pyrnova/release.py`,
    `test_b4_release.py` (immutable staged releases, health-gated atomic swap, rollback, `/healthz`).
12. **Soak-harness / provenance evidence:** `docs/operations/SOAK_PROVENANCE_RC.md`,
    `pyrnova/soak_provenance.py`, `test_b4_soak_provenance.py`, `test_live_ops_acceptance.py`
    (pinned-commit immutability, fail-closed drift, reproducible `chain_sha256`).
13. **Dependency/config reproducibility:** `requirements.lock.txt`, `requirements-dev.lock.txt`,
    `docs/operations/RELEASE_INSTALL.md`, `test_b4_dependency_contract.py` (fresh isolated venv verified).
14. **WEBSITE GO verification:** `B4_13_WEBSITE_STATE.md` — `website-go/` byte-identical to accepted
    baseline `8e5ae46`; 14/14 site tests; intake disabled; no form/collection controls.
15. **Full regression result:** **866 passed / 0 failed / 2 skipped**, exit 0, at `50e1b7a`
    (`B4_15_FULL_REGRESSION.md`).
16. **Skip adjudication:** both skips = real OFAC archive git-ignored → live-archive replay skips, offline
    path covered. Legitimately deferred; not defects.
17. **Authority reconciliation:** this document (matrix below).
18. **RC gate matrix A–O:** below.
19. **Remaining blockers:** none that are RC-candidate blockers. External/non-required dependencies are
    listed separately.
20. **Final replacement soak:** **NOT STARTED.** Historical failed soak preserved, **zero time credit**.

## RC gate matrix A–O (exact candidate `50e1b7a`)

| Gate | Domain | Verdict | Basis |
|---|---|---|---|
| A | Authority / Scope | **PASS** | Locked commercial authority applied to customer-facing path (B4.12); source-rights ruling intact/not weakened; no prohibited action taken. See reconciliation note on the internal strategy doc. |
| B | Product / Customer Experience | **PASS** | B4.12 rehearsal + B4.14 proof: complete coherent product, per-opportunity decision outputs, truthful empty/AS-OF. |
| C | Intelligence Chain | **PASS** | B2 chain (10 modules) + B4.1 recompute; decision-chain tests green. |
| D | Data / State Durability | **PASS** | B4.4 fcntl locks + O_APPEND/fsync + torn-tail fail-closed recovery; `test_b4_durability.py`. |
| E | SOURCE-RIGHTS | **PASS** | `test_source_rights/source_expansion/sec_edgar`; Bundle-2 ruling; B4.16 removed D&B DUNS from derived provenance (raw evidence unchanged). |
| F | Customer Isolation / Auth | **PASS** | `test_m22f_server_auth/access`; cross-tenant rejection; opportunity-id disjointness. |
| G | Delivery | **PASS** | B4.3 wiring + B4.16 production-equivalent real-SMTP transmit; unauthorized recipient hard-refused; FAILED never fabricated. Real external send = external dependency. |
| H | Operator Alerting | **PASS** | B4.9 wiring + B4.16 production-equivalent real-SMTP alert; dead-man watcher; INFO/OPERATOR_ATTENTION/CRITICAL doctrine; decoupled from customer delivery. |
| I | Backup / Restore | **PASS** | B4.8 RC; SHA-linked, backup-during-writes consistent, restore-readable post-hardening. Off-host destination = external infra dependency. |
| J | Release / Rollback | **PASS** | B4.6 immutable release/deploy/rollback + `/healthz`; state never touched by rollback. |
| K | Configuration / Dependencies | **PASS** | B4.5 pinned lockfiles, RELEASE_INSTALL, fresh-venv verified. 3.11+ fresh install = documented env dependency. |
| L | Website / Commercial Path | **PASS** | B4.13 State-1 preserved (byte-identical to `8e5ae46`, 14/14 tests, intake disabled) + B4.12 commercial path coherent with locked offer. |
| M | Testing / Regression | **PASS** | B4.15 866/0/2, skips adjudicated, all required domains mapped to passing tests. |
| N | Acceptance Evidence | **PASS** | This package + `docs/evidence/bundle4/` + operations RC docs; regenerable capture. |
| O | Soak-Entry Readiness | **PASS** | Immutable harness + provenance (B4.10–11), clean tracked tree, pinned-commit preflight. Ready to START the final soak — **not started**. Historical failed soak: zero time credit, preserved. |

**All A–O: PASS.** No gate is FAIL or EVIDENCE MISSING at the RC-candidate level.

## Authority reconciliation notes (non-blocking)

- **Internal strategy doc predates the lock:** `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` carries an
  older `$12,500` design-pilot figure. The controlling authority is the owner's locked package
  ($15,000 / 60 days / $18,000 quarterly / $72,000 annual), which the customer-facing path uses (B4.12).
  Updating that internal strategy doc would reopen product strategy, which is out of scope here — flagged
  for owner, not changed. Not a customer-facing defect.
- **Obsolete Intelligence Sprint:** removed from the only customer-facing surface that carried it
  (`brief.py`, B4.12). Remaining mentions are in historical decision/authority records, preserved as
  history (not rewritten).

## Remaining external / non-required dependencies (explicitly NOT RC-candidate blockers)

Per the owner's RC distinctions, these are not blockers by virtue of being incomplete:

- Real EXTERNAL customer-email / operator-alert send to real inboxes — needs genuine SMTP credentials;
  personal Gmail forbidden; sending to real prospects forbidden. Production-equivalent transport is
  proven.
- Off-host backup destination — external storage/infra.
- Python 3.11+ fresh-install environment (only 3.9.6 verified locally; documented).
- The actual 72-hour replacement soak — owner action; not started.
- Public website intake / OUTREACH READY; legal seller / banking / vendor onboarding; international work
  — all out of RC scope.

## End state

**BUNDLE 4: IMPLEMENTATION / VERIFICATION COMPLETE.**
**US PHASE 1: RC CANDIDATE EVIDENCE PACKAGE COMPLETE — AWAITING OWNER RC ACCEPTANCE.**
**FINAL REPLACEMENT SOAK: NOT STARTED.**

main not merged/promoted (`origin/main` = `7bd36c2`). No accepted history rewritten. Historical soak
evidence untouched.
