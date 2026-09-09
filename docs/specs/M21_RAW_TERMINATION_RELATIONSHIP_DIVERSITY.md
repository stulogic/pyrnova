# M21 — raw adverse event + economic relationship diversity + observable outcomes

_Status: CLOSED 2026-09-09. Builds additively on M20; `scoring_v1`, `fit.py`, `replay.py`, the frozen
severity dollar bands, and `corpus_m15`…`corpus_m20` remain byte-identical._

## Contract

M21 must prove the threat path on a **raw**, authoritative adverse event and a **genuinely economic
relationship outside the government-program graph**:

> RAW authoritative adverse event → deterministic exposed entity → real economic relationship →
> direct threat → propagated threat → later observable outcome (where defensibly available).

It closes M20's two stated gaps: (a) M20's flagship SEC evidence was a curated, identity-checked
extract, explicitly *not* raw filing bytes; (b) the exercised propagation relations were confined to
`SUBCONTRACTOR_OF` and `COMPANY_TO_PROGRAM`.

## Phase 0 — authority reconciliation

- **Product Language Authority** (D-041, `01-PROJECT-AUTHORITY.md`): formal, operational product copy;
  prohibited slogan/marketing/anthropomorphic/generic language; copy quality is part of acceptance.
- **Strategic capability reconciliation + phase control** (D-042, roadmap areas 16–22 + the
  combined-depth and phase-control doctrine): the broader customer-facing capability set is preserved
  durably and cannot silently disappear; new capabilities discovered mid-development do not expand the
  phase unless required for correctness/safety/architecture/existing acceptance.

## SEC ingestion hardening

Rolled into M21 as an infrastructure correction (not a separate milestone), archive-once/replay-many:

- **Declared identity** — `config.sec_user_agent()` composes a contact-bearing `User-Agent` from
  `PYRNOVA_SEC_CONTACT_EMAIL` / `PYRNOVA_SEC_USER_AGENT`; it returns empty (never a fabricated address)
  when unconfigured, and a live path fails cleanly with the fix. `EdgarClient` defaults its identity
  from config.
- **Preferred authoritative access order** — `sec_edgar.SEC_ACCESS_ORDER`: data.sec.gov structured
  submissions/XBRL metadata → bulk submissions/companyfacts → **raw EDGAR filing/submission archive
  artifact** → filing HTML only where structure requires → curated extract only as an explicitly
  labelled fallback. Ingestion is not forced through one mechanism.
- **Discovery vs body** — `DISCOVERY_ENDPOINTS` (submissions/companyfacts) are separated from
  `BODY_ENDPOINTS`; `EdgarClient.fetch_full_submission` retrieves the raw immutable filing body only on
  deliberate demand.
- **Accession dedupe** — `accession_dedupe` skips an already-archived accession (content hash +
  first-observed retained) and treats an amendment/correction (`/A` or a distinct accession) as a NEW
  artifact rather than silently rewriting history.
- **Safe 403** — a 403 is terminal: exactly one call, clean raise, spend recorded, no internal retry
  loop; a 429 installs a concrete cooldown (backoff). No provider-limit evasion, no identity rotation.

## Flagship raw adverse event

A real USAspending **terminate-for-convenience** action, preserved as **raw response bytes** (D-043):

- PIID `36C25726N0240` — VA (Kerrville VAMC boiler replacement, 671A4-21-160), NAICS 236220.
- Modification `P00002`, FPDS action_type `F`, action date **2026-08-31**, federal_action_obligation
  **−$3,908,263.25** (the near-total settlement of a $3.95M base award).
- Archived raw bytes: `examples/real_evidence/usaspending_award_termination_dap.transactions.json`
  (the transaction-history body carrying the termination), `.award.json` (recipient UEI + period of
  performance), and `usaspending_recipient_dap.json` (recipient hierarchy). Each has a `.provenance.json`
  sidecar with the exact `sha256` over the raw response bytes, the request URL, and retrieval date.
