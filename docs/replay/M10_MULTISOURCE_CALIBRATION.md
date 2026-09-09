# Milestone 10 multi-source real-profile fit calibration report

_Verified 2026-09-09 from `examples/replay/corpus_m10.json` (8 fit cases) under a frozen `scoring_v1` and
an unchanged `fit.py` (`capability_fit_v1`). Offline: every fixture is archived under
`examples/real_evidence/`; no live calls were made in this acceptance run._

`corpus_m10.json` **extends** the frozen 55-case M9 corpus with 8 REAL, MULTI-SOURCE company fit cases.
Each case attaches a constructed opportunity probe to a company profile built by
`multisource.build_multisource_profile` from **multiple archived real source families**, filtered
strictly point-in-time (`available_at <= replay_as_of`). Multi-source-real metrics are reported
**separately** from synthetic M8 fixtures and single-family real M9 profiles — never blended.

## Real companies grounded (multi-source)

| Company | Source families used | Material evidence beyond USAspending prime |
|---|---|---|
| Science Applications International Corp (SAIC, public prime) | usaspending_prime + **sec_edgar** + usaspending_recipient | SEC submissions: VA geography, former name "SAIC Gemini", sector; recipient eligibility (other-than-small-business), UEI |
| Torch Technologies (private ESOP) | usaspending_prime + **usaspending_subawards** + usaspending_recipient | Repeat prime↔subrecipient partner edges (authoritative teaming evidence); recipient eligibility observed 2023-01-01 |
| Modern Technology Solutions (inherited from M9) | usaspending_prime | (single family; M9 real bucket) |

SAIC is the added public prime that satisfies gate #2/#5 (≥2 families; ≥1 real profile gains material
evidence beyond USAspending prime) via keyless SEC EDGAR. Torch gains a real third family
(USAspending sub-awards) that populates authoritative partner edges. Both are grounded from bytes
already on disk.

## Cases (8, all `profile_source=multisource_real`)

| Case | As-of | Posture | Fit | What it proves |
|---|---|---|---|---|
| m10-saic-prime-hwil-missile | 2026-09-09 | PRIME | ✓ | 3-family real PRIME (prime + SEC + recipient) |
| m10-torch-team-hwil-te | 2022-06-01 | TEAM | ✓ | TEAM fires only from an authoritative repeat sub-award partner edge |
| m10-saic-support-false-team | 2026-09-09 | SUPPORT | ✓ | **false tempting TEAM** → SUPPORT (no authoritative edge → never a manufactured TEAM) |
| m10-torch-defend-seta | 2022-06-01 | DEFEND | ✓ | real incumbent SETA recompete → retention, not new capture |
| m10-torch-nofit-setaside | 2026-09-09 | NO_FIT | ✗ | capable firm blocked by **real eligibility** (`insufficient_certification`) |
| m10-saic-nofit-broadsector | 2026-09-09 | NO_FIT | ✗ | broad-sector rejection (`no_required_capability`) |
| m10-torch-leakage-2017 | 2017-06-01 | NO_FIT | ✗ | point-in-time gate: future HWIL + 2023/24 sub-awards excluded |
| m10-torch-unknown-2013 | 2013-01-01 | NO_FIT | ✗ | insufficient early evidence → UNKNOWN/NO_FIT, never manufactured |

## Multi-source-real fit metrics (separate bucket, directional)

| Metric | Value |
|---|---:|
| Fit cases / graded fits | 8 / 8 |
| Fit precision | 1.0 |
| No-fit precision | 1.0 |
| False-match rate | 0.0 |
| Posture precision (overall) | 1.0 |
| Per-posture precision (PRIME/SUPPORT/TEAM/DEFEND/NO_FIT) | 1.0 / 1.0 / 1.0 / 1.0 / 1.0 |
| Blocker accuracy | 1.0 |
| Capability-match coverage | 0.875 |
| Buyer-history coverage | 1.0 |
| Unknown rate | 0.125 |
| **Temporal leakage violations** | **0** |

Posture distribution: PRIME 1 / SUPPORT 1 / TEAM 1 / DEFEND 1 / NO_FIT 4. A small-sample warning
(`graded_fits < 20`) is surfaced, never hidden.

## Multi-source grounding observability (separate bucket)

| Metric | Value |
|---|---:|
| Profiles evaluated | 8 |
| Multi-source profiles (≥2 families) | 8 |
| Distinct source families | sec_edgar, usaspending_prime, usaspending_recipient, usaspending_subawards |
| Profile source diversity (avg families/profile) | 2.5 |
| Max source families on one profile | 3 |
| Eligibility coverage | 0.5 |
| Subcontract coverage | 0.625 |
| Profiles with an authoritative partner edge | 5 |
| Temporal leakage violations | 0 |

## `scoring_v1` and frozen corpora

`scoring_v1` is **unchanged** in M10; `fit.py` is unchanged. The M10 cases exercise only the fit engine
(real profiles vs a constructed opportunity probe) and are deliberately **not** scored as a
scoring-corpus — their `expected_disposition` encodes the fit-consistent intent, not a `scoring_v1`
claim. `scoring_v1` stability is proven over the frozen M9 corpus: 55 cases, false-negative rate 0.0,
one inherited false strike (no new false positive), no STRIKE explosion. Frozen M4–M9 corpora are
byte-for-byte unchanged (`corpus_m10.json` `extends` `corpus_m9.json` additively).

## Point-in-time truth (hard gate)

Every SourceFact, sub-award, SEC filing, and partner edge is filtered `available_at <= replay_as_of`.
The leakage probe (`m10-torch-leakage-2017`) declares future sub-award ids (`P010277106`, `PO-0011221`)
and asserts they never appear in the 2017 profile: `temporal_leakage_violations == 0`. Torch partner
edges grow monotonically forward in time (absent 2013 → authoritative by 2020), and recipient
eligibility is unknown before its 2023-01-01 observation.

## Limitations (explicit, never hidden)

- 3 real companies, 8 graded multi-source fits — all metrics are **directional**, not stable rates.
- The opportunity records are constructed probes attached to real profiles; the *grounding* is real,
  the opportunity is illustrative. These cases are not `scoring_v1` cases.
- SAM entity certifications/vehicle eligibility were **not** ingested in this offline acceptance;
  eligibility is grounded from USAspending recipient business categories only. SAM-sourced
  set-asides/vehicle eligibility remain documented-insufficient, not fabricated.
- Sub-award teaming evidence is USAspending sub-awards only; a single occurrence is treated as weak —
  TEAM requires a repeat relationship (or an archived official announcement, none ingested here).
- SEC grounding applies only to public primes (SAIC); Torch/MTSI are privately held (no SEC filings).
