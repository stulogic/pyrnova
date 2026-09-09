# M17 — real relationship propagation + continuous threat operations

_Status: CLOSED 2026-09-09 · canonical for M17 additions. Builds on
`docs/specs/M16_THREAT_CALIBRATION_PROPAGATION.md` (propagation/selectivity/calibration semantics) and
`docs/specs/M15_THREAT_INTELLIGENCE.md` (threat/exposure semantics), which it does not repeat._

M16 proved the propagation *semantics* (bounded, degrading, cycle-safe) on illustrative edges and
measured selectivity in a harness. **M17 proves those semantics survive on a REAL economic relationship
graph, and that selectivity + threat quality can be measured continuously as part of normal operation.**
Central question answered: *can Pyrnova follow a real economic relationship graph and continuously
measure whether its threat warnings are useful — without turning the graph into an alarm amplifier?*

Additive only: `scoring_v1` / `fit.py` / `replay.py` and every frozen corpus (incl. `corpus_m15`,
`corpus_m16`) are **byte-for-byte unchanged**. New module `relationships.py`; additive edits to
`selectivity.py`, `scheduler.py`, `threat.py`, `threat_calibration.py`, `ops.py`; new `corpus_m17.json`.

## A. Real relationship graph grounding (`relationships.py`) — primary target

`ground_subaward_edges(parse_subawards(...), ...)` turns archived, authoritative USAspending sub-award
bytes (where the target company is the SUBRECIPIENT) into canonical `SUBCONTRACTOR_OF` edges
`from_ref` (exposed prime) → `to_ref` (dependent subcontractor), in the exact shape
`propagation.propagate_threats` consumes. Real evidence strength maps **honestly** to propagation
behavior:

| Real evidence | Edge | Propagation |
|---|---|---|
| **Program-anchored** — a sub-award's `prime_award_id` matches a globally-unique PIID the prime is known to be exposed on | `CONFIRMED` / `deterministic_native_id` | one degradation step (strongest) |
| **Authoritative repeat** — ≥2 sub-awards or ≥2 distinct years, no known-exposed anchor | `INFERRED` / `inferred_strong_attribute` | degrades faster (two steps) |
| **Single occurrence** | `name_only_weak` | **terminates** (weak-hop termination) |

A short local order number (e.g. `"0002"`, shared across primes) can never manufacture a false
deterministic anchor (`min_anchor_id_len` guard). Every edge retains subject/object/relation, source,
real sub-award `evidence_ids`, `available_at` (first knowable), `join_method`, `link_class`, numeric
confidence, and full provenance (count/total/years/anchor ids). No industry-adjacency, no fuzzy-name
edges.

**Grounded from real bytes** (`examples/real_evidence/usaspending_subawards_torch.json`): **22 real
prime→Torch edges** — 1 program-anchored deterministic (SAIC), 11 authoritative-repeat, 10
single-occurrence weak (terminating).

## B. Real propagation cases (`corpus_m17.json`)

Two flagship chains traverse a REAL, deterministic economic relationship: **Torch Technologies is a
repeat subcontractor to SAIC on the same prime awards SAIC holds** (matched on globally-unique
Prime-Award-ID — the strongest possible linkage):

- **Chain A** — SAIC incumbent on GSA task order `47QFSA20F0057` ($1.43B); a modeled funding reduction →
  `PROGRAM_CONTRACTION` (CRITICAL/HIGH) direct on SAIC → **propagated one hop to Torch** (HIGH/MEDIUM —
  severity and confidence degraded, never increased) via the real sub-award edge (sub `P010277776`).
- **Chain B** — SAIC incumbent on Army task order `W31P4Q21F0095` ($825.8M); a modeled cancellation →
  `PROGRAM_CANCELLATION_OR_DELAY` (CRITICAL/HIGH) → propagated one hop to Torch (HIGH/MEDIUM) via sub
  `P010270457`. Distinct program, agency, and sub-award from Chain A.

The RELATIONSHIP EDGE and INCUMBENCY EXPOSURE are real and archived; the direct-threat CATALYST is a
modeled adverse event (structured, dated, evidence-strength-tagged — the M16 corpus convention).
`tests/test_m17_real_propagation.py` proves the corpus edges are the same edges `ground_subaward_edges`
derives from the archived bytes, and that a real single-occurrence edge terminates end-to-end.

## C. Continuous selectivity instrumentation (`selectivity.py` + `scheduler.py`)

`selectivity.source_run_funnel(...)` decorates a `run_selectivity` funnel with source-run operational
context (run id, timing, calls made/avoided, records received/changed). `SourceScheduler` gains
`record_selectivity_run` (append-only, bounded, persisted in the durable **M12/M13 source-state
document** — not a second metrics store), `selectivity_runs`, and `selectivity_report` (per-source latest
funnel + lifetime totals; denominator-honest, empty-safe). The headline stays the raw-events →
threats-emitted drop; standards are measured, never lowered.

