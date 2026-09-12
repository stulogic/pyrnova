# Engineering guide

Status: descriptive workflow  
Audience: first senior engineer and future contributors  
Last reviewed: 2026-09-12

## Before changing anything

1. Confirm the canonical repository and inspect `git status`, branch, upstream, and worktrees.
2. Read [`../../AGENTS.md`](../../AGENTS.md) and perform its start-of-work check.
3. Resolve authority through [`../../00-INDEX.md`](../../00-INDEX.md). Only
   [`../../02-EXECUTION.md`](../../02-EXECUTION.md) authorizes implementation.
4. Read the relevant specification and ADRs. Research/roadmap/history do not authorize work.
5. Identify frozen behavior and the smallest accepted pattern to extend.
6. Keep local state, evidence, generated output, and secrets out of Git.

If the canonical checkout contains another contributor’s unfinished work or branch divergence, use an
isolated worktree from an explicitly justified baseline. Do not stash, clean, reset, merge, or rebase that
work as a convenience.

## Environment

Pyrnova requires Python 3.10+. Runtime dependency is `requests`; optional extras are `boto3` for the
S3-compatible archive, `psycopg` for future PostgreSQL work, and `pytest` for development.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
python -m pytest
```

The existing canonical checkout may already have `.venv`; when validating an isolated worktree, it is
safe to invoke that interpreter with the isolated worktree as the current directory. Do not use system
Python if it lacks the project’s dev dependencies.

## Project structure

- `pyrnova/`: one application package, intentionally flat while boundaries remain manageable.
- `pyrnova/sources/`: source registry, controls, state, transport, and adapters.
- `pyrnova/engines/`: opportunity detection engines.
- `pyrnova/ops_web/`: static browser assets.
- `tests/`: offline deterministic tests plus environment-dependent acceptance checks.
- `examples/`: fixtures, profiles, replay corpora, and evidence-backed demonstration material.
- `db/schema.sql`: intended PostgreSQL mirror; not an active migration/runtime integration.
- `docs/`: authority, specs, replay evidence, system/developer/operations docs, and history.
- `var/`, `out/`, `.env`: local-only ignored runtime material.

Use [`../REPOSITORY_MAP.md`](../REPOSITORY_MAP.md) for module-to-test routing.

## Code conventions

- Follow Python standard-library conventions and the existing dataclass/function style.
- Prefer explicit deterministic transformations and stable source-native identities.
- Keep state ownership obvious; reads should not quietly write.
- Preserve observed facts, derived assessment, customer relevance, review, and outcome as distinct fields.
- Use timezone-aware UTC at new boundaries; do not spread the current naive/aware inconsistency.
- Use narrow exception handling. Broad containment is acceptable only at a documented per-source,
  per-customer, or telemetry boundary where semantic failure is explicit.
- Do not introduce a second resolver, customer model, intelligence graph, or scoring path.
- Add a dependency only when the standard library/current dependency cannot meet an evidenced need.
- Apply [`CODE_DOCUMENTATION_STANDARD.md`](CODE_DOCUMENTATION_STANDARD.md) to non-obvious public boundaries.

Binding engineering rules are in
[`../architecture/ENGINEERING_DOCTRINE.md`](../architecture/ENGINEERING_DOCTRINE.md) and infrastructure
rules in [`../architecture/INFRASTRUCTURE_DOCTRINE.md`](../architecture/INFRASTRUCTURE_DOCTRINE.md).

## Adding or changing a domain object

1. Define the semantic owner, stable identity, mutability, tenancy, time fields, evidence requirements,
   and invariants before writing code.
2. Reuse an existing canonical dataclass/stream when the concept already exists.
3. Update `models.py` or the owning module; keep read projections separate from truth.
4. If persistence changes, update the local implementation and intended relational mirror deliberately.
   Do not claim schema/runtime parity until both are tested.
5. Add serialization/backward-compatibility handling for older JSONL rows where needed.
6. Test identity, empty/unknown behavior, invalid input, time cutoff, and deterministic ordering.
7. Update [`../system/DOMAIN_MODEL.md`](../system/DOMAIN_MODEL.md) and relevant spec.
8. Add an ADR only if the change is a materially important architecture decision.

## Adding an event or relationship type

- Require a source-native/evidence-backed reason for the vocabulary addition.
- Define direction and meaning precisely; do not use a vague universal ontology.
- Identify allowed join methods and rejection/defer behavior.
- Carry `available_at` and, where applicable, `valid_from`/`valid_to`.
- Add positive, negative, ambiguous, duplicate, and future-leakage tests.
- Exercise propagation only if the relationship supports a defensible economic path.
- Update relevant corpus by extension; do not mutate frozen historical cases casually.

## Material Changes and customer relevance

Global engines write global intelligence. Customer-specific profile/watch/relevance/delivery/review state
goes only to customer streams. Extend the existing chain:

```text
global record → material_changes projection → customer fan-out/version → lifecycle overlay → API/UI
```

Preserve source intelligence id as `material_change_id`, three first-seen times, content-hash idempotency,
review history across rebuild, and application-layer access checks. A UI convenience must not become a
new truth store.

## Source adapters

Follow [`SOURCE_ADAPTER_GUIDE.md`](SOURCE_ADAPTER_GUIDE.md). Development is offline-first; live calls are
scarce, explicitly authorized acceptance/operation. Do not add a source because it is interesting or easy.

## Replay corpora and scoring

- Existing corpus files are historical test evidence and are extended, not retroactively rewritten,
  unless a documented correctness defect requires repair.
- Every record used at a cutoff needs defensible availability.
- Include negative and ambiguity controls.
- Give a challenger a new version id and compare across the full applicable corpus.
- Do not promote a challenger or change `scoring_v1` without authority.
- Keep Phase 1 and Phase 1.5/domain-specific policies separate.

See [`../system/REPLAY_AND_TEMPORAL_TRUTH.md`](../system/REPLAY_AND_TEMPORAL_TRUTH.md) and
[`../system/SCORING_AND_DECISION_LOGIC.md`](../system/SCORING_AND_DECISION_LOGIC.md).

## Testing

Run the smallest relevant tests while iterating, then the full offline suite before a coherent merge/
release checkpoint:

```bash
python -m pytest tests/test_m22f_access.py tests/test_m22f_server_auth.py
python -m pytest
```

Do not use the count alone as evidence. Record command, date, commit, pass/fail/skip counts, and environment
for material acceptance. Live source, socket, browser, deployed, and owner-acceptance gates remain separate.

## Schema and migrations

There is no migration framework in this baseline. `db/schema.sql` is a monolithic intended PostgreSQL
schema with incremental `ALTER TABLE` statements and currently has no clean-apply test. Treat changes as
high risk:

1. do not edit it inside an unrelated feature;
2. define expand-contract and rollback/backfill behavior;
3. test a clean database and upgrade path;
4. compare local JSONL semantics with the destination;
5. add tenant controls before enabling direct/multi-service access;
6. update domain, security, operations, and diligence docs.

## Debug workflow

1. Reproduce from a pinned fixture/archive and explicit `as_of`.
2. Identify the state owner and inspect only the relevant JSONL/source-state file.
3. Trace source ref → archive hash → normalized/event/relationship id → assessment → customer version.
4. Confirm policy and engine version.
5. Distinguish source absence, parser rejection, temporal exclusion, relevance suppression, review state,
   and authorization denial.
6. Add a failing test that captures the contract.
7. Make the narrowest semantic fix and rerun focused/full tests.

Never repair a missing fact by filling a default that changes meaning.

## Release discipline

A code checkpoint requires current authority, clean and reviewable diff, risk-proportional tests, updated
current-state/spec/docs, no secrets/runtime artifacts, and an explicit statement of what remains
unverified. Deployment and owner acceptance are separate actions and require separate evidence.

For documentation-only work, verify that no `pyrnova/`, `tests/`, `db/`, corpora, or runtime files changed.

## Compatibility expectations

- Preserve older JSONL rows with absent optional fields.
- Keep stable ids and source-native refs through refactors/migrations.
- Add optional parameters with safe existing defaults where practical.
- Separate refactoring from behavior change.
- Do not let an infrastructure migration change intelligence semantics.
- Maintain customer isolation and point-in-time behavior across every new read/write path.
