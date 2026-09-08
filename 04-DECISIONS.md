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

The original strategic adjudication and 30-day authority are preserved under `docs/research/` and
`docs/archive/` for provenance; they no longer control current execution.
