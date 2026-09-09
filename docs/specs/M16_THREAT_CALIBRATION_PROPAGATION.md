# M16 — threat calibration + exposure expansion + live selectivity

_Status: CLOSED 2026-09-09 · canonical for M16 additions. Builds on `docs/specs/M15_THREAT_INTELLIGENCE.md`
(threat/exposure semantics), which it does not repeat._

M15 proved Pyrnova can issue an evidence-backed threat. **M16 proves it resists issuing one when the
evidence is weak**, models more exposure families, propagates exposure through real company
relationships, and begins measuring whether historical warnings were correct — without becoming an alarm
machine. Additive only: `scoring_v1`/`fit.py`/`replay.py` and all frozen corpora (incl. `corpus_m15`)
are byte-for-byte unchanged; new modules `propagation.py`, `selectivity.py`, `threat_calibration.py`;
additive edits to `threat.py`/`ops.py`.

## Exposure-family expansion (`threat.py`)

Three new evidence-safe mechanisms exercise additional families; each rejects the un-exposed case:

| Mechanism | Requires | Zero-threat rejection |
|---|---|---|
| `SUPPLIER_DEPENDENCY_DISRUPTION` | evidenced SUPPLIER exposure (never industry-adjacency) + disruption of that supplier | `NO_DEPENDENCY` |
| `TECHNOLOGY_SUBSTITUTION` | TECHNOLOGY exposure + an **explicit** substitution mandate | `VAGUE_TREND_NOT_EVIDENCE` |
| `GEOGRAPHY_FACILITY_DISRUPTION` | FACILITY/GEOGRAPHY exposure inside the event scope | `OUTSIDE_EXPOSURE_GEOGRAPHY` |

Ten mechanisms total. Severity (magnitude band) and confidence (ordinal) stay orthogonal.

## Real event-stream selectivity (`selectivity.py`) — primary target

`run_selectivity(monitored, designations=, raw_event_count=, ...)` runs the unchanged engine over a
monitored company set and reports the funnel: **raw events → exposure candidates → accepted exposures →
threats emitted → zero-threat rejections**, plus `threat_emission_rate`, `exposure_acceptance_rate`,
`weak_rejection_rate`. It measures existing standards; it never lowers them to reduce noise, and makes no
live calls.

**Proof at scale** (`tests/test_m16_selectivity.py`, guarded — skips without the git-ignored archive):
the **19,365 real archived OFAC SDN designations** against 4 monitored companies with benign
counterparties → 4 weak name candidates, **0 accepted exposures, 0 threats** (`threat_emission_rate`
0.0, `weak_rejection_rate` 1.0). A deterministic CI test on the committed fixture shows the same drop and
that an `ent_num`-linked company still correctly emits one threat.

## Cross-company propagation (`propagation.py`)

`propagate_threats(seed_threats, relationships, *, max_depth=2, as_of)` traverses ONLY explicit,
evidence-backed edges to model a small network effect:

- `SUBCONTRACTOR_OF | SUPPLIES_TO | DEPENDS_ON | TEAMMATE_OF | SUBSIDIARY_OF | CUSTOMER_OF` → a degraded
  propagated threat on the dependent company.
- `SUBSTITUTE_FOR | COMPETES_WITH` → a beneficiary **opportunity** (not a threat) — the duality network.

Safety invariants (all tested): bounded `max_depth`; confidence degrades each hop and terminates below
LOW (double depth bound); severity/confidence **never increase**; a weak/inferred edge degrades faster
or terminates; deterministic cycle prevention; duplicate collapse (same subject+mechanism+root emitted
once — shared evidence never multiplied); industry-adjacency relations never propagate; full
`propagation_path` provenance per hop; point-in-time edge filtering.

## Calibration semantics (`threat_calibration.py`)

Three orthogonal quality axes, always with denominators:

- **Detection**: `TRUE_THREAT | FALSE_ALERT | UNRESOLVED | INSUFFICIENT_EVIDENCE`. An unresolved threat
  is **never** a false alert; only an explicit `FALSE_ALARM` observation is; `AVOIDED`/`MITIGATED`/
  `DELAYED` stay `TRUE_THREAT` (the warning was correct). Success is never inferred from absence.
