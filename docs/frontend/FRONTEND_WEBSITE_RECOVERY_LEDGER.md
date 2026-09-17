# Frontend / Public-Website Recovery Ledger

**Workstream:** FRONTEND RECOVERY + COMMERCIAL SURFACE RECONCILIATION
**Branch:** `international-government-rollout-001`  **Starting tip:** `3cf3119`
**Date:** 2026-09-16
**Canonical repo:** `/Users/stu/Documents/Pyrnova-intl`

## Headline finding

The customer-facing frontend and the public website are **not missing and were not
lost.** Both exist at the current international tip (`3cf3119`), are reachable, render
**real** multi-country backend data, and pass their tests. The perceived gap was
**discoverability + rendered proof**, not a missing artifact. This workstream therefore
*confirms, proves and documents* the visible surfaces rather than rebuilding them —
consistent with the standing rule "recover before you replace."

A full forensic search of history, branches, tags and worktrees found **no separate
customer SPA that was built and then deleted.** The branch whose name implied lost work,
`backup-before-ui-recovery-20260915-211122`, is *older* than the current tip: relative to
`3cf3119` it **deletes** `website-go/` and `tools/workstream-control/`. It is a prior
checkpoint, not a source of recoverable frontend.

## A. What exists and is worth preserving

### A1. Customer-facing product (SPA-style multi-page web app)
- **Code:** `pyrnova/ops_web/` (HTML/CSS/vanilla-JS, dependency-free)
- **Server:** `pyrnova/ops_server.py` (Python stdlib `ThreadingHTTPServer`)
- **Customer routes** (served by the same shared shell — no per-country frontends):
  - `/` → `product.html` — **Customer Lens**, ranked **Opportunities**, **Decision View**,
    **Evidence**, downloadable **Brief**, delivery.
  - `/material.html` → **Decision View / Material Changes**, **AS-OF** temporal view,
    uncertainty/falsifiers, confidence, version history, review history.
  - `/investigate` (`/search`, `/company`, `/program`) → **Evidence Inspector** /
    investigation.
- **Auth:** access gate (`access.js` / `access.css`); `/api/me` drives identity + tenant
  posture. Non-local binds **force auth and hide** the operator console (`AccessPolicy`).
- **Operator console** (internal, local-only): `/console` → `index.html`. Hidden on remote
  binds. This is distinct from the customer surface.
- **Design:** dark/light theme tokens, accessible (skip-link, ARIA, `:focus-visible`),
  responsive breakpoints, provenance labelling, source-rights fail-closed footer — calm,
  restrained, evidence-led. Matches the required product aesthetic.

### A2. Public marketing website
- **Code:** `website-go/` (WEBSITE-GO-001 Revision B). Node stdlib static renderer, no deps,
  **no server logic in output**, **intake disabled (State 1)**.
- **Routes (7):** `/` home, `/intelligence`, `/method`, `/trust`, `/research`, `/company`,
  `/evaluate` (informational; **omits the intake form entirely** by design).
- **Evidence:** committed desktop+mobile screenshots under
  `website-go/evidence/screenshots/`.
- **Tests:** 14/14 pass (`node --test`) — State-1 invariants + route completeness.

## B. What is missing

- **Nothing structural.** No lost SPA; no lost website. No obsolete mock-API layer — the
  frontend already talks to the live `ops_server` contract.
- Rendered screenshots of the *customer* SPA could not be regenerated **in this session**
  because no headless browser is installable offline. The API/asset layer is proven instead
  via the smoke transcript (below); `website-go` ships its own committed screenshots.

## C. Reconciliation performed

No frontend/backend interface gap was found — the customer pages consume the **current**
endpoints directly:

| Surface | Endpoint(s) verified against live server |
|---|---|
| Identity / Lens context | `GET /api/me` |
| Customer Lens | `GET /api/lens?customer=&as_of=` |
| Opportunities (ranked) | `GET /api/opportunities?customer=&as_of=` |
| Decision View | `GET /api/opportunities/{id}/decision` |
| Evidence Inspector | `GET /api/opportunities/{id}/evidence/{evidence_id}` |
| Material Changes + AS-OF | `GET /api/material-changes?customer=&as_of=` (+ `/versions`, `/review-history`) |
| Downloadable Brief | `GET /api/opportunities/{id}/brief?download=1` |
| Disposition / deliver | `POST /api/opportunities/{id}/disposition`, `/deliver` |

National differences (US/AU/NZ/UK/CA) surface as **contextual product truth inside the
shared shell** — the frontend is country-agnostic and renders whatever fields the API
returns; the multi-country logic is exercised by the Python regression, which is green.
No backend or accepted product logic was modified by this workstream.

## D. Visible reality check

See `docs/frontend/VISIBLE_SURFACE_SMOKE.txt` for the full captured transcript. Verified
end-to-end against the live server with real demo tenants (`torch`, `dap`):
Lens, Opportunities (with attractiveness/confidence/source-rights), Decision View
(`buyer.status: EVIDENCED`), Evidence Inspector (source_url → usaspending.gov + sha256),
AS-OF historical divergence, downloadable Brief (200, real content), and a **legitimate
empty state** for `dap` (count 0 — rendered as empty, never fabricated).

## Exact local launch commands

```sh
# Customer product (Customer Lens / Opportunities / Decision / Evidence / AS-OF / Brief)
cd /Users/stu/Documents/Pyrnova-intl
python -m pyrnova.ops_server            # local dev, no auth, seeds demo tenants
#   → http://127.0.0.1:8765/            customer product (pick tenant: torch or dap)
#   → http://127.0.0.1:8765/material.html   Decision View / Material Changes / AS-OF
#   → http://127.0.0.1:8765/console     operator console (local-only)
# Auth posture (optional): PYRNOVA_REQUIRE_AUTH=1 python -m pyrnova.ops_server
#   provision a credential:  python -m pyrnova.cli credential create --customer torch

# Public website (informational, intake-disabled State 1)
cd /Users/stu/Documents/Pyrnova-intl/website-go
npm run serve                           # build + read-only preview
#   → http://127.0.0.1:4318/
```

A convenience wrapper is provided: `ops/launch_visible.sh` (starts the customer product,
optionally builds the website preview, and prints both URLs).

## Commercial-surface state (unchanged, for reference)

Public website remains **WEBSITE-GO / OUTREACH INTAKE DISABLED (State 1)** — informational
only, no collection. The commercial offer (Pyrnova Live Intelligence: $15,000 / 60 days /
1 Customer Lens / up to 10 Named Users; continuation $18,000 quarterly or $72,000 annual;
no auto-renew) is presented as informational copy, not an intake flow. Activating public
intake is a separate, deliberate WEBSITE-GO state change and is **out of scope** here.
