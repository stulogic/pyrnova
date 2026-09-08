# Milestone 4 — source expansion and signal coverage

_Status: CLOSED 2026-09-08; implementation refinements recorded below._

## Core question

Can Pyrnova see materially more of the world without degrading selectivity, provenance, replayability,
API efficiency, or explainability?

## Candidate source families

1. Grants.gov.
2. SEC EDGAR capex and corporate-change filings.
3. Federal budgets, appropriations, and agency budget justifications.
4. Procurement forecasts, RFIs, sources-sought, and stronger SAM chain coverage.
5. State-capital and industrial-policy sources.
6. Selected regulatory and enforcement sources.
7. Later, commercial web change detection where higher-authority sources are insufficient.

## Entry gate for each source

A source proposal must state:

- the commercial mechanism and user problem it covers;
- representative positive and negative historical cases;
- source authority, identity, timestamps, mutability, and retention tier;
- OFFLINE, LIVE-SAFE, and ACCEPTANCE behavior;
- expected cadence, cursor/delta support, request budget, quota/backoff/circuit-breaker behavior;
- mapping into existing evidence/candidate objects without enrichment-only candidate creation;
- replay plan and full-corpus selectivity regression;
- success metric and kill criterion.

## Non-goals

- No generic connector platform, source count target, frontend, or customer personalization.
- No source is accepted because access is easy.
- No scoring or mechanism complexity before corpus evidence demonstrates the need.

Implementation was activated by the explicit M4 execution instruction recorded on 2026-09-08; this
document does not authorize later milestones or broader source families.

## Implemented refinement

- Grants.gov Search2, SEC EDGAR submissions/companyfacts, and official agency procurement forecast
  artifacts are the accepted first source families.
- New-source observations replay through one offline integration boundary into normalized records,
  SEC CIK entities, archived evidence, and explicitly keyed partial program chains.
- Program stages are `INTENT`, `AUTHORIZATION`, `FUNDING`, `PROGRAM`, `MARKET_ENGAGEMENT`,
  `PROCUREMENT`, `AWARD`, and `OUTCOME`; no stage is required and no join is inferred from topic alone.
- New sources are evidence/enrichment/WATCH inputs by default. Candidate creation and STRIKE promotion
  remain behind existing direct-opportunity, capability, evidence, and human-review gates.
- Source contribution is measured with deterministic leave-one-source-out replay against the M4 corpus;
  the frozen M3 corpus and `scoring_v1` are unchanged.
