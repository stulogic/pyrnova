# M22-E — Opportunity Material Changes

_Status: delivered 2026-09-10 (D-060). Extends M22-A/B/C/D. Additive only._

## Problem

The customer-facing product was **threat-only**. The Material Changes architecture always supported
OPPORTUNITY / THREAT / MONITORING, and both the read model (`build_material_changes`) and the M22-C
fan-out already consumed an `opportunities` stream — but the demo estate produced only
`threats.jsonl` / `propagated_threats.jsonl`. There was no opportunity data to show. This was a design-
customer readiness P0: Pyrnova's thesis is *opportunity **and** threat*, and the running product only did
half of it.

M22-E is a **wiring / materialization / integration** milestone. It does **not** build a new opportunity
engine. It connects the opportunity engine Pyrnova already proved (M2–M11 Capture Radar) to the product
customers actually use.

## Authoritative source & representation (§39, §43, §44)

- **Engine:** the existing deterministic `detect_recompetes` (`pyrnova/engines/recompete.py`) — contract
  period-of-performance expiry within a forward window becomes a `recompete_expiry` opportunity carrying a
  mandatory falsification note. No new engine.
- **Model:** the existing `Opportunity` dataclass (`pyrnova/models.py`). No new model.
- **Stream:** the existing global `opportunities` stream that the read model and fan-out already consume.
  No new stream, no new persistence.
- **Identity (§43):** deterministic `opp_<sha256(award_id, catalyst_kind, subject_ref)[:20]>`, pinned in
  the demo seed from source-linked content (the pipeline's random `_uid` is not used for a materialized,
  replay-safe record). Stable across rebuild and fan-out; not prose-based; non-duplicative.

## Real evidence (§47)

Torch Technologies' own archived USAspending awards (`examples/real_evidence/usaspending_torch.json`) run
through the real engine at a pinned scan date (`2026-09-01`), a 540-day window, and a $100M materiality
floor → **6 real recompete opportunities** on Torch's large incumbent contracts (DIRECT_SUBJECT: Torch is
the incumbent). No live calls, no fabrication; the fixture is byte-reproducible (all engine-assigned ids
pinned). DAP has no active recompete in the archived estate and honestly stays threat-only — which also
proves the opportunity is isolated to Torch.

## Two genuine defects fixed (engineering doctrine §2/§3/§10)

1. **`_opportunity_change` conflated the tenant `customer_id` with the affected canonical entity.** The
   customer's `entity_refs` hold the canonical `co_*` ref, so using the tenant id as `subject_ref` broke
   DIRECT_SUBJECT relevance and investigation links. Fixed: the opportunity carries the canonical
   `subject_ref` (`co_torch`) + `subject_name` in `meta`, distinct from the tenant `customer_id`; the read
   model prefers the asserted canonical subject and falls back to `customer_id` only for legacy
   opportunities (no silent identity guess).
2. **Opportunities were read from `self.store` while threats/fan-out read from `mc_store`.** Unified to
   `mc_store` in both the Material Changes feed and the investigation estate (one canonical pattern) — a
   no-op in production (same store) and correct on a fresh checkout (demo fixture store).

## Truth-model properties (reused, not rebuilt)

- **Observed vs assessed (§45):** observed contract facts (incumbent, known value, period-end deadline,
  agency) stay in a separate structured block from Pyrnova's forward recompete assessment (confidence,
  falsification, recommended action). Never flattened. The known contract value is an OBSERVED fact and
  never masquerades as an assessed severity (materiality stays UNKNOWN).
- **Relevance (§46):** deterministic `assess_relevance`, unchanged. Torch's recompetes resolve
  DIRECT_SUBJECT; no LLM, no weak text similarity.
- **Temporal truth (§48/§49):** `observed_at` = the pinned in-window scan date (never earlier than
  knowable); `expected_action_at` = the real period-end deadline (future = legitimately active). A cutoff
  before the scan date hides the opportunity; a far-future scan of the same awards yields no candidate (an
  expired opportunity is not shown as active).
- **Customer-scoped fan-out (§52):** the M22-C `fan_out` / `CustomerMaterialChange` path, unchanged —
  deterministic, idempotent, customer-isolated, versioned, rebuild-safe. `first_relevant_at` never
  precedes `intelligence_observed_at`.
- **Lifecycle & outcomes (§53/§54):** the M22-B review lifecycle, unchanged (no parallel opportunity
  lifecycle); a derived rebuild never erases a customer action. Outcome linkage preserved; UNRESOLVED is
  first-class (no forced win/loss/conversion).
- **Investigation (§51):** every opportunity links to the affected company (`co_torch`) and program (real
  PIID) via the M22-D investigation block — no dead-end cards.

## Frontend (§55/§56)

`material.js` already rendered the OPPORTUNITY disposition (and `material.css` already styled it). Added
only the necessary opportunity distinctions beside THREAT: **known contract value** and **expected-action
deadline** (both omitted where not a fact, so threats are unaffected). No redesign, no separate
opportunities dashboard. §56 copy fix: `threat.py` economic-effect now names the affected entity
explicitly instead of the ambiguous "the subject's revenue" (threat id derives from
`(subject_ref, mechanism, anchor)`, not copy — no id ripple; consequence is not in the customer-scoped
content hash — no spurious versions).

## Non-goals honored (§58/§60)

No new source families; no natural-language search / RAG; no new relationship types or graph
visualization; no dashboard customization; no authentication/onboarding/IAM; no autonomous action; no
infrastructure or production-Postgres/Cloudflare work. Frozen components (`scoring_v1`, `fit.py`,
`replay.py`, severity bands, closed corpora) byte-identical.

## Tests

`tests/test_m22e_opportunity.py` (14) covers the §59 priorities: opportunity → Material Change;
deterministic identity; idempotent fan-out / duplicate suppression; relevance vs irrelevant-customer
suppression; storage isolation; lifecycle across rebuild; observed vs assessed; evidence references; no
future leakage; first-relevant ≥ observed; expired award → no active recompete; investigation links;
UNRESOLVED outcome; threat behavior unchanged. Full suite **571 passed** (was 557; +14).

## Files

- `examples/material_changes_demo/build_seed.py` — real-evidence opportunity generation → `opportunities.jsonl`.
- `pyrnova/material_changes.py` — `_opportunity_change` canonical subject + value; projection value/deadline.
- `pyrnova/ops.py` — opportunities read from `mc_store` (feed + estate).
- `pyrnova/threat.py` — §56 copy fix.
- `pyrnova/ops_web/material.js` — value/deadline distinctions.
