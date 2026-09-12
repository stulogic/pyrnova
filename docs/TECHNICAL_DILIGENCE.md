# Technical diligence index

Status: internal evidence index; not a warranty, security attestation, or legal opinion  
Last reviewed: 2026-09-12

## Executive technical position

Pyrnova has a compact, inspectable deterministic Python core; content-addressed evidence; explicit
source/provenance/time rules; append-only customer/review/outcome state; versioned replay corpora; broad
offline tests; and application-layer tenant isolation for a controlled pilot. The code and milestone
evidence support the claim that it is engineered and testable.

They do not support a claim that Pyrnova is a deployed, PostgreSQL-backed, enterprise-secured,
high-availability service. The most material diligence gap is the transition from the local JSONL/
stdlib-server implementation to operated production infrastructure with migration, RLS/data-access,
TLS, backups/restores, monitoring, and soak evidence.

## Evidence map

| Review area | Primary evidence | What it establishes | Important limit |
|---|---|---|---|
| Product/roadmap authority | `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md`, `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`, `01-PROJECT-AUTHORITY.md`, `02-EXECUTION.md` | Cross-phase and Phase 1 boundaries plus implementation authorization rules | Authority-history divergence was scope-reconciled in D-063; current branch and status must still be verified for each review |
| Architecture | `docs/system/SYSTEM_ARCHITECTURE.md`, `docs/architecture/`, `docs/adr/`, code | Planes, state owners, decisions, tradeoffs | One process/package today; deployment architecture not implemented |
| Domain model | `docs/system/DOMAIN_MODEL.md`, `pyrnova/models.py`, `db/schema.sql` | Identity, time, evidence, lifecycle, tenant semantics | Python/JSONL and schema are not a fully verified one-to-one persistence layer |
| Code quality | engineering doctrine, module docstrings/types/tests, `docs/development/` | Explicit patterns and safe-change guidance | No automated lint/type/complexity/coverage gate |
| Tests | `tests/`, `examples/replay/`, `docs/replay/`, testing guide | Deterministic unit/integration/replay/security behavior | No CI, DB migration test, browser E2E, load, or general live suite |
| Security | security doc, M22-F spec, access/server/customer tests | Credential lifecycle and application-layer tenant isolation | No RLS, MFA/SSO, TLS edge, pen test, compliance attestation |
| Data rights | source registry, source manifest, proper-means/YELLOW doctrine | Per-source rights/retention metadata and collection boundaries | No legal opinion/terms archive/data-processing inventory in repo |
| Provenance | archive/state/source controls and provenance doc | Exact-byte hashes, observations, source-native refs, sanitized request identity | Evidence-independence and universal amendment lineage incomplete |
| Dependencies | `pyproject.toml`, `requirements.txt` | Very small direct dependency surface | Broad version ranges; no lock/SBOM/vulnerability scan |
| Operations | scheduler/live driver, source-state tests, operations runbook, M13 report | Offline-default control, budgets, cadence, breaker, restart/dedupe primitives | No daemon/deployment, central alerting, backup/restore, unattended soak |
| Replay | replay/outcome code, versioned corpora/reports, temporal doc | Future exclusion, frozen policies/predictions, sourced outcomes | Dated/small corpora; Phase 1.5 research not production runner |
| Technical debt | `KNOWN_LIMITATIONS_AND_TECH_DEBT.md` | Prioritized evidenced risks and mitigations | Priority is not authority to implement |
| History/acceptance | `04-DECISIONS.md`, `06-HISTORY.md`, `docs/replay/`, specs | Traceable milestone decisions and results | Dated evidence may be stale; acceptance levels differ |

## Architecture and code review

Reviewers should trace one opportunity and one threat from source record through archive, normalization,
identity/relationship, assessment, customer fan-out, Material Change, review, and outcome. Use
[`REPOSITORY_MAP.md`](REPOSITORY_MAP.md) to select the modules and matching tests.

Questions to test:

- Can every customer-facing fact identify source/evidence and knowability time?
- Does a weak or ambiguous join remain rejected/deferred/ambiguous?
- Can identical inputs reproduce identity, ordering, score, and report?
- Can a customer action change another customer or global assessment?
- Does a later outcome leave the prior prediction and assessment intact?
- Can a failed archive/source call change meaning or trigger unbounded retries?
- Does the implemented store match the schema being claimed for deployment?

## AI-assisted development and authorship

