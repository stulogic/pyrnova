# Pyrnova decision record

Durable decisions are append-only. A later decision must identify what it supersedes.

| ID | Date | Decision | Rationale / consequence |
|---|---|---|---|
| D-001 | 2026-09 | Capture Radar is the active commercial wedge. | Keeps engineering tied to the first $100k; broader products remain deferred. |
| D-002 | 2026-09 | Deterministic state and evidence are authoritative; AI is bounded and human-gated. | Prevents model output from becoming fabricated fact. |
| D-003 | 2026-09 | Preserve point-in-time raw evidence and source-native identity. | Enables replay, audit, amendment history, and deterministic deduplication. |
| D-004 | 2026-09 | Use five evidence levels; Federal Register enrichment is capped at levels 1–2 and cannot create a candidate. | Prevents broad topical context from independently producing STRIKEs. |
| D-005 | 2026-09 | Freeze the accepted baseline as `scoring_v1`; every revision gets a new immutable version ID. | Preserves prior outputs and makes comparisons reproducible. |
| D-006 | 2026-09-08 | Reject `scoring_v2_candidate` after full-corpus comparison. | Its apparent precision gain came from demoting one case among only three STRIKEs; evidence was too sparse for adoption. |
| D-007 | 2026-09-08 | Close M3 with 20 cases across six mechanism families. | All 15 acceptance criteria passed; weaknesses remain explicit in the baseline report. |
| D-008 | 2026-09-08 | Live external calls are scarce infrastructure: archive once, replay many. | Protects quotas and makes offline development, replay, and acceptance roles explicit. |
| D-009 | 2026-09-08 | Keep the current flat Python/test layout until scale creates navigation cost. | Avoids churn with no behavioral benefit; conceptual boundaries are already clear. |
| D-010 | 2026-09-08 | Root authority documents supersede dated execution handovers and research. | Removes competing “canonical” claims and gives agents a short mandatory reading path. |
| D-011 | 2026-09-08 | M4 sources enter as conservative evidence/WATCH inputs; none independently manufactures a STRIKE. | More records must not weaken selectivity or bypass the existing evidence and human-review gates. |
| D-012 | 2026-09-08 | Program chains use explicit `program_key` or source-reference crosswalks across the eight M4 stages. | Partial and uncertain chains are representable without inferring relationships from topical similarity. |
| D-013 | 2026-09-08 | Adopt small adapter-neutral source controls, not a generic ingestion platform. | OFFLINE/LIVE-SAFE/ACCEPTANCE, request identity, budgets, accounting, retry metadata, and circuit state are reusable while transport stays source-specific. |
| D-014 | 2026-09-08 | Preserve `corpus_v1.json` and extend it with `corpus_m4.json`. | M3 remains reproducible while M4 can measure incremental source contribution and leave-one-source-out lift. |
| D-015 | 2026-09-08 | M5 cross-source joins are deterministic-first (`program_key`, native-identifier crosswalk); inference requires an explicit shared program identifier plus agency match. | Keeps chains evidence-gated; agency-name-only, topic-only, and chronology-only matches are rejected and counted, never materialized. |
| D-016 | 2026-09-08 | Relationships carry temporal/confidence provenance (`first_observed_at`, `join_method`, `confidence`, `rationale`); chain confidence is the weakest link, not a sum. | Lets replay answer "when could we first have known this relationship?" and keeps chain confidence simple, conservative, and explainable. |
| D-017 | 2026-09-08 | Opportunity transitions are derived by replaying `scoring_v1` point-in-time, not by a new scoring model. | Evolution history stays consistent with production scoring and never fabricates an unsupported promotion state. |
| D-018 | 2026-09-08 | Extend `corpus_m4.json` with a separate `corpus_m5.json` chain corpus; leave the M4 baseline frozen. | M4 scoring metrics stay reproducible while M5 validates multi-stage chains, rejected joins, and evolution. |

The original strategic adjudication and 30-day authority are preserved under `docs/research/` and
`docs/archive/` for provenance; they no longer control current execution.
