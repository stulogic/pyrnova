# Phase 1 operational-soak test Lens and start gates

_Owner clarification and execution record · 2026-09-12_

This document fixes configuration and acceptance criteria before runtime results. Actual foreground
results, supervised start timestamp, cycles, health, and interventions are authoritative in gitignored
`var/phase1_soak/evidence/`; this document is not a successful-soak or commercial-readiness claim.

## Authority and designation

The owner accepts PHASE1-LIVE-OPS-CLOSURE implementation conditionally and authorizes
`IRONMOUNTAIN SOLUTIONS, LLC` only as a **SOAK TEST LENS — NON-CUSTOMER / NON-COMMERCIAL**.
It is not Customer #1, a design customer, a fixed CUSTOMER-001 cohort member, a substitute for MTSI,
an outreach target, or willingness-to-pay/commercial-validation evidence. The fixed commercial cohort
is not reconstructed or replaced by this execution.

## Source-backed configuration

Canonical test tenant ID: `soak-ironmountain-solutions`. The profile and watches were persisted through
`pyrnova.onboarding.create_customer` / `add_watch` at `2026-09-12T19:21:51.167659+00:00` into
`var/state`. The designation is explicit in persisted provenance and the capability-profile JSON.
Existing Torch/DAP profiles remained unchanged; no customer credential was created.

Evidence: the accepted real USAspending response acquired at `2026-09-12T14:53:08.917394+00:00`, SHA-256
`3c5a3fc2ee6c754ec2b3980925dd9326224596b7e43960fa70760f3e07bc3061`, under
`var/phase1_live_ops/baseline_2026-09-12/archive/`. All ten records identify the same legal recipient and
literal recipient ID. The smallest representative watch universe is six objects, not a fabricated
75-object commercial entitlement:

| Type / category | Source-backed identity | Reason |
|---|---|---|
| ENTITY / direct company | `07414b10-4845-6e30-03fc-0046ab6ae670-C` | Literal USAspending recipient ID; explicitly unresolved, not invented as a canonical `co_*` entity |
| CONTRACT / direct contract | `W31P4Q21FB001` | Direct award, period ended 2026-09-07; preserves recently ended context |
| CONTRACT / direct contract | `W9126024F5010` | Direct award, period ends 2027-03-14 |
| AGENCY / observed agency | Department of Defense | Awarding agency on all ten records |
| AGENCY / observed agency | Department of the Army | Awarding sub-agency on nine records |
| AGENCY / observed agency | Defense Logistics Agency | Awarding sub-agency on `SPRRA125P0008` |

Profile agencies use those exact observed names. Capability keywords are literal award-description
phrases: `technical management support` (`W31P4Q21FB003`), `technical services support`
(`W31P4Q20FB001`), and `systems integrations` / `engineering and technological advice`
(`W9126024F5010`). These are historical performance-evidence keywords, not a verified general capability
statement or inferred pursuit interests. Recipient search anchors use the exact source legal name.

NAICS and PSC are null in all ten archived records and remain empty. Canonical company entity refs,
geography, sectors, size preferences, set-asides, clearances, certifications, competitors, relationships,
and commercial interests remain unset. SAM's accepted adapter treats NAICS as optional, so its bounded
date-window request omits `ncode`; downstream relevance/selectivity is unchanged. Negative cycles are valid.

Reproducible private configuration: `var/phase1_soak/lens_configuration.json` and
`ironmountain_profile.json`. Repeated watch persistence with the same validity timestamp appended zero
records; profile/watch reload and stable tenant ID were verified.

## Narrow pre-start corrections

- Replaced the old `customer_1` plan label with the explicit non-commercial test-Lens designation;
  preflight checks persisted provenance and profile designation and rejects commercial labeling.
- Corrected example paths for the documented copied-plan destination, `var/phase1_soak/plan.json`.
- Added a clean-tracked-tree preflight gate; known intentional untracked files do not invalidate it.
- Added `foreground` validation that records a real cycle and immediate unchanged fan-out without
  creating `manifest.json` or starting the official clock. `serve` starts the official manifest only
  after that gate passes and supervision is activated.
- HTTP transport exceptions retain safe endpoint/type only; prepared-URL query credentials never enter
  operational exception text.

Focused verification: 119 tests passed. Final canonical verification: 635 passed, zero failed/skipped.
Changed operational modules compiled, the launchd template passed `plutil`, and patch checks passed.
The current Python 3.9/LibreSSL environment emits urllib3's compatibility warning; it is retained as
environment evidence, not hidden or relabeled as failure.

## Locked execution and acceptance contract

