# Milestone 8 capability-fit report

_Verified 2026-09-08 from `examples/replay/corpus_m8.json` under `scoring_v1`._

`corpus_m8.json` extends the frozen 43-case M7 corpus with 5 capability-fit cases attaching
evidence-backed company profiles and per-company fit ground truth. M2–M7 corpora are byte-for-byte
unchanged. Fit precision is graded only where per-company `expected_fits` are declared.

## Scoring impact (no `scoring_v1` change)

| Corpus | Cases | STRIKE precision | FPR | FNR |
|---|---:|---:|---:|---:|
| `corpus_m7` (frozen) | 43 | 0.875 | 0.125 | 0.0 |
| `corpus_m8` | 48 | 0.9231 | 0.125 | 0.0 |

The five added cases are all true-positive procurements; STRIKE precision rises (12 true / 1 inherited
false) with no new false positive and FNR still 0. No STRIKE explosion. `scoring_v1` unchanged.

## Fit observability

- Fits evaluated: **12** (all graded). Companies evaluated against a single consequence: up to **4**.
- Posture distribution: PRIME **3**, SUPPORT **2**, TEAM **1**, DEFEND **1**, NO_FIT **5** — all five
  postures exercised.
- Fit precision **1.0**; no-fit precision **1.0**; **false-match rate 0.0**.
- Posture precision overall **1.0** (per-posture PRIME/SUPPORT/TEAM/DEFEND/NO_FIT all 1.0).
- Blocker accuracy **1.0**.
- Capability-match coverage **0.75**; buyer-history coverage **0.5833**; unknown-rate **0.1667**.
- Small-sample warning surfaced and never hidden (12 graded fits).

## Case findings

| Case | Companies → posture |
|---|---|
| `m8-fit-navy-radar-2024` | Coastal Radar → **PRIME** (full capability + prime Navy history + clearance); Antenna Subsystems → **SUPPORT** (capability, sub-only, small scale); Broad Defense Consulting → **NO_FIT** (no capability — broad-sector false match rejected); SecureRadar → **NO_FIT** (`security_clearance_mismatch`). |
| `m8-fit-chips-construction-2023` | Meridian Build → **PRIME** (both required capabilities); Copper Line Electric → **TEAM** (partial capability + partner); Desert Wiring → **SUPPORT** (partial capability, no partner). |
| `m8-fit-radar-recompete-defend-2024` | Incumbent Radar Sustainment → **DEFEND** (incumbent on the recompeted program). |
| `m8-fit-directed-energy-open-2024` | Photon Dynamics → **PRIME**; Unknown Capability Ventures → **NO_FIT** (`insufficient_capability_evidence`, `is_unknown`); Future Optics → **NO_FIT** (capability evidence dated after cutoff, excluded point-in-time). |
| `m8-fit-directed-energy-closed-2023` | Late Beam → **NO_FIT** (`timing_passed` — capable but the window closed). |

## Point-in-time

`Future Optics Corp` has directed-energy capability evidence dated 2025-06 against a 2024-10 cutoff; the
profile built as-of the cutoff has no capabilities, so the fit is NO_FIT/unknown. Future capability
evidence cannot establish an earlier fit; company profiles and contract history are filtered
`available_at <= replay_as_of`.

## Reproduce

```bash
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_m7.json   # frozen baseline
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_m8.json   # +5 true-positive STRIKEs
python -m pyrnova.cli fit-corpus    --corpus examples/replay/corpus_m8.json --verbose
```

## Limitations

- Fit precision/false-match/posture-precision/blocker-accuracy rest on 12 graded fits — directional.
- Fit depends on structured source fields; absent them, fit is UNKNOWN/NO_FIT rather than guessed.
- Company profiles here are synthetic offline fixtures; building profiles from real archived award/SEC
  evidence is deferred. No live API calls were made.
