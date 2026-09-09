# M19 — deterministic OBSERVED exposure + multi-family adverse-event validation

_Status: CLOSED 2026-09-09 · canonical for M19 additions. Builds on
`docs/specs/M18_INDEPENDENT_ADVERSE_EVENTS.md` (archived OBSERVED catalysts + independent real
relationships) and `M15`/`M16`/`M17` (threat/exposure/propagation/calibration semantics), which it does
not repeat._

M18 proved a REAL, archived, OBSERVED adverse event → real exposure → independent real relationship →
real propagated threat, but the observed chains still rested on an **INFERRED** prime exposure
(MODERATE/MEDIUM) in ONE adverse-event family (BIS/Federal Register export controls). M19 strengthens
empirical truth on two axes: a **deterministic OBSERVED exposure** carrying a **HIGH-confidence** direct
threat, and a **second adverse-event family** materially independent of export-control rules.

Additive only: `scoring_v1` / `fit.py` / `replay.py` and every frozen corpus (incl. `corpus_m15`…
`corpus_m18`) are **byte-for-byte unchanged**. Additive edits to `adverse_events.py`, `threat.py`,
`propagation.py`, `ops.py`; new `corpus_m19.json` + two tests.

## A. Second adverse-event family — USAspending contract modifications (`adverse_events.py`)

`parse_usaspending_contract_modifications(raw)` normalizes archived USAspending contract-modification
bytes into first-class **OBSERVED** `contract_modification` adverse events: a real, dated, source-native
contract **deobligation** (negative `federal_action_obligation`) on a specific PIID held by a specific
recipient UEI. `contract_target_ref(event)` is the exact PIID (the deterministic join key);
`to_contract_contraction_catalyst(event)` emits a `funding_reduction` catalyst the **existing**
`threat._assess_program_change` engine consumes (→ `PROGRAM_CONTRACTION`) — no parallel architecture.

This family is materially different from the BIS/Federal Register export-control family: a different
source, mechanism (contract-funding contraction vs regulatory compliance), and — critically — a
**deterministic native-id** join rather than an inferred EAR exposure.

Evidence archived once at `examples/real_evidence/usaspending_contract_mods_saic_47QFSA20F0057.json`
(**3 live USAspending calls**, keyless, public domain; content hashes recorded in-file). All development
and replay are offline.

## B. Deterministic exposure authority (`threat.exposure_join_class`)

The existing `incumbency_exposures` already grounds a **deterministic** PROGRAM/INCUMBENT exposure when a
subject's own award recipient UEI matches an award (`deterministic_native_id` / CONFIRMED) — linkage
strictly stronger than fuzzy name, broad industry, shared geography, modeled incumbency, or an inferred
prime relationship. M19 makes that authority **first-class and durable**: `exposure_join_class(exposures)`
∈ {`deterministic`, `inferred`, `candidate`} travels on every `Threat.meta` (direct **and** propagated,
retained across every hop), parallel to catalyst authority. The catalyst→exposure join is itself
deterministic — the `funding_reduction` catalyst's `target_ref` must equal the exposure's exact PIID.

Confidence is unchanged and is NOT mechanically inflated by determinism: a deterministic CONFIRMED
exposure + a strength-≥3 catalyst yields **HIGH confidence** (`_confidence_from_exposures`), while
severity remains a magnitude band of the deobligated dollar figure (orthogonal — Workstream H).

## C. Deterministic identity is not a threat — materiality + temporal validity

Two additive guards in `_assess_program_change` ensure an exact identifier never manufactures a threat:

- **Materiality gate (Workstream K/O)** — a `funding_reduction` below a `$1,000,000` floor (overridable
  per-catalyst) is `IMMATERIAL` (a routine funding pull-back on a large contract is not a contraction).
  The floor sits below every modeled corpus reduction, so no prior case changes.
- **Temporal exposure-window validity (Workstream P)** — if the incumbency's `valid_to` precedes the
  catalyst date, the subject was not exposed at event time → `EXPOSURE_ENDED`. A deterministic
  relationship can still be historically invalid; future exposure evidence never creates a past threat.

## D. Flagship real deterministic chain (`corpus_m19.json`)

