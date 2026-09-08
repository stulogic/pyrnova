# Pyrnova prioritized backlog

Backlog presence is not implementation authority. `02-EXECUTION.md` controls active work.

## P0 — next authorized sequence

- Complete the post-reset M2 SAM acceptance and formal closure.
- Confirm M3 reproducibility after M2 closes.
- Accumulate additional reviewed Grants.gov, SEC EDGAR, and agency-forecast outcomes before drawing
  general lift conclusions.

## P1 — deferred source expansion

- Federal budgets, appropriations, and agency budget justifications.
- Additional per-agency forecast mappings, archived amendments, and forecast → SAM → award crosswalks.
- State and local capital-program sources beyond the federal/industrial-policy path established in M4.
- Selected regulatory and enforcement sources.
- Commercial web change detection only after higher-authority sources justify it.

Every source must pass the coverage/selectivity/provenance/replay/API-efficiency test in
`docs/specs/M4_SOURCE_EXPANSION.md` before implementation.

## P1 — deferred cross-source (graph) work

- Exercise and calibrate the conservative `inferred_strong_attribute` join path against reviewed cases
  before relaxing its 0.60 confidence.
- Entity-level predicates (`AWARDED_TO`, `SUBSIDIARY_OF`, `LOCATED_AT`) once recipient/entity evidence
  justifies them.
- Explicit budget/appropriation precursor stages (INTENT/AUTHORIZATION/FUNDING linkage groundwork)
  from a focused official source, without turning M5 into another source-expansion milestone.
- Richer chain-confidence modeling (source independence weighting, expected-stage completeness) only
  if per-relationship confidence proves insufficient.
- Human-review queue for inferred cross-source joins with persisted reviewer/decision/outcome for
  future calibration.

## Deferred product/infrastructure work

- Polished frontend, mobile apps, enterprise UI, self-serve dashboard.
- Proprietary-data integrations and broad customer personalization.
- Public API commercialization, SEO product, CRM/outbound automation, proposal generation.
- Production PostgreSQL/object-storage adapters until deployment or customer need authorizes them.
- Dormant FLOW, SHIFT, RISK, and broad outcome-graph engineering.

## Commercial work held separately

The prior founder commercial-readiness hold and Torch outbound package remain documented in the dated
handover and `docs/outbound/`. They do not authorize engineering scope.
