# Pyrnova prioritized backlog

Backlog presence is not implementation authority. `02-EXECUTION.md` controls active work.

This backlog holds prioritized near-term work. Longer-horizon strategic capabilities live in
`docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`; milestone planning must consult that roadmap and
promote, defer, supersede, or reject its items explicitly — never drop them silently.

## P0 — next authorized sequence

- Execute M10 (`docs/specs/M10_MULTI_SOURCE_INTELLIGENCE.md`) from an environment with egress to the
  keyless data hosts (`data.sec.gov`, `api.usaspending.gov`) and/or a provisioned `SAM_API_KEY`. The
  spec, TEAM/evidence/temporal semantics, and 21-point acceptance gate are ready; only real external
  evidence acquisition is blocked here. Do not fabricate evidence or weaken the gates. M11 is gated on a
  clean M10 close.
- Complete the post-reset M2 SAM acceptance and formal closure (also blocked here by a missing
  `SAM_API_KEY`; rerun the unchanged gate where the key is provisioned).
- Confirm M3 reproducibility after M2 closes.
- Accumulate additional reviewed Grants.gov, SEC EDGAR, and agency-forecast outcomes before drawing
  general lift conclusions.

## P1 — deferred threat intelligence (M15 delivered the foundation)

M15 delivered first-class threat intelligence + the exposure graph (roadmap area 1 → DELIVERED; see
`docs/specs/M15_THREAT_INTELLIGENCE.md`). Carried-forward, not-yet-built threat work:

- Exercise the remaining `EXPOSURE_RELATIONS` families with real archived evidence: supplier-dependency,
  geography/facility, commodity-input, technology-substitution, procurement-vehicle (M15 exercised
  sanctioned-counterparty, program/incumbency, regulation/certification, customer-concentration).
- Measure threat selectivity against a **real event stream** (the M15 corpus is mechanism-dense by
  design; the explosion guardrail must be proven on a live feed where most events reject).
- Threat-outcome calibration at scale (threat precision once enough real outcomes resolve) via the
  append-only threat-outcome ledger.
- A real (non-probe) sanctions-exposure counterparty linkage once counterparty-relationship evidence is
  archived; today's confirmed positives are clearly-labelled controlled probes against real designations.
- Evidence-backed mitigation modelling (no autonomous action on threats — a roadmap boundary).

Each still honours point-in-time truth, deterministic-vs-weak linkage, and no invented probability.

## P1 — deferred source expansion

- Federal budgets, appropriations, and agency budget justifications.
- Additional per-agency forecast mappings, archived amendments, and forecast → SAM → award crosswalks.
- State and local capital-program sources beyond the federal/industrial-policy path established in M4.
- Selected regulatory and enforcement sources.
- Commercial web change detection only after higher-authority sources justify it.

Every source must pass the coverage/selectivity/provenance/replay/API-efficiency test in
`docs/specs/M4_SOURCE_EXPANSION.md` before implementation.

## P1 — deferred cross-source (graph) work

- Grow the reviewed inferred-join corpus (true, false, and ambiguous) well beyond M6's small sample,
  then re-evaluate the frozen 0.60 acceptance threshold and the `[0.45, 0.60)` deferral band with
  real override statistics. (M6 delivered the weighted model, deferral band, and review queue;
  the threshold stays frozen until the sample materially grows — D-020/D-021/D-023.)
- Archive at least one live official budget/appropriation artifact through the `appropriations`
  adapter and add per-artifact column mappings for additional agencies.
- Extend entity predicates beyond `AWARDED_TO`/`SUBSIDIARY_OF`/`LOCATED_AT` (e.g. `SUPPLIES_TO`,
  `OPERATES`, `RECEIVES_FUNDING_FROM`) only where authoritative primary evidence clearly justifies
  each one.
- Richer chain-confidence modeling (source independence weighting, expected-stage completeness) only
  if per-relationship confidence proves insufficient.

