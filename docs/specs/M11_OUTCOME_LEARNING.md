# Milestone 11 — production opportunity lifecycle + append-only outcome learning

_Status: **CLOSED 2026-09-09** · authority: `01-PROJECT-AUTHORITY.md`, activated by `02-EXECUTION.md`._

## Core question

Once Pyrnova has predicted and scored an opportunity, can it learn from **what actually happened** —
authoritatively, point-in-time, append-only — without ever inferring a loss it did not observe, without
mutating the prediction it made, and without letting outcome learning perturb the frozen production
scorer?

## Design (additive, `pyrnova/outcomes.py`)

- **Authoritative outcome vocabulary (12 labels):** `WON`, `LOST`, `PARTICIPATED`, `NO_BID`,
  `AWARD_TO_OTHER`, `CANCELLED`, `EXPIRED`, `DELAYED`, `PARTIAL_CAPTURE`, `SUBCONTRACT_CAPTURE`,
  `INCUMBENT_RETENTION`, `UNKNOWN`. `UNKNOWN` is the honest default and is **not** a recordable
  observation — it is only ever a *resolved* state.
- **`OutcomeObservation` (append-only, dated, sourced):** every observation carries `observed_at` (the
  point-in-time gate), `source_id`, `source_ref`, `evidence_strength` (1–5), provenance. Capture-positive,
  capture-negative, and terminal-null labels **require** an explicit `source_ref` and
  `evidence_strength >= 3` — they can never be inferred. Deterministic id; `record_observation` is
  idempotent on the `outcome_observations` stream.
- **`resolve_outcome(observations, as_of)`:** filters `observed_at <= as_of` (strict future-outcome
  exclusion), then surfaces the most authoritative knowable label (authority rank, then recency, then
  strength). **No knowable observation → `UNKNOWN`, never a loss.** The result reports
  `future_excluded_count`/`_refs` and carries `loss_inferred_from_absence: false` as a standing invariant.
- **`build_learning_record(prediction, observations, as_of)`:** copies the prediction **verbatim** into
  the ledger (never mutated) and pairs it with the resolved outcome, classifying correctness
  (`CONFIRMED` / `OVERCALLED` / `CORRECT_NEGATIVE` / `INDETERMINATE` / `PENDING`). Correctness is a
  calibration read only — it does **not** feed back into scoring.
- **`evaluate_challenger(...)`:** scores a challenger predictor against the resolved ledger and returns
  precision/recall, but hard-codes `promoted=False` and `production_scoring_version="scoring_v1"`.
  Challengers are **evaluation-only**; `ACTIVE_SCORING_VERSION` stays `scoring_v1`.

## Hard rules (enforced in code)

1. **Never infer loss from absence.** Missing observation → `UNKNOWN`. Negative labels demand a dated,
   sourced observation (`test_negative_outcomes_cannot_be_inferred_without_a_source`).
2. **Strict future-outcome exclusion.** A future award never leaks into a historical reconstruction
   (`test_future_outcome_is_strictly_excluded`).
3. **Predictions preserved.** The ledger snapshots the prediction unchanged
   (`test_prediction_is_preserved_verbatim`).
4. **`scoring_v1` is production; challengers are evaluation-only** (`test_challenger_is_evaluated_but_never_promoted`).

## Corpus and metrics

`corpus_m11.json` **extends** the frozen `corpus_m10.json` (lifecycle chain explicit; M4–M10 byte-for-byte
unchanged) with 13 `outcome_cases`: one per authoritative label, plus an **absence-guard** case
(resolves `UNKNOWN`, never `LOST`) and a **future-outcome-exclusion** case. Metrics are directional
(small-sample warning surfaced): resolution rate 0.8462, capture count 4, win-rate-among-contested
0.6667, `loss_inferred_from_absence` 0, `future_outcomes_excluded` 1. A sample challenger
(`scoring_v2_recompete_bias`) scores precision 0.75 / recall 0.75 over 6 contested cases and is **not**
promoted.

## Acceptance (all hold)

1. All 12 authoritative labels exercised. 2. Absence → `UNKNOWN`, never a loss. 3. Future outcomes
excluded (`future_outcomes_excluded == 1`, `loss_inferred_from_absence == 0`). 4. Predictions preserved
verbatim. 5. Append-only + idempotent observation store. 6. Challenger evaluated but never promoted;
`scoring_v1` production. 7. Frozen M4–M10 corpora unchanged; M9 canonical base still loads (55).
8. Full tests pass (284 passed, 1 skipped). 9. Docs updated. 10. Pushed; `HEAD == origin/main`.

## Limitations (explicit)

- 13 outcome cases, 11 resolved — all metrics directional, not stable rates.
- Outcome observations here are reviewed illustrative lifecycle records (real award refs where known,
  e.g. the Torch W31P4Q21F0038 win); this is a learning-mechanics acceptance, not a large live
  outcome harvest. Real bulk outcome ingestion arrives with source integration (M12).
- `NO_BID` / `PARTICIPATED` / `DELAYED` are open states (`INDETERMINATE` correctness) — they measure
  lifecycle coverage, not capture success.
