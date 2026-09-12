# Security and tenancy

Status: implemented-boundary description, not a compliance attestation  
Last reviewed: 2026-09-12

## Current posture

Pyrnova implements a minimal controlled-pilot access model. It is not enterprise IAM, zero trust, SOC 2,
FedRAMP, or production hardening. Tenant isolation is enforced in application code; PostgreSQL row-level
security does not exist.

## Identity and credentials

`pyrnova/access.py` creates bearer tokens in the form:

```text
<credential_id>.<secret>
```

- the secret is generated with `secrets.token_urlsafe(32)`;
- a per-credential salt and `sha256(salt || secret)` are stored;
- the plaintext is returned once and is not recoverable from state;
- verification uses `hmac.compare_digest`;
- credential records are append-only; revocation appends a later `revoked` version;
- list APIs/CLI return metadata, never the secret.

This construction is for high-entropy bearer tokens, not human passwords. It has no MFA or recovery flow.

`AuthContext` carries credential id, role, customer id, and actor label. Customer credentials have exactly
one tenant; operator credentials are internal and not tied to one tenant. HTTP handlers consume the
context, not the raw token.

## Request authentication and authorization

`ops_server.py` authenticates each request, sets a thread-local current context, applies a route-level
check, and clears the context in `finally`. When auth is enforced, `OperatorConsole.access_check` also
calls `request_access_check`, providing a second application-layer check.

| Level | Access |
|---|---|
| PUBLIC | Static customer app/access assets; no protected data |
| CUSTOMER | Credential’s own customer; operator may choose an explicit customer |
| GLOBAL | Any authenticated actor; global search/company/program data, no private overlay by default |
| OPERATOR | Internal operator only; snapshot, fan-out, briefs, adjudication, all-customer administration |

The customer tenant comes from the credential. A supplied different customer id returns 403; there is no
fallback. An ordinary customer’s `/api/customers` result contains only itself. Customer review actor is
derived from authenticated context, replacing any client-supplied actor.

Failure semantics:

- 401: no valid credential;
- 403: authenticated actor lacks authorization;
- 404: route/surface not exposed on this binding;
- 400: invalid request body/parameters.

Responses are `Cache-Control: no-store`. The server suppresses request-line logging to avoid leaking
identifiers or tokens. Bearer tokens must never appear in URLs.

## Binding interlock

`AccessPolicy.decide` forces authentication when any of the following is true:

- host is not `127.0.0.1`, `localhost`, or `::1`;
- `--require-auth` is supplied;
- `PYRNOVA_REQUIRE_AUTH` is truthy;
- any credential exists in the configured state store.

The Operator Console assets and operator routes are exposed only on a local bind. A non-local bind hides
them with 404. This prevents a configuration flag from enabling anonymous remote access, but it does not
supply TLS, a firewall, reverse proxy, rate limiting, or production process security.

## Tenant data boundary

Global intelligence includes evidence, entities, relationships, events, opportunities, threats,
propagated threats, and outcomes. Customer-private state includes profiles, watchlists, relevance inputs,
customer Material Change versions, lifecycle actions, credentials, and fan-out operational records.

Customer Material Changes contain references and compact assessment/relevance snapshots. They do not copy
global evidence bodies or let a customer mutate global truth. Review actions are keyed by customer and
change; cross-customer actions/retirements fail.

Company/program investigation is global by default. A customer overlay is added only after customer-level
authorization and remains a separately keyed block.

## Database boundary

`db/schema.sql` carries `customer_key` columns and customer-scoped tables, but defines no RLS policies,
database roles, grants, or session tenant variables. Moreover, no runtime PostgreSQL adapter is wired in
this baseline. Therefore:

- application-layer tests are evidence for current isolation;
- the schema is not evidence for database-enforced isolation;
- a future direct DB/reporting/worker path must not bypass the application boundary;
- PostgreSQL activation requires clean migration tests and a separate tenant-control design/verification.

## Secrets and configuration

Secrets come from process environment or the repository-local gitignored `.env`. The configuration module
reads SAM API key, archive credentials, database URL, state/output paths, and SEC identity settings.
Source request provenance applies broad secret-key redaction.

Controls not implemented:

- secrets manager, rotation schedule, audit trail, or automatic file-mode enforcement;
- customer-managed keys or per-tenant encryption keys;
- encrypted JSONL state/archive at rest;
- formal sensitive-data classification or deletion/offboarding automation.

Phase 1 authority excludes high-sensitivity/CUI data. That policy boundary is not a technical DLP control.

## Browser security

The static frontend stores the bearer token in `sessionStorage`, attaches it through an Authorization
header, clears it on sign-out/tab close, and returns to the access gate after 401. The authenticated
customer cannot switch tenants in the UI.

Known gaps include XSS exposure inherent to browser-accessible bearer storage, no CSP documented by the
built-in server, no CSRF framework (bearer header rather than cookie reduces conventional CSRF exposure),
no security headers beyond content type/cache control, and no browser security/E2E test suite.

## Evidence access and source rights

Customer APIs return evidence references rather than raw archive bodies. The built-in server does not
expose a generic raw-evidence download route. Source rights/status live in the registry and should gate any
future evidence-delivery feature. The OFAC path is intelligence evidence, not an authoritative compliance
screening service.

## Tests proving current controls

- `tests/test_m22f_access.py`: credential lifecycle, no plaintext, secure compare, revocation, role/context,
  fail-closed check.
- `tests/test_m22f_server_auth.py`: 401/403/404, forged-customer rejection, no enumeration, route separation,
  remote-bind interlock, token-not-echoed.
- `tests/test_m22f_onboarding.py`: tenant-scoped onboarding/watch/fan-out and cross-customer rejection.
- `tests/test_m22b_customers.py` and `test_m22c_customer_material_changes.py`: customer-private/global
  separation, lifecycle, storage isolation, temporal correctness.
- `tests/test_m22d_investigation.py`: private overlay isolation and access check.

These are offline application tests. No penetration test, dependency scan, cloud configuration audit,
database RLS test, or production security review is present.

## Pre-deployment security gate

Before any public or production exposure, require explicit authorization and evidence for TLS/edge,
process isolation, rate limits, CSP/security headers, credential issuance/rotation/revocation, backup and
restore, logging without secret leakage, dependency scanning, PostgreSQL/data-access controls if used,
least-privilege infrastructure credentials, incident response, and the applicable MFA/trust gate.
