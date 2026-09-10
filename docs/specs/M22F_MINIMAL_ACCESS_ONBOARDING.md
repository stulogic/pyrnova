# M22-F — Minimal Customer Access + Onboarding

**Status:** CLOSED 2026-09-10. Full suite **615 passed** (was 571; +44 M22-F).
**Decision:** D-061. **Authorized by:** the M22-F work order. **Predecessors:** D-055 (M22-A), D-056
(M22-B), D-057 (M22-C), D-058 (M22-D), D-060 (M22-E), D-059 (engineering/infrastructure doctrine), D-048
(Phase-1 non-goals — enterprise IAM deferred).

M22-A→E built the customer-facing intelligence product (Material Changes, investigation, opportunity +
threat) and an **authorization seam** (`OperatorConsole.access_check` → `PermissionError` → HTTP 403), but
**authentication itself was deferred (D-048/D-057/D-058)**: the seam was permissive (`None`) and the
customer was chosen from a request parameter / a frontend dropdown. That is unsafe to hand to a real
design customer. M22-F attaches a real authenticated identity to that seam — **the smallest serious access
model** that closes the design-customer access P0 — without building enterprise IAM.

Primary flow:

    credential → authenticated actor → authorized customer → customer-scoped reads/actions
              → customer onboarding → watch configuration → existing fan-out / Material Changes

## Authentication model

* **Credential.** A high-entropy bearer token `Authorization: Bearer <credential_id>.<secret>`, where
  `secret` is a 256-bit CSPRNG value (`secrets.token_urlsafe(32)`) and `credential_id` is a public,
  non-secret id (`cred_<hex>`). The id embeds in the token so authentication is an O(1) lookup of exactly
  one record — never a scan that hashes every stored credential.
* **Storage** (`pyrnova/access.py`, append-only `credentials` stream; PG mirror `credential` in
  `db/schema.sql`). Only a **salted one-way hash** of the secret is persisted (`sha256(salt || secret)`).
  The plaintext token is shown **once** at creation and is **not recoverable** from storage. Because the
  secret is a full-entropy CSPRNG token (not a low-entropy password), a single salted SHA-256 is a
  sufficient, standard representation — no slow KDF, no custom cryptography (stdlib only). Comparison is
  constant-time (`hmac.compare_digest`).
* **Revocation** appends a closure record (`status='revoked'`, `revoked_at`); last-write-wins per id. A
  revoked credential fails authentication immediately and cannot read or write. History is never
  destructively erased (audit-preserving, consistent with watchlist retirement).
* **Actor ≠ tenant (§48).** An `AuthContext` carries `credential_id`, `role`, `customer_id`, `actor_label`.
  A **customer** credential is scoped to exactly one tenant; an **operator** credential is Pyrnova-internal
  (no single-tenant scope) for operations/debugging. Business handlers consume the `AuthContext`, never a
  bearer token or a request-controlled `customer_id` — so a later OIDC/SSO/SCIM layer replaces only
  `authenticate()`, not the authorization spread through the product (§49).

## Authorization + tenant isolation (fail closed)

* **The customer never chooses their own authority.** Tenant scope comes from the credential. A customer
  route with no `customer` param resolves to the authenticated tenant; a `customer` that mismatches the
  actor is a **hard 403**, never a fallback or a partial cross-tenant read (§14).
* **Enforcement chokepoint.** `pyrnova/ops_server.py` authenticates each request, sets a thread-local
  request context, and enforces a route access level (`_require`). Defense in depth: when auth is enforced
  the shared console's `access_check` is bound to the per-request actor (`access.request_access_check`), so
  even a route that forgot to scope a read fails closed.
* **Route levels.** PUBLIC (customer app shell + login assets — data behind them is protected);
  CUSTOMER (tenant-scoped; effective customer derived from the actor); GLOBAL (global intelligence —
  search/company/program; any authenticated actor, never anonymous when enforced); OPERATOR (snapshot,
  fan-out, briefs, opportunity adjudication, all-customer listing/creation, `/console` assets).
* **`/api/customers` (§13).** An ordinary customer receives **only itself** (or `/api/me`); the
  unrestricted all-tenant listing is operator-only. Customer enumeration is eliminated.
* **Failure semantics (§15).** 401 = no valid authentication; 403 = authenticated but not authorized;
  404 = surface not exposed on this binding (e.g. operator routes bound remotely). Error bodies never echo
  secret material, hashes, storage paths, or another tenant's ids.

## Remote binding + operator separation (§11/§16)

* **Interlock.** `AccessPolicy.decide()` forces `require_auth` ON whenever the bind host is non-local, or
  `PYRNOVA_REQUIRE_AUTH` is set, or any credential has been provisioned. Only a purely local checkout with
  no credentials runs permissively (the historical dev behavior) — an explicit, safe-by-default posture
  that can never activate silently for remote access (§30).
