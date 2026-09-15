# WEBSITE GO — Rendered Acceptance Evidence

**Deliverable:** Pyrnova public informational website.
**Target state:** `WEBSITE GO / OUTREACH INTAKE DISABLED` (State 1).
**Prepared:** 2026-09-14.
**Status:** READY FOR OWNER ACCEPTANCE. Claude does not grant final owner acceptance.

State 1 means: **safe to publish** as an informational site; **not** safe to use as a
public evaluation-intake destination. Public evaluation intake (State 2) is a separate,
separately-authorized workstream and is intentionally not built here.

---

## Branch / worktree

- **Branch:** `website-go-001` (new, isolated).
- **Base commit:** `e7cb2c98c3594166cbcb4d5691c0f370d4c5eb57` (the pinned Live Ops soak
  commit — used only as a clean, committed starting point; the running soak is untouched).
- **Worktree:** isolated scratchpad worktree, separate from the running soak and from all
  operational worktrees.
- **Implementation location:** `website-go/` (self-contained; imports no product code).

## Recovery state

- Prior website work exists on branch `website-001` (worktree `/private/tmp/pyrnova-website-001`).
  It is a **different, State-2 doctrine**: active `POST /api/contact` intake with durable R2
  storage of personal data, an operator inbox, engagement analytics, a credentialed brief
  viewer, and navigation `Trust / About / Contact / Privacy / Terms`.
- That doctrine does **not** match this task's locked authority: primary message
  "Know what changed. Know what it changes.", navigation
  INTELLIGENCE / METHOD / TRUST / RESEARCH / COMPANY / EVALUATE, and a State-1
  intake-disabled requirement (active intake is an explicit State-1 hard failure).
- Decision: `website-001` was **preserved untouched** (not merged, edited, or deleted).
  A new branch `website-go-001` was created for the current locked doctrine, per the
  recovery protocol's suggested branch name. The accepted Pyrnova CSS design language from
  `website-001` was reused for visual coherence; content and structure follow the new authority.
- **Existing website work recovered into this deliverable:** design language only (CSS).

## Implementation scope

- Static, dependency-free site. Node standard-library generator (`build.mjs`) renders fixed
  content to `dist/` as one static HTML file per route. **No JavaScript is shipped** to the
  browser; there is no server logic, no framework, no external font/SDK/tracker.
- Accepted institutional design direction (dark, evidence-led, cyan accent, evidence panel,
  reasoning loop) reused from the accepted Pyrnova visual language.

## Site routes (locked authority)

| Route | Nav label | Purpose |
|-------|-----------|---------|
| `/` | HOME | Primary message + supporting proposition, both CTAs, illustrative evidence panel |
| `/intelligence/` | INTELLIGENCE | Anatomy of a conclusion; attribution labels; uncertainty; AS-OF |
| `/method/` | METHOD | Reasoning loop; detect / trace / evidence / point-in-time / learn |
| `/trust/` | TRUST | Implemented-vs-not-verified claim register; data boundary |
| `/research/` | RESEARCH | Evidence-led approach; replay; future-exclusion; falsification |
| `/company/` | COMPANY | Founder-led; purpose; initial application (US federal contractors) |
| `/evaluate/` | EVALUATE | Informational; intake explicitly not open; **no submission mechanism** |

- Primary message: **"Know what changed. Know what it changes."** (home H1, verified).
- Primary CTA: **Evaluate Pyrnova** → `/evaluate/`. Secondary CTA: **See the intelligence**
  → `/intelligence/`. Header CTA: **EVALUATE**.
- All primary navigation routes resolve (HTTP 200); unknown routes return 404. No dead nav,
  no placeholder pages, no lorem ipsum.

## EVALUATE — intake-disabled verification

The EVALUATE page is a complete informational page that **omits the intake form entirely**
and states plainly: *"Public evaluation intake is not open yet … there is no submission form
or account sign-up here, and this site does not collect your details."*

Verified across **all** routes (automated in `website-go/tests/site.test.mjs`, and by
manual source + rendered inspection):

- Personal-data fields present: **NO** (no `<input>`, `<textarea>`, `<select>` anywhere).
- Submit action present: **NO** (no `<form>`, no submit control, no `enctype`).
- Hidden collection path present: **NO** (no `<script>`, no inline event handlers, no
  `fetch`/`XMLHttpRequest`/`sendBeacon`, no `/api/` reference).
- Calendar / file upload / founder workaround present: **NO** (no `mailto:`/`tel:`, no
  Calendly/Cal.com/Typeform/Formspree/HubSpot references, no file input).
- No personal email/phone, no invented privacy/controller identity, no dormant intake endpoint.

## Trust / claims discipline

- Product semantics described as implemented/tested: evidence provenance, source attribution,
  four attribution labels, uncertainty, AS-OF / point-in-time reconstruction and replay,
  customer-specific consequence, application-layer customer isolation, source-rights controls.
- Explicitly **not** claimed: SOC 2, FedRAMP, ISO 27001, CMMC, database row-level security,
  production MFA/SSO, penetration testing, verified backups/DR, encryption at rest, production
  TLS architecture, 24/7 monitoring, authority to process FCI/CUI/classified data.
