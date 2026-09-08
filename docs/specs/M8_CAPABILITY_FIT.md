# Milestone 8 — capability fit and opportunity personalization

_Status: IN PROGRESS 2026-09-08 · authority: `01-PROJECT-AUTHORITY.md`, activated by `02-EXECUTION.md`._

## Core question

Given a validated `CommercialConsequence`, does a *specific company* have a credible, evidence-backed
path to capture it — and in what capture posture? The answer must be explainable from retained
evidence; unknown stays unknown.

    EVENTS -> CATALYST -> CONSEQUENCE -> **CAPABILITY FIT (per company)** -> capture posture

## Personalization doctrine (the hard rule)

Fit is based on explicit capability/evidence overlap. **Forbidden:** agency-name-only fit, NAICS-only
fit, keyword-overlap-only fit, and AI-semantic-similarity as the sole basis of fit. A weak signal is
not promoted because a company operates in the same broad sector. "Company A works in defense, so this
seems like a fit" is not a fit.

This is enforced structurally: the SAME normalizer (`capabilities.py`) extracts both the consequence's
required capability classes and the company's capabilities, so a match is a shared *specific*
capability label — and broad labels (technology, consulting, services, manufacturing…) are rejected at
the source, so they can never form a match.

## Company capability profile (`pyrnova/company.py`, `CompanyProfile`)

A durable, source-linked profile distinct from the customer relevance profile in `match.py` (which is a
`scoring_v1` input and is left untouched). Each `CapabilityEvidence` carries a normalized label,
confidence, `source_id`/`source_ref`, `raw_phrase`, and `available_at`. `build_profile` /
`profile_from_dict` filter both capability evidence and contract history strictly point-in-time
(`available_at <= as_of`), so future capability evidence and future awards cannot leak into an earlier
fit. `company_id` is deterministic from the canonicalized name.

## Fit dimensions (`pyrnova/fit.py`)

Nine dimensions, each POSITIVE / NEGATIVE / UNKNOWN with confidence, evidence, and basis — never forced
to a neutral value:

CAPABILITY_FIT (decisive), BUYER_RELEVANCE, GEOGRAPHY, CERTIFICATION, SECURITY, SCALE, TIMING,
INCUMBENT_POSITION, TEAMING_POTENTIAL.

Requirements (required certifications, clearance, geographic restriction, contract vehicle, incumbency,
timing) are read only from explicit record fields — never inferred.

## Negative fit / falsification

Structured `FitBlocker`s with a code and a `fatal` flag. **Fatal** blockers forbid any fit (NO_FIT):
`no_required_capability`, `insufficient_certification`, `security_clearance_mismatch`,
`geographic_exclusion`, `timing_passed`, `historically_failed_capability`,
`explicit_source_contradiction`. **Soft** blockers forbid PRIME but permit a lesser posture, or mark an
unknown that cannot establish a credible path: `insufficient_capability_evidence`, `scale_mismatch`,
`wrong_contract_vehicle`, `unsupported_team_dependence`. A blocker is never a silent confidence drop.

## Capture posture

| Posture | Meaning |
|---|---|
| PRIME | full capability, eligible, credible scale, and prior **prime** performance → can pursue as lead |
| SUPPORT | capability fits a subcontract/supplier or downstream role |
| TEAM | partial capability plus known teaming partners |
| DEFEND | company is the incumbent — retention/defense, not new capture |
| NO_FIT | evidence says do not pursue, or insufficient evidence (`is_unknown`) |

Unknown/insufficient evidence is NO_FIT with `is_unknown=true` and low confidence — never PRIME. A
NAICS/agency match as a subcontractor is a support signal, not a prime signal.

## Fit ≠ opportunity score

Fit confidence measures a company's capture path, not opportunity quality. It is kept strictly separate
from `scoring_v1`, opportunity attractiveness, evidence confidence, and consequence confidence. A strong
opportunity can be a poor fit; a strong fit can sit on a weak opportunity. This module never changes
scoring.

## Human review

A lightweight fit review queue (`enqueue_fit_review` / `pending_fit_reviews` / `adjudicate_fit`) reuses
`StateStore`: ACCEPT_FIT / REJECT_FIT / DEFER, retaining the automated posture and pre-review confidence
as calibration evidence. It reuses the existing adjudication pattern rather than a new system.

## Acceptance and validation

`examples/replay/corpus_m8.json` extends the frozen `corpus_m7.json` with fit cases. Each attaches
evidence-backed company profiles and per-company `expected_fits` (posture, fit/no-fit, decisive
blocker), so fit precision, posture precision, and false-match rate are graded only where per-company
fit ground truth exists. Company profiles are built as-of the replay cutoff. Results are in
`docs/replay/M8_FIT_REPORT.md`.

```bash
python -m pyrnova.cli fit         --case <case.json>
python -m pyrnova.cli fit-corpus  --corpus examples/replay/corpus_m8.json --verbose
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_m8.json   # scoring_v1 unchanged
```
