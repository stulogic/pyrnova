# Customer product — premium visual redesign (FRONTEND-R2 / R3)

**Branch:** `international-government-rollout-001`  **Starting tip:** `48b8eb3`
**Scope:** one coherent visual + UX pass over the existing customer SPA. No backend
semantics, no API contracts (one additive static-asset route only), no framework migration,
no rebuild. Plain HTML/CSS/vanilla-JS preserved. Real data only.

## Thesis (evidence-led, not improvised)

Prior repository evidence outranks a fresh aesthetic. The accepted Pyrnova house style
already existed in `material.css`, `investigation.css` **and** the public site
(`website-go/assets/site.css`): dark graphite, steel accent, a cold cyan *signal* accent
used sparingly, semantic disposition colour, and mono + wide-uppercase metadata. The
`FRONTEND_WEBSITE_RECOVERY_LEDGER` recorded the intended character — "calm, restrained,
evidence-led."

The stale surface was **`product.css`** — a generic blue (`#6ea8fe`) SaaS theme that had
never been brought onto the house style. The redesign therefore **unifies every surface on
the accepted house system and elevates them together**, rather than inventing a new look.

## Visual system (`system.css`, new shared stylesheet)

One design-system stylesheet, served publicly and linked first by every customer surface
(and the operator console). It owns the tokens (the accepted house palette), the textured
body, typography, and the shared primitives. Route added in `ops_server.py`
(`/system.css`) — the only server change, a static-asset seam; no API/product semantics.

- **Elevation hierarchy:** `--bg` (near-black) → `--surface-1` (work surface / cards) →
  `--surface-2` (analysis panels) → `--inset` (evidence / detail layer), with hairline
  (`--line`) and interactive (`--line-2`) separators.
- **Texture / atmosphere (barely perceptible, fixed, non-animated):** near-black base + a
  faint 46px technical grid + a soft overhead vignette + a sub-2.5%-opacity SVG grain
  overlay. Never wallpaper, no scanlines, no CRT, readability first.
- **Semantic colour:** open/positive = subdued green; caution/watch = controlled amber;
  blocked/denied = restrained red; monitoring/post-award = muted steel; source vs derived =
  steel vs muted violet; live/now = cold cyan (sparingly). Not a rainbow — the default
  surface stays neutral.
- **Typography:** legible system sans for reading; `--mono` (tabular) for identifiers,
  timestamps, SHA-256, AS-OF and provenance; a canonical uppercase-tracked `.label` micro
  style for metadata (the "technical voice" done without a novelty font — offline-safe).
- **Primitives:** pills/badges/chips (semantic variants), a thin confidence/relevance
  **meter**, restrained buttons (cyan primary, not neon), grouped section headers,
  audit-grade evidence styling, empty/loading/error states, the persistent Lens strip.

## Per-surface improvements

- **Customer Lens context strip (new, persistent):** whose bounded lens, live-vs-as-of
  state, and a compact count summary (opportunities / material changes / uncertain) — sits
  under the masthead on every route, populated from real `/api/lens` data.
- **Opportunity queue:** each item now reads as an intelligence record — `OPP·<code>`,
  pursuit verdict + qualitative confidence, why-now, attractiveness/confidence **meters**,
  decision-window chip (`Window · N days`), value, evidence count, your-view, rights state —
  hierarchy instead of a raw field dump.
- **Decision View (strongest surface):** reorganised into labelled intelligence groups —
  **Why it matters / disposition** (verdict + confidence + supports/against + reversal),
  **What changed / why now**, **Decision window**, **Access / route**, **Customer
  consequence / fit**, **Incumbent / competitive**, **Uncertainty (falsifiers)**,
  **Evidence (audit trail)**, **Decision memory / temporal**. Confidence meters bind to real
  numeric values.
  - **Bug fixed with real data:** the Access section read `dc.access.status` (nonexistent),
    so it always showed *Unknown*; it now reads the real `dc.access.verdict`
    (`DIRECT_ACCESS`) + `summary` + teaming/vehicle. Purely a display fix — no backend change.
- **Evidence Inspector:** audit-grade provenance — source + media type (structured record
  vs document), reference, distinct **Published / Retrieved / First-seen** dates, retention
  tier, SHA-256 integrity, official-record link, a Source→Retrieved→Retained→Assessed chain,
  and rights state. Presented as evidentiary support, not debug metadata.
- **Material Changes / Investigation:** brought onto the shared system (texture + primitives)
  by inheriting `system.css`; their own strong observed-vs-assessed / disposition-rail
  treatments are retained.
- **Operator console (internal, local-only):** aligned to the house palette (off the lime
  terminal look) while keeping its instrument character (mono body, serif headings).
- **Access gate:** restyled onto house tokens (cyan-accented, restrained).

## Guardrails honoured

Dark-first (matches the existing Material/Investigation surfaces and the target aesthetic);
no fake reticles/radar/crosshairs/skulls/scanlines/glitch/neon HUD; motion is a single
subtle loading pulse that respects `prefers-reduced-motion`; every treatment maps to a real
field; **no mock data** — empty/Unknown states render honestly.

## Proof

- Full Python regression: **1033 passed, 2 skipped, 0 failed** (no backend behaviour changed).
- Frontend asset + route + real-data checks green (`test_b3`, `m22c`, `m22d`, `m22f`).
- Rendered snapshots: `docs/frontend/render/` — real `product.js` executed against real
  server JSON with real CSS inlined (see that folder's `README.md`). Pixel screenshots need
  a browser/headless tool (unavailable offline this session); the saved pages are the
  rendered substitute.

## Launch

```sh
cd /Users/stu/Documents/Pyrnova-intl
source .venv/bin/activate
python -m pyrnova.ops_server         # → http://127.0.0.1:8765/   (tenant: torch or dap)
#   /material.html  Decision View / Material Changes / AS-OF
#   /investigate    Evidence Inspector / investigation
#   /console        operator console (local-only)
```
