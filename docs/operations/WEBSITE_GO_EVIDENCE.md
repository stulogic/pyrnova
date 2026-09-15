# WEBSITE GO. Rendered acceptance evidence.

**Deliverable:** Pyrnova public informational website.
**Target state:** `WEBSITE GO / OUTREACH INTAKE DISABLED` (State 1).
**Current revision:** B (Revision A was owner-reviewed and acceptance was withheld).
**Prepared:** 2026-09-15.
**Status:** REVISION B, READY FOR OWNER REVIEW. Claude does not grant final owner acceptance.

State 1 means: safe to publish as an informational site; not safe to use as a public
evaluation-intake destination. Public evaluation intake (State 2) is a separate,
separately-authorized workstream and is intentionally not built here.

Branch `website-go-001`, isolated from the Live Ops soak (built on pinned base
`e7cb2c98c3594166cbcb4d5691c0f370d4c5eb57`). Imports no product code; shares no runtime,
state, secrets or configuration with `pyrnova/`, `ops/`, `var/`; never touches the soak.

---

## Revision B (owner rework)

### Why Revision A was rejected

Technical acceptance passed, but owner acceptance was withheld for severe visual and
product-authority drift: the site was bland and brochure-like and did not show Pyrnova
meaningfully. Revision B is the same workstream, not new strategy. Positioning, navigation,
the locked primary message, the intake-disabled doctrine and the excluded surfaces are
unchanged; the presentation was reworked to be a controlled static window into the product.

### Canonical authority actually read (Phase 0 preflight)

- `AGENTS.md` (disclosure and voice, binding; customer face of D-054).
- `00-INDEX.md`, `01-PROJECT-AUTHORITY.md` (Product language authority section).
- `docs/strategy/CORPORATE_POSTURE_AND_BRAND.md` (D-054 brand doctrine).
- `04-DECISIONS.md`: D-041 (Product Language Authority), D-054 (corporate posture and
  brand), with D-055 and D-062 for the Material Changes product surface and commercial ICP.
- Product UI: `pyrnova/ops_web/material.html` + `material.css`, `investigation.html` +
  `investigation.css` (the canonical Material Change and investigation grammar).
- `docs/brand/notion/pyrnova-notion-header.svg` (canonical mark and wordmark).

### Canonical brand assets used

- The canonical Pyrnova mark (mission-control reticle with a cyan-cored nova star) is
  extracted verbatim from `docs/brand/notion/pyrnova-notion-header.svg` into
  `website-go/assets/pyrnova-mark.svg` (cropped viewBox, geometry unchanged) and a matching
  `favicon.svg`. No invented logo. The wordmark is rendered as tracked "PYRNOVA" text exactly
  as the product masthead renders it (`letter-spacing: 0.32em`).
- Canonical brand cyan `#25cfe8` is used as signal only (mark, active nav, telemetry trace,
  live indicator), never as decoration.

### Product UI references used (visual continuity)

The website reuses the product's own design tokens and component grammar so the site and
`pyrnova/ops_web` read as one product family:

- Palette: `--bg #0b0d10`, `--panel #14181d`, `--panel-2 #1a1f26`, `--line`, `--ink`,
  `--ink-dim`, `--ink-faint`, and the semantic dispositions `--threat #d66b6b`,
  `--opportunity #6fae8f`, `--monitoring #b8a06a`, plus `--observed`, `--assessed`, `--accent`.
- The Material Change object grammar: disposition pill, materiality and confidence badges,
  headline, "Why it matters" with relevance basis, the observed-fact vs Pyrnova-assessment
  split panes, evidence chips (with single-source treatment), uncertainty and falsifier list,
  AS OF, provenance references, monospaced metadata.
- Investigation grammar: resolution result rows, identifier chips, section headers.

### Visual changes (A to B)

- HOME now exposes a full Material Change specimen in the first viewport, beside the locked
  message, over a restrained mission-control telemetry field (deterministic SVG reticle,
  orbital arc, signal node and evidence trace). It shows what Pyrnova does within seconds.
- INTELLIGENCE presents multiple connected product surfaces (three Material Change specimens,
  company exposure with relevance basis, resolution and evidence), not marketing cards.
- METHOD renders the intelligence chain visually (signal trace plus an eight-stage chain:
  signal, material change, customer exposure, commercial consequence, evidence, uncertainty,
  AS OF, decision implication).
- TRUST shows fact vs assessment, provenance, uncertainty and point-in-time integrity as
  product objects, with the implemented-vs-not-verified posture as two compact objects.
- RESEARCH shows point-in-time reconstruction (temporal axis), an illustrative thesis
  lifecycle (historical replay) and validation disciplines. No benchmark result is claimed.
- COMPANY is sparse and purposeful (functional metadata rows), not a headline-and-paragraphs
  brochure. Founder privacy preserved (founder-led only; no name, photograph, bio or contact).
- EVALUATE shows the output an evaluation produces (a labelled synthetic specimen) and states
  plainly that intake is not open, with no form, collection, calendar, upload or contact path.
- Copy reworked toward the Product Language Authority (D-041): functional and operational,
  literal section headings (Material Changes, Evidence, Point-in-time truth, Company exposure,
  Historical replay, Current posture). The owner-locked primary message is preserved.
- All specimens are clearly labelled `SYNTHETIC SPECIMEN / NIGHTGLASS` and are never presented
  as live production output.

### Zero em dash

Enforced by test and by full-tree scan of `website-go/` source and built `dist/`:
**em dash (U+2014) count = 0.**

### Critique pass (after first Revision B render)