- **Exposure**: `CONFIRMED | INFERRED_CORRECT | INFERRED_INCORRECT | CANDIDATE_REJECTED | UNRESOLVED`.
- **Outcome**: the `threat.THREAT_OUTCOME_LABELS` vocabulary (M15).

`calibrate_threats(results)` reports confirmed-threat precision **with its denominator**, unresolved
rate, materialization + mitigation/avoidance rates, and median lead time; `false_alert_from_absence`
is an enforced-0 invariant.

## Corpus & metrics

`corpus_m16.json` (18 new cases) **extends** `corpus_m15` via `load_threat_corpus` chain-merge (frozen
m15 byte-identical); merged corpus = **35 cases, all pass**, own point-in-time replay
(`run_threat_corpus`), `scoring_v1` untouched. `summarize_m16` folds threat + propagation + calibration.

Merged metrics (directional, small sample): 22 direct threats, **3 propagated** across **2 cases**
(max depth **2** — no explosion), 2 beneficiary opportunities; 10 mechanisms; severity {CRITICAL 2,
HIGH 16, MODERATE 4} distinct from confidence {HIGH 18, MEDIUM 3, LOW 1}; rejection reasons across 7
codes; 34 confirmed / 6 inferred exposures / 3 weak rejected. Calibration: **precision 1.0 over 5
resolved TRUE_THREAT** (denominator 5), unresolved-rate 0.77 (never counted false), materialization 0.4,
median lead time **306 days**, `false_alert_from_absence` 0.

## Operations Panel (`ops.py`)

`threat_propagation_view()` — direct vs propagated counts, max depth, per-propagated-threat
path/provenance + root id, beneficiary opportunities (empty-safe). `selectivity_view(result)` — formats
one funnel for the operator. The existing panel is untouched.

## Acceptance gate (all 37 met — see `docs/replay/M16_THREAT_CALIBRATION_PROPAGATION.md`)

M15 invariants preserved (1); real event-stream selectivity measured (2); majority of irrelevant events
emit no threat (3); funnel reported (4); **3** new exposure families with evidence (5); weak exposure
rejection (6); propagation implemented safely (7); depth bounded (8); cycles prevented (9); duplicates
prevented (10); **2** propagation cases (11); direct vs propagated distinguishable (12); historical
outcome calibration exists (13); unresolved stays valid (14); false-alert classification exists (15); no
absence-as-false-alarm (16); point-in-time replay preserved (17); future evidence excluded (18);
precision reported with denominator (19); lead time reported (20); negative corpus expanded (21); no
threat explosion (22); no propagation explosion (23); `scoring_v1` unchanged (24); `fit.py` unchanged
(25); prior corpora byte-identical (26); no secret leakage (27); **0 live calls** (28–30); focused tests
pass (31); full suite 400 (32); panel functional (33); limitations documented (34); roadmap updated
(35); each block pushed (36–37).

## Limitations (explicit)

- The corpus remains mechanism-dense by design (semantic coverage). The **live-feed** selectivity proof
  (19,365 → 0) is the real guardrail evidence; corpus distributions are directional, not stable rates.
- Calibration rests on **5 resolved outcomes** — precision 1.0 is directional only (small-sample warning
  surfaced, never hidden). Real threat precision awaits many more resolved outcomes.
- Propagation relationship edges in the corpus are illustrative/labelled where public sub-award/teaming
  evidence is not archived; the propagation **semantics** (bounded, degrading, cycle-safe) are real. Real
  archived sub-award edges (M10 Torch sub-awards) can seed a real propagation case in future work.
- Supplier/technology/geography positive cases use disclosed-style structured exposure records; broad
  live supplier-disclosure / WARN / facility source ingestion is deferred (no source added in M16).
- New source families (BIS, WARN, facility/closure) were **not** added — M16 needed none, and the
  archive-first discipline says never add a source merely for count.