1. Freeze/push the verified canonical commit and copy the plan to `var/phase1_soak/plan.json`, pinning it.
2. Run `preflight`, then `foreground`. Inspect source results, exact archives, downstream/fan-out,
   checkpoints, health/freshness, retry state, duplicate suppression, and `foreground_validation.json`.
3. Stop on a P0 failure; do not silently edit checkpoints, outputs, thresholds, or source state.
4. Only after a clean foreground result, render/lint the validated launchd template. Inspect the exact
   `/Users/stu/Library/LaunchAgents/com.pyrnova.live-ops.plist` target before installing; never overwrite
   an unknown service. Bootstrap the user GUI domain, verify loaded/running PID and first supervised
   cycle, and read expected stdout/stderr/status evidence.
5. The service's `serve` call creates the official immutable manifest. Record its exact start, +7-day
   earliest completion, and fifth business day; stop this execution without claiming elapsed acceptance.

Duration is exactly seven consecutive calendar days including at least five business days. USAspending
is weekly with maximum two calls per epoch; SAM is daily with maximum one. The six-object Lens and
source/cadence/criteria are fixed before results. Evidence is `var/phase1_soak/evidence`.

Hard-zero thresholds: unresolved P0 correctness failures, future-data leakage, tenant leakage,
unexplained evidence loss, uncontrolled duplication, and silent source failure. Three consecutive failed
cycles is the failure threshold. Expected schedules, bounded retries, coherent checkpoints/fan-out,
honest degraded state, and reconstructable operation are mandatory; external uptime perfection is not.

Observation (logs, health, review, evidence capture) is allowed. Documented restart, externally forced
credential rotation, and documented provider-outage response are allowed only when logged. Manual
ordinary ingestion, checkpoint edits, manual dedupe/fan-out repair, and threshold changes invalidate the
window. Acceptance-critical code changes restart the entire 7-day/5-business-day window from the corrected
commit. P1 customer alerting, production backup/restore, public TLS, PostgreSQL/RLS, S3, additional sources,
and Phase 1.5 production work do not block this local soak unless runtime independently proves necessity.

## Recovery and rollback

Service rollback is `launchctl bootout` of the exact installed service, preserving all state/archive and
evidence. Configuration correction uses append-only profile versions/watch retirement, never JSONL
rewrites. No irreversible migration or product-scoring/replay change occurs here. A code rollback before
acceptance requires a newly pinned verified commit; during acceptance it restarts the full window.

## Foreground real cycle — independent evidence gate blocked

The plan pinned to `4b791045f82ae12955b1715c2e828620db15ce61` passed preflight at
`2026-09-12T19:27:56.800774+00:00`, with one persisted six-object Lens, both credentials/source paths,
and a clean tracked tree. The single foreground cycle `cycle_ad674920546a4709f84c` began at
`2026-09-12T19:28:14.725629+00:00` and completed at `2026-09-12T19:31:16.405801+00:00`.

| Source | Actual archived rows | Ledger rows | SHA-256 |
|---|---:|---:|---|
| USAspending | 14 | 0 (incorrect) | `df603dca8d27bbae28bf83d33117c6a43d74ea2614c80321ff366ac7834010de` |
| SAM | 100 | 0 (incorrect) | `c84b27447a621078093ae0675ec6fd517955b16764d91d0b201322bac8636ce6` |

Both hashes independently verified. One call per source was made, no retry/throttle/error occurred, both
sources were HEALTHY/CURRENT, pending-processing markers cleared, and checkpoints advanced to the cycle
ID. The source ledger's count discrepancy is not a zero-result provider response.

The pipeline evaluated 26 candidates: 24 REJECT, one WATCH, one STRIKE. Fan-out inserted one relevant
watched-contract Material Change (`W9126024F5010`), suppressed 28 other global items, and failed zero
items. Immediate unchanged fan-out inserted/updated zero and suppressed one duplicate. These selective
results are operational test evidence only, not commercial value or willingness-to-pay proof.

The automatic foreground result returned `ok=true`, but independent artifact inspection fails the overall
pre-soak evidence gate: the harness did not supply `LiveRunner.record_counter`, so `_null_counter` reported
zero for non-empty real data. This is an acceptance-critical operational-evidence defect. The original
foreground ledger/result is preserved unchanged; `pre_soak_gate_decision.json` records the negative gate.
No metrics/checkpoints/output were manually repaired, no second provider request was issued, and no
post-cycle product fix was applied. A minimal counter-wiring correction plus non-empty real-artifact
regression is required before a new verified start gate, respecting retained evidence and cadence/budgets.

**SOAK BLOCKED.** `launchctl print gui/501/com.pyrnova.live-ops` confirmed no such service. No plist was
installed/activated and `manifest.json` does not exist. The deployment-checklist pre-deploy evidence gate
held activation. Operational acceptance is blocked before start; no official soak timestamp exists.
