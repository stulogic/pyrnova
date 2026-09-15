# SOURCE-RIGHTS-001 enforcement evidence

2026-09-14. Engineering gate: **PASS** in the isolated `source-rights-001` branch, based on
`e7cb2c98c3594166cbcb4d5691c0f370d4c5eb57`. This closes only the Customer #1 source-rights gate.
It does not establish overall readiness, deployment, or soak acceptance.

The canonical registry owns typed source policies. Shared HTTP checks source identity and endpoint
scope before transport; redirects are disabled. Archive writes enforce reviewed representations.
Customer material-change, version, and investigation reads check current rights. Derived persistence
and the reusable model callback gate enforce degraded, overdue, and expired rights independently.
No model provider is connected by this task.

## Deterministic evidence

- Existing worker report: 191/191 focused tests passed before this finish pass. Reused as prior
  evidence; the independent worker was usage-blocked and supplied no verification result.
- New boundary selection: 11 passed after reproducing and correcting missing sidecar fields,
  legacy-key aliases, derived expiry enforcement, model flag/payload checks, and connector identity.
- Adjacent archive/connector/customer run: 81 passed, one SEC archive mismatch failed. The mismatch
  was corrected by retaining normalized SEC filing metadata and selected capex facts rather than
  source JSON expression. The subsequent SEC/Federal Register/Grants.gov run passed 26/26.
- Final rights/SAM/customer-display regression: 105/105 passed across `test_source_rights.py`,
  `test_sam_observation.py`, and M22-C/D/E/F. Includes the reproduced and corrected raw-display
  attribution bypass, unknown display permission, and copied-expression limit.
- Additional company-facts archive check: 1/1 passed after correcting a missing import. Stored
  selected values match extraction; original response bytes and source labels are absent.
- `git diff --check` passed. No full-suite repetition was needed for this bounded delta.

Tests used the canonical `.venv/bin/python` with bytecode disabled, executing only in the isolated
worktree. Fake transports and local temporary archives were used; no provider or model call occurred.

| Required boundary | Evidence |
| --- | --- |
| Unknown, Reuters/premium, LinkedIn/social | Denied before ingest; archive denial leaves no material |
| USAspending and SAM public API | Approved shared transport succeeds with explicit identity |
| SAM HTML and D&B legacy | HTML transport denied; nested underscore/camel-case D&B fields denied |
| Corporate default | Unreviewed AMBER denied; reviewed conditional fixture retains normalized facts only |
| Prohibited raw retention | Original hash retained; sentinel expression absent from every persisted file |
| Current display / degradation / expiry | Source content blocked; identifiers and rights diagnostics preserved |
| Retrieval provenance | Class, policy version, retrieval time, source URL and hashes persist in sidecars |
| Historical evidence | Later display disablement leaves prior normalized bytes and retrieval snapshot intact |
| Backup/restore | No backup/restore operation is owned by the archive interface (`put`/`get` only). Reinsertion through `put` is rights-gated; no new framework or external restore claim |

## Soak isolation

Read-only comparison against `/private/tmp/source-rights-isolation-before.json` found no change to
baseline `pyrnova/` or `ops/` runtime files, plan, manifest, or LaunchAgent hashes. Service remained
running with PID 45716 and `runs = 1`; no restart or provider activity was initiated here.
Canonical tracked status was clean. Canonical HEAD had independently advanced to
`3737afda0e464ec4d046208ab6d4cff082e274fe` through SOCIAL-GROWTH-001 documentation only; its runtime
still matches the pinned soak baseline. This task did not integrate or alter that documentation.

Implementation remains isolated. No merge, push, deployment, migration, or soak-evidence edit occurred.