Pyrnova does not claim that AI was absent from development. Repository history and contribution records
should be preserved as they exist; legal ownership/contributor representations belong outside this
technical document.

Engineering trust is established irrespective of who typed a line through:

- version control and reviewable diffs;
- governing authority and explicit execution boundaries;
- deterministic ids, transforms, and replay;
- source provenance and retained raw evidence;
- typed domain boundaries and documented state owners;
- negative, temporal, security, and customer-isolation tests;
- frozen policies/predictions and append-only outcomes;
- ADRs and explicit limitations/debt;
- reproducible verification commands and dated acceptance artifacts;
- code review that tests semantics, failure behavior, and operational consequences.

Runtime AI is optional behind `pyrnova.ai.Reasoner`; default `NullReasoner` means deterministic operation
does not depend on a model. The protocol says AI enrichment cannot overwrite deterministic fields and must
remain non-authoritative. A full first-class runtime Claim lifecycle is not implemented, so any future AI
use that affects delivery should add explicit claim persistence, evidence spans, model/version/prompt
provenance, validation, and review under separate authority.

The diligence position is: engineering quality is judged through inspectability, verification,
reproducibility, and operational behavior, not by whether every line was manually typed.

## Security and enterprise review

Start with [`system/SECURITY_AND_TENANCY.md`](system/SECURITY_AND_TENANCY.md). Request evidence for the exact
deployment under review. Application tests do not establish network/cloud/database configuration. The
repository contains no SOC 2/FedRAMP certification, pen-test report, RLS policy, enterprise IAM, or
production incident/DR evidence.

Phase 1 authority excludes high-sensitivity/CUI data. Before accepting other classifications, require an
approved data inventory, handling/retention/deletion controls, vendor/subprocessor review, and deployment
security design.

## Operations and scalability review

The local implementation is intentionally cheap and inspectable. `StateStore` reads whole JSONL streams,
has no multi-process locking/transaction, and the stdlib server is not a production application server.
Capacity/performance claims require measurements. Ask for:

- representative data-volume and concurrency results;
- persistence migration/shadow comparison;
- clean schema apply and upgrade/rollback;
- source cadence/budget/failure telemetry;
- alerting and operator response evidence;
- backup/restore and integrity checks;
- deployed restart/failover/soak evidence.

None is inferred from the offline unit suite.

## Data/provenance and rights review

Inspect registry entries, source-specific code/tests, archive objects/sidecars, request redaction, and a
sample Material Change evidence reference. Validate actual source terms and retention decisions against
the planned commercial use. “US government work” metadata is not a substitute for a legal review of API
terms, embedded third-party materials, privacy, redistribution, or customer contracts.

Source/legal records that may be privileged or commercially sensitive should remain in a controlled
corporate data room; Git should retain only non-sensitive decision references and engineering constraints.

## IP and contribution records

Git history provides commit-level technical provenance. This repository audit does not establish IP
ownership, assignment, open-source license compliance, employee/contractor invention assignment, or model
provider terms. Those records belong in the corporate data room and should be reviewed by counsel. A
future release process should produce a dependency lock and SBOM for the reviewed revision.

## Repository versus corporate data room

| Keep in repository | Keep in corporate workspace/data room | Reference in both |
|---|---|---|
| Architecture, domain semantics, code, tests, ADRs, runbooks, source engineering constraints, technical debt, non-secret deployment interfaces | Formation/capitalization, financials, tax, insurance, customer personal/contact data, contracts, legal advice, privileged source-rights analysis, security questionnaires/reports, credentials, investor communications | Approved policy/decision identifiers, release evidence, architecture/security summaries, dependency/SBOM artifacts, non-privileged vendor/source decisions |

Do not turn Git into the company filing cabinet. Do not place secrets, live customer data, raw privileged
advice, or confidential counterpart documents in tracked examples.

## Principal open diligence concerns

1. Branch/authority divergence and stale execution/backlog text before integration.
2. PostgreSQL schema defect and absence of runtime adapter/migration tests.
3. Application-only tenancy, pilot bearer auth, and missing production edge/security verification.
4. No backup/restore/DR or unattended operational evidence.
5. No CI/static/dependency/security/SBOM pipeline.
6. Limited source-live evidence and small, milestone-specific real outcome samples.
7. No formal source-rights/legal evidence pack in repository (appropriately external, but must exist).
8. No clean-machine or independent senior-engineer handover observation.

These concerns do not negate the implemented deterministic core; they define the work needed before a
stronger production or enterprise claim.
