# Repository map

Status: descriptive  
Last reviewed: 2026-09-12

Paths are responsibilities, not separate deployable services. Pyrnova is currently one Python package
with a small static frontend and local-file development state.

| Path/module | Responsibility | Important dependencies | Relevant tests | Primary docs |
|---|---|---|---|---|
| `AGENTS.md`, `00-INDEX.md` | Operating rules and authority routing | Root authority files | Documentation validation | `docs/README.md` |
| `pyrnova/models.py` | Shared dataclasses for evidence, event, relationship, opportunity, consequence, threat, prediction, review | stdlib | Most engine tests | `docs/system/DOMAIN_MODEL.md` |
| `pyrnova/config.py` | Environment and repository-local `.env` loading | stdlib | M21 SEC tests indirectly | `docs/development/ENGINEERING_GUIDE.md` |
| `pyrnova/sources/registry.py` | Machine-readable source identity, rights, retention, cadence, status | stdlib | source/manifest tests across adapters | `docs/specs/SOURCE_MANIFEST.md` |
| `pyrnova/sources/control.py` | Modes, budgets, fingerprints, redaction, retry metadata, breaker | stdlib | `test_source_control.py` | `docs/specs/SOURCE_INGESTION.md` |
| `pyrnova/sources/source_state.py` | Durable per-source checkpoints, budgets, breaker state, cache index | `StateStore`-independent JSON files | `test_source_state.py` | Source guide and runbook |
| `pyrnova/sources/*.py` | Source-specific request, parse, normalization, and archive helpers | `requests`, registry/control/archive as applicable | matching source test files | `docs/development/SOURCE_ADAPTER_GUIDE.md` |
| `pyrnova/archive.py` | Content-addressed local or S3-compatible raw evidence archive | config; optional `boto3` | `test_archive.py` | `docs/system/DATA_AND_PROVENANCE.md` |
| `pyrnova/normalize.py`, `resolve.py`, `enrich.py`, `integrate.py` | Source-faithful normalization, deterministic identity, conservative linking | models | normalization/integration/grounding tests | Architecture/domain docs |
| `pyrnova/engines/` | Deterministic recompete and pre-solicitation detection | models | `test_recompete.py`, `test_presolicitation.py` | `docs/specs/CAPTURE_RADAR_V1.md` |
| `pyrnova/pipeline.py` | Capture Radar orchestration, archival, dedupe, match/review/prediction persistence | archive, engines, match, review, state | `test_pipeline.py`, milestone-2 tests | Architecture and scoring docs |
| `pyrnova/chains.py`, `precursors.py`, `transitions.py` | Cross-source capital chains and point-in-time disposition changes | replay/models | M5/M6/transition tests | M5/M6 specs; temporal doc |
| `pyrnova/catalysts.py`, `capabilities.py`, `value.py` | Capital catalyst and commercial-consequence derivation | models/chains | M7 and capability/value tests | M7 spec; domain/scoring docs |
| `pyrnova/company.py`, `grounding*.py`, `multisource.py`, `fit.py` | Evidence-linked company profiles and customer capability fit | source parsers/models | M8–M10 tests | M8–M10 specs |
| `pyrnova/adverse_events.py`, `relationships.py`, `threat.py`, `propagation.py` | Adverse events, explicit economic edges, threat assessment and bounded propagation | models/outcomes | M15–M21 tests | M15–M21 specs and replay reports |
| `pyrnova/selectivity.py`, `threat_calibration.py`, `metrics.py` | Funnel and replay/calibration summaries | engine outputs | M16–M21 metrics tests | Scoring/testing docs |
| `pyrnova/replay.py`, `review_queue.py`, `outcomes.py` | Frozen-corpus replay, uncertain-join review, append-only outcomes | models/state | replay, M5–M11 tests | `docs/system/REPLAY_AND_TEMPORAL_TRUTH.md` |
| `pyrnova/customers.py` | Customer profiles, watchlists, lifecycle actions, point-in-time context | StateStore | `test_m22b_customers.py`, onboarding tests | Domain/security docs |
| `pyrnova/material_changes.py` | Customer-relevance and Material Change read projection | threat/opportunity streams | `test_material_changes.py`, M22-E tests | M22-A/E specs |
| `pyrnova/customer_material_changes.py` | Customer-scoped materialization, versions, fan-out, rebuild | customers/material_changes/StateStore | `test_m22c_customer_material_changes.py` | M22-C spec |
| `pyrnova/investigation.py` | Deterministic search and company/program read projections | global streams/material changes | `test_m22d_investigation.py` | M22-D spec |
| `pyrnova/access.py` | Bearer credentials, auth context, fail-closed tenant check | StateStore, stdlib crypto | M22-F access/server tests | Security doc; M22-F spec |
| `pyrnova/ops.py` | Application service over state, projections, review, export, source health | most read/write modules | `test_ops.py`, M14/M15/M16 panel tests | Operator Console/runbook |
| `pyrnova/ops_server.py` | Threaded local HTTP server, route policy, static assets | access/ops/config | M22-F server tests | Security/runbook docs |
| `pyrnova/ops_web/` | Static customer Material Changes, investigation, access, and internal console UI | HTTP API | server/API tests; no browser suite | M22 specs |
| `pyrnova/scheduler.py`, `live_ops.py` | Offline-default source jobs, durable control, live driver, health/cost telemetry | registry/control/source state/archive | M12/M13/M17 tests | Operations runbook |
| `pyrnova/cli.py` | Operator/developer commands | package modules | exercised across tests; help smoke check | Engineering/runbook docs |
| `pyrnova/brief.py`, `scoreboard.py` | Markdown delivery and append-only metric events | models/state | pipeline/ops tests | Capture Radar spec |
| `db/schema.sql` | Intended PostgreSQL mirror of canonical objects | PostgreSQL + `uuid-ossp` | no executable migration test | Domain/security/limitations docs |
| `examples/` | Profiles, tracked real-evidence extracts/raw examples, replay corpora, demo builders | package modules | replay/milestone tests | Replay/provenance docs |
| `tests/fixtures/` | Deterministic source-shaped fixtures | pytest | source tests | Testing doc |
| `tests/` | Unit, contract, integration, security, replay and milestone acceptance tests | pytest | self | Testing doc |
| `docs/specs/` | Detailed implemented subsystem/milestone contracts | code + decisions | cited test files | `docs/README.md` |
| `docs/replay/` | Dated empirical and acceptance evidence | corpora/test runs | replay tests | Testing/diligence docs |
| `var/`, `out/`, `.env` | Local evidence, state, outputs, secrets; ignored | runtime | not tracked | Operations runbook |

There is no separate service directory, migration runner, deployment manifest, CI workflow, or runtime
PostgreSQL repository implementation in this baseline.
