# Milestone 9 — real company grounding and production fit calibration

_Status: IN PROGRESS 2026-09-08 · authority: `01-PROJECT-AUTHORITY.md`, activated by `02-EXECUTION.md`._

## Core question

Can Pyrnova build a trustworthy company capability profile from only evidence that was actually
available at a historical cutoff, then correctly determine whether that real company was positioned to
capture a real opportunity **at the time** — without future knowledge, generic sector matching, or AI
guesswork?

M9 replaces M8's synthetic `CompanyProfile` fixtures with real, evidence-backed profiles. The matching
and posture logic is unchanged from M8; what changes is that the profile facts are now real and
point-in-time.

## The hard rule — no future-knowledge profile construction

Every profile fact carries temporal provenance, and a profile as of date X uses only evidence knowable
by X. If a company won an award in 2025, that award cannot build its 2023 profile. This is enforced in
`grounding.profile_as_of`, which filters **capabilities, scale, contract vehicles, buyer agencies, and
contract history** by `available_at <= cutoff`, and verified by a leakage gate in replay.

## Evidence and hierarchy

M9 grounds profiles in **USAspending prime-award history** — official government, public domain,
keyless. Award `Start Date` is used as `available_at` (a small, documented generosity vs. publication
lag). Source hierarchy: official government > official company primary source > authoritative filing >
secondary. SAM, SEC, and capability statements are deferred (see limitations), so certifications,
clearances, contract-vehicle breadth, and teaming access remain **UNKNOWN** — never inferred.

Archived once under `examples/real_evidence/` (Torch Technologies, Modern Technology Solutions), replayed
offline. Live USAspending calls are counted; SAM is untouched (frozen until M2 acceptance).

## Ingestion (`pyrnova/grounding.py`)

- `parse_usaspending_awards(raw, company_name)` → temporally-provenanced facts: `awards`,
  `contract_history`, `capability_records`, `scale`, `vehicles`, `buyer_agencies`. Deterministic; dedup
  by award id; `available_at` = award start date.
- `detect_vehicles(text)` — only explicitly named vehicles (e.g. "GSA OASIS SB"); never inferred.
- `profile_as_of(company_name, parsed, cutoff, ...)` → a point-in-time `CompanyProfile` (reuses
  `company.build_profile`; capabilities via the shared `capabilities.py` normalizer).
- `first_supportable_capability_date(parsed, label)` → earliest date a capability is supportable.

Capability normalization is extended with specific defense-services classes (hardware-in-the-loop
simulation, SETA, missile-defense engineering, modeling & simulation, test & evaluation, specialty
engineering). Additive only — frozen M4–M8 corpora are byte-for-byte unchanged. Broad terms
("engineering support", "technical services") still yield nothing.

## Fit doctrine (unchanged from M8)

Fit is explicit shared-capability-class overlap using the same normalizer for the opportunity
requirement and the company. Forbidden: broad-sector match, agency-only, NAICS-only, keyword-only,
semantic-similarity-only, "company is innovative" reasoning. PRIME requires full capability +
eligibility + credible scale + prior **prime** performance; SUPPORT is partial/subcontract capability;
TEAM is partial capability with teaming partners; DEFEND is incumbency; NO_FIT is an explicit blocker or
insufficient evidence (`is_unknown`). Unknown stays valid.

## Temporal-leakage gate

Each real case may declare a `leakage_probe` (future-dated award refs). `run_fit_replay` asserts none
appear in the as-of profile and reports `temporal_leakage_violations`. This is a hard acceptance gate.

## Calibration (real vs synthetic, never blended)

`summarize_fit_results(results, source="real"|"synthetic")` reports the two populations separately.
Cases tag `profile_source`; M9 cases are `real`, inherited M8 cases are `synthetic`.

## Acceptance and validation

`examples/replay/corpus_m9.json` extends the frozen `corpus_m8.json` with 7 real fit cases. Results are
in `docs/replay/M9_REAL_PROFILE_CALIBRATION.md`.

```bash
python -m pyrnova.cli profile     --company "Torch Technologies" \
    --evidence examples/real_evidence/usaspending_torch.json --as-of 2020-12-31T23:59:59+00:00
python -m pyrnova.cli fit-corpus  --corpus examples/replay/corpus_m9.json --verbose
python -m pyrnova.cli replay-corpus --corpus examples/replay/corpus_m9.json   # scoring_v1 unchanged
```