- `adverse_events.parse_usaspending_award_termination` emits OBSERVED `CONTRACT_TERMINATION` events —
  positively evidenced from the FPDS action_type (`E`/`F`) or an explicit `TERMINAT` description, never
  inferred from a funding pull-back or from spending disappearing. `to_contract_termination_catalyst`
  maps it to a categorical `program_cancellation` catalyst (→ `PROGRAM_CANCELLATION_OR_DELAY`), keyed on
  the exact PIID.

## Deterministic exposure

The exposed entity is resolved by the recipient **UEI `YR7CLZFGCM95`** on the terminated award
(`incumbency_exposures`, deterministic native id), not by name. The direct threat is
`PROGRAM_CANCELLATION_OR_DELAY`, CONTINUITY, **HIGH confidence** (OBSERVED catalyst + deterministic
exposure), severity **LOW** — honestly following the frozen dollar bands for a ~$3.9M contract; the
categorical termination raises confidence, not severity.

## New economic relationship — `SUBSIDIARY_OF`

`relationships.ground_subsidiary_edges` grounds the first propagation relation **outside the
government-program graph** from the authoritative USAspending recipient hierarchy: child UEI
`YR7CLZFGCM95` → parent UEI `KMSLVW1MZWU9`, joined by **exact native UEIs** (`deterministic_native_id`,
CONFIRMED). USAspending's self-parent hierarchy row is filtered — a name is never identity. Directed
child → parent, so a threat on the subsidiary propagates up to the parent, which inherits consolidated
exposure. The threat degrades to **MEDIUM** confidence one hop up (never increasing); severity is not
inflated by graph distance.

## Selectivity, temporal truth, provenance

`corpus_m21.json` extends the frozen `corpus_m20` lineage (74 → **80 cases, all pass**) with the flagship
plus five selectivity/negative cases: an unrelated same-sector/same-geography firm is **NO_EXPOSURE** (a
shared sector is not a dependency); a not-yet-valid `SUBSIDIARY_OF` edge is a relationship temporal
termination (0 propagated); a weak name-only edge terminates propagation; a lapsed incumbency is
**EXPOSURE_ENDED**; a duplicated edge yields exactly one propagated threat. Every relationship is
evaluated at event time; raw evidence is immutable (hash-verified) and derived state is rebuildable; no
temporal leakage.

## Observable outcome

The flagship termination's later outcome is honestly **UNRESOLVED**: the action is days old (2026-08-31)
and no defensible independent later evidence (re-solicitation/re-award, parent disclosure, layoff) is
knowable within the bounded evidence budget. The case is recorded unresolved rather than forced into a
label (truth over milestone cosmetics). Prior resolved direct (N=17, precision 0.9412) and propagated
(N=4) outcomes are retained unchanged. A re-award probe of requirement 671A4-21-160 is the natural
later-outcome path once time passes.

## Operations and calls

`OperatorConsole.raw_adverse_event_view` (thin, read-only, functional labels) surfaces the adverse-event
family, raw/archive provenance, deterministic exposure state, relationship path + validity,
direct/propagated classification, and SEC source status. No second console; no frontend redesign.

Live external calls (all keyless, public-domain USAspending, one-time acquisition, archived for replay):
~16 USAspending calls total — discovery/probe to locate a material termination with a distinct parent,
then 3 archival retrievals (transactions/award/recipient). 0 SEC, 0 SAM, 0 other. All parser, corpus,
replay, and test work is offline against the archived bytes.

## Acceptance

All 28 M21 acceptance items in the work order are met (see the replay evidence). `scoring_v1`, `fit.py`,
`replay.py`, severity bands, and frozen corpora are unchanged; `.codex/` untouched.

## Limitations and next work

- Severity is LOW by the frozen dollar bands ($3.9M contract); the flagship's strength is rawness +
  deterministic exposure + the new relationship type + categorical cancellation + HIGH confidence.
- The later outcome is genuinely unresolved (recent event); grow real propagated outcomes as time passes.
- `SUBSIDIARY_OF` is the one new economic relation exercised; `CUSTOMER_OF`/`SUPPLIER_OF`/`FACILITY_OF`
  remain for a later milestone where authoritative evidence supports each.
- Per the expected post-M21 direction, the next milestone pivots toward customer-facing productization
  (Company Intelligence Dossier + Opportunity/Threat Surface + universal search + fast read projections).