* **Operator surface** (all-customer listing, snapshot, fan-out, briefs, opportunity adjudication, and the
  `/console` assets) is exposed **only on a local bind**. Bound remotely it returns 404. This is the
  "localhost-only operator surface" §11 permits; a future production edge/TLS will front the app (no
  Cloudflare/TLS/reverse-proxy built here).

## Frontend (§10/§36/§37)

`ops_web/access.js` + `access.css`: an **Access** gate (credential entry), the credential held in
`sessionStorage` (cleared on tab close — the conservative choice for this controlled stage; never placed in
a URL), a `Pyrnova.authFetch` wrapper attaching the bearer and returning to the gate on 401, and Sign Out.
The customer **dropdown is removed**: `material.js` renders the authenticated **organization** identity
from `/api/me` and never lets the user switch tenant; a dev/operator selector appears only when the server
offers a switchable list (local dev). `investigation.js` uses the authenticated customer for the overlay,
never a URL parameter. There is **no auth in the frontend only** — every boundary is server-enforced.

## Onboarding (§17–§27) — seed-free, reuse everything

`pyrnova/onboarding.py` + CLI (`pyrnova customer|watch|credential`). A competent operator onboards a
customer **without editing any seed/Python/JSONL**:

* **Create customer** → reuses the M22-B `CustomerProfile` (same persisted stream the product reads; no
  parallel customer model). `pyrnova customer create --id <slug> --name <name> [--entity-ref/--agency/…]`.
* **Watch configuration** → reuses the M22-B `WatchlistEntry` (ENTITY / PROGRAM / CONTRACT / AGENCY;
  `valid_from`/`valid_to` temporal truth; honest `resolved` flag; cross-customer-safe retirement).
  `pyrnova watch add <customer> <ref> --type … [--resolve]`.
* **Entity resolution** → reuses the M22-D deterministic `search` (no second resolver, no runtime LLM).
  With `--resolve`: **EXACT** is selected; **PROBABLE** requires `--accept-probable` (explicit
  confirmation); **AMBIGUOUS** is never silently chosen; **UNRESOLVED** is never fabricated (an operator
  may record an honestly-unresolved literal watch with `--allow-unresolved --type …`). Resolution is
  explicit, never magic (§54).
* **Credential provisioning** → `pyrnova credential create --customer <id> [--operator]` prints the token
  once; `credential list` shows metadata only (never secrets); `credential revoke <id>`.
* **Fan-out** → the onboarded customer enters the existing M22-C fan-out / Material Changes read path
  unchanged; temporal truth holds (a watch added now does not backdate relevance — tested).

## Frozen components (§57)

Additive only. `scoring_v1`, `fit.py`, `replay.py`, the opportunity engine, materiality/value/severity
bands, replay corpora, and M22-A/B/C/D/E identity/version/lifecycle semantics are byte-identical /
behaviorally unchanged. The M22-A→E HTTP behavior is preserved in the permissive local-dev posture; the
`make_handler` signature gained optional `policy`/`auth_store` (default: permissive local) so existing
handler tests are unaffected.

## Tests (§31/§32)

`tests/test_m22f_access.py` (credential lifecycle, no-plaintext, secure compare, revocation, roles,
fail-closed request context), `tests/test_m22f_server_auth.py` (401/403/404 semantics, tenant isolation,
no enumeration, forged-customer rejection, operator separation, remote-bind interlock, token-not-echoed),
`tests/test_m22f_onboarding.py` (seed-free creation + reload, all four watch types, duplicate suppression,
cross-customer rejection, retirement history, resolution states, credentialed customer into fan-out,
temporal non-backdating). Full suite **615 passed** (was 571; +44).

## Deferred (DOCUMENT → ROADMAP → DEFER)

SSO / SAML / OIDC / SCIM, MFA platform, enterprise RBAC, org hierarchy, invitation/self-service signup,
password reset / email verification, billing/subscriptions, audit-log export, SOC 2 tooling, customer-
managed keys, full offboarding automation, per-request `last_used_at` (write-amplifying in append-only
JSONL — deferred), production edge/TLS/reverse-proxy, Cloudflare/PostgreSQL-migration/Redis. The M22-F auth
seam is deliberately replaceable by an enterprise IAM layer at `authenticate()` without rewriting product
authorization (§49). **Data volume / live-operations readiness is the separate next task, not M22-F.**

## Known limitations (honest)

Single-factor bearer credentials (no MFA); sessionStorage token (XSS-exposed like any bearer SPA — the
conservative per-tab choice for a controlled pilot); `credentials` stored as local append-only JSONL in dev
(the PG mirror exists but production PostgreSQL integration is **not** validated here); operator surface is
localhost-only (no remote operator portal); TLS is assumed to be terminated by a future production edge, not
implemented here. Not "enterprise-grade / zero-trust / SOC 2 / production-hardened" — exactly the minimal
serious access model described above.
