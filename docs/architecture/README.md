# Pyrnova architecture authority and map

For the cross-cutting implementation description, read
[`../system/SYSTEM_ARCHITECTURE.md`](../system/SYSTEM_ARCHITECTURE.md) and
[`../system/DOMAIN_MODEL.md`](../system/DOMAIN_MODEL.md). This directory contains architectural
authority and durable engineering doctrine. Descriptive system documents point back here; they do not
supersede it. Materially important implemented choices are indexed in [`../adr/README.md`](../adr/README.md).

The current package is intentionally compact. Conceptual boundaries exist without premature directory
splitting:

| Concern | Current module/home |
|---|---|
| Source adapters | `pyrnova/sources/` |
| Raw evidence archive | `pyrnova/archive.py` |
| Normalization/entity resolution | `pyrnova/normalize.py`, `pyrnova/resolve.py` |
| Candidate detection/pipeline | `pyrnova/engines/`, `pyrnova/pipeline.py` |
| Capability scoring | `pyrnova/match.py` |
| Evidence enrichment | `pyrnova/enrich.py` |
| Human review/adjudication | `pyrnova/review.py` |
| Replay and versioned evaluation | `pyrnova/replay.py`, `pyrnova/metrics.py` |
| Durable local state | `pyrnova/state.py`, `pyrnova/scoreboard.py` |
| Operator interface | `pyrnova/cli.py` |
| Production schema | `db/schema.sql` |

Pipeline:

```text
OBSERVE → ARCHIVE → NORMALIZE → RESOLVE → DETECT → MATCH → REVIEW → STRIKE → OUTCOME
```

The deterministic core owns facts and state. AI is optional and bounded behind `pyrnova/ai.py`.
Detailed behavior lives in `docs/specs/CAPTURE_RADAR_V1.md`; source-call constraints live in
`docs/specs/SOURCE_INGESTION.md`.

Split modules into deeper `src/` or test subtrees only when file count, ownership, or independent
release/testing boundaries make the move pay for itself. Do not move working code for visual symmetry.

## Engineering & infrastructure doctrine (binding)

How Pyrnova is built — not just what — is governed by two binding doctrine documents at this
(architectural-authority) level. Read them before substantive implementation or infrastructure work:

- **`ENGINEERING_DOCTRINE.md`** — software-engineering doctrine: decision order, one-concept-one-pattern,
  simplicity over premature abstraction, explicit state ownership, no silent semantic fallback, testing,
  refactoring, and the completion standard. **Start cheap. Architect expensive.**
- **`INFRASTRUCTURE_DOCTRINE.md`** — capital & infrastructure doctrine: capacity follows utilization,
  reliability follows consequence, permanent-vs-replaceable, staged evolution, migration invariants.
  **Infrastructure may change; intelligence semantics must not.**

Both were adopted as D-059.
