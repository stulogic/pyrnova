# Pyrnova infrastructure & capital doctrine

_Status: canonical infrastructure authority · adopted 2026-09-10 (D-059)_

Binding infrastructure and capital doctrine. Architectural-authority level in the hierarchy
(`00-INDEX.md`): governs *how* infrastructure is chosen, scaled, and migrated beneath the product and
strategic authority above it. Companion to `ENGINEERING_DOCTRINE.md`. Consistent with the Phase 1
non-goals (D-048: no unnecessary graph-database migration, no premature streaming, no premature
production-Postgres/Cloudflare build ahead of need).

## Mantra

- **Capacity follows utilization. Reliability follows consequence.**
- **Start cheap. Architect expensive.**
- **Infrastructure may change. What Pyrnova knows must not change because infrastructure changed.**

## 24. Capital rule

Infrastructure spending scales proportionately with demonstrated customer demand, revenue, actual
utilization, data volume, contractual/security requirements, and measured operational need. Do not
engineer capacity ahead of evidence.

## 25. Reliability vs capacity

Capacity follows utilization; reliability follows consequence. Cheap reliability improvements (backups,
restore testing, redundant copies, hashes, integrity checks, rollback, failure observability) may be
justified long before additional capacity.

## 26. Permanent vs replaceable

**Permanent (semantics that must survive any infrastructure change):** canonical IDs; source-native
identifiers; intelligence semantics; provenance; evidence hashes; bitemporal truth; customer isolation;
Material Change identity; adjudication/outcome history; replay behavior; domain/API contracts.

**Replaceable (implementation details behind stable abstractions):** Postgres provider; object-store
provider; compute host; queue; scheduler; search backend; analytics backend; secrets provider;
observability provider.

## 27. Expected evolution (spend only as each stage is reached)

- **Stage 0 — pre-revenue:** near-zero cost. Likely Cloudflare edge/static delivery, R2/equivalent
  object storage, low-cost/free managed PostgreSQL, minimal container compute, existing scheduler,
  structured logs.
- **Stage 1 — design customers:** paid DB where justified, stronger backups/PITR, remote deployment,
  better logging/monitoring, modest dedicated compute, restore testing.
- **Stage 2 — meaningful recurring revenue (add only from measurement):** larger DB, replicas/pooling,
  dedicated workers, search if needed, analytical separation if transactional load suffers, stronger
  redundancy.
- **Stage 3 — enterprise:** HA database, distributed compute, dedicated search, dedicated analytics,
  stronger observability, regional/multi-region where required.
- **Stage 4 — very large data estate:** owned storage clusters, colocation, hybrid infrastructure,
  petabyte-scale archive — only when economics justify it.

## 28. PostgreSQL direction

PostgreSQL is the authoritative structured-store direction unless measured evidence proves otherwise.
Prefer portable PostgreSQL semantics. Expected growth: small managed Postgres → larger → pooling →
replicas → partitioning → analytical separation → specialized systems only where justified. **No
rewrite-based scaling plan.** The canonical schema lives in `db/`.

## 29. Object storage

Raw/object evidence sits behind a stable abstraction (e.g. an `EvidenceArchive`); R2 may be the first
implementation. Business/domain logic must not scatter provider-specific assumptions. Object identity,
hashes, and provenance stay stable through migration. (See `pyrnova/archive.py`.)

## 30. Stateless compute

Compute is disposable. Important state must not live solely on local disk or in process memory.
Progression: single process → multiple instances → worker pools → queue/event infrastructure when
justified. No premature Kubernetes / Kafka / Redpanda.

## 31. Migration doctrine

Important migration path: CURRENT → PARALLEL DESTINATION → BACKFILL/REPLICATION → VALIDATION → SHADOW
COMPARISON → CANARY → CUTOVER → ROLLBACK WINDOW → RETIRE OLD SYSTEM. Never "switch and hope".

## 32. Schema migrations

Prefer expand-contract: ADD → compatible deploy → backfill → compare → switch reads → monitor → remove
later. Avoid destructive synchronized schema/code changes requiring perfect timing.

## 33. Infrastructure invariants

Any infrastructure migration must preserve, provably: (1) canonical IDs; (2) source-native IDs; (3) raw
bytes; (4) hashes; (5) provenance; (6) temporal values; (7) relationship validity; (8) customer
boundaries; (9) customer lifecycle; (10) Material Change identity; (11) adjudication; (12) outcomes;
(13) replay semantics; (14) supported API/domain behavior. **If semantic equivalence cannot be proved,
the migration does not ship.**

## 34. Backup / restore

Backups are not proven until a restore has been tested. As consequence rises, validate: database restore
→ evidence availability → hash integrity → customer-state integrity → replay integrity.

## 35. Failure testing

Eventually test: DB loss mid-operation; object-store outage; duplicate events; concurrent duplicate jobs;
worker crash; malformed source data; schema mismatch; stale projection; overlapping deployment; partial
migration. No silent corruption.

## 36. Observability

Scale observability with consequence. Candidate metrics: uptime; ingest lag; delivery lag; source
failures; fan-out failures; stale projections; evidence availability; failed jobs; tenant-boundary
failures; backup age; restore success; recovery time. (The M22-C fan-out already emits a structured
per-run observability report — extend that pattern rather than bolting on a parallel one.)

## 37. Infrastructure change gate

Before adding a substantial dependency, answer: (1) what measured problem requires it? (2) why can't the
current system solve it? (3) what state does it own? (4) how does it fail? (5) how is it recovered?
(6) how is it migrated? (7) what coupling does it create? (8) what does it cost now? (9) what does it
cost later? (10) what tests prove integration? (11) how do we roll back? If unclear, do not add it.
