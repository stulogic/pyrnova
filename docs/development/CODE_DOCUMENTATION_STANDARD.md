# Code documentation standard

Status: descriptive contributor standard; subordinate to engineering doctrine  
Last reviewed: 2026-09-12

## Document when meaning is expensive

Substantive documentation is expected for public module boundaries, domain objects, stable identity,
complex algorithms, temporal behavior, security/tenant checks, provenance, scoring/policy versions,
replay, state machines/lifecycles, migrations, failure containment, and intentionally surprising choices.

Prefer clear names, types, tests, and short explanations of **why** over comments that restate **what** the
next line does.

## Module docstring

A domain module should state:

- responsibility and authoritative/non-authoritative role;
- inputs/outputs and state owner;
- key invariants and time/tenant boundary;
- important predecessor/spec/decision;
- what it deliberately does not do.

## Public functions and classes

Document behavior that callers cannot infer safely from the signature: identity, mutation, persistence,
ordering, cutoff rules, idempotency, error/fallback behavior, source rights, and whether output is a fact,
claim, assessment, projection, or outcome.

Avoid verbose parameter recitation where types and names already explain the contract.

## Comments

Use comments for:

- why a tempting simpler path is unsafe;
- why a broad exception is a bounded containment boundary;
- why an identity or threshold is frozen;
- why missing data returns unknown/reject/defer;
- source/provider constraints and rights-sensitive retention;
- compatibility with older records;
- non-obvious time or tenant behavior.

Do not use comments as untracked roadmap authority. Temporary compromises must name limitation, trigger,
and relevant decision/backlog reference.

## Domain and schema changes

Update [`../system/DOMAIN_MODEL.md`](../system/DOMAIN_MODEL.md) when canonical semantics change. Schema
comments must match runtime ownership and must not call a schema-only path operational. Migrations need
purpose, expand/contract sequence, backfill, verification, rollback, and compatibility notes.

## Tests as executable documentation

Name tests for the contract, especially negative behavior. Tests should show future exclusion, unknown
handling, identity stability, weak-join rejection, customer isolation, idempotency, and failure modes—not
merely mirror internal lines.

## High-risk modules for continued improvement

- `pyrnova/threat.py`: large policy/mechanism surface; changes need focused rationale and corpus coverage.
- `pyrnova/ops.py`: broad application-service/read aggregation with graceful-degradation boundaries.
- `pyrnova/cli.py`: many operator paths and a legacy direct live-capture path distinct from scheduler.
- `pyrnova/scheduler.py`: budget/cadence/archive/retry sequencing where order is semantic.
- `pyrnova/customer_material_changes.py`: multi-customer fan-out/version/time/failure isolation.
- `pyrnova/ops_server.py`: route authorization and remote/local exposure policy.
- `db/schema.sql`: intended production semantics without migration/runtime verification.

These modules already contain useful docstrings/comments. The need is to keep boundary documentation
current as behavior changes, not to add prose to every function.
