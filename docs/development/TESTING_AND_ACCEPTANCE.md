# Testing and acceptance

Status: descriptive  
Last reviewed: 2026-09-12

## Evidence hierarchy

```text
unit/contract test
→ module integration test
→ deterministic replay/corpus test
→ local HTTP/runtime test
→ fresh source acceptance
→ deployed operational test/soak
→ owner/customer acceptance
```

Passing one level does not imply the levels to its right.

## Current suite

Tests are collected from `tests/` with `pytest -q` configured in `pyproject.toml`. The suite covers source
request/parsing, archive/state, pipeline/detection/matching, chain/replay/consequence/fit, threats and
propagation, source scheduling/live-driver behavior with injected fetchers, customer Material Changes,
investigation, access, and onboarding.

On 2026-09-12, commit baseline `ce7ee5c` collected 615 tests across 75 test files. This is dated evidence,
not a permanent expected count. The final DOCS-001 verification record belongs in the audit/commit result.

## Test types

- **Unit/contract:** pure normalizers, identifiers, policy helpers, redaction, parsing, scoring components.
- **Integration:** pipeline/archive/state, fan-out/lifecycle, investigation projections, application service.
- **HTTP/security:** handler-driven route tests validate auth and isolation without needing a socket.
- **Replay/acceptance fixtures:** versioned corpora assert point-in-time dispositions, chains, outcomes,
  negative controls, selectivity, and frozen behavior.
- **Environment-dependent:** real OFAC archive tests skip when gitignored bytes are absent; one loopback
  test may skip where socket binding is prohibited.
- **Live acceptance:** kept outside the ordinary suite; M13 tests use injected fetchers and never reach the
  network.

There is no browser E2E suite, CI configuration, coverage threshold, PostgreSQL migration/integration test,
S3 integration environment, load test, security scan, or deployed soak in this baseline.

## Deterministic fixtures and golden behavior

`tests/fixtures/` contains small source-shaped inputs. `examples/replay/` holds progressively extended
challenge corpora; `examples/real_evidence/` contains retained evidence used by milestone cases;
`examples/material_changes_demo/` builds tracked customer-facing demo state.

Historical corpora are frozen so later code can be evaluated against the original cases. Extend with new
cases and explicit schema versions. Do not silently update expected results to make a regression pass.
Generated report ids/content hashes should remain stable for identical canonical inputs.

## What counts as regression

- changed stable identity or nondeterministic ordering;
- future evidence/outcome/customer configuration visible before its cutoff;
- unknown converted to zero/loss/false certainty;
- weak join accepted or ambiguity silently resolved;
- evidence/provenance/rights metadata lost;
- global/customer-private state crossed;
- customer action rewrote system assessment;
- cross-tenant read/write or anonymous remote access;
- source call bypassed mode/budget/cadence/breaker/archive controls;
- scoring/policy semantics changed under the same version id;
- frozen corpus behavior changed without approved rationale;
- fixture/cache/error represented as a fresh acceptance result;
- UI/read projection became a second source of truth.

## Running tests

```bash
# Full offline suite
python -m pytest

# Focused examples
python -m pytest tests/test_archive.py tests/test_source_control.py tests/test_source_state.py
python -m pytest tests/test_replay.py tests/test_m11_outcomes.py
python -m pytest tests/test_m22b_customers.py tests/test_m22c_customer_material_changes.py
python -m pytest tests/test_m22f_access.py tests/test_m22f_server_auth.py tests/test_m22f_onboarding.py

# Inventory without execution
python -m pytest --collect-only -q
```

Use the project virtual environment. Test output should include pass/fail/skip counts and no network calls
unless the run is explicitly an acceptance job.

## Phase 1 acceptance versus operational acceptance

Phase 1 milestone acceptance is represented by specifications, corpus/fixture tests, and dated replay
reports. Operational acceptance separately requires actual runtime/source/deployment evidence: fresh calls
where needed, archival proof, restart/dedupe, source health, failure injection, persistence, browser path,
security posture, backup/restore, monitoring, and unattended soak.

Repository evidence records a bounded M13 USAspending live validation, but that one-source/two-call run is
not a multi-source production characterization. No DOCS-001 statement upgrades it to current live or
production acceptance.

## Before merge

1. Confirm current authority and scope.
2. Inspect the diff for production, schema, corpus, test, secret, and runtime-state changes.
3. Run focused tests for the changed contract.
4. Run the full offline suite for a coherent code change.
5. Run documentation link/reference checks for doc changes.
6. Record skips and environment limitations.
7. Update spec/domain/architecture/runbook/ADR/limitations as triggered.
8. Confirm no acceptance criterion was weakened.

## Before release/deployment

In addition to merge evidence, require a clean build/install, executable migration verification if used,
production configuration review, secrets handling, security/tenant tests, archive/persistence integrity,
backup and restore, rollback, health/alerting, deployed smoke/browser checks, and the applicable owner/
customer acceptance. State explicitly which gates were not run.

## Documentation-only changes

Run link/reference checks, `git diff --check`, and a changed-path boundary check. The full suite remains a
useful non-regression signal when proportionate; it does not turn documentation into runtime acceptance.
