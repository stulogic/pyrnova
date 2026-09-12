# Architecture decision records

ADRs explain materially important implemented choices. They are descriptive and subordinate to the
authority hierarchy in [`../../00-INDEX.md`](../../00-INDEX.md). The compact durable product/engineering
decision ledger remains [`../../04-DECISIONS.md`](../../04-DECISIONS.md).

DOCS-001 records only decisions already evidenced by authority, code, tests, and specifications. The ADR
date is the date this rationale was written; “Related authority” identifies the prior decision/work that
actually established it.

## Index

| ADR | Status | Decision |
|---|---|---|
| [0001](0001-derived-read-projections.md) | Accepted | Authoritative state produces derived read projections |
| [0002](0002-global-intelligence-customer-private-state.md) | Accepted | Global intelligence remains separate from customer-private state |
| [0003](0003-append-only-temporal-truth.md) | Accepted | Append-only histories and cutoff-based reconstruction preserve temporal truth |
| [0004](0004-archive-first-governed-sources.md) | Accepted | Sources are registry-driven, archive-first, offline-default, and explicitly controlled |
| [0005](0005-application-layer-tenant-isolation.md) | Accepted with known limits | Current tenant isolation is application-layer |

## Format for future ADRs

```markdown
# ADR-NNNN — Decision title

Status: proposed | accepted | superseded | rejected
Date: YYYY-MM-DD

## Context
## Decision
## Alternatives
## Consequences
## Related code
## Related authority
```

Do not create an ADR for routine implementation detail, an unapproved proposal, or to manufacture
retrospective certainty. If a future ADR changes product scope, execution authority must exist first.