1. Shares DNA with the Pyrnova app: PASS (same tokens, Material Change grammar, mono metadata).
2. Real intelligence object visible immediately: PASS (HOME first viewport specimen).
3. A serious defense/GovCon executive understands the product: PASS.
4. Feels expensive and institutionally capable: PASS.
5. Generic SaaS/brochure drift: PASS (removed; product-forward, functional copy).
6. Canonical identity intact: PASS (canonical reticle/nova mark and wordmark).
7. Mobile still has impact: PASS (specimens legible at 390px; intentional nav strip).

Targeted corrections applied after the pass and re-rendered: tightened interior page-head
line-height (institutional density), and hid the compressed signal-trace SVG on mobile to
avoid microscopic telemetry (the chain grid carries it legibly). No positioning was reopened.

---

## Implementation

- Static, dependency-free site. Node standard-library generator renders fixed content to
  `dist/` as one static HTML file per route. No JavaScript is shipped, no server logic, no
  framework, no external font, SDK or tracker. Motion is CSS only (signal pulse, evidence
  trace, quiet reveal) and respects `prefers-reduced-motion`. Environmental graphics are
  deterministic inline SVG.

### Site routes (locked authority)

`/` (HOME), `/intelligence/`, `/method/`, `/trust/`, `/research/`, `/company/`, `/evaluate/`.
Primary nav: INTELLIGENCE, METHOD, TRUST, RESEARCH, COMPANY, EVALUATE. Primary message:
"Know what changed. Know what it changes." All routes return 200; unknown routes return 404.

## EVALUATE, intake-disabled verification

EVALUATE omits the intake form entirely and states: "Public evaluation intake is not open ...
there is no submission form or account sign-up here, and this site does not collect your
details." Verified across all routes (tests plus source and rendered inspection):

- Personal-data fields present: NO (no input, textarea, select anywhere).
- Submit action present: NO (no form, no submit control).
- Hidden collection path present: NO (no script, no inline handler, no fetch/XHR/sendBeacon,
  no `/api/` reference).
- Calendar / file upload / founder workaround present: NO (no mailto/tel, no booking/forms
  provider, no file input, no personal contact).
- No invented privacy/controller identity; no dormant intake endpoint stored for later.

## Trust and claims discipline

- Implemented/tested product semantics described: evidence provenance, source attribution,
  observed-vs-assessed separation, materiality and confidence, AS OF and replay, source-rights
  controls, application-layer customer isolation.
- Explicitly not claimed: SOC 2, FedRAMP, ISO 27001, CMMC, database row-level security,
  production MFA/SSO, penetration testing, backups/DR, encryption at rest, production TLS,
  24/7 monitoring, authority to process FCI/CUI/classified data. Application-layer isolation is
  distinguished from database row-level security. SOC 2/FedRAMP/ISO/CMMC appear only in their
  negation on the Trust page (enforced by test). Unsupported legal/security claims found: NONE.

## Founder privacy

No founder photograph, name, legal/controller identity, social profile, education,
nationality, location, immigration, family, personal phone/email or personal narrative.
COMPANY describes Pyrnova as founder-led only.

## Browser acceptance (real rendering)

Rendered in a real browser engine (headless Chrome / "Google Chrome for Testing"). Desktop at
1440 width; mobile at a true 390px layout viewport (each page loaded inside a 390px iframe
within a 420px frame; the grey margin in a mobile capture is the frame, not the page. Page
content ends cleanly at 390px with no horizontal overflow).

### Screenshots reviewed (`website-go/evidence/screenshots/`)

Desktop (1440): `desktop-home.png`, `desktop-intelligence.png`, `desktop-method.png`,
`desktop-trust.png`, `desktop-research.png`, `desktop-company.png`, `desktop-evaluate.png`.
Mobile (390): `mobile-home.png`, `mobile-intelligence.png`, `mobile-method.png`,
`mobile-trust.png`, `mobile-research.png`, `mobile-company.png`, `mobile-evaluate.png`.

- Desktop render review: PASS.
- Mobile render review: PASS (no overflow; specimens legible; intentional scrollable nav strip).

## Build and tests

- `npm run build`: renders 7 static pages plus `site.css`, `favicon.svg`, `pyrnova-mark.svg`,
  `robots.txt`, `sitemap.xml`. PASS.
- `npm test` (`node --test`, standard library, no dependencies): 12 suites PASS / 0 FAIL.
  Covers: required routes; locked nav; complete documents (no placeholder); locked home
  message, both CTAs and a first-viewport Material Change specimen; canonical mark referenced
  with canonical cyan; zero em dash across source and rendered output; no form/input/textarea/
  select/submit; no script/inline handler/collection call; no mailto/tel/api/booking provider;
  EVALUATE intake-closed with an output specimen and no submission; specimens labelled
  synthetic; no certification claims outside the Trust negation.
- No backend/product tests were run (no product code was touched).

## Soak non-interaction

Running soak process, configuration, checkpoints, cadence, environment and evidence directory
`var/phase1_soak/evidence_source_counter_fix_2026-09-12`: not touched, not tested against, not
deployed into. The directory is not present in this base checkout. The pinned soak worktree and
acceptance-critical product code are unmodified.

## Residual deployment dependencies (outside this task)

State 1 is publishable as-is. Before public launch the owner still controls domain/DNS and
hosting account setup and TLS/CDN at the chosen host. State 2 (public intake) remains
separately authorized and is not built.

## Final state

`WEBSITE GO / OUTREACH INTAKE DISABLED`, Revision B, READY FOR OWNER REVIEW.
