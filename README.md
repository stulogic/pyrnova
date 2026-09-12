# Pyrnova

Pyrnova is an evidence-backed economic and commercial intelligence system. Its current Phase 1
application serves US federal and defense contractors by turning attributable external change into
customer-specific Material Changes: opportunity, threat, or monitoring items that retain evidence,
uncertainty, temporal truth, review state, and later outcomes.

The current customer product is the Material Changes feed with company/program investigation and
deterministic search. Capture Radar is the opportunity-detection kernel within that product, not a
separate product. Broader industrial and cross-sector architecture is direction or research unless the
current execution authority explicitly opens it.

## Start here

| Reader | First path |
|---|---|
| Founder or product owner | [`docs/README.md`](docs/README.md) → governing authority |
| New engineer | [`docs/ENGINEERING_HANDOVER.md`](docs/ENGINEERING_HANDOVER.md) → [`docs/development/ENGINEERING_GUIDE.md`](docs/development/ENGINEERING_GUIDE.md) |
| Operator | [`docs/operations/OPERATIONS_RUNBOOK.md`](docs/operations/OPERATIONS_RUNBOOK.md) |
| Technical reviewer | [`docs/TECHNICAL_DILIGENCE.md`](docs/TECHNICAL_DILIGENCE.md) |
| Agent | [`AGENTS.md`](AGENTS.md) first, then [`00-INDEX.md`](00-INDEX.md) |

The governing hierarchy starts with
[`docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md`](docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md),
[`01-PROJECT-AUTHORITY.md`](01-PROJECT-AUTHORITY.md), and
[`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`](docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md).
Only [`02-EXECUTION.md`](02-EXECUTION.md) authorizes implementation. Descriptive documentation in
`docs/system/`, `docs/development/`, and `docs/operations/` explains the repository; it does not create
product authority.

## Architecture at a glance

```text
external sources
      │
      ▼
OBSERVE → ARCHIVE → NORMALIZE → RESOLVE → DETECT / CONNECT
      │                                      │
      │                                      ▼
      └──────────── provenance ───────► ASSESS / MATCH
                                             │
                                             ▼
                                   REVIEW → MATERIAL CHANGES
                                             │
                                             ▼
                                      OUTCOME / REPLAY
```

- **Evidence plane:** source registry, governed retrieval, immutable content-addressed archive, source
  state, and provenance.
- **Intelligence plane:** normalized events/entities/relationships, opportunity and threat engines,
  consequence and fit logic, review, and outcomes.
- **Compute plane:** deterministic pipeline, source scheduler/live driver, fan-out, replay, and metrics.
- **Delivery plane:** append-only local state, customer-scoped Material Change projections, HTTP API,
  customer views, internal Operator Console, CLI, and Markdown briefs.

See [`docs/system/SYSTEM_ARCHITECTURE.md`](docs/system/SYSTEM_ARCHITECTURE.md) and
[`docs/REPOSITORY_MAP.md`](docs/REPOSITORY_MAP.md) for implementation paths.

## Local setup

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m pytest
```

The default development path is local and offline-capable. Runtime state is append-only JSONL under
`var/state`; raw evidence defaults to `var/archive`; generated briefs go to `out`. These paths and `.env`
are ignored by Git.

Run the deterministic fixture path:

```bash
python -m pyrnova.cli capture-radar \
  --profile examples/profiles/acme_c4isr.json \
  --fixtures
```

Run the customer-facing product locally:

```bash
python -m pyrnova.ops_server
```

Open `http://127.0.0.1:8765/` for Material Changes or `/console` for the local-only Operator Console.
The server may seed tracked demonstration customers and use tracked demonstration intelligence when the
configured local state is empty; this is demo behavior, not a production ingestion claim.

Live retrieval is never required for ordinary development or tests. When explicitly authorized, see
[`docs/specs/LIVE_RUN.md`](docs/specs/LIVE_RUN.md) and the stricter current operational contract in
[`docs/operations/OPERATIONS_RUNBOOK.md`](docs/operations/OPERATIONS_RUNBOOK.md).

## Major implementation areas

| Area | Primary paths |
|---|---|
| Source registry and adapters | `pyrnova/sources/` |
| Evidence archive and local state | `pyrnova/archive.py`, `pyrnova/state.py` |
| Pipeline and opportunity detection | `pyrnova/pipeline.py`, `pyrnova/engines/` |
| Events, relationships, consequences, fit | `pyrnova/models.py`, `pyrnova/chains.py`, `pyrnova/catalysts.py`, `pyrnova/fit.py` |
| Threats and propagation | `pyrnova/threat.py`, `pyrnova/propagation.py`, `pyrnova/adverse_events.py` |
| Customer relevance and Material Changes | `pyrnova/customers.py`, `pyrnova/material_changes.py`, `pyrnova/customer_material_changes.py` |
| Search and investigation | `pyrnova/investigation.py` |
| Access and delivery | `pyrnova/access.py`, `pyrnova/ops.py`, `pyrnova/ops_server.py`, `pyrnova/ops_web/` |
| Replay, outcomes, and metrics | `pyrnova/replay.py`, `pyrnova/outcomes.py`, `pyrnova/metrics.py` |
| Structured-store direction | `db/schema.sql` |

## Important boundaries

- Canonical records are not presentation. Material Changes and investigation pages are derived read
  projections over retained global and customer-scoped state.
- Capture, verification, publication, customer review, and outcome are separate states.
- Missing information remains unknown; absence is not converted to zero, loss, or certainty.
- `scoring_v1` is the active Phase 1 policy. Challenger policies are evaluation-only.
- Tenant isolation is implemented in the application layer. Database row-level security is not present.
- Local JSONL is the active development store. PostgreSQL tables are a production mirror/direction;
  no runtime PostgreSQL repository adapter is implemented in this baseline.
- Phase 1.5 industrial replay lives on a separate research branch and is not production behavior.

See [`docs/KNOWN_LIMITATIONS_AND_TECH_DEBT.md`](docs/KNOWN_LIMITATIONS_AND_TECH_DEBT.md) for the full
evidenced register.