## D/F/G. Threat quality over time + propagation quality (`threat_calibration.py` + `threat.py`)

`threat_quality_over_time(results)` derives durable aggregates from **append-only predictions + later
outcomes** (no prediction is ever mutated): warnings issued/resolved/materialized/mitigated/avoided/
delayed/false/unresolved, median lead time, **per-mechanism reliability** (precision only WITH its
denominator, null when unresolved), and which **source families** contribute useful (resolved-true)
warning signal. `summarize_m17` extends `summarize_m16` with propagation quality: real propagation cases,
chains, avg/max depth, `confidence_never_increases` (proven per-threat), weak terminations,
cycles/duplicates suppressed, and an explosion guard.

## E/M. Company threat network view (`ops.py`)

`OperatorConsole.company_threat_network_view(company_ref)` answers *"for Company X, what direct and
indirect threats affect it, through which relationships?"* — composing the persisted streams into direct
threats (with `company_threat_surface`), inbound-propagated threats (root catalyst, full relationship
path, degraded severity/confidence, evidence, outcome status), and the company's outbound network
footprint. Builds on `company_threat_surface`; read-only, empty-safe; **not** the full Company
Opportunity Surface (deliberately out of scope).

## Corpus & metrics

`corpus_m17.json` (11 new cases) **extends** `corpus_m16` (byte-identical) → **46 cases, all pass**, own
point-in-time replay, `scoring_v1` untouched. Merged metrics (directional, small sample):

- **32 direct threats, 5 propagated** across **4 chains** (2 REAL SAIC→Torch), 2 beneficiary
  opportunities; **max depth 2, avg 1.2 — no explosion** (`propagated ≤ direct`); confidence never
  increases (proven); 0 cycles, 0 duplicate propagations in this corpus.
- Calibration / quality: **resolved outcomes grew 5 → 12**; confirmed-threat precision **0.9167 over 12**
  (an honest `FALSE_ALARM` keeps it below a vacuous 1.0); materialized 3, mitigated/avoided 4, delayed 2;
  **median lead time 336 days**; `false_alert_from_absence` **0**.
- Source contribution: real USAspending award evidence backs the most resolved-true warnings.

**0 live API calls.** Full suite: **428 passed**.

## Acceptance gate (all 37 met — see `docs/replay/M17_REAL_PROPAGATION_CONTINUOUS_OPS.md`)

M16 invariants preserved (1); real edges grounded from archived evidence (2); ≥1 real multi-company
chain — **2** delivered (3–4); direct vs propagated distinguishable (5); depth bounded (6); cycles
prevented (7); duplicates suppressed (8); confidence never increases (9); weak-hop termination
demonstrated on real edges (10); continuous selectivity integrated into the scheduler (11); source-run
funnel persisted/reported (12); resolved outcomes materially expanded beyond 5 → 12 (13); unresolved
stays valid (14); false-alert uses explicit evidence (15); no absence-as-false-alarm (16); lead time
measured (17); mechanism/source quality with denominators (18); negatives preserved (19); no threat
explosion (20); no propagation explosion (21); temporal truth preserved (22); future evidence excluded
(23); `scoring_v1` unchanged (24); `fit.py` unchanged (25); prior corpora byte-identical (26); no secret
leakage (27); 0 live calls documented (28–30); focused tests pass (31); full suite 428 (32); panel
functional (33); limitations documented (34); roadmap/backlog updated (35); each block pushed (36–37).

## Limitations (explicit)

- **One real company relationship** (SAIC↔Torch) fully grounds the two flagship chains; both share that
  company pair (distinct programs/agencies/sub-awards). A genuinely *second* company relationship awaits
  archived prime-side exposure evidence for another of Torch's real primes (Parsons/KBR/NTSI have real
  edges but no archived prime-award exposure here). No second pair was fabricated.
- The direct-threat **catalyst** on each SAIC program is a modeled adverse event (structured, dated); the
  relationship edge and incumbency exposure are real & archived. Real archived adverse-event feeds
  (BIS/WARN/enforcement) were **not** added — M17 needed none, and archive-first discipline forbids
  adding a source for count.
- Calibration rests on **12 resolved outcomes**; precision 0.9167 is directional (small-sample warning
  surfaced, never hidden). Two outcomes are grounded in real contract end dates (EXPOSURE_ENDED); the
  rest are directional structured observations exercising the full vocabulary incl. one FALSE_ALARM.
- The continuous-selectivity integration is offline/deterministic here (real OFAC fixture + committed
  sub-award bytes); no live calls were made. A single optional live acceptance refresh remains available
  under the M13 budgeted path but was not required.
