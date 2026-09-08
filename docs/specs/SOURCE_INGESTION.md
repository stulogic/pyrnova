# Source ingestion doctrine

_Status: active global adapter contract · authority: `01-PROJECT-AUTHORITY.md`_

## Governing rule

Live external calls are scarce infrastructure. **Archive once, replay many.** A source adapter must
optimize for attributable coverage per permitted call, not maximum polling volume.

## Operating modes

- **OFFLINE** — default for development and tests. Use explicit fixtures or archived raw responses;
  make no external calls.
- **LIVE-SAFE** — operational ingestion within configured source budgets. Reuse archived responses,
  persistent cursors, request identities, and source-native cadence. Fetch only missing/delta state.
- **ACCEPTANCE** — explicit fresh uncached retrieval used only to prove connectivity, freshness,
  adapter behavior, or archival integrity. Never silently fall back to cache or fixtures.

The mode must be visible in operator output and durable request provenance. An error, quota response,
fixture, or cache hit cannot be reported as a successful ACCEPTANCE retrieval.

## Required adapter behavior

- Retain exact raw response bytes, retrieval timestamp, endpoint identity, sanitized request parameters,
  deterministic content hash, source-native record identity, and adapter/extraction version.
- Keep credentials ephemeral. Never archive URLs, headers, query parameters, exceptions, or payloads
  containing keys or tokens.
- Prefer incremental/delta fetching and persistent cursors/checkpoints when supported.
- Deduplicate equivalent requests and records; reuse cached/archive content in OFFLINE and LIVE-SAFE.
- Poll at the source-native change cadence, not a generic high-frequency interval.
- Apply bounded exponential backoff with jitter to retryable errors and honor provider retry guidance.
- Open a circuit breaker after repeated quota/throttle/service failures; record the next permitted poll.
- Configure explicit per-source request budgets. Stop at the budget rather than degrading provenance or
  rotating credentials/accounts against provider terms.
- Preserve amendments and materially distinct states for mutable Tier-A sources. Avoid redundant raw
  copies for durable Tier-B sources while retaining observation metadata.

## Standard source metrics

Expose where practical:

- calls made
- cache hits
- avoided calls
- current quota state and next permitted poll
- last successful call and last detected change
- records returned/accepted per call
- throttles, retryable errors, and terminal errors
- cursor/checkpoint position

Missing provider quota information must remain `unknown`; do not infer remaining quota from silence.

## Current implementation boundary

SAM raw archival, sanitized request provenance, immutable hashing, and offline fixtures remain intact.
M4 adds small adapter-neutral controls for explicit modes, sanitized request fingerprints, budgets,
call/cache/error accounting, retry metadata, and breaker state. Grants.gov, SEC EDGAR, and official
agency forecast adapters use those controls while retaining source-specific transport/cadence logic;
there is no generic orchestration platform.
