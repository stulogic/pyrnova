# Milestone 6 inference-calibration report

_Verified 2026-09-08 from `examples/replay/corpus_m6.json` under `scoring_v1`._

`corpus_m6.json` extends the frozen 27-case M5 corpus with eight reviewed cases that exercise budget
precursor coverage and inferred-relationship calibration. M2–M5 corpora are byte-for-byte unchanged.

## Scoring impact (no `scoring_v1` change)

| Corpus | Cases | STRIKE precision | WATCH conversion | FPR | FNR | Median lead |
|---|---:|---:|---:|---:|---:|---:|
| `corpus_m5` (frozen) | 27 | 0.75 | 0.875 | 0.25 | 0.0 | 297.5 |
| `corpus_m6` | 35 | 0.80 | 0.8889 | 0.1429 | 0.0 | 213 |

The one added STRIKE is the appropriation-anchored Air Force radar lifecycle — a true positive with an
appropriation, a forecast, a matching SAM solicitation, and the award all sharing one program key. No
false positive was added; precision rises and FPR falls from correctly adjudicated cases. The
corpus-wide median lead time drops only because the corpus now contains more short-horizon negative
and ambiguous cases, not because any chain got shorter. `scoring_v1` was not modified.

## Inferred-join calibration

Across the 15 chain-carrying cases (7 from M5, 8 from M6):

- Accepted inferred joins: **2**, both ground-truth true positives → **inferred precision 1.0**,
  **inferred false-join rate 0.0**.
- Deferred joins (review band `[0.45, 0.60)`): **1** (the GSA number-fragment case).
- Rejected weak joins: **≥4** — cross-agency shared identifier (agency conflict), authorization that
  postdates its procurement (temporal impossibility), same-agency-plus-topic only, and the inherited
  M5 HHS/DHS topic-only false join.
- Deterministic relationships: 10; inferred: 2; contradictions/corroborations: 0.
- **Small-sample warning is emitted and never hidden:** precision/false-join rates rest on 2 accepted
  and 5 total anchored candidates — directional, not stable.

### Case findings

| Case | Type | Result |
|---|---|---|
| `m6-inferred-cfda-appropriation-doe-2022` | true inferred (shared assistance-listing 81.086) | Accepted at confidence 0.60; stays WATCH (funding, not executable demand). |
| `m6-inferred-entity-uei-navy-2023` | true inferred (matching recipient UEI) | Accepted at 0.60; exercises `AWARDED_TO` / `SUBSIDIARY_OF` / `LOCATED_AT`; WATCH. |
| `m6-false-cfda-cross-agency-2023` | tempting false | Rejected: shared identifier invalidated by agency conflict. TRUE_NEGATIVE. |
| `m6-false-temporal-impossible-navy-2023` | tempting false | Rejected: authorization postdates the procurement it would precede. TRUE_NEGATIVE. |
| `m6-false-agency-topic-only-interior-2024` | tempting false | Rejected `agency_name_only`: no structured anchor. TRUE_NEGATIVE. |
| `m6-defer-fragment-ambiguous-gsa-2024` | ambiguous | Deferred to review at 0.49 (fragment anchor only). AMBIGUOUS. |
| `m6-precursor-appropriation-chain-airforce-2021` | precursor lifecycle | Deterministic program-key chain; WATCH→STRIKE; **1053-day** lead from appropriation to award. |
| `m6-partial-authorization-dhs-2024` | partial | Single AUTHORIZATION stage; WATCH; no downstream stage invented. |

## Precursor lead-time gain

The appropriation-anchored chain is first observable at the FY21 appropriation (2021-03-15) and
resolves at the award (2024-02-01): a **1053-day** lead time, versus the M5 flagship's 434 days from a
procurement forecast. Reaching the appropriation stage is what buys the additional ~619 days.

## Entity predicates

`AWARDED_TO`, `SUBSIDIARY_OF`, and `LOCATED_AT` are each exercised from authoritative structured fields
(recipient UEI, parent UEI, place of performance) on real award records — 6 entity relationships
across the corpus. No entity edge is inferred from topic.

## Human review

The single deferred join was enqueued and adjudicated end-to-end via `join-review`; the reviewer
overrode the DEFER recommendation to REJECT_JOIN, giving a demonstrated override on the (currently
tiny) review set. The queue retains pre-review confidence and prior automated state as calibration
evidence.

## Threshold evaluation

`inferred-threshold` sweeps `{0.45 … 0.70}` over the 5 anchored candidates. Precision is 1.0 at every
threshold from 0.45 through 0.65; lowering to 0.45 would auto-accept the ambiguous fragment case that
should be reviewed, and raising past 0.60 begins dropping true joins. **Recommendation: keep the
threshold at 0.60** — the reviewed sample is far too small (5 anchored candidates) to justify a move.

## Reproduce

```bash
python -m pyrnova.cli replay-corpus      --corpus examples/replay/corpus_m5.json   # frozen baseline
python -m pyrnova.cli replay-corpus      --corpus examples/replay/corpus_m6.json   # +1 true-positive STRIKE
python -m pyrnova.cli chain-corpus       --corpus examples/replay/corpus_m6.json
python -m pyrnova.cli inferred-threshold --corpus examples/replay/corpus_m6.json
```

## Limitations

- Inferred precision and false-join rate rest on very few accepted joins; treat as directional.
- The override rate is a live metric, meaningful only once several real reviews accumulate.
- The `appropriations` adapter has been exercised only on synthetic offline fixtures; no live budget
  artifact has been archived, and each agency artifact still needs a reviewed column mapping.
- Entity predicates depend on structured UEI/place fields being present; cross-source entity
  resolution across name variants is out of scope.
