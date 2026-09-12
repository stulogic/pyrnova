# Replay and temporal truth

Status: descriptive  
Last reviewed: 2026-09-12

## Purpose

Replay asks: “Given only evidence legitimately available at cutoff T, what would the named policy have
produced?” It is not a present-day narrative reconstructed with hindsight.

```text
published/effective time ─┐
first observed/available ─┼─► visible at cutoff? ─► frozen system call
relationship validity ───┘                              │
                                                       ▼
later sourced observation ───────────────────────► outcome/calibration
```

## Time vocabulary

| Field | Meaning | Common implementation |
|---|---|---|
| `published_at` | Source-declared publication time | Evidence metadata |
| `occurred_at` / effective date | Time of the external event | Event/catalyst/outcome records |
| `first_seen_at` / `fetched_at` / `observed_at` | When Pyrnova first recorded the information | Evidence/observation/outcome |
| `available_at` | Earliest defensible reasoning availability | Replay records/relationships/profiles |
| `valid_from`, `valid_to` | Interval in which a relationship/watch is valid | Relationship, exposure, watchlist |
| `replay_as_of` / `as_of` | Historical reconstruction cutoff | Replay and read APIs |
| `predicted_at`, `resolve_by` | Frozen prospective call and grade horizon | Prediction |
| `first_relevant_at`, `delivered_at` | Customer-specific relevance and first delivery | Customer Material Change |

Source publication, event occurrence, Pyrnova observation, customer relevance, customer delivery, review,
and outcome can all occur at different times.

## Phase 1 replay behavior

`replay.visible_records` requires a non-empty `available_at` and includes only records at or before
`replay_as_of`. It sorts deterministically by time, source id, and source ref. Missing availability is
excluded. `pipeline.run(replay_as_of=...)` applies the equivalent future-record gate before normalization.

The active policy is `scoring_v1`, with explicit evidence/threshold/mechanism version ids. Replay result
ids hash canonical inputs. Corpus runners operate on tracked JSON fixtures under `examples/replay/` and
can append results to local state. Chain replay reconstructs all source-native signals while each
relationship retains its own first-observed time; disposition transitions are computed only from evidence
visible at each cutoff.

## Frozen predictions and later outcomes

`review.make_prediction` creates a new Prediction snapshot. `outcomes.record_observation` appends a sourced
OutcomeObservation; `resolve_outcome(as_of=...)` excludes future observations and selects among those
visible at the cutoff. It never edits the Prediction.

The runtime enforces:

- no observable `UNKNOWN` row: UNKNOWN is the honest resolver result when nothing is known;
- no loss/capture/terminal result from absence;
- explicit source id/ref and observation time for every recorded outcome;
- evidence strength at least 3 for capture, negative, and terminal labels;
- future outcomes excluded from earlier views.

Customer review state is also append-only and separate. A customer may dismiss a Material Change while
the system threat/opportunity remains intact. A later outcome can append a new customer Material Change
version without altering the earlier assessment snapshot.

## Relationship and customer temporal truth

At event/catalyst time, relationship and exposure validity is checked using `valid_from`/`valid_to`.
Customer context uses the profile version effective at the cutoff and watches active during the cutoff.
`first_relevant_at` is no earlier than both global knowability and the relevant customer configuration.
A watch added now does not create historical relevance.

Investigation pages reconstruct the estate at `as_of`; they do not leak later entities, edges, events, or
outcomes into earlier views.

## Corpora, versioning, and negative controls

Tracked corpora are versioned milestone evidence. Older corpora are intentionally frozen when later
milestones add cases. A scoring change must be evaluated against the full applicable corpus, not a favored
example, and must not silently rewrite expected history.

Negative controls include weak topical joins, future evidence, unrelated entities, lapsed exposure,
immaterial changes, absent outcomes, and other attractive but unsupported paths. A correct zero-output or
REJECT result is valuable evidence.

Replay reports under `docs/replay/` are dated acceptance artifacts. They do not prove current provider
availability, deployed operation, or future performance.

## Phase 1.5 industrial replay research

The integrated `docs/replay/PHASE1_5_INDUSTRIAL_REPLAY_EVIDENCE.md` and
`examples/replay/industrial_phase1_5/` paths contain `industrial_replay_corpus_v1` research. Their status
is evaluation evidence ready with production implementation locked. The fixture validates source
references, cutoffs, frozen categorical calls, outcomes, facility identities, rights fields, hashes of
retained paraphrased spans, and negative controls. Its test intentionally does not import production
pipeline/scoring modules.

Therefore, Phase 1.5 does **not** currently establish:

- governed production acquisition for corporate IR/state economic-development/general filing bodies;
- first-class facility identity and lifecycle grounding;
- industrial event clustering/amendment lineage;
- industrial seller relevance or a production scoring policy;
- an industrial outcome vocabulary or production replay runner;
- customer-facing industrial behavior.

Do not describe or promote this evidence as production implementation without separate execution authority.

## Determinism boundary

Determinism currently covers canonicalized inputs, visibility filtering, scoring policies, several stable
identities, ordering, content hashing, and tracked corpus results. It does not mean external sources never
change or that every local timestamp is already normalized to one timezone representation.

A reproducible replay requires:

1. exact tracked corpus or archived bytes;
2. explicit cutoff and policy version;
3. the same code revision and dependency environment;
4. no fresh network dependency;
5. stable source/native identifiers;
6. retained expected results and negative controls;
7. a dated test/report record.

## Safe extension rules

- Never use a later publication to improve an earlier frozen call.
- Preserve the old prediction and append the new evidence/outcome.
- Distinguish a source amendment from a separate underlying event.
- Make missing availability fail closed.
- Keep customer configuration temporal and tenant-scoped.
- Add a policy/version id rather than mutating the meaning of an existing id.
- Evaluate challengers without promoting them; production policy promotion requires authority.
- Document fixture, archive, live, deployed, and owner-accepted evidence as separate gates.
