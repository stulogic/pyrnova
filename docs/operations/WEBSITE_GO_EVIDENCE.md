# WEBSITE GO. Rendered acceptance evidence.

**Deliverable:** Pyrnova public informational website.
**Target state:** `WEBSITE GO / OUTREACH INTAKE DISABLED` (State 1).
**Current revision:** B, with final polish pass applied (Revision A acceptance was withheld;
Revision B was conditionally accepted; this pass applies six bounded refinements).
**Prepared:** 2026-09-15.
**Status:** OWNER ACCEPTED / CLOSED. Revision B final polish is complete and the owner has
granted final acceptance (see "Owner acceptance and closure" below). This record was previously
"READY FOR FINAL OWNER ACCEPTANCE"; owner acceptance has now been given.

State 1 means: safe to publish as an informational site; not safe to use as a public
evaluation-intake destination. Public evaluation intake (State 2) is a separate,
separately-authorized workstream and is intentionally not built here.

Branch `website-go-001`, isolated from the Live Ops soak (built on pinned base
`e7cb2c98c3594166cbcb4d5691c0f370d4c5eb57`). Imports no product code; shares no runtime,
state, secrets or configuration with `pyrnova/`, `ops/`, `var/`; never touches the soak.

---

## Owner acceptance and closure (WEBSITE-GO-001)

**Owner decision:** ACCEPTED.
**Recorded:** 2026-09-15.
**Accepted implementation (Revision B final-polish baseline):**
`8e5ae46559f605816116b43ecf46cf543c5eca77` (tip of `website-go-001`).
**Accepted operating state:** `WEBSITE GO / OUTREACH INTAKE DISABLED`.
**Disposition:** OWNER ACCEPTED / CLOSED. This is now the non-regression baseline.

The owner has granted final acceptance of the Revision B final-polish website at the commit
above. No further design or copy iteration is authorized under this workstream.

### Scope of this acceptance (important)

This acceptance is for `WEBSITE GO / OUTREACH INTAKE DISABLED` (State 1) only. It is explicitly
NOT `WEBSITE GO / OUTREACH READY`:

- It authorizes publishing the site as an informational destination.
- It does NOT authorize public evaluation intake (State 2).
- It does NOT satisfy the separate OUTREACH READY gate, which remains independently gated and
  separately authorized. Nothing here opens intake, adds a submission or contact path, or
  changes the intake-disabled operating state.

### Non-regression baseline (preserved)

The accepted implementation is the baseline. Preserved without regression: canonical Pyrnova
mark and wordmark; dark institutional palette; restrained cyan `#25cfe8` signal treatment;
telemetry / texture treatment; product-forward home hero; Material Change specimen prominence;
product UI grammar; observed-fact vs Pyrnova-assessment distinction; evidence / uncertainty /
falsifier / provenance / AS OF presentation; page architecture; desktop composition; wrapped
mobile navigation; mobile readability treatment; State 1 CTA language "SEE HOW EVALUATION
WORKS"; EVALUATE terminology in navigation and descriptive contexts; synthetic specimen
disclosure; trust posture; zero-em-dash rule; intake-disabled operating state.

Future video, motion, real product screenshots, richer product demonstrations and conversion
improvements are DEFERRED enhancement work under a later separately authorized scope. They are
not defects in WEBSITE-GO-001 and are not to be started now.

### Preserved evidence at acceptance

- Desktop (1440) and mobile (390) render review: PASS (see "Browser acceptance" below).
- `npm run build`: PASS.
- `npm test`: 14/14 PASS (State 1 CTA-semantics and NIGHTGLASS-absence checks included).
- Em dash (U+2014) count: 0 across source and `dist/`.
- Intake-disabled invariants: verified (no input/form/submit, no hidden collection path, no
  calendar/upload/founder workaround, no dormant endpoint).
- Live Ops soak: not touched, not tested against, not deployed into. No process, configuration,
  checkpoint, cadence or evidence change.

