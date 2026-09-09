# Milestone 10 — multi-source company intelligence + subcontract/teaming resolution

_Status: **CLOSED 2026-09-09** · authority: `01-PROJECT-AUTHORITY.md`, activated by `02-EXECUTION.md`._

> **Closed offline from archived evidence.** M10 grounds real company profiles from ≥2 authoritative
> source families (SAIC: USAspending prime + SEC EDGAR + USAspending recipient; Torch: USAspending
> prime + sub-awards + recipient), exercises PRIME/SUPPORT/TEAM/DEFEND/NO_FIT on real evidence, rejects
> a false tempting TEAM, blocks on real eligibility, and holds the point-in-time gate at
> `temporal_leakage_violations == 0`. `fit.py` and `scoring_v1` unchanged; frozen M4–M9 corpora
> byte-for-byte unchanged. Metrics and the 21-point gate result are in
> `docs/replay/M10_MULTISOURCE_CALIBRATION.md`. The original blocker note below is retained for history.

> **Execution precondition (hard).** M10's defining requirement is real, multi-source company grounding
> (≥2 source families, material evidence beyond USAspending prime history). That requires acquiring
> **new real archived evidence** from at least one keyless external source (SEC EDGAR and/or the
> USAspending award-detail / recipient / sub-award endpoints), and ideally live SAM entity data. In the
> execution environment where this spec was authored, **all external data hosts are blocked by the
> organization egress policy** (`data.sec.gov`, `api.usaspending.gov` return 403 CONNECT policy denials;
> only Anthropic APIs and package registries are allowed), and **no `SAM_API_KEY` is provisioned**.
> M10 therefore cannot begin real grounding here. See `06-HISTORY.md` (M10 blocker) and the
> "Environmental preconditions" section below. This document is the complete plan so a network-enabled
> session can execute it with minimal re-reasoning; **do not fabricate evidence or weaken the acceptance
> gates to simulate progress.**

## Core question

Can Pyrnova build richer real company profiles from multiple authoritative sources and correctly
distinguish direct, downstream, teaming, incumbent, blocked, and uncertain capture positions —
**without inventing company relationships** — while preserving point-in-time truth and a frozen
`scoring_v1`?

M10 extends M9. M9 grounded real profiles in a single family (USAspending prime awards). M10 adds a
second (and ideally third) authoritative family and exercises SUPPORT and TEAM on real evidence.

## The architectural finding that shapes M10

`pyrnova/fit.py` (M8, unchanged) **already reads every field M10 needs**:

| Fit dimension / blocker | Profile field it reads | M10 evidence that populates it |
|---|---|---|
| CERTIFICATION | `profile.certifications` | SAM set-asides/certs; USAspending recipient business categories |
| SECURITY | `profile.clearances` | official/primary only (never inferred) — likely stays UNKNOWN |
| GEOGRAPHY | `profile.geography`, `profile.facilities` | SEC facilities/segments; SAM registered address |
| SCALE | `profile.scale.max_contract_usd` | USAspending (kept); SEC revenue as observability only |
| INCUMBENT_POSITION | `contract_history[].program_key`, `meta.incumbent_of` | USAspending program links |
| TEAMING_POTENTIAL → TEAM | `profile.partners` (with `matched_partial`) | **real sub-award prime↔subrecipient edges** |
| wrong_contract_vehicle | `meta.contract_vehicles` | USAspending (kept); SAM vehicle eligibility |
| SUPPORT | `matched_partial`, sub-role `contract_history` | sub-award subrecipient rows |

**Consequence: M10 is overwhelmingly additive grounding + data + metrics. `fit.py` and `scoring_v1`
must not change.** No new posture logic is required; the postures already exist and are exercised the
moment the profile carries real multi-source evidence. This is the single most important constraint for
keeping M10 safe.

## Source hierarchy (narrow, material-only)

Retain a fact only if it could materially alter fit posture, blocker status, confidence, or
explanation. Priority when sources conflict:

1. **SAM.gov** — entity registration, aliases/UEI, NAICS, set-aside/eligibility, supported
   certifications, entity status, explicit vehicle eligibility. (Requires `SAM_API_KEY`.) Do **not**
   infer security clearances from SAM.
2. **USAspending** — prime award history (have), plus award-detail/recipient business categories,
   recipient UEI/location, and **sub-awards** (keyless; new endpoints).
3. **SEC EDGAR** — for public companies only: business segments, facilities, subsidiaries, operational
   geography, scale, major customers, material capability descriptions, capex footprint (keyless).
   Torch and MTSI are privately held (ESOP), so SEC applies only to added public primes.
4. **Official company primary sources** — narrow capability statements resolving a specific gap;
   explicit technical claims only, never marketing. Archive once, replay many.
5. **Official contracting/agency announcements** — teaming/JV/award announcements.

No broad crawling. No paid data.

## Evidence model — `SourceFact` (new, additive)

Add a `pyrnova/multisource.py` defining a `SourceFact` and a point-in-time merger. Every fact retains:
`fact_type`, `value`, `source_id`, `source_ref` (native id/URL), `available_at`, `evidence_strength`
(the existing five-level scale), `confidence`, `provenance`. The merger filters `available_at <= cutoff`
(same gate as `company.build_profile` / `grounding.profile_as_of`) and writes into the **existing**
`CompanyProfile` fields (`certifications`, `geography`, `facilities`, `partners`, `contract_history`,
`scale`) plus `meta["source_facts"]` and `meta["source_families"]` for observability. The merger never
overwrites a higher-authority fact with a lower one; conflicts are recorded, not silently resolved.

