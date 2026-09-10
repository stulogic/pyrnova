# Pyrnova research index

> **Status: research navigation.** Research is supporting analysis and provenance — **not**
> implementation authority (see `00-INDEX.md` precedence). Research can *inform* authority; it does not
> *authorize* implementation. Adopted conclusions live in `01-PROJECT-AUTHORITY.md`,
> `docs/strategy/`, and `04-DECISIONS.md`.

This index records each durable research artifact and — importantly — **what decision it caused**, so
research never becomes a graveyard of long reports. Every strategically significant conclusion should be
traceable to a decision, and every strategically significant decision should reference the research that
informed it.

## Research → decision traceability

| Artifact | Date | Purpose | Status | Major conclusions | Decisions caused | Authority affected |
|---|---|---|---|---|---|---|
| [`2026-09-09-RED-TEAM-REVIEW.md`](2026-09-09-RED-TEAM-REVIEW.md) | 2026-09-09 | Adversarial review of direction before productization | BINDING (adopted) | Long-term thesis survives; launch thesis narrows to federal contractors; breadth ≠ differentiation; material-change→consequence loop is the product; dossiers/search/AI are supporting, not moat; finishability is the top founder risk; defer global detection; expansion is customer-pulled; historical/outcome intelligence is defensible | D-044, D-045, D-046, D-047, D-048, D-049, D-050 | `01-PROJECT-AUTHORITY.md`, `PHASE_1_PRODUCT_AUTHORITY.md`, `STRATEGIC_CAPABILITY_ROADMAP.md`, `02-EXECUTION.md`, `AGENTS.md` |
| [`2026-09-09-STRATEGIC-DATA-INTELLIGENCE.md`](2026-09-09-STRATEGIC-DATA-INTELLIGENCE.md) | 2026-09-09 | Open vs. premium data feasibility for the intelligence layer | INFORMATIVE (data-strategy conclusion adopted) | Open/authoritative data goes far; institutional-quality public-contractor intelligence feasible; global detection uneconomic initially; full supply-chain reconstruction infeasible from public data; own the intelligence layer, rent evidence selectively | Informs D-045, D-048, D-049; reinforces D-008 | `01-PROJECT-AUTHORITY.md`, `PHASE_1_PRODUCT_AUTHORITY.md`, `STRATEGIC_CAPABILITY_ROADMAP.md` |
| [`PRECURSOR_CASEBOOK.md`](PRECURSOR_CASEBOOK.md) | 2026-09-08 | Retrospective proof that upstream events precede procurement with trackable lead time | INFORMATIVE (methodology proof) | Genuinely upstream signal exists ahead of RFP; separable from hindsight-obvious | Supports D-001, precursor scope | `01-PROJECT-AUTHORITY.md`, `docs/replay/M3_BASELINE.md` |
| [`ADJUDICATION_EVALUATION.md`](ADJUDICATION_EVALUATION.md) | 2026-09-08 | Hostile evaluation of feedback on the original red team | INFORMATIVE (provenance) | Accept commercial compression, reject strategic amputation; resist "cheap to keep" scope re-expansion | Informs the finishability posture later hardened in D-047 | `docs/archive/EXECUTION_AUTHORITY_30D_V1.md`, `04-DECISIONS.md` |

## Binding / informative / deferred / superseded

- **BINDING** — the red team review's adopted implications (scope narrowing, wedge, product loop,
  finishability, moat) now govern via `01-PROJECT-AUTHORITY.md` and `04-DECISIONS.md`.
- **INFORMATIVE** — feasibility and methodology findings that shape but do not by themselves authorize
  work.
- **DEFERRED** — capabilities research indicates may eventually be useful are recorded in
  `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`; research indicating usefulness does **not** authorize
  implementation (D-042, D-047).
- **SUPERSEDED** — superseded strategic material is retained under `docs/archive/`.

## Rule

Research informs authority. Research does **not** independently authorize implementation. A capability
appearing only in research is `DEFERRED` until promoted through `02-EXECUTION.md`.
