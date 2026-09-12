# ADR-0005 — Current tenant isolation is application-layer

Status: accepted with known limits  
Date: 2026-09-12 (retrospective record of D-061)

## Context

M22 required controlled customer access before enterprise IAM or production PostgreSQL infrastructure was
authorized. The system already had a single `access_check` seam and customer-keyed state.

## Decision

Authenticate a high-entropy bearer credential into an actor context. Derive a customer actor’s tenant
from the credential, apply route-level checks in the HTTP handler, and bind the service-layer
`access_check` to the current actor as defense in depth. Force authentication for non-local binds and hide
operator surfaces remotely. Keep this explicitly application-layer; do not claim database RLS.

## Alternatives

- Request-selected tenant/dropdown: rejected for authenticated customer operation.
- Full OIDC/SSO/SCIM/RBAC platform before a controlled pilot: deferred by Phase 1 authority.
- Claim schema keys equal RLS: rejected because no RLS policies exist.

## Consequences

The controlled application path has testable tenant isolation and can later replace authentication behind
`AuthContext`. Direct database, analytics, background-worker, or new service access must not bypass this
boundary. TLS/edge, MFA, RLS, rate limits, security headers, and production security review remain open.

## Related code

`pyrnova/access.py`, `pyrnova/ops_server.py`, `pyrnova/ops.py`, `pyrnova/customers.py`,
`pyrnova/customer_material_changes.py`; M22-F tests.

## Related authority

D-061 and M22-F specification; D-048 deferred enterprise IAM boundary.
