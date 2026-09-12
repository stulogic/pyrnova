# ADR-0001 — Authoritative state produces derived read projections

Status: accepted  
Date: 2026-09-12 (retrospective record of D-055/D-057/D-058)

## Context

Pyrnova needed a customer Material Changes feed and company/program investigation without creating a
second intelligence graph or letting presentation become canonical truth.

## Decision

Keep evidence, events, relationships, opportunities, threats, outcomes, and customer actions in their
own authoritative stores. Build Material Changes and the IntelligenceEstate as deterministic,
point-in-time read projections. Customer Material Change persistence stores source references and a
compact delivered snapshot/version, not copied evidence bodies or authoritative prose.

## Alternatives

- Persist complete UI cards as a second truth system: rejected because they drift from engines/evidence.
- Query every raw source directly from the UI: rejected because it bypasses archive/time/policy layers.
- Introduce a new graph/search database immediately: deferred until measured need.

## Consequences

Reads remain traceable and rebuildable; UI changes cannot rewrite intelligence. Projection code must be
kept compatible with source records and tested for stable identity/order/time. Current local reads may be
less scalable than a specialized read store; migration must preserve semantics.

## Related code

`pyrnova/material_changes.py`, `pyrnova/customer_material_changes.py`, `pyrnova/investigation.py`,
`pyrnova/ops.py`.

## Related authority

D-055, D-057, D-058 in `04-DECISIONS.md`; M22-A/C/D specifications; engineering doctrine §§2, 3, 6, 7.
