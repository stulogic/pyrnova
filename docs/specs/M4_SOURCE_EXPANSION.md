# Milestone 4 authority stub — source expansion and signal coverage

_Status: prepared, not authorized for implementation._

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

Implementation begins only under a later explicit M4 execution instruction.
