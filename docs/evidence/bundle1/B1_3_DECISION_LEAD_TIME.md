# B1.3 — Decision Lead Time (canonical derived model)

PRELAUNCH-CONVERGENCE-001 · Bundle 1 · B1.3. Implementation: `pyrnova/decision_lead_time.py`
(pure derived logic, no new persisted schema). Tests: `tests/test_decision_lead_time.py` (7 passed).

## Model

Anchors reuse temporal fields that already exist in the intelligence artifacts:

| Anchor | Meaning | Existing source field |
|---|---|---|
| T0 | source evidence publicly available | record `available_at` / `first_observed_at` |
| T1 | Pyrnova acquired/received it | evidence `retrieved_at` |
| T2 | identity/program/customer relationship resolved | relationship `first_observed_at` / knowability floor (`observed_at`) |
| T3 | consequential assessment completed | explicit `assessed_at`; deterministic-on-read ⇒ derived from T2 (recorded via `T3_source`) |
| T4 | customer-ready intelligence available | customer material change `delivered_at` (→ `first_relevant_at`) |
| B | ordinary-environment equivalent-understanding point | **never fabricated**; `NOT_ESTABLISHED` when unknown |

Derived latencies (days, unknown never becomes zero):

- `acquisition_latency` = T1 − T0
- `analysis_latency` = T3 − T1
- `customer_readiness_latency` = T4 − T3
- `internal_pipeline_latency` = T4 − T0 (total internal)
- `external_decision_lead_time` = B − T4 (how much earlier than the ordinary environment) — `NOT_ESTABLISHED` unless B is objectively known

`from_customer_material_change(...)` attaches the model to an existing customer-material-change record
without new storage, reusing its first-seen semantics (`intelligence_observed_at`, `first_relevant_at`,
`delivered_at`).

## Honesty guarantees (verified by tests)

- A missing anchor yields `UNKNOWN`, not a fabricated zero.
- B absent ⇒ `external_decision_lead_time = NOT_ESTABLISHED`, `external_lead_time_established = False`.
  Decision Lead Time is **not** turned into marketing fiction.
- Deterministic-on-read T3 is imputed transparently (`T3_source = derived_from_T2/T1`), never silently.
- A negative span (e.g. acquired before public availability) is surfaced in `anomalies`, not hidden.

## Illustrative derivation (real-shaped, SAIC→DAP termination lineage)

Anchors from the archived termination provenance produce: acquisition 1.0 d, analysis 0.0 d, readiness
1.0 d, **internal pipeline latency 2.0 d**, external lead time **NOT_ESTABLISHED** (no benchmark B for
this event). Internal responsiveness is measurable today; the external "how much earlier than everyone
else" claim is explicitly withheld until a benchmark B can be objectively established — which is a CLOSE
dependency, not a marketing number.

## Verdict

**PASS.** Pyrnova can now express and derive Decision Lead Time honestly from existing temporal truth,
attachable to any intelligence artifact, with UNKNOWN / NOT_ESTABLISHED discipline and anomaly surfacing.
