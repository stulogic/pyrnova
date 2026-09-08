# Milestone 5 — cross-source intelligence and capital-chain resolution

_Status: CLOSED 2026-09-08 · authority: `01-PROJECT-AUTHORITY.md`. Superseded for active work by
`docs/specs/M6_PRECURSOR_AND_INFERENCE.md`; the inferred path described here as flat-0.60 was refined
into a weighted, anchored model in M6 (see D-020)._

## Core question

Can Pyrnova determine that apparently separate signals from different sources are actually stages of
the same economic event, capital program, procurement chain, or commercial opportunity — without
sacrificing evidence discipline?

M4 taught Pyrnova to see more. M5 teaches it to connect what it sees.

## What M5 adds

- **Capital-chain resolution** (`pyrnova/chains.py`): typed, temporal, evidence-backed relationships
  between source-native `ProgramSignal`s, with a strict join hierarchy and explicit rejection of weak
  matches.
- **Opportunity evolution** (`pyrnova/transitions.py`): a point-in-time history of disposition changes
  and the evidence that caused each one, derived from the existing scoring policy.
- **Temporal relationships**: every edge records when it first became knowable, so replay and
  lead-time measurement remain honest.
- **Chain-level observability metrics** and a small, high-quality chain replay corpus.

M5 does not build a general ontology, does not add sources for their own sake, and does not change
`scoring_v1`.

## Canonical objects (reused, not multiplied)

M5 uses the existing model. The only additions are temporal/confidence fields on `Relationship` and a
new `OpportunityTransition`, both mirrored in `db/schema.sql`.

- `Entity`, `Event`, `Evidence`, `Opportunity`, `ProgramSignal`, `ProgramChain` — unchanged.
- `Relationship` gains `join_method`, `confidence`, `rationale`, `first_observed_at`, `available_at`,
  `valid_from`, `valid_to`. These serve a concrete M5 need: answering "when could we first have known
  this relationship?".
- `OpportunityTransition` records one evidence-caused disposition change.

## Relationship vocabulary (only what the data justifies)

Stage-adjacent, same-program edges:

| Precursor → successor | Predicate |
|---|---|
| AUTHORIZATION → FUNDING | `AUTHORIZES` |
| FUNDING → PROGRAM / MARKET_ENGAGEMENT / PROCUREMENT | `FUNDS` |
| PROGRAM → MARKET_ENGAGEMENT / PROCUREMENT | `IMPLEMENTS` |
| any other consecutive occupied stages | `PRECEDES` (temporal backbone) |

Plus `CORROBORATES` (independent sources on the same program+stage) and `CONTRADICTS` (a later
same-program record that reverses an earlier one: cancellation, withdrawal, rescission). Entity-linking
predicates (`AWARDED_TO`, `SUBSIDIARY_OF`, `LOCATED_AT`) are deferred to `05-BACKLOG.md` until a case
requires them.

## Join doctrine (strongest first)

1. `deterministic_program_key` — signals carry the same explicit `program_key`. Confidence 0.95.
2. `deterministic_native_id` — one signal's `downstream_refs` contains another's source-native
   identifier (e.g. forecast → SAM solicitation → USAspending award). Confidence 0.95.
3. `inferred_strong_attribute` — no shared key, but an **explicit authoritative program identifier**
   (e.g. a CFDA number) is equal on both signals and the agency matches. Confidence 0.60, with
   rationale and evidence retained.

Everything weaker is **rejected, not linked**, and counted: agency-name-only, topic-overlap-only, and
chronological-proximity-only candidates are recorded as `RejectedJoin`s. Generic organizational words
("Department", "Office", …) and bare years never establish identity.

## Temporal requirement

A relationship becomes knowable only when its later endpoint is observed; `first_observed_at` is the
maximum of the two endpoints' `available_at`. Point-in-time replay filters signals by cutoff.
Chain *reconstruction* is explicitly retrospective (it links all known stages), but each edge carries
its own knowable-at time, and transition derivation never sees evidence beyond a given cutoff.

## Chain-level confidence (simple and explainable)

Not a sum. Starts from the weakest evidence-backed link, then:

- caps a single-source chain at 0.70 (a source cannot corroborate itself across stages);
- halves confidence if any edge runs backward in knowable time;
- caps a contradicted chain at 0.30.

Each factor is reported in a `basis` list. If richer chain-confidence modeling is later justified, the
per-relationship confidence remains the durable primitive.

## Opportunity evolution

`derive_transitions` replays the active scoring policy at each successive cutoff where new evidence
becomes visible and records each disposition change with its cause (stage, source, time,
scoring version). It reuses `run_replay`, so transitions are consistent with `scoring_v1` by
construction and never fabricate an unsupported promotion. This supports statements such as: "First
observed 434 days before award; promoted to WATCH after market engagement; promoted to STRIKE after
the procurement solicitation."

## Scoring discipline

`scoring_v1` is unchanged. Chain resolution enriches evidence, timing, provenance, and explanation; it
never creates a candidate or promotes a disposition on its own. Any future scoring change still
requires a full-corpus comparison, aggregate improvement, no unacceptable regression, and Opus
approval.

## Acceptance and validation

`examples/replay/corpus_m5.json` extends the frozen `corpus_m4.json` with four reviewed chain cases:
a public-sector forecast→solicitation→award lifecycle, a grant→downstream-spend chain, a deliberately
tempting false join that must be rejected, and an unresolved partial chain. Results are in
`docs/replay/M5_CHAIN_RESOLUTION.md`.

```bash
python -m pyrnova.cli chain-corpus --corpus examples/replay/corpus_m5.json
python -m pyrnova.cli chain-resolve --case <case.json>
```
