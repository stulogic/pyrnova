# ADR-0002 — Global intelligence remains separate from customer-private state

Status: accepted  
Date: 2026-09-12 (retrospective record of D-056/D-057)

## Context

Customer relevance, watchlists, review state, and delivery history must personalize Pyrnova without
contaminating evidence-backed global intelligence or leaking between tenants.

## Decision

Global evidence/entities/events/relationships/opportunities/threats/outcomes remain global. Customer
profiles, watches, relevance facts, customer Material Change versions, lifecycle actions, credentials,
and fan-out records are customer-private and keyed by customer id. Customer records may reference global
ids but cannot promote private facts into the global graph or mutate system assessment.

## Alternatives

- Copy the whole global record into each tenant: rejected as duplicate truth.
- Store customer reviews on global threat/opportunity rows: rejected because one customer’s judgment
  would affect others.
- Treat customer watches as global relationships: rejected because private intent is not public evidence.

## Consequences

Customer-specific behavior is auditable and independently rebuildable. Every new read/write path must
choose a state owner and carry/verify customer id. Cross-customer negative tests are mandatory. Shared
global infrastructure still requires careful access control for customer overlays.

## Related code

`pyrnova/customers.py`, `pyrnova/customer_material_changes.py`, `pyrnova/material_changes.py`,
`pyrnova/investigation.py`, `pyrnova/access.py`.

## Related authority

D-056, D-057; M22-B/C/D/F specifications; engineering doctrine §6.
