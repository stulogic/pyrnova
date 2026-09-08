# Milestone 6 — precursor expansion and inferred-relationship calibration

_Status: IN PROGRESS 2026-09-08 · authority: `01-PROJECT-AUTHORITY.md`, activated by `02-EXECUTION.md`._

## Core question

Can Pyrnova (1) detect meaningful precursor signals earlier in the capital lifecycle, and (2) safely
connect records when authoritative cross-source identifiers are absent — without increasing false
joins, false positives, or speculative causal reasoning?

M5 taught Pyrnova to connect what it sees deterministically. M6 teaches it to reach earlier in the
capital chain and to infer relationships **safely**, keeping structured intelligence out of semantic
guesswork.

## Precursor chain model

M6 keeps the eight-stage backbone and improves support for its earliest stages:

`INTENT → AUTHORIZATION → FUNDING → PROGRAM → MARKET_ENGAGEMENT → PROCUREMENT → AWARD → OUTCOME`

- **INTENT** — a President's Budget request / budget-justification line (pre-enactment).
- **AUTHORIZATION** — enacted authority (authorization/appropriation act line, public law).
- **FUNDING** — appropriated budget authority available to obligate (Treasury Account / Federal
  Account / assistance listing).

These are never collapsed into one generic precursor type. Missing, unknown, contradicted, and
partial chains stay representable; a missing stage is never inferred merely because a later award
exists.

## Budget/appropriation precursor source

`pyrnova/sources/appropriations.py` (registry id `appropriations`) consumes explicitly configured
official budget artifacts, mirroring the acquisition-forecast contract: pure parse over exact bytes,
deterministic source-native identity, `available_at`, exact-byte archival with a sanitized request
fingerprint, malformed-row handling, and OFFLINE default. It emits, for each row, the single most
authoritative structured identifier available as `program_identifier`, preferring
`TAS → Federal Account → CFDA/assistance listing → program element → budget line item`, and retains
every raw id field. It cannot create a candidate or a STRIKE. It has no live discovery: archive once,
replay many.

## Inferred-join doctrine (weighted, explainable, anchored)

`pyrnova/chains.py:score_inferred_join` scores each candidate cross-program pair deterministically.

**Anchors** (authoritative structured identity; at least one is required to be linkable):

- shared explicit program identifier (equal `program_identifier`) — weight 0.45
- matching authoritative entity identity (equal recipient UEI) — weight 0.45
- shared specific program/solicitation number fragment (len ≥ 6, contains a digit) — weight 0.25

**Non-anchor positive factors:** agency match (0.15), program-name similarity (Jaccard-scaled, ≤ 0.15),
funding-amount proximity within 25% (0.10), geography match (0.05).

**Contradiction penalties:** agency conflict (−0.40), temporal impossibility — an earlier-stage
record postdating the later-stage record it supposedly precedes (−0.40), geography conflict (−0.20),
funding divergence ≥ 10× (−0.15).

`confidence = clamp(Σ factors − Σ penalties, 0, 0.95)`. **Without an anchor the confidence is capped at
0.55**, below the acceptance threshold — so agency + topic + chronology + name-similarity can never
combine into an accepted join.

**Dispositions** (acceptance threshold frozen at 0.60, per D-020):

- anchored and `confidence ≥ 0.60` → **accept** as `join_method=inferred_strong_attribute`, retaining
  every factor, penalty, and anchor in the rationale plus evidence IDs and `first_observed_at`.
- anchored and `0.45 ≤ confidence < 0.60` → **defer** to the human review queue (a `DeferredJoin`).
- otherwise → **reject** (`inference_contradiction` when penalties dominate, `inference_below_threshold`
  when anchored but too weak; un-anchored pairs keep the M5 categorical `agency_name_only` /
  `topic_overlap_only` reasons).

The canonical shared-identifier + agency case scores exactly 0.45 + 0.15 = 0.60, so all M5 inferred
tests are preserved unchanged. Deterministic program-key and native-identifier joins remain strictly
stronger and are resolved first; inference only runs on otherwise-unlinked cross-program pairs.

## Human review queue

`pyrnova/review_queue.py` (CLI `join-review list|decide`) persists deferred inferred joins to durable
append-only state (idempotent per relationship id), each carrying its pre-review confidence and prior
automated recommendation. A reviewer records `ACCEPT_JOIN | REJECT_JOIN | WATCH` with reviewer,
timestamp, and reason; the prior automated state is always retained. `override_rate` reports how often
reviewers disagree with the automated recommendation. This data is future calibration/training
evidence — no frontend, CLI/state only.

## Entity-level predicates

`resolve_entity_relationships` establishes `AWARDED_TO`, `SUBSIDIARY_OF`, and `LOCATED_AT` only from
authoritative structured fields (recipient/parent UEI, place of performance), never from topic. Each
edge is evidence-backed, temporal (`first_observed_at`), deterministic, and carries confidence 0.95.

## Scoring discipline

`scoring_v1` is unchanged. Inference, deferral, entity predicates, and precursor coverage enrich
evidence, timing, provenance, and explanation only; none creates a candidate or promotes a disposition
on its own. Any scoring change still requires a full-corpus comparison, aggregate improvement, no
unacceptable regression, and Opus approval.

## Threshold governance

The 0.60 acceptance threshold is frozen. `evaluate_inferred_threshold` sweeps candidate thresholds
over every anchored candidate in the corpus and reports accepts/precision/false-joins/deferrals; the
result explicitly recommends **keep 0.60** while the reviewed sample is small, and never hides the
small-sample warning.

## Acceptance and validation

`examples/replay/corpus_m6.json` extends the frozen `corpus_m5.json` with eight reviewed cases. Results
are in `docs/replay/M6_INFERENCE_CALIBRATION.md`.

```bash
python -m pyrnova.cli replay-corpus      --corpus examples/replay/corpus_m6.json   # scoring (fnr 0, precision 0.80)
python -m pyrnova.cli chain-corpus       --corpus examples/replay/corpus_m6.json   # inferred/deferred/entity metrics
python -m pyrnova.cli inferred-threshold --corpus examples/replay/corpus_m6.json   # threshold sweep (keep 0.60)
python -m pyrnova.cli join-review list    --corpus examples/replay/corpus_m6.json   # enqueue + list deferred joins
```