- Application-layer isolation is explicitly distinguished from database row-level security.
- SOC 2 / FedRAMP / ISO / CMMC strings appear only in their negation on the Trust page
  (enforced by test). **Unsupported legal/security claims found: NONE.**

## Founder privacy

- No founder photograph, name, legal/controller identity, LinkedIn, social profile, education,
  nationality, location, immigration, family, personal phone, personal email or personal
  narrative. COMPANY describes Pyrnova as "founder-led" only.

## Browser acceptance (real rendering)

Rendered in a real browser engine (headless Chrome / "Google Chrome for Testing" from the
Playwright cache) against the local static preview at `http://127.0.0.1:4318`.

- **Desktop:** 1440×900 viewport.
- **Mobile:** true **390px** layout viewport (page loaded inside a 390px-wide iframe within a
  420px frame; the 30px grey margin in each mobile capture is the frame, not the page — page
  content ends cleanly at 390px with **no horizontal overflow**).

Note: a first mobile pass using Chrome's `--window-size=390` was discarded — headless Chrome
enforces a 500px minimum window and cropped to 390, producing a *false* overflow illusion. An
instrumented measurement (`scrollWidth == clientWidth`, zero elements past the viewport)
confirmed the layout has no overflow; the iframe method then produced correct 390px captures.

### Screenshots reviewed (`website-go/evidence/screenshots/`)

Desktop (1440): `desktop-home.png`, `desktop-intelligence.png`, `desktop-method.png`,
`desktop-trust.png`, `desktop-research.png`, `desktop-company.png`, `desktop-evaluate.png`.

Mobile (390): `mobile-home.png`, `mobile-intelligence.png`, `mobile-method.png`,
`mobile-trust.png`, `mobile-research.png`, `mobile-company.png`, `mobile-evaluate.png`.

- **Desktop render review: PASS.** Hierarchy, hero, evidence panel, reasoning loop, card grid,
  claim register all render correctly.
- **Mobile render review: PASS.** Navigation wraps cleanly, H1 wraps, CTAs stack full-width,
  evidence panel and grids collapse to single column, no clipping, no overflow, readable text.

## Independent critique — findings and corrections

One focused critique pass (fidelity, hierarchy, clarity, trust, responsiveness, visual
defects, accidental intake implication, unsupported claims). Positioning was not reopened.

- **Finding (fixed):** INTELLIGENCE "Anatomy of a conclusion" section reused the `.hero`
  two-column grid but had three direct children (eyebrow, copy, panel), so grid auto-placement
  misaligned them on desktop (eyebrow floated low-left, panel dropped a row). Mobile stacked
  correctly. **Correction:** wrapped the eyebrow + copy into a single grid child and added a
  top-aligned `.hero.anatomy` rule. Re-rendered desktop + mobile INTELLIGENCE: PASS.
- No other defects, doctrine deviations, intake implications or unsupported claims found.

## Build / tests run

- `npm run build` — renders 7 static pages + `site.css`, `favicon.svg`, `robots.txt`,
  `sitemap.xml` to `dist/`. PASS.
- `npm test` (`node --test`, standard library, no dependencies) — 9 suites PASS / 0 FAIL,
  covering: required routes present; nav matches locked authority; every route is a complete
  document (no placeholder); home carries the locked message and both CTAs; **no form / input /
  textarea / submit** on any page; **no script / inline handler / collection call** on any page;
  **no mailto / tel / api / booking-provider** on any page; EVALUATE states intake not open with
  no submission; no unsupported certification claims outside the Trust negation.
- Route/asset smoke test via HTTP: all 7 routes + assets return 200; unknown route returns 404.
- No backend/product tests were run (no product code was touched).

## Excluded / not built (State 1 discipline)

Products/Solutions/Industries/Resources nav, AI page, pricing, self-serve funnel, booking
flow, founder bio programme, feature-grid positioning, invented testimonials/logos/legal
identity, fake certifications, invented deployment claims. No privacy/terms controller
identity, no intake fields, no receiving destination, and **no dormant intake endpoint stored
"for later."**

## Soak non-interaction

- Running soak process: **not touched** (not started, stopped, signalled, reloaded, reseeded
  or rebaselined).
- Soak configuration/checkpoints/cadence/environment: **not touched.**
- Protected evidence dir `var/phase1_soak/evidence_source_counter_fix_2026-09-12`:
  **not written** (it is not even present in this base checkout).
- Pinned soak worktree and acceptance-critical product code: **not modified.** This deliverable
  imports no product code and shares no runtime, state, secrets or configuration with it.

## Residual deployment dependencies (outside this task)

State 1 is publishable as-is. Before any public launch the owner still controls: domain/DNS
and hosting account setup (not performed here), TLS/CDN at the chosen host, and — only if and
when State 2 is separately authorized — a privacy notice, accurate controller/legal identity,
intake fields with validation and abuse controls, a receiving destination, and production
end-to-end intake verification.

## Final state

`WEBSITE GO / OUTREACH INTAKE DISABLED` — **READY FOR OWNER ACCEPTANCE.**
