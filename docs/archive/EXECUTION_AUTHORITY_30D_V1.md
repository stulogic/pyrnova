# Pyrnova — 30-Day Execution Authority (v1)

**Status:** ✅ CONTROLLING (locked). Supersedes the broad strategic authority for the next 30 days of
execution. Incorporates the red-team, the adjudication feedback, the evaluation of that feedback
(`docs/ADJUDICATION_EVALUATION.md`), and the Final Strategic Adjudication.
**Locked:** 2026-09-08. Change only if implementation reveals a genuine contradiction or blocker.
**Scope:** What we build, sell, measure, and refuse until the first $100k is collected.
**Founded on:** the red-team review + founder adjudication ("accept the commercial compression, reject the strategic amputation").

This document is deliberately narrow. The full company vision (economic & commercial intelligence
platform, three pipelines, eight canonical objects, 21-stage doctrine) remains **canonical architecture**
and is preserved in schema and data retention. It is not the build target for the next 30 days.

---

## 0. The one sentence

> Build a tiny slice of the enormous company, sell it immediately, preserve all the intelligence
> exhaust, measure whether it works, and expand the substrate underneath demonstrated demand.

---

## 1. Locked decisions (post red-team)

| # | Decision | State |
|---|----------|-------|
| 1 | **One active commercial wedge:** Pyrnova Capture Intelligence | LOCKED |
| 2 | **One active engine:** Opportunity Engine (Business Opportunity Pipeline) | LOCKED |
| 3 | **One immediate buyer:** federal contractor Growth / Capture / BD (individual with budget) | LOCKED |
| 4 | **One immediate objective:** first **$100k collected** | LOCKED |
| 5 | **One immediate product:** human-supervised **Capture Radar**, delivered as a **Signal Brief** — not self-serve SaaS | LOCKED |
| 6 | **One Day-1 asset:** immutable **point-in-time evidence archive** (source pull #1) | LOCKED |
| 7 | **One Day-1 learning mechanism:** **prediction + rejection + outcome** recording | LOCKED |
| 8 | **One first deterministic engine:** **recompetes / award expirations** | LOCKED |
| 9 | No self-service SaaS before revenue | LOCKED |
| 10 | No premium data purchases before customer evidence demands it | LOCKED |
| 11 | No product-building across Enterprise / Strategic-Data pipelines yet | LOCKED |
| 12 | **STRIKE** remains a canonical object (qualified opportunity) | LOCKED |
| 13 | **Pyrnova remains an economic intelligence company**; Capture Intelligence is its first *product*, not its *identity* | LOCKED |

## 2. Deferred — NOT deleted (the reconciliation that matters)

The distinction the founder insisted on, encoded so the team cannot accidentally violate it:

- **Enterprise Intelligence Pipeline** and **Strategic/Data Intelligence Pipeline** remain canonical.
  We **do not build their products**, but our storage and schemas **must not preclude them**. Schema
  carries the necessary objects and retains the necessary data now (see `db/schema.sql`).
  **Bound:** "retain the data necessary" means **cheap raw archival of bytes we already fetch** for the
  Opportunity Engine — NOT building normalization, resolution, or ingestion for objects the Opportunity
  Engine does not use. Unbounded, this line silently smuggles the amputated scope back in.

### 2.1 Anti-accumulation rule (governs every "keep it, it's cheap" decision)

> Every "keep it canonical / retain the data / it's cheap to leave in" decision is free **only** as raw
> archival or schema shape. The moment it requires **active engineering, normalization, or founder-hours
> during the selling window**, it is **deferred by default** and must earn its place against the $100k
> target.

This rule exists because the individual scope-keeping decisions below are each cheap, but in aggregate
they rebuild the substrate-first temptation this authority rejects. When in doubt, defer.
- **FLOW / SHIFT / RISK** — deferred as *products*, present as *reserved concepts*. Not abandoned.
- **State-capital precursors** (OMB, Congress/GovInfo, agency budget justifications, procurement
  forecasts, RegInfo/OIRA) — **strategically central**, begin entering **Weeks 3–6**, once the
  SAM/USAspending/FedReg/Grants kernel produces a Signal Brief. They are the answer to
  *"why isn't this just HigherGov/GovWin + AI?"* and must not disappear into an indefinite roadmap.
- **Capability Graph / Outcome-Graph tooling / mechanism library / data-licensing API** — later.

## 3. Architecture: substrate stays canonical, only one engine gets priority

```
                 Economic Intelligence Substrate  (canonical, retained from Day 1)
                 ┌───────────────────────────────────────────────────────────┐
   ACTIVE  ───►  │  Opportunity Engine  (Business Opportunity Pipeline)       │
   BUILD         └───────────────────────────────────────────────────────────┘
   DORMANT       │  Enterprise Intelligence Engine   (schema retained, no build) │
   (retained)    │  Strategic / Data Intelligence Engine (schema retained, no build) │
                 └───────────────────────────────────────────────────────────┘
```

**Rule:** any Week-1–4 engineering decision that would make Enterprise or Strategic/Data pipelines
*impossible later* is out of bounds. Any decision that merely *defers* their features is fine.

## 4. Canonical MVP objects (what we instantiate now)

| Object | Build now? | Notes |
|--------|-----------|-------|
| Entity | **YES** | UEI-keyed; contractors, agencies, programs |
| Evidence | **YES** | point-in-time, hashed, immutable |
| Claim | **YES** | extracted assertion, always evidence-grounded |
| Event | **YES** | something happened |
| Catalyst | **YES** | precursor that moves future demand |
| Opportunity | **YES** | candidate, pre-qualification |
| **STRIKE** | **YES** | qualified commercial opportunity (LOCKED canonical) |
| Capability Profile | **YES (minimal)** | per customer |
| Outcome | **YES** | observed result of a prediction |
| Signal | label, not a major engineering object | |
| FLOW / SHIFT / RISK | later | reserved in schema, not populated |
| full Capability Graph / Outcome-Graph tooling | later | |

Object flow for the MVP: **Event → Catalyst → Opportunity (candidate) → STRIKE**, every node carrying
Evidence + Claims, every STRIKE producing a Prediction whose Outcome is later recorded.

## 5. Two pipelines, never confused

We separate the **intelligence process** (doctrine) from the **software modules** implementing it.

**Full Pyrnova intelligence doctrine (unchanged, correct):**
OBSERVE → ARCHIVE → NORMALIZE → RESOLVE → CONNECT → DETECT EVENT → DETECT CATALYST →
GENERATE HYPOTHESIS → INVESTIGATE → CORROBORATE → FALSIFY → MODEL → QUANTIFY → MATCH → SCORE →
REVIEW → PUBLISH → MONITOR → REPRICE → OBSERVE OUTCOME → LEARN

**MVP implemented pipeline (software modules built now):**
OBSERVE → ARCHIVE → NORMALIZE → RESOLVE → DETECT → MATCH → REVIEW → **STRIKE** → OUTCOME

The intermediate doctrine stages (HYPOTHESIS, INVESTIGATE, CORROBORATE, FALSIFY, MODEL, QUANTIFY,
REPRICE, LEARN) happen **manually inside the REVIEW step** by the analyst, and are *recorded* — not
built as subsystems — until volume justifies code. FALSIFY is mandatory as a recorded discipline
(every STRIKE carries a "why this may be weak" note), not as a subsystem.

## 6. The offer — Pyrnova Capture Radar

For a federal contractor, Pyrnova identifies:

1. **Recompetes & contract expirations** — where existing federal spend returns to market.
2. **Pre-procurement catalysts** — evidence of new/changing demand before the obvious solicitation.
3. **Capital movement** — funding, authorization, programs, policy supporting future demand.
4. **Capability matching** — why those opportunities specifically fit this customer.
5. **Falsification** — reasons the apparent opportunity may be weak, unavailable, or inappropriate.
6. **Action** — what the capture team should investigate or do next.

**Delivery unit:** the **Pyrnova Signal Brief** (human-reviewed document). No customer dashboard
required for first revenue.

### 6.1 The first artifact is product output, not free consulting

The sales-opening artifact is a **Signal Brief with ~3 items**, generated by the product, e.g.:

> **SIGNAL 01 — $XXm recompete approaching.** Existing award ends in X months. Capability fit: HIGH.
> Incumbent: X. Evidence: links. Why now: X.
>
> **SIGNAL 02 — precursor program movement.** Agency activity suggests emerging requirement X.
> Procurement not yet obvious. Authority/evidence: links.
>
> **SIGNAL 03 — funding / policy catalyst.** Capital/policy movement could generate demand X.

Then: *"Pyrnova found N additional relevant items. We investigate, rank and monitor them under a paid
engagement."* This is **sales collateral produced by the product**, not an unpaid consulting project.

### 6.2 Offer ladder (founder-led, below procurement thresholds)

| Offer | Price | What it is | Role |
|-------|-------|------------|------|
| Signal Brief (opener) | free (3 items, product-generated) | proof in first meeting | open |
| Intelligence Sprint | $2,500 | one-time deep teardown of a target agency / pursuit | fast cash |
| Capture Radar | $5,000/mo (or ~$30–60k/yr) | recurring, monitored, ranked STRIKEs | recurring revenue |
| Enterprise conversion | $50k–$100k/yr | multi-seat / multi-BU | **opened now, closed Q2+** — not a 90-day cash line |

## 7. Revenue targets — engineered around $100k

| Target | Meaning | Realism (red-team) |
|--------|---------|--------------------|
| **$100k** | execution target — engineer the company to hit this | PLAUSIBLE |
| **$250k** | stretch target | STRETCH |
| **$500k+** | exceptional outcome | VERY UNLIKELY in 90 days |
| **$1m** | bounty / attack target only — **not an operating forecast** | fantasy on this timeline |

The plan must **not fail unless it reaches $1m**. It must succeed at $100k. Enterprise ($50k–$100k) is
pipeline *opened* now, cash *collected* in the following two quarters.

## 8. The 30-day plan

### Week 1 — Ship the deterministic wedge
- Stand up **point-in-time evidence archive** (R2/object storage): raw bytes, fetch timestamp, content
  hash, source version. Immutable. **This is the moat seed; it starts at pull #1.**
- Stand up **Postgres** with canonical objects: Entity, Evidence, Claim, Event, Catalyst, Opportunity,
  STRIKE, Customer, Capability Profile, Outcome, Prediction.
- Connect **USAspending + SAM**.
- Build the deterministic **recompete / award-expiration detector**. This generates useful commercial
  intelligence almost immediately, with near-zero hallucination risk.

### Week 2 — Add signal sources + AI-assisted layer, produce the Brief
- Add **Federal Register + Grants.gov**.
- AI-assisted, **evidence-grounded, human-reviewed**: extraction, catalyst classification, summarization,
  candidate opportunity generation. No free-form generation — every claim cites a span.
- Human handles CONNECT, economics, FALSIFY, final qualification (→ STRIKE).
- Output the first **Pyrnova Signal Brief**. No dashboard.

### Week 3 — Sell aggressively
- **10 deeply researched accounts first**, then expand toward 50–100 as we learn.
- Each prospect receives **actual Pyrnova intelligence** (a 3-item Signal Brief in their domain), not
  "we built an exciting AI platform."
- Pitch: *"We found these things affecting your capture pipeline. You may not be tracking them yet."*
- **Precursors — the cheap path, not the OMB/Congress pipeline.** The differentiation argument
  ("recompetes alone ≈ HigherGov parity; we see before procurement") is correct, but the answer in the
  selling window is NOT to build OMB/Congress/budget ingestion (hardest, highest-hallucination CONNECT
  step, competes for selling hours). Instead:
  1. **Exploit precursors already in the P0 kernel** — SAM Sources Sought / RFI / Special Notice /
     Presolicitation notice types, and USAspending option-years / IDV ceilings. Differentiated, ~zero
     new-source cost.
  2. **Prove OMB/Congress-style precursors manually in the retrospective casebook** — one analyst, one
     budget-justification → later-solicitation chain, per example. Buys the "we see before procurement"
     proof at ~zero pipeline cost.
  3. **Automate one external precursor only on paying-customer pull** (Week-4 rule), never on spec.

### Week 4 — Let paying customers drive priorities
- Turn on **monitoring, outcome tracking, customer relevance labels, score calibration**.
- Convert Sprints → Capture Radar retainers.
- Build **only** features demanded by real intelligence production.

## 9. Proof strategy — two forms of evidence (the point pushed harder than the red team did)

- **RETROSPECTIVE PROOF (available now):** using only information available before date X, could Pyrnova
  have identified Y? Requires a **small historical casebook — 10–20 meticulously controlled examples**,
  drawn from government sources with strong historical depth. NOT a giant replay platform.
  **Over-index on precursor cases, not recompetes.** A recompete "we could have known" is trivially true
  (contract end dates are public), so it is weak proof. The compelling casebook item is the precursor
  chain (budget line → months later → solicitation) — the hard, differentiated thing. This is also how
  we deliver precursor differentiation without building the precursor pipeline.
- **LIVE FORWARD PROOF (compounding):** Pyrnova issued this on Sep 18; outcome occurred Oct 22. Every
  Signal Brief item is logged as a timestamped Prediction and later graded. This becomes the durable,
  vastly more powerful asset.

## 10. Day-1 moat mandate (non-optional, encoded)

The moat is the **combination**, not outcome labels alone:

> point-in-time evidence + resolved economic graph + precursor relationships + predictions +
> **rejected** predictions + outcome labels + customer-relevance labels + accumulated performance stats.

Every source pull is snapshotted with a fetch timestamp. Every STRIKE emits a Prediction (with its
FALSIFY note and the *rejected* candidates). Every prediction is later graded against an Outcome.
Nothing is discarded. This is what a competitor with the same public data cannot reconstruct after the
fact.

**Two disciplines on the moat claim:**
- **The moat is only real if it produces demonstrable predictive lift** a competitor cannot cheaply
  match. A pile of snapshots with no proven lift is "expensive to reconstruct," which is *not* a moat.
  The performance stats (Section 9 live-forward proof) are what convert storage into moat.
- **Point-in-time capture is source-dependent, not uniform.** Concentrate the discipline where records
  churn — **SAM opportunities** (amendments, cancellations, deletions) and **USAspending** (agency
  restatements). It buys little on **Federal Register**, which is a permanent immutable public archive.
  Snapshot everything cheaply, but do not pretend FedReg/Grants snapshots carry moat weight.

## 11. Metrics (measure only these for 30 days)

- **Cash:** collected $, # Sprints, # Radar retainers, MRR.
- **Selling:** # qualified conversations, # Signal Briefs delivered, first-meeting proof hit rate
  (did we show ≥3 real signals they didn't have?).
- **Proprietary history:** # point-in-time snapshots, # predictions logged, # outcomes graded, entity
  resolution coverage on target agencies.
- **Intelligence advantage:** lead time (days) between Pyrnova signal and public solicitation;
  retrospective casebook hit rate.

## 12. Refuse list (do not build / buy / research yet)

- Self-serve SaaS UI, dashboards, trials.
- Enterprise or Strategic/Data pipeline **products** (schema retention only).
- FLOW / SHIFT / RISK population; full Capability Graph; Outcome-Graph tooling; mechanism library;
  data-licensing/API product; "autonomous" agent loop.
- Premium data purchases (GovWin, ZoomInfo, lobbying feeds) — only when a paying client demands it.
- SEC EDGAR, OFAC, BIS, EIA for now (not relevant to the capture buyer in 30 days).
- The 21-stage pipeline as subsystems (run doctrine stages manually inside REVIEW, but record them).

---

*Companion: `docs/IMPLEMENTATION_SPEC_CAPTURE_RADAR_V1.md` (technical spec) and `db/schema.sql`
(canonical objects, forward-compatible).*

---

# PART II — LOCKED CONTROLLING ADDENDA (Final Strategic Adjudication)

## A. What Pyrnova is (locked)

Pyrnova is an economic and commercial intelligence company. Long-term architecture:

```
ECONOMIC INTELLIGENCE SUBSTRATE
        ↓
AI INTELLIGENCE LAYER
        ↓
OPPORTUNITY ENGINE  |  ENTERPRISE INTELLIGENCE ENGINE  |  STRATEGIC/DATA INTELLIGENCE ENGINE
        ↓
PYRNOVA PRODUCTS
```

The three pipelines remain strategically canonical. **Only the Business Opportunity Pipeline is active
during the initial commercial phase.** Enterprise and Strategic/Data are **dormant until activated** —
they may influence forward-compatible schemas and cheap raw archival, but must NOT generate active
engineering, normalization, integrations, UI, research, or founder-hours before the first $100k unless
explicitly justified by customer demand.

## B. AI Intelligence Layer (doctrine, locked)

Pyrnova uses AI as a **bounded reasoning and interpretation layer** over authoritative evidence and the
proprietary substrate. AI outputs are **claims, classifications, hypotheses, or recommendations** — not
authoritative facts — until supported by provenance, deterministic validation, or required human review.
Deterministic systems remain authoritative for: source state, identifiers, timestamps, raw evidence,
rights, calculations, workflow state, access control, historical reconstruction. **Pyrnova is
model-agnostic.**

Conceptual AI roles (responsibilities, NOT five services to build now):
- **EXTRACT** — unstructured evidence → structured claims with evidence spans.
- **CONNECT** — suggest relationships (entities / events / programs / activity).
- **REASON** — catalyst interpretations, opportunity hypotheses, economic mechanisms.
- **CHALLENGE** — actively attempt to falsify candidate intelligence.
- **COMMUNICATE** — validated intelligence → concise customer-facing output.

Use the **minimum implementation necessary for Capture Radar**. AI is invoked behind one interface,
always producing evidence-grounded claims routed through human REVIEW before customer exposure.

## C. Tiered data retention doctrine (replaces "snapshot everything")

Preserve everything necessary to reconstruct Pyrnova's knowledge state, using **source-specific**
policies. Cryptographic hashes + dedup throughout.

- **TIER A — version-sensitive** (SAM amendments/cancellations, mutable procurement records, changing
  forecasts, revised awards, dynamic web): aggressive temporal preservation; retain materially distinct
  states + full observation history.
- **TIER B — durable authoritative publication** (Federal Register, Grants.gov, canonical filings):
  store canonical content **once**; always retain source id, publication/effective date, Pyrnova
  first-observed timestamp, extraction version, derived claims, entity state, resulting intelligence.
  Do NOT duplicate immutable byte copies.
- **TIER C — ephemeral web**: where lawful and valuable, preserve observed state (future reconstruction
  may be impossible).

## D. The moat test (apply continuously)

> Does Pyrnova's accumulated private history let it make **materially better intelligence decisions**
> than a competent competitor starting today with the same public sources? If not, accumulation is not a
> moat. **Storage volume is not success. Predictive/intelligence lift is success.**

## E. Pyrnova Intelligence Benchmark (accumulate now, do NOT build a platform)

Every sufficiently adjudicated intelligence task may later become a private evaluation case (extraction,
entity, catalyst, opportunity classification, falsification, capability match, relevance, outcome).
**Store the decisions and labels now where cheap** (that is what the REVIEW records + prediction log do).
Do not build a benchmark platform.

## F. Commercial + intelligence scoreboard (track from Day 1)

**Commercial:** targeted accounts · Signal Briefs produced · decision-makers contacted · replies ·
meetings · paid Sprints · Radar customers · cash collected · avg sales cycle · rejection reasons ·
enterprise conversations opened.
**Intelligence:** candidate opportunities · STRIKEs published · customer-relevant STRIKE rate ·
rejection reasons · evidence completeness · lead time · precursor class · source contribution ·
prediction outcomes.

Implemented as `pyrnova/scoreboard.py` (append-only event log) so the numbers accrue automatically.

## G. First Definition of Done (the milestone that matters)

Given one real federal contractor capability profile, Pyrnova ingests current authoritative federal data
and produces **at least one human-reviewed, evidence-backed STRIKE or clearly valuable
pre-solicitation/recompete intelligence item** credible enough to show a target company's Growth/Capture
leadership. It must carry: source evidence · provenance · customer relevance · timing · incumbent/history
where applicable · falsification/contra evidence · recommended action · confidence (separated from
attractiveness) · a stored prediction/intelligence state for later outcome comparison.

## H. What must NOT be built now (kill list, expanded — unless a paying customer/proven workflow requires)

Polished self-service dashboard · mobile apps · Enterprise Intelligence product · Strategic/Data product
· FLOW/SHIFT/RISK UI · institutional deployment · API/data-licensing product · full Capability Graph ·
giant Outcome-Graph product · full replay engine · mechanism library · autonomous multi-agent
architecture · global source coverage · large state/local ingestion · premium data · social monitoring ·
satellite/geospatial · deep private-company intel · CUI handling · SSO/enterprise deployment · broad CRM
integrations · giant crawler · speculative OMB/Congress connectors.

> The economic intelligence substrate emerges from useful work, it does not precede it.