## P1 — deferred commercial-consequence work

- Exercise the SUPPLY_DISPLACEMENT and TECHNOLOGY_MIGRATION mechanism families with reviewed corpus
  cases (implemented in M7 but not yet corpus-exercised).
- Weave per-cutoff consequence supportability into `derive_transitions` so a single trajectory can read
  "catalyst supportable at AUTHORIZATION, consequence supportable at FUNDING, STRIKE at PROCUREMENT".
- Evidence-backed SUPPLIER/SUBCONTRACTOR roles once subcontract/supplier-tier data is available.
- Richer value estimation (comparable-award selection, program-fraction priors by mechanism) once more
  reviewed value cases exist; keep UNKNOWN honest until then.
- Human review of uncertain commercial causality reusing the M6 review-queue pattern for consequences.
- Capability fit-matching against customer `CapabilityProfile` (foundation only in M7).

## P1 — deferred fit / personalization work

- Grow the reviewed fit corpus well beyond 12 graded fits (more TEAM/DEFEND, more tempting false
  matches, historical fits that later proved right/wrong) before drawing general fit-precision
  conclusions.
- Build company profiles from real archived evidence (USAspending award history, SEC operational
  descriptions, official capability statements) via existing adapters, point-in-time.
- Optional Operations Panel fit view: surface posture, capability match, blockers, strongest evidence,
  and fit review over current engine state (thin read/write; do not redesign the panel).
- Capability fit-matching thresholds and confidence calibration once a larger reviewed sample exists.
- Contract-vehicle and set-aside eligibility depth (currently a single structured blocker each).

## P1 — deferred real-profile / calibration work

- Broaden real profile evidence beyond USAspending prime awards: SAM entity/eligibility (certifications,
  set-asides, clearances), SEC EDGAR business descriptions/facilities/segments, and official capability
  statements — each point-in-time with provenance, to fill the UNKNOWN certification/clearance/vehicle
  gaps.
- Profile additional real companies and grow the graded real-fit sample well beyond 7 before
  generalizing fit precision; add real SUPPORT/TEAM cases once subcontract/teaming evidence is available.
- Real subcontract/support signal (USAspending sub-award data) so "public prime award absent" is not
  read as "no participation".
- Profile-fact review (ACCEPT/REJECT/DEFER PROFILE FACT) reusing the fit-review pattern.
- Operations Panel real-profile view (selected company, facts, evidence, cutoff, posture, blockers,
  unknowns) — thin read/write over engine state; deferred in M9 to protect core progress.
- USAspending publication-lag modeling so `available_at` reflects true knowability, not award start date.

## Deferred product/infrastructure work

- Operations Panel UX concepts salvaged from the superseded Operator Console v0.1 (orphan commit
  `e9253b4`, D-040) — preserve the *workflow*, not the old code, and only build on the current
  state-centric panel + M12–M14 governed ingestion: (a) **UI-triggered Capture Radar run** with
  operator parameters (mode, forward window, SAM lookback, min award $, min relevance) that routes
  through `live_ops`/`scheduler` (never the orphan's ungoverned fetch); (b) **selective Signal Brief
  assembly** from hand-picked approved candidates (vs the current by-target export); (c) **richer human-
  review-queue filters** (candidate type, source, review status, min relevance). Relates to roadmap
  area 13 (customer-facing simplification). Do not create a second console.
- Polished frontend, mobile apps, enterprise UI, self-serve dashboard.
- Proprietary-data integrations and broad customer personalization.
- Public API commercialization, SEO product, CRM/outbound automation, proposal generation.
- Production PostgreSQL/object-storage adapters until deployment or customer need authorizes them.
- Dormant FLOW, SHIFT, RISK, and broad outcome-graph engineering.

## Commercial work held separately

The prior founder commercial-readiness hold and Torch outbound package remain documented in the dated
handover and `docs/outbound/`. They do not authorize engineering scope.
