# Pyrnova current state

_Verified 2026-09-08 in `~/Documents/Pyrnova` on `main`._

## Milestone status

- **M2: CONDITIONAL PASS / EXTERNAL SAM ACCEPTANCE PENDING.** All implemented behavior is green; a
  fresh post-quota-reset SAM call is the sole formal closure gate.
- **M3: CLOSED.** The formal acceptance review passed on 2026-09-08.
- **M4: NOT STARTED.** A planning stub exists; no source-expansion implementation is authorized.

## Implemented and verified

- USAspending, SAM, and bounded Federal Register ingestion with raw evidence/provenance handling.
- Source-native deterministic identity/deduplication and stable candidate IDs.
- Five evidence levels; Federal Register context capped at levels 1–2 and unable to create candidates.
- Selectivity regression: 1 STRIKE / 57 WATCH / 43 REJECT from the prior 101-candidate Torch run.
- Durable human adjudication with reviewer, timestamp, reason, score, prior system disposition, and final
  decision.
- Strict point-in-time replay, future exclusion, deterministic result/report IDs, and persistent
  scoring/evidence/threshold/mechanism versions.
- Canonical M3 corpus: 20 cases, six mechanism families, positive/negative/partial/ambiguous outcomes.
- Automated classification, evidence, temporal, calibration, value, WATCH, failure-taxonomy,
  mechanism, and model-versus-human diagnostics.
- Full-corpus `scoring_v2_candidate` comparison completed and rejected; `scoring_v1` unchanged.
- 52 tests pass; compilation and diff-integrity checks pass.
- `SAM_API_KEY` loads from the repository-local, gitignored `.env`; file mode is `600`. The value is
  never documented or logged.

## M3 baseline

- STRIKE precision: 0.6667
- WATCH conversion: 0.8571
- False-positive rate: 0.3333
- False-negative rate: 0.0
- Median measurable lead time: 306.5 days
- Human override rate: 0.15

## Known limitations

- M2 has no fresh post-reset SAM acceptance artifact yet.
- Only three known-outcome M3 cases are STRIKEs, so precision uncertainty remains wide.
- Binary metrics exclude PARTIAL and AMBIGUOUS cases.
- Value calibration has only two comparable cases and supports no general conclusion.
- Several official source sites restrict automated URL checks; canonical source/document identity is
  retained separately from current URL reachability.
- Local JSONL state and filesystem evidence archive are development implementations; production
  PostgreSQL/object storage remain deferred.

## Exact next action

Run the M2 live acceptance sequence in `02-EXECUTION.md` at or after `2026-09-09T00:00:00Z`, then record
the acceptance timestamp and raw SAM archive hash here and in `06-HISTORY.md`.
