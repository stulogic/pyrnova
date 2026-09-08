# Milestone 9 real-profile fit calibration report

_Verified 2026-09-08 from `examples/replay/corpus_m9.json` under `scoring_v1`._

`corpus_m9.json` extends the frozen 48-case M8 corpus with 7 real fit cases. Company profiles are built
from real archived USAspending award evidence (`examples/real_evidence/`), filtered strictly
point-in-time. Real-profile metrics are reported **separately** from synthetic M8 fixtures.

## Real companies grounded

| Company | Source evidence | Domain (real) |
|---|---|---|
| Torch Technologies Inc | 28 archived USAspending prime awards (2008–2024) | Army AMCOM HWIL simulation, missile systems engineering, SETA; GSA OASIS SB vehicle; Air Force TMAS |
| Modern Technology Solutions Inc | 30 archived USAspending prime awards (2009–2025) | MDA specialty engineering, GSA/FAS engineering support, SETA |

## Point-in-time profile evolution (Torch)

| As of | Capabilities | Max contract | Contracts |
|---|---|---:|---:|
| 2010-12-31 | (none — only broad early "SERVICES") | $111.6M | 3 |
| 2018-12-31 | systems_engineering_technical_assistance | $575.3M | 14 |
| 2020-12-31 | systems_engineering_technical_assistance | $575.3M | 16 |
| 2024-12-31 | + hardware_in_the_loop_simulation, specialty_engineering | $623.3M | 28 |

The 2021 $623M HWIL award and the HWIL capability do **not** appear before 2021; scale and vehicles are
filtered point-in-time. First-supportable dates: SETA 2018-05-23, HWIL 2021-01-15.

## Real-profile fit metrics (separate from synthetic)

| Metric | Real (M9) | Synthetic (M8) |
|---|---:|---:|
| Graded fits | 7 | 12 |
| Fit precision | 1.0 | 1.0 |
| No-fit precision | 1.0 | — |
| False-match rate | 0.0 | 0.0 |
| Posture precision | 1.0 | 1.0 |
| Capability coverage | 0.857 | — |
| Buyer-history coverage | 0.714 | — |
| Unknown rate | 0.143 | — |
| **Temporal leakage violations** | **0** | — |

Real posture distribution: PRIME 3, SUPPORT 1, DEFEND 1, NO_FIT 2, TEAM 0 (deferred). All on a
deliberately tiny sample — directional, not stable; the small-sample warning is surfaced.

## Case findings

| Case | Cutoff | Company → posture | Basis |
|---|---|---|---|
| `m9-torch-army-seta-prime-2020` | 2020-12-31 | Torch → **PRIME** | prior Army SETA + prime history; 2021 HWIL award excluded (leakage probe) |
| `m9-torch-radar-hardware-nofit-2021` | 2021-06-30 | Torch → **NO_FIT** | real defense firm, no radar-manufacturing capability — broad-sector match rejected |
| `m9-torch-weapons-seta-defend-2023` | 2023-02-15 | Torch → **DEFEND** | real incumbency (2023 award is a follow-on to Torch's own W31P4Q19FC003) |
| `m9-mtsi-mda-specialty-prime-2019` | 2019-06-30 | MTSI → **PRIME** | 2017 MDA specialty-engineering prime award knowable by 2019 |
| `m9-mtsi-fas-leakage-2021` | 2021-06-30 | MTSI → **PRIME** | FAS prime + specialty engineering; 2024/2025 awards excluded (leakage probe) |
| `m9-mtsi-early-unknown-2010` | 2010-12-31 | MTSI → **NO_FIT** (is_unknown) | only broad early evidence — insufficient to classify |
| `m9-mtsi-hwil-support-2020` | 2020-12-31 | MTSI → **SUPPORT** | partial capability (specialty engineering, not HWIL) |

## Leakage verification

Torch profile as of 2020 excludes W31P4Q21F0038/W31P4Q21F0052 (2021). MTSI profile as of 2021 excludes
47QFMA24F0023 (2024 Digital Bloodhound), 47QFSA25F0011 (2025 ARCWERX ARTEMIS), HQ086024F0005 (2024).
`temporal_leakage_violations = 0` across the corpus.

## Scoring impact (no `scoring_v1` change)

55 cases, STRIKE precision 0.9412 (16 true / 1 inherited false), WATCH conversion 0.8571, FPR 0.125,
FNR 0.0, no STRIKE explosion. Frozen M4–M8 baselines byte-for-byte unchanged.

## Reproduce

```bash
python -m pyrnova.cli fit-corpus    --corpus examples/replay/corpus_m9.json --verbose
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_m9.json
python -m pyrnova.cli profile --company "Torch Technologies" \
    --evidence examples/real_evidence/usaspending_torch.json --as-of 2020-12-31T23:59:59+00:00
```

## Limitations

- 2 real companies, 7 graded real fits — directional only.
- Evidence is USAspending prime awards only; SAM/SEC/capability statements not ingested, so
  certifications, clearances, contract-vehicle breadth, and teaming access are UNKNOWN (never inferred).
- Public award data cannot prove subcontract/support activity — absence of a public award is not proof
  of non-participation (ambiguity preserved).
- TEAM is not exercised for real profiles (public data does not reveal teaming agreements).
- `available_at` = award start date; true knowability is slightly later (USAspending publication lag).
- 4 live USAspending calls (keyless, public domain, archived); no SAM calls.
