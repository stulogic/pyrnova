# ADR-0004 — Sources are registry-driven, archive-first, offline-default, and controlled

Status: accepted  
Date: 2026-09-12 (retrospective record of M4 and M12–M14)

## Context

External calls are scarce, provider rules differ, sources change, and replay needs exact retained inputs.
Ad hoc fetching would lose provenance, amplify calls, and make acceptance irreproducible.

## Decision

Declare each source in one registry with identity, rights, retention, cadence, budget posture, and
reliability. Default development/scheduling to OFFLINE. For live-safe operation, authorize a sanitized
request through durable budgets, cadence, cache/dedupe, retry metadata, breaker, and checkpoint; archive
permitted exact bytes before downstream interpretation. ACCEPTANCE requires a fresh uncached call.

## Alternatives

- Let every adapter manage policy independently: rejected as inconsistent and hard to audit.
- Poll all sources frequently: rejected as wasteful and provider-hostile.
- Treat cache/fixture success as live acceptance: rejected as false provenance.
- Build a broad orchestration platform: rejected; current scheduler is a small composition layer.

## Consequences

Offline tests/replay are cheap and deterministic; live calls are inspectable and bounded. Each adapter
still owns source-specific semantics. The original `capture-radar --live` flow predates scheduler wiring,
so it is a manual path rather than the unattended governed path.

## Related code

`pyrnova/sources/registry.py`, `pyrnova/sources/control.py`, `pyrnova/sources/source_state.py`,
`pyrnova/archive.py`, `pyrnova/scheduler.py`, `pyrnova/live_ops.py`.

## Related authority

Project authority global source-ingestion rule; SOURCE_INGESTION and SOURCE_MANIFEST; M12/M13/M14 specs.
