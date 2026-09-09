# M14 — Multi-source intelligence expansion + continuous operations

_Status: active spec · authority: `01-PROJECT-AUTHORITY.md` › `02-EXECUTION.md` · created 2026-09-09_

## Mission

Move Pyrnova from "a live system proven on one primary source" (M13) to "a broad multi-source economic
intelligence collection layer that observes different parts of the economy and connects them." Breadth
is the strategic objective; **external call volume is not.** The governing rule stays
`SOURCE_INGESTION.md`: collect broadly, call sparingly, archive everything useful, replay many times.

M14 is additive. `scoring_v1` and `fit.py` are frozen; the M12/M13 ingestion primitives
(`sources/control.py`, `sources/source_state.py`, `scheduler.py`, `live_ops.py`, `archive.py`) are
reused unchanged. Frozen historical corpora are byte-for-byte unchanged.

## Workstream 2 finding — common ingestion contract already suffices (no redesign)

The existing primitives already support every M14 source shape, so **no new orchestration
abstraction is introduced**:

- bulk file → `SourceScheduler.run_job(offline_bytes=...)` (OFFLINE replay archives + indexes bytes);
- REST pagination / delta window / feed / snapshot / append-only → generic `request` + `fetcher` with a
  persistent `checkpoint` cursor and the request-dedupe/cache index in `source_state.py`;
- budgets, circuit breaker, backoff, secret redaction, request fingerprinting, metrics → `control.py`;
- cadence, pause/resume, mode override, per-source health → `scheduler.py`.

All sources produce common evidence/provenance semantics through the existing archive + `SourceFact` /
`ProgramSignal` paths. New abstractions are added only where an actual M14 source requires one.

## Source selection decision (Workstream 1)

Pyrnova already declares seven source families spanning procurement spend, procurement opportunities,
procurement forecast, appropriations/budget, regulation/policy, funding/assistance, and corporate
intelligence. M14 adds two **materially different** economic domains, chosen for new knowledge type,
keyless bulk/archive-first access, deterministic entity identifiers, and cross-source linking value:

1. **`sanctions_ofac` — OFAC Sanctions Lists (SDN + Consolidated).** New domain: sanctions / export /
   trade exposure — a first-class threat/exposure evidence family. Keyless bulk download (fixed-field
   CSV + XML): near-zero call amplification, snapshot-diff incremental. Entity exposure matched only on
   authoritative identity; name-only matches are rejected weak joins.
2. **`sbir` — SBIR/STTR federal R&D awards.** New domain: federally funded R&D — the earliest
   observable capability/commercialization precursor, pushing Pyrnova upstream of procurement for extra
   lead time. Keyless JSON; carries firm UEI/DUNS enabling a deterministic SBIR-award → USAspending
   prime-award entity chain.

That yields **nine registered families across distinct economic domains** (see `SOURCE_MANIFEST.md`).
Neither new source can independently create a candidate or STRIKE; both enrich capability evidence,
precursor chains, and threat/exposure context.

Deferred with documented reason (not silently dropped — see `STRATEGIC_CAPABILITY_ROADMAP.md` area 12):
Congress/legislation, EIA/energy, BLS/BEA/Census labor, USPTO patents, WARN, and state/local — each
either needs an api.data.gov key, adds heavy volume, or duplicates an existing precursor stage without a
new knowledge type at this milestone. They remain roadmap items with an explicit rationale.

## Source manifest (Workstream 2 / manifest)

`pyrnova/sources/registry.py` is the durable machine-readable manifest: every source records family,
signal types, access method, auth, incremental mechanism, identifiers, linking potential, historical
depth, native + recommended cadence, live-call budget posture, reliability state, implementation
status, intelligence priority, precursor stage, and rights/licensing notes. Unknown facts are recorded
as `unknown` — never fabricated. `SOURCE_MANIFEST.md` renders and annotates it for humans.

## Cross-source event chains (Workstream 5 — major acceptance target)

Demonstrated by reusing the frozen M5/M6 engine (`chains.py`) and the M10 multi-source grounding
(`multisource.py`) — no parallel stack:

- **Chain A — R&D precursor → procurement (deterministic entity anchor).** SBIR/STTR award (`PROGRAM`
  stage) → USAspending prime award (`AWARD` stage) for the same firm, joined on authoritative recipient
  **UEI** (`chains.resolve_chain` anchored inference), demonstrating measurable lead time. A name-only
  candidate for a different UEI is a **rejected weak join**.
- **Chain B — corporate + procurement entity linkage.** SEC EDGAR submissions + USAspending awards +
  company profile for one real public contractor, entity-linked deterministically (CIK ↔ recipient),
  via `multisource.build_multisource_profile`. Join method, confidence, temporal ordering, provenance,
  and rejected weak joins are recorded.

Every chain records join method, confidence, temporal ordering, and provenance; weak joins
(agency-name-only, topic-overlap-only, below-threshold inference) are rejected and counted, never
materialized. Deterministic identifiers are preferred; inferred joins remain auditable.

## Live-call budget (conservative)

Per new keyless source: at most one connectivity/schema call, at most one narrow representative
acquisition, at most one acceptance refresh — and fewer whenever a bulk file or existing archive removes
the need. Development and tests run OFFLINE against archived/fixture bytes. Authenticated sources (SAM)
keep stricter delta-only budgets; live SAM quota is never spent on historical development. The goal is
to **avoid** spending budget, not to spend it. All live acquisitions archive-once/replay-many.

## Non-goals (roadmap, not M14)

Billing/CRM/mobile/sales automation, generic chat UI, visual redesign, scoring v2, autonomous bidding,
premium-source purchases, a large state/local scraper network, full AlphaSense parity, and a threat-
engine implementation. M14 builds the data + operational foundation that makes those possible later
without redesign (see `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`).

## Acceptance gate

Close M14 only if the evidence supports: Phase 0 roadmap authoritative; manifest expanded; materially
broader coverage with several non-procurement families; SEC EDGAR + Federal Register operational or a
documented blocker; government spend/procurement retained; authenticated-source budget enforced;
per-source cadence + incremental/checkpoint behavior; archive-first development, request dedupe, budget
enforcement, and calls-avoided all demonstrated; ≥2 credible cross-source chains with weak joins
rejected and deterministic IDs preferred; point-in-time truth + raw provenance preserved; frozen corpora
+ `scoring_v1` + `fit.py` unchanged; no STRIKE explosion; no secret leakage; focused tests pass and the
full suite passes at the final integration gate; Operations Panel functional; every coherent block
committed/pushed; final HEAD == origin/main. If honest breadth falls short, document blockers and leave
M14 open.