A REAL archived deobligation (mod **P00256**, **−$5,152,916.35**, action date **2024-05-06**) on SAIC's
exact prime PIID **47QFSA20F0057** (SAIC UEI **MMLKPW9JLX64** is the award recipient — deterministic
native-id incumbency) yields a **HIGH-confidence** (deterministic exposure + observed catalyst)
`PROGRAM_CONTRACTION` direct threat at **MODERATE** severity (the >$5M deobligated magnitude), then
**propagates one hop to Torch** on the SAME PIID via the real program-anchored SAIC→Torch sub-award edge
(HIGH→MEDIUM, confidence never increases). A second real deobligation (P00330, −$3.39M) is HIGH
confidence but **LOW** severity — determinism does not inflate severity.

`tests/test_m19_deterministic_exposure.py` is the honesty gate: the OBSERVED catalyst reproduces from the
archived USAspending bytes; the SAIC→Torch edge is the SAME program-anchored edge `ground_subaward_edges`
derives on that PIID; and deterministic identity alone is not a threat (immaterial → `IMMATERIAL`,
wrong-award → `NO_EXPOSURE`).

## E. Metrics, calibration, panel

- `threat.summarize_m19` reports **deterministic-vs-inferred** exposure/threat/outcome counts (each with
  its denominator) and **multi-family selectivity** across both OBSERVED families (Workstream K/L/Q).
- `threat_calibration.propagated_outcome_calibration` grows resolved **propagated** outcomes **1 → 4**
  with **outcome diversity** (MATERIALIZED / MITIGATED / AVOIDED), directional structured probe outcomes
  (no real-company future fact asserted).
- `ops.py` (thin): the network view + adverse-catalyst view surface `exposure_join_class` and the
  adverse-event family; no second console.

## Corpus & metrics

`corpus_m19.json` (9 new cases) **extends** `corpus_m18` (byte-identical) → **66 cases, all pass**, own
point-in-time replay, `scoring_v1` untouched. Merged metrics (directional, small sample):

- **46 direct / 16 propagated** threats (no explosion `propagated ≤ direct`; confidence never increases;
  max depth 2); **14 unique company pairs**; **2 OBSERVED adverse-event families**
  (`regulatory_adverse_event`, `contract_modification`); **7 observed-catalyst chains**.
- Catalyst authority **10 OBSERVED / 36 MODELED** direct; **deterministic exposures 79 / inferred 13**;
  deterministic direct threats **38 / 8**; **2 REAL** observed-deterministic-**HIGH**-confidence direct
  threats (flagship + low-severity) + 3 probe.
- **16 negative/zero-threat cases** (incl. deterministic `IMMATERIAL` / `NO_EXPOSURE` / `EXPOSURE_ENDED`).
- Resolved outcomes **16** (direct), confirmed precision **0.9375 over 16**, median lead **342.5 days**;
  resolved **propagated 4**, propagated precision **1.0 over 4**; `false_alert_from_absence` **0**.
- Multi-family selectivity: `contract_modification` threat/event ratio **0.714** vs
  `regulatory_adverse_event` **0.75** — the new family is not noisier.

**3 live USAspending calls** (archive-once). Full suite: **457 passed**.

## Acceptance gate

All M19 acceptance criteria are met — see `docs/replay/M19_DETERMINISTIC_EXPOSURE.md`.

## Limitations (explicit)

- The deterministic flagship uses **contract deobligation**, an authoritative but *magnitude-modest*
  contraction (−$5.15M / −$3.39M on a $2.9B-ceiling IDIQ), so direct severity is MODERATE/LOW; a contract
  **termination** on a monitored incumbent awaits archived evidence that does not yet exist.
- Resolved **propagated** outcomes (4) and the deterministic-vs-inferred splits are small and directional;
  the new 2024–2026 events have no knowable later real outcome, so the propagated-outcome growth is
  clearly-labelled directional probe observations, not real-company future facts.
- Relationship **type** diversity for the real chains remains `SUBCONTRACTOR_OF`; other relation types
  are added only when real evidence requires them.
- Two OBSERVED adverse-event families are integrated (export-control regulatory + contract modification);
  WARN/facility, enforcement, and SEC-disclosure families remain on the roadmap.
