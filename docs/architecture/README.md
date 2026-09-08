# Pyrnova architecture map

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