The test count is 14/14 for the final-polish pass; the "Build and tests" section below records
the pre-polish 12-suite baseline and the polish pass added the State 1 CTA-semantics and
NIGHTGLASS-absence checks. Both records are retained for provenance.

---

## Revision B final polish pass

Applied on the protected Revision B baseline `9cbe0ea`. Six bounded refinements only; no
redesign. Every locked element (visual direction, canonical mark and wordmark, dark palette,
cyan-as-signal, telemetry treatment, specimen prominence, product-forward first viewport,
product UI continuity, evidence/uncertainty/provenance/AS OF grammar, page architecture, State
1 intake-disabled state, zero em dash, trust posture) was preserved.

Files changed: `website-go/src/site.mjs`, `website-go/assets/site.css`,
`website-go/tests/site.test.mjs`, `website-go/evidence/screenshots/*`, and this record.

1. **Mobile readability.** Added a narrow-screen typography block: specimen metadata bumped up
   1 to 2px (facts labels/values 13px, monospaced values 12px, evidence chips 12px, why-detail
   14px, badges 12px, caption 10.5px, foot 12.5px), with more specimen padding. Density and the
   authentic product grammar preserved; the headline was not inflated. Before: 10 to 12px
   metadata was hard to read at 390px. After: materially clearer, still dense.
2. **Mobile navigation.** Replaced the horizontal-scroll strip (which hid RESEARCH and COMPANY)
   with a wrapping module strip so all five section routes plus EVALUATE are visible at 390px.
   Before: two routes were only reachable by an undiscoverable horizontal scroll. After: every
   route is visible. Restrained language kept; no SaaS drawer or hamburger introduced.
3. **State 1 CTA semantics.** The primary button copy changed from "Evaluate Pyrnova" to
   "See how evaluation works" on the home hero and the closing section, and the closing heading
   changed from "Evaluate Pyrnova against ..." to "An evaluation tests Pyrnova against ...".
   EVALUATE is retained as the nav/section label and the evaluate page kicker (terminology kept
   for a future OUTREACH READY state). A test now rejects any button copy implying active
   submission. No intake, form, booking, mailto or founder-contact path was added.
4. **Home hero hierarchy.** The second line "Know what it changes." was changed from `--ink-dim`
   to full `--ink`, so it no longer reads as disabled or unimportant. Composition and tone
   unchanged.
5. **Public terminology.** NIGHTGLASS is not established canonical public terminology under
   current authority (no supporting material exists in the repository), so it was removed from
   specimen captions and the footer. The required `SYNTHETIC SPECIMEN` disclosure is retained.
   No replacement terminology was invented. A test asserts NIGHTGLASS does not appear publicly.
6. **Minor copy tightening.** The closing heading reword above is the only copy change beyond the
   CTA wording; positioning was not touched and no generic marketing language was introduced.

Additional defect fixed during verification (necessary for the required no-overflow check): the
decorative hero telemetry field bled ~8px past the viewport, adding to page scroll width. The
field is now clipped to the hero box (`.hero { overflow: hidden }`); measured page scroll width
now equals the viewport at 390, 500 and 1440 (no horizontal page overflow). The field's
appearance is unchanged.

Verification: `npm run build` PASS; `npm test` 14/14 PASS (adds State 1 CTA-semantics and
NIGHTGLASS-absence checks); em dash count 0 across source and `dist/`; all seven routes
re-rendered at 1440px and true 390px; no horizontal overflow; specimens remain credible and
clearly synthetic; all routes discoverable on mobile; CTA represents State 1; no intake or data
collection introduced; no product code or Live Ops soak touched. Screenshots refreshed in
`website-go/evidence/screenshots/`.

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

`WEBSITE GO / OUTREACH INTAKE DISABLED`, Revision B final polish, OWNER ACCEPTED / CLOSED.
Accepted baseline commit `8e5ae46559f605816116b43ecf46cf543c5eca77`. This is the non-regression
baseline. OUTREACH READY remains a separate, independently gated authorization and is not
granted by this acceptance.
