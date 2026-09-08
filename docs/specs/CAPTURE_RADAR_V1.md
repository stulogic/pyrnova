# Capture Radar / Opportunity Engine v1 — Implementation Spec

Companion to `01-PROJECT-AUTHORITY.md` and `02-EXECUTION.md`. Scope: the smallest runnable path that
produces sellable intelligence and starts proprietary accumulation on Day 1.

## Pipeline (software modules, not 21 subsystems)

```
OBSERVE → ARCHIVE → NORMALIZE → RESOLVE → DETECT → MATCH → REVIEW → STRIKE → OUTCOME
```

| Stage | Module | Determinism |
|-------|--------|-------------|
| OBSERVE | `pyrnova.sources.*` (USAspending, SAM) | deterministic fetch |
| ARCHIVE | `pyrnova.archive` (content-addressed, tiered) | deterministic |
| NORMALIZE | `pyrnova.normalize` | deterministic |
| RESOLVE | `pyrnova.resolve` (UEI/name → entity) | deterministic (AI only for ambiguous, human-gated) |
| DETECT | `pyrnova.engines.recompete`, `pyrnova.engines.presolicitation` | deterministic |
| MATCH | `pyrnova.match` (capability profile) | deterministic scoring |
| REVIEW | `pyrnova.review` (records adjudication; AI may recommend) | human authoritative |
| STRIKE | opportunity state → `strike` + `pyrnova.prediction` logged | deterministic |
| OUTCOME | `pyrnova.outcome` (graded later) | deterministic |

AI (the AI Intelligence Layer) is invoked behind **one** interface `pyrnova.ai.reasoner` with roles
EXTRACT/CONNECT/REASON/CHALLENGE/COMMUNICATE. v1 keeps AI **optional**: the deterministic recompete +
pre-solicitation path produces real intelligence with **zero** model dependency, satisfying the first
Definition of Done without an API key. AI enriches (summaries, mechanism reasoning, contra-evidence
search) where a key is present, always emitting evidence-grounded `claim`s routed through REVIEW.

## Storage

- **Evidence archive** (`pyrnova.archive`): content-addressed by sha256. Local filesystem adapter by
  default (`file://`); S3/R2 adapter when configured. Immutable; write-once per content hash. Sidecar
  metadata records source, observed_at, published_at, retention tier, source_ref, source_url.
- **Operational store**: Postgres in prod (`db/schema.sql`). Local dev persists append-only state
  (predictions, reviews, scoreboard) as JSONL under `PYRNOVA_STATE_DIR` — no DB required to run the
  kernel or tests. The repository layer is abstracted so the Postgres adapter drops in later.

## Retention tiers (per source)

- USAspending awards → **Tier A** (agencies restate/resubmit; capture materially distinct states).
- SAM opportunities → **Tier A** (amendments/cancellations; preserve transition history).
- Federal Register / Grants.gov → **Tier B** (durable; store canonical content once + metadata).

## Deterministic engines

### Recompete / expiry (`engines/recompete.py`)
Input: USAspending awards (contracts A/B/C/D) with `End Date`, `Award Amount`, `Recipient Name`,
`Awarding Agency`, NAICS, `generated_internal_id`. Output: candidate opportunities where the
period-of-performance end date falls within a configurable forward window. Ranks by months-to-expiry
and value. Not treated as predictive on its own — it is a high-confidence **entry** signal that gains
value once matched to capability + pre-solicitation + incumbent/history + timing. Emits a `prediction`
("recompete solicitation likely to post before <end_date>") for later grading.

### Pre-solicitation (`engines/presolicitation.py`)
Input: SAM Opportunities notices. Structures notice class (Sources Sought `r`, RFI, Presolicitation `p`,
Special Notice `s`, Solicitation `o`, Combined `k`, Award `a`), response deadlines, NAICS/PSC, set-aside,
office/agency, and amendment/cancellation transitions. This is the commercial wedge: qualify meaningful
federal demand before the RFP.

> Notice-type codes are configurable in `pyrnova/sources/sam.py` and must be verified against current
> SAM "Get Opportunities" API docs before production; we do not silently invent field contracts.

## Matching (`match.py`)
Deterministic relevance score in [0,1] from capability profile overlap: agency, NAICS/PSC prefix,
capability keyword hits in title, value band, set-aside eligibility, minus hard exclusions. Kept
**separate** from opportunity attractiveness and from our confidence in the intelligence.

## Output (`brief.py`)
Markdown **Signal Brief** (3 items, outbound) and **Capture Radar Report** (full). Each item shows:
found · why it matters · customer fit · buyer/agency/program · timing · incumbent/history · evidence
links · contra/falsifying info · recommended action · confidence (separate from attractiveness). PDF is
a later, trivial render step; Markdown is sufficient initially.

## Accumulation (Day 1, non-optional)
Every run appends: observations (with observed_at), evidence hashes, predictions (with precursor class +
lead time), reviews (accept/reject + reason = benchmark labels), and scoreboard events. This is the
moat's raw material; the measurable-lift test in `01-PROJECT-AUTHORITY.md` is applied continuously.

## Repo layout
```
pyrnova/            package (see modules above)
db/schema.sql       Postgres canonical schema
examples/profiles/  sample capability profiles
tests/              pytest; deterministic engines covered with fixtures
tests/fixtures/     sample source payloads (clearly marked, shape-faithful)
```

## EXTERNAL ACTIONS
- **SAM_API_KEY** required for live SAM ingestion (pre-solicitation engine). USAspending needs none.
- **Object storage (R2/S3)** optional; local archive works without it. Provide bucket + S3 creds to move
  to production retention.
- **Postgres** optional for dev; provide `PYRNOVA_DATABASE_URL` and apply `db/schema.sql` for prod.
