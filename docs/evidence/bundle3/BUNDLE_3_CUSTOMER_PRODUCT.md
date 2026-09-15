# PRELAUNCH-CONVERGENCE-001 — Bundle 3 evidence: Customer Product Experience + Delivery

Scope: convert the accepted Bundle-2 integrated decision object into a usable, tenant-safe, rights-aware
customer product and a reliable customer delivery path. Backend service + HTTP routes + Customer Lens SPA +
delivery contract, all composed from ALREADY-PERSISTED accepted intelligence. No fabricated verdicts, no
invented composite scores, no fabricated external delivery.

## B3.0 — SEC archival residual (rights fail-closed)
`test_source_expansion::offline_source_expansion` was red because the offline source-expansion path
archived raw SEC submissions/companyfacts bytes, which `representation_for_storage` rejects for
`sec_edgar`'s NORMALIZED_ONLY posture. Fixed by archiving through the reviewed structured-fact contract
used by `sec_edgar.archive_observation` (derived facts + hash provenance, allowlisted storage metadata):
raw source expression is never durably stored, `original_content_sha256` links back to the raw page for
audit. Rights preserved, not weakened. Now GREEN with a focused normalized-only assertion.

## Customer product surface (composed, not duplicated)
- **Customer Lens (B3.1)** `GET /api/lens`, served at `/` (product.html): what materially changed, which
  opportunities matter, what is uncertain.
- **Material Changes (B3.2)**: the accepted M22 consequence feed remains first-class (`/material.html`,
  `/api/material-changes`) and is surfaced in the Lens.
- **Opportunities (B3.3)** `GET /api/opportunities`: prioritisation list of persisted opportunities
  (catalyst=why-now, incumbent, recommended action, native attractiveness/confidence signals surfaced
  as-is — NOT combined into a fabricated composite). UNKNOWN preserved.
- **Opportunity Decision View (B3.4)** `GET /api/opportunities/<id>/decision`: coherent decision chain
  (why-now → buyer → incumbent/competitive → access → customer fit → pursuit → material changes →
  next action → evidence → temporal → uncertainty) plus the composed B2.10 Integrated Decision contract by
  reference. Pursuit shows the persisted recommendation + native signals + reversal; the PURSUE/WATCH/
  INVESTIGATE/PASS verdict is left **UNKNOWN** where Bundle-2 pursuit inputs are not persisted per
  opportunity — never fabricated.
- **Customer Intelligence Profile (B3.5)**: the persisted customer profile is surfaced with provenance
  labelling (customer-supplied vs Pyrnova-derived); the derived narrative is explicitly `PYRNOVA_DERIVED`.
- **Evidence Inspector (B3.6)** `GET /api/opportunities/<id>/evidence/<eid>`: source fact / provenance
  (content_sha256, source_url) / observed-at, rights-gated fail-closed.
- **As-of / Known-then/Known-now (B3.7)**: every read takes `as_of`; a past cutoff never surfaces evidence
  first-seen after it.
- **Customer Disposition (B3.8)** `POST /api/opportunities/<id>/disposition` → Decision Memory
  (origin `CUSTOMER_FEEDBACK`, tenant-isolated, distinct from Pyrnova judgment).
- **Search (B3.9)** `GET /api/search` over the customer-visible decision surface.
- **Authenticated brief download (B3.10)** `GET /api/opportunities/<id>/brief[?download=1]`: deterministic
  (audit-stable content hash), rights-aware, tenant-safe.
- **Customer delivery (B3.11)** `pyrnova/customer_delivery.py` + `POST /api/opportunities/<id>/deliver`:
  explicit tenant, operator-authorized recipients, deterministic delivery id / dedupe (no duplicate mail on
  reissue/restart), PENDING→DELIVERED|FAILED|RIGHTS_BLOCKED lifecycle, bounded retry that resumes the same
  delivery, durable failure audit (no silent loss), rights fail-closed. Decoupled from operator alerts
  (reuses only the generic email transport seam). **REAL EXTERNAL DELIVERY VERIFICATION is pending**: with
  no verified SMTP transport the default `DisabledTransport` raises, so a send is recorded FAILED, never
  fabricated as DELIVERED.

Rights note: the Pyrnova-DERIVED opportunity narrative is gated on the underlying source POLICY via the
canonical derived-projection gate (as the Material Changes feed does), not the copied-source-prose
heuristic that governs verbatim text; raw source facts stay separately inspectable and gated. No
source-rights weakening.

## B3.14 — integrated authenticated flow
`tests/test_b3_integrated_flow.py` drives the real handler with enforced auth and a customer credential
through Lens → Material Change → Opportunity → buyer/incumbent/access/fit → Pursuit → Evidence → As-of →
Disposition → brief export → delivery, asserting cross-tenant isolation at every step and no fabricated
transport success.

## B3.15 — real MTSI / Torch product proof (existing accepted data only)
Observed through the Bundle-3 product:

**Torch (persisted opportunities, real usaspending evidence):**
- Opportunities surfaced: 6; Lens material changes: 8 (6 OPPORTUNITY / 2 THREAT) — not empty, not noisy.
- Representative opportunity: "Recompete watch: Department of Defense — incumbent TORCH TECHNOLOGIES INC
  (ends 2026-09-30)".
- Why-now: `recompete_expiry` — "Contract period of performance ends 2026-09-30 (1.0 months)."
- Native signals: attractiveness ≈ 0.91, confidence ≈ 0.59 (surfaced as-is; no composite).
- Pursuit verdict: **UNKNOWN** (honest — Bundle-2 pursuit inputs not persisted per opportunity); the real
  persisted recommended action is still shown.
- Evidence sources: `usaspending` (real). Decision source-rights display: PARTIAL (some related material
  changes are rights-restricted and correctly minimized).
- Brief representation is truthful: carries the rights disposition and explicitly states the pursuit
  verdict is UNKNOWN; makes no unsupported certainty claim.

**MTSI (accepted profile + real usaspending_mtsi evidence file, no persisted opportunities here):**
- Onboarded from the accepted profile. Opportunities surfaced: **0** — an honest, empty lens, not
  fabricated and not noisy. MTSI never sees Torch's opportunities (tenant isolation holds).
- What remains UNKNOWN: MTSI has no persisted opportunity/material-change intelligence in this
  environment; producing MTSI opportunities is an ingestion/fan-out step, not a product-layer concern.

## Tests
Focused Bundle-3 suites: `test_source_expansion` (B3.0), `test_customer_delivery` (B3.11 contract),
`test_b3_customer_product` (surface + routes + tenant isolation), `test_b3_integrated_flow` (B3.14),
`test_b3_mtsi_torch_proof` (B3.15). See the Bundle-3 final return for full-regression counts.