Parsers (new, additive, delegatable — each self-contained, no imports from fit/replay/scoring):
- `grounding_sam.py` — SAM entity JSON → SourceFacts (identity, aliases, NAICS, set-asides,
  certifications, registration status, vehicle eligibility). Registration/observation date is
  `available_at`.
- `grounding_sec.py` — archived SEC `companyfacts`/`submissions` bytes → SourceFacts (segments,
  facilities, geography, revenue/scale, subsidiaries, major customers). Filing date is `available_at`.
- `grounding_subawards.py` — archived USAspending sub-award bytes → subaward records (prime,
  subrecipient, award/program link, amount, `available_at`, provenance, dedupe) + partner edges +
  sub-role `contract_history` rows.
- extend `grounding.py` (small, additive) — pull recipient business categories / set-asides / UEI /
  location from USAspending award-detail when archived.

## TEAM semantics (Opus-defined)

TEAM is asserted **only** from authoritative evidence, never from complementary capability alone:

- an official teaming/JV/mentor-protégé/consortium announcement, **or**
- a **repeat** prime↔subrecipient relationship in real USAspending sub-award data (a single occurrence
  is weak; require repetition or an explicit announcement), **or**
- defensible complementary capability **plus** an explicit review state (human ACCEPT in the fit queue).

Mechanically: TEAM fires when a consequence is a `matched_partial` capability match **and**
`profile.partners` carries a real, provenance-backed partner edge (populated only by
`grounding_subawards.py` from repeat relationships, or an archived announcement). If teaming evidence is
insufficient → **UNKNOWN/DEFER**, never a manufactured TEAM. A "false tempting TEAM" case (two firms
with complementary capability but no authoritative relationship) must resolve to SUPPORT or UNKNOWN, not
TEAM.

## Point-in-time truth (hard gate)

`available_at <= replay_as_of` for **every** SourceFact, sub-award, and SEC filing. Extend the existing
`run_fit_replay` leakage probe so a case may declare future-dated SEC filings and future sub-awards in
`leakage_probe`; the gate verifies none appear in the as-of profile and reports
`temporal_leakage_violations` (must be 0). No future knowledge.

## Corpus and metrics

`corpus_m10.json` **extends** frozen `corpus_m9.json` (never rewrite older corpora). Add real cases:
PRIME, real SUPPORT (subrecipient/partial), real TEAM (or explicit deferral), DEFEND, NO_FIT, UNKNOWN, a
real sub-award fit, a **false tempting TEAM**, an eligibility blocker (real set-aside/cert), a
future-evidence leakage case, and a stale-evidence case if practical.

Keep three metric buckets **separate, never blended**: M8 synthetic, M9 real-USAspending, M10
multi-source-real. M10 reports: real fit precision, false-match rate, posture precision, per-posture
precision (PRIME/SUPPORT/TEAM/DEFEND/NO_FIT), unknown rate, capability coverage, buyer-history coverage,
**eligibility coverage**, **subcontract coverage**, **profile source diversity** (avg source families
per real profile), and `temporal_leakage_violations`. All small-sample warnings surfaced, never hidden.

## `scoring_v1`

Frozen. No M10 change unless a full-corpus challenger proves a systematic issue without unacceptable
regression (not expected in M10). No STRIKE explosion. Frozen M4–M9 corpora byte-for-byte unchanged.

## Operations Panel (only after core M10 is safe, cheap/low-risk)

Expose, internal-only: multi-source facts, evidence strength, cutoff date, capability, buyer history,
eligibility, vehicle evidence, subcontract/teaming, fit posture, blockers, unknowns. No redesign.

## Acceptance (all must hold to close M10)

1. M2 gate addressed first (done — CONDITIONAL retained, env-blocked, gate not weakened).
2. ≥2 source families ground real company profiles.
3. Torch remains grounded. 4. MTSI remains grounded.
5. ≥1 real profile gains material evidence beyond USAspending.
6. Point-in-time reconstruction works. 7. `temporal_leakage_violations == 0`.
8. SUPPORT exercised on real evidence.
9. TEAM exercised on real evidence **or** explicitly deferred for insufficient authoritative evidence.
10. False tempting TEAM rejected.
11. Eligibility/vehicle represented where supported.
12. Subcontract evidence integrated **or** technically documented as insufficient.
13. Synthetic/real/multi-source metrics kept separate. 14. `scoring_v1` unchanged.
15. Prior frozen corpora unchanged. 16. No STRIKE explosion. 17. Full tests pass.
18. Limitations recorded. 19. Docs updated. 20. Each block pushed. 21. `HEAD == origin/<branch>`.

## Environmental preconditions to execute (what a resume needs)

- **Either** a session whose egress policy allows `data.sec.gov` + `api.usaspending.gov` (keyless —
  enough for SEC grounding of an added public prime and USAspending sub-awards, satisfying gate #2),
  **and/or** a provisioned `SAM_API_KEY` with SAM egress allowed (for SAM entity grounding of Torch).
- With SEC + USAspending sub-awards reachable, M10 can close **without** SAM: family 1 = USAspending
  prime, family 2 = SEC (added public prime), family 3 = USAspending sub-awards; SAM certs/eligibility
  are then documented as insufficient rather than fabricated.
- Suggested added public primes (SEC-registered, real USAspending primes, plausible teaming partners for
  Torch/MTSI in missile-defense/SETA): e.g. SAIC, CACI, Leidos, ManTech, Parsons — add only 1–3, per
  Workstream F (3–5 real firms total is enough).
