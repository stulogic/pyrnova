# M18 — independent relationship expansion + archived adverse catalysts

_Status: CLOSED 2026-09-09 · canonical for M18 additions. Builds on
`docs/specs/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md` (real relationship grounding + propagation) and
`docs/specs/M15_THREAT_INTELLIGENCE.md` / `M16_THREAT_CALIBRATION_PROPAGATION.md` (threat/exposure/
propagation/calibration semantics), which it does not repeat._

M17 proved **real relationship → real propagation** over ONE company pair (SAIC↔Torch) with a *modeled*
adverse catalyst. **M18 proves the harder, empirical claim: a REAL, ARCHIVED, OBSERVED adverse event →
real catalyst → real exposure → an INDEPENDENT real company relationship → a real propagated threat**,
with an auditable chain at every hop and no alarm explosion.

Additive only: `scoring_v1` / `fit.py` / `replay.py` and every frozen corpus (incl. `corpus_m15`,
`corpus_m16`, `corpus_m17`) are **byte-for-byte unchanged**. New module `adverse_events.py`; additive
edits to `relationships.py`, `threat.py`, `propagation.py`, `threat_calibration.py`, `ops.py`; new
`corpus_m18.json`.

## A. Second (and third) independent real relationship — 0 new calls (Workstream A/B)

`relationships.exposed_prime_awards_from_subawards(parsed, prime_name)` establishes a PRIME's incumbency
from the **authoritative sub-award PRIME fields** (prime recipient + globally-unique prime PIID) in the
already-archived `examples/real_evidence/usaspending_subawards_torch.json` — exactly the prime-side
exposure evidence M17 lacked for Torch's non-SAIC primes. Passing that PIID set to
`ground_subaward_edges` promotes the prime's edge to a program-anchored (CONFIRMED /
`deterministic_native_id`) real relationship. Two independent pairs are grounded, **neither SAIC**:

- **Parsons Government Services → Torch** on MDA prime award `HQ085821C0015` (4 sub-awards).
- **Intuitive Research & Technology → Torch** on Army prime award `W31P4Q23FC001` (repeat).

Relationship diversity is reported by `relationships.independence_metrics` (unique company pairs, roots,
relation types, source families, observed chains) so "N real cases that are all one relationship" can
never read as breadth.

## C/D/G/H. Archived OBSERVED adverse-event catalysts (`adverse_events.py`)

`parse_federal_register_adverse(raw)` normalizes archived, authoritative **Federal Register BIS/Commerce
export-control & Entity List rules** into first-class **OBSERVED** catalysts, retaining the source-native
identifier (FR document number), event type, agency, publication/knowability date, RIN, docket ids,
source URL, an archive hash, and the raw record (nothing useful discarded). `to_regulatory_catalyst`
emits the catalyst record the existing threat engine consumes — **no parallel threat architecture**.

Catalyst **authority** is durable and first-class (Workstream H): every catalyst / threat carries
`catalyst_class ∈ {OBSERVED, MODELED, SYNTHETIC, PROBE}`; a record with no declared class is `MODELED`,
so **no earlier M16/M17 fixture is silently relabelled OBSERVED**. The distinction travels onto every
`Threat.meta` (direct and propagated).

Evidence archived once at `examples/real_evidence/federal_register_bis_export_controls.json` (**1 live
Federal Register call**, keyless, public domain; content hash recorded in-file). All development and
replay are offline.

## I. Real end-to-end observed chains (`corpus_m18.json`)

Two flagship chains, INDEPENDENT of SAIC↔Torch, driven by the SAME real observed rule (FR **2026-17231**,
"Revisions to the Entity List", RIN **0694-AK49**, published **2026-08-24**):

- **Parsons → Torch** — export-control rule (OBSERVED) → `REGULATORY_COMPLIANCE_EXPOSURE` on Parsons
  (INFERRED EAR exposure via its MDA missile-defense R&D prime, MODERATE/MEDIUM) → propagated one hop to
  Torch via the real program-anchored Parsons→Torch edge (LOW/LOW — degraded, never increased).
- **Intuitive → Torch** — same rule → `REGULATORY_COMPLIANCE_EXPOSURE` on Intuitive (Army weapon-system
  engineering prime) → propagated one hop to Torch. A different company pair, agency and program.

