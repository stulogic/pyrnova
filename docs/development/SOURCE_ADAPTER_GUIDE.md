# Source adapter guide

Status: descriptive implementation guide; source activation still requires authority  
Last reviewed: 2026-09-12

## Entry gate

Before code, show that the source improves a current accepted question rather than adding undirected data.
Apply [`../specs/M4_SOURCE_EXPANSION.md`](../specs/M4_SOURCE_EXPANSION.md), governing source doctrine in
[`../specs/SOURCE_INGESTION.md`](../specs/SOURCE_INGESTION.md), current execution authority, and the lawful
collection/YELLOW-review boundary in strategy. Unknown rights or access terms must remain unknown and may
block activation.

## 1. Register the source

Add one `SourceSpec` in `pyrnova/sources/registry.py` with:

- stable lowercase source id and human name;
- canonical base URL, source family, and access method;
- auth mode without any credential value;
- native identifiers and defensible links to existing sources;
- retention tier and rights note;
- incremental/checkpoint mechanism;
- native and recommended cadence;
- conservative call-budget posture;
- reliability/status based on evidence, not aspiration;
- whether it is active under current Phase 1 authority.

Update [`../specs/SOURCE_MANIFEST.md`](../specs/SOURCE_MANIFEST.md) if its rendered table or explanatory
text changes. `active=True` does not mean the scheduler automatically knows how to fetch it.

## 2. Define source-native identity and time

Choose the strongest immutable/native key the publisher supplies. State how pagination, amendments,
reissues, and deletions are identified. Retain separately:

- publication time;
- event/effective time;
- Pyrnova retrieval/first-observed time;
- earliest defensible `available_at`;
- source revision/version if present.

Never use a title or a normalized description as the only identity when a native id exists. If no stable
id exists, document the limitation and collision controls before activation.

## 3. Rights and retention

Record whether Pyrnova may retain exact bodies, only metadata/structured facts, or only references.
Choose Tier A for mutable/version-sensitive content, Tier B for durable publications, and Tier C only with
an explicit ephemeral lifecycle. Do not infer commercial redistribution rights from public accessibility.
Legal opinions/terms snapshots belong in the corporate data room; the repository may reference their
approved decision ids.

## 4. Implement a narrow adapter

Place source-specific code under `pyrnova/sources/<source>.py`. Separate:

1. request construction and pagination;
2. transport (reuse `sources/http.py` where suitable);
3. raw observation object/bytes;
4. pure parsing/normalization;
5. archive call and safe provenance;
6. checkpoint advancement.

Do not create a new orchestration/control framework. Reuse `SourceControl`, `SourceStateStore`,
`SourceScheduler`, `EvidenceArchive`, and the registry. The scheduler performs no HTTP; supply a fetcher at
the boundary.

## 5. Govern every request

Build a sanitized request fingerprint before transport. Enforce:

- OFFLINE default;
- explicit LIVE_SAFE or ACCEPTANCE mode;
- per-source max calls and budget epoch;
- source-native poll interval;
- pause/resume/mode override;
- cache reuse outside ACCEPTANCE;
- checkpoint/cursor;
- bounded retry metadata and breaker state;
- no key/account rotation to evade limits.

The resolution order is paused → cached request → offline fixture/skip → authorized live fetch → archive
and index. An archive failure after a successful call must preserve spent budget and engage failure
protection; do not retry-storm.

## 6. Archive before interpretation

On successful retrieval retain exact permitted bytes through `EvidenceArchive` before normalization or
domain inference. Record source id/ref, URL where safe, media type, content hash, retention tier,
publication/retrieval time, adapter version, and sanitized request metadata. Never archive secrets.

Where retention permits only structured facts/reference metadata, make the hash scope explicit; do not
call a paraphrase hash the source artifact hash.

## 7. Normalize conservatively

Pure parsers should accept source-shaped fixtures and return source-faithful fields. Invalid rows without
required identity may be skipped with observable counts; parsing failures must not fabricate values.
Use the common event/entity/relationship vocabulary only when semantics match. Preserve source-specific
fields in metadata rather than weakening the canonical model.

## 8. Connect to intelligence

Specify whether the source may:

- create a direct candidate;
- provide precursor/context only;
- ground entity/relationship/exposure;
- contribute threat/adverse-event evidence;
- corroborate or contradict an existing item.

Enrichment-only sources must not independently manufacture STRIKE. Name/topic/chronology alone must not
create an authoritative relationship. Use reject/defer/review paths for weak joins.

## 9. Health, dedupe, and idempotency

Expose records returned/accepted/rejected, calls made/avoided, cache hits, checkpoint, last success/change,
quota state, throttles/retryable/terminal errors, breaker, and next poll where available. Missing quota is
`unknown`. Repeat request/content processing should be deterministic and no-op where appropriate.

## 10. Tests

Minimum offline coverage:

- request shape and secret redaction;
- pagination/checkpoint and restart;
- raw archival/hash/metadata;
- parser happy path plus malformed/missing identity;
- amendment and dedupe behavior;
- OFFLINE makes zero network calls;
- LIVE_SAFE budget/cadence/cache/breaker paths through injected fetcher;
- ACCEPTANCE forbids cached success;
- deterministic native identity;
- temporal cutoff/future exclusion;
- positive, negative, ambiguity, and weak-join controls;
- contribution/selectivity and no forced candidate/STRIKE where applicable;
- error category and safe message behavior.

Real connectivity is a separate, explicitly budgeted acceptance run. Record date, commit, endpoint,
request count, response class, archive hash/reference, useful record count, and limitations without
retaining secrets.

## 11. Production activation checklist

- current execution authority names the source/use;
- rights/retention/access terms reviewed at the required level;
- registry status/reliability accurate;
- source-native ids and temporal semantics documented;
- adapter is archive-first and scheduler-governed;
- budgets, cadence, retry, breaker, checkpoint, dedupe tested;
- fixture/archive replay passes;
- live acceptance passes within budget, if required;
- contribution/selectivity justifies activation;
- source failure produces degraded/unknown, not false freshness;
- monitoring and operator recovery documented;
- no credential or customer-private data enters Git/logs/provenance;
- relevant system, runbook, manifest, tests, and technical-debt docs updated.

## Current examples

- `usaspending.py`: keyless award search and source-native award identity; M13 has bounded live evidence.
- `sam.py`: authenticated quota-limited opportunity search and raw observation capture.
- `sec_edgar.py`: required declared User-Agent, CIK/accession handling, amendment preservation, safe 403.
- `ofac.py`: bulk snapshot parsing and authoritative list identity; intelligence evidence only.
- `grants_gov.py`: request sanitization, source-specific opportunity identity/dedupe, fixture validation.
- `acquisition_forecast.py` and `appropriations.py`: bulk artifact parsing with per-artifact semantics.
- `sbir.py`: fixture-tested adapter whose registry currently records blocked/unverified live status.

Copy patterns, not claims: each new source still needs its own rights, cadence, identity, and acceptance
evidence.