`tests/test_m18_observed_catalyst.py` is the honesty gate: the corpus OBSERVED catalyst is reproduced
from the archived FR bytes; the two edges are the SAME program-anchored edges `ground_subaward_edges`
derives from archived sub-award bytes; and the same rule yields NO threat where there is no evidenced
exposure.

## Negative discipline — no propagation spam (Workstream D/P)

The prime's export-control exposure is **INFERRED**, not deterministic, so a broad rule never becomes a
deterministic hit; and propagation crosses only explicit archived edges. The corpus proves:

- **no exposure → no threat** — the same real rule threatens a company only where it declares an evidenced
  REGULATION exposure to *that* rule (`NO_EXPOSURE`); a BIS/EAR action is never an automatic exposure.
- **real weak edge terminates** — NTSI is a real MDA prime, but subcontracts Torch once, so the real
  NTSI→Torch edge is `name_only_weak`: the direct threat exists, propagation terminates.
- **temporal truth** — the rule published 2026-08-24 is excluded at a 2026-01-01 cutoff.

## K/L/M/N/O/Q. Metrics, calibration, selectivity, panel

- `relationships.independence_metrics` + `threat.summarize_m18` report catalyst authority (OBSERVED vs
  MODELED) and relationship independence.
- `threat_calibration.propagated_outcome_calibration` begins distinguishing resolved **DIRECT** from
  resolved **PROPAGATED** outcomes (each precision WITH its denominator; small-N flagged). Resolved
  outcomes grew **12 → 15**.
- The new source feeds the SAME `selectivity.run_selectivity` + `source_run_funnel` (Workstream N/O): a
  real rule threatens only the evidenced-exposure company; the raw-events→threats drop is measured with
  call/yield accounting (1 call made, 7 avoided).
- `ops.py` (thin): `company_threat_network_view` surfaces each threat's catalyst authority;
  `adverse_catalyst_view` surfaces archived observed catalysts + independence counts. No second console.

## Corpus & metrics

`corpus_m18.json` (11 new cases) **extends** `corpus_m17` (byte-identical) → **57 cases, all pass**, own
point-in-time replay, `scoring_v1` untouched. Merged metrics (directional, small sample):

- **41 direct threats, 12 propagated** across 12 chains (2 REAL observed independent chains + 2 real M17
  SAIC chains among 4 real propagation cases); **3 observed-catalyst chains**; **max depth 2, no
  explosion** (`propagated ≤ direct`); confidence never increases (proven); cycles/duplicates suppressed;
  a real weak edge terminates.
- **11 unique company pairs**; catalyst authority **5 OBSERVED / 36 MODELED** direct (distinct, durable);
  **13 negative/zero-threat cases**.
- Resolved outcomes **15**, confirmed precision **0.9333 over 15**, median lead **337 days**;
  `false_alert_from_absence` **0**. Propagated calibration: **1** resolved propagated (directional).

**1 live Federal Register call** (archive-once). Full suite: **445 passed**.

## Acceptance gate

All 40 M18 acceptance criteria are met — see `docs/replay/M18_INDEPENDENT_ADVERSE_EVENTS.md`.

## Limitations (explicit)

- Both flagship observed chains use the **export-control regulatory family** and an **INFERRED** prime
  exposure (missile-defense/defense-article work subject to EAR), so direct threats are MODERATE/MEDIUM.
  A *deterministic* observed exposure (e.g. a real counterparty of a BIS-listed entity, or a
  program-specific cancellation notice tied to a PIID) awaits archived evidence that does not yet exist.
- Relationship **type** diversity is still `SUBCONTRACTOR_OF` for the real chains (plus `SUBSTITUTE_FOR`
  beneficiary + a `DEPENDS_ON` edge from M16); COMPANY_TO_PROGRAM/SUPPLIER_OF/etc. remain roadmap items,
  added only when real evidence requires them.
- Resolved-outcome growth is modest (12 → 15) and honest: the new 2026 adverse events have no knowable
  later outcome yet, so the additions are clearly-labelled directional structured observations plus the
  real M17 outcomes. Propagated calibration rests on **1** resolved propagated threat (directional only).
- One adverse-event family (Federal Register / BIS export controls) is integrated; WARN/facility and
  program-cancellation families remain on the roadmap (added only when they materially improve evidence).
