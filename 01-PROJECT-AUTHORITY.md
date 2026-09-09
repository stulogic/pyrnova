# Pyrnova project authority

_Status: canonical · effective 2026-09-08_

## Mission

Pyrnova is an economic and commercial intelligence company. It turns attributable, time-bounded
external evidence into explainable commercial opportunity judgments and learns from later outcomes.

The first product is **Capture Radar**: human-supervised pre-RFP and recompete intelligence for
mid-market US federal and defense contractors. The current commercial objective remains the first
**$100,000 collected**; infrastructure and product scope must earn their place against that objective.

## Core doctrine

- Show what is known, where it came from, when it was knowable, and what remains unknown.
- Deterministic facts, identities, timestamps, evidence, calculations, and lifecycle state are
  authoritative. AI may assist reasoning and communication but cannot silently create facts.
- Every customer-facing opportunity is explainable from retained evidence and remains human-gated.
- Unknown stays unknown. Do not fabricate research, payloads, outcomes, values, or acceptance proof.
- Point-in-time evaluation enforces `available_at <= replay_as_of`; later evidence is explicitly
  excluded, never smuggled into historical judgment.
- Human review is evidence, not unquestioned truth; retain model and reviewer outputs so both can be
  compared with eventual outcomes.

## Product language authority (binding)

Pyrnova uses formal, precise, operational business and intelligence language. All user-facing copy —
dashboards, reports, briefs, notifications, search results, AI-generated analysis, company dossiers,
exports, and the internal operator UI where applicable — must prioritize information, scope, state,
evidence, action, and analytical meaning over personality or marketing tone.

Prohibited inside the product: slogans, taglines, quirky or clever headings, inspirational or
rhetorical language, conversational jokes, anthropomorphic AI language, faux-dramatic intelligence
language, startup motivational copy, vague benefit claims, generic AI-generated prose, unnecessary
adjectives, headings written mainly for personality, and generic phrases such as "unlock opportunity",
"stay ahead", "turn insights into action", "navigate uncertainty", "make smarter decisions", or
equivalent.

Acceptable headings are literal and functional, e.g. Company Intelligence, Threat Intelligence,
Opportunity Assessment, Company Exposure, Material Changes, Evidence, Relationship Analysis, Source
Operations, Outcome History, Intelligence Gaps, Review Evidence, Run Assessment, Add to Watchlist,
Export Brief.

**Copy quality is part of feature acceptance.** A technically correct feature carrying prohibited
product language is not complete. See D-041.

## Locked product boundaries

- Capture Radar is the active wedge. Broader Pyrnova products remain future options, not current build
  authority.
- Scoring, evidence thresholds, and mechanism rules change only after full-corpus evaluation shows a
  systematic improvement without unacceptable regression.
- Do not optimize for showcase cases, build speculative frontends, or add sources because they are
  merely available.
- Raw evidence and durable evaluation history are moat inputs; stored data is not itself proof of a
  moat. The test is measurable predictive and commercial lift.
- Preserve source-native identity and provenance. Enrichment cannot independently manufacture a
  candidate or STRIKE.

## Global source-ingestion rule

**Live external calls are scarce infrastructure: archive once, replay many.** Development defaults to
offline fixtures or archived responses. Fresh uncached calls are reserved for acceptance and
freshness verification. Adapters must respect provider limits and terms; never rotate keys or accounts
to evade them.

The complete operating contract, modes, budgets, checkpoints, backoff, and metrics is
`docs/specs/SOURCE_INGESTION.md`.

## Scope governance

- `02-EXECUTION.md` authorizes current work. Backlog entries do not.
- Strategically material capabilities not yet built are recorded durably in
  `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`. Milestone planning must consult that roadmap; items
  there may be prioritized, deferred, researched, superseded, or explicitly rejected, but must not be
  silently dropped without owner direction or a documented decision in `04-DECISIONS.md`. The roadmap is
  strategic authority only — it never overrides this authority, execution, or a closed milestone.
- Prefer narrow, test-backed changes and preserve proven behavior.
- Do not deploy, contact prospects, spend money, or begin a later milestone without explicit authority.
- Historical research and handovers cannot override current authority. See `00-INDEX.md` for precedence.

## Canonical execution tree

**Pyrnova's canonical local execution tree is `/Users/stu/Documents/Pyrnova` on `main`.** All local
Claude/Codex implementation work must operate from this tree unless the owner explicitly authorizes
another. GitHub `origin/main` is the repository authority; the canonical tree is the only local working
copy that carries the project's local-only runtime state.

- Agent-created clones or worktrees are **not** implementation authority. A separate clone exists at
  `/Users/stu/pyrnova` (a different local branch); it lacks `.env`/credentials and `examples/real_evidence/`
  and must not be used for milestone work or treated as authoritative.
- Local-only secrets, archives, caches, scheduler/checkpoint state, and `.venv` live only in the
  canonical tree and must never be assumed to exist in an alternate clone/worktree. Never migrate `.env`
  or secrets into Git or copy secret values anywhere.
- If a Claude session starts elsewhere (e.g. its launch directory is the separate clone), switch to the
  canonical tree before doing any work: `cd /Users/stu/Documents/Pyrnova` (or launch the CLI from there).
- The untracked `.codex/` directory in the canonical tree is known and intentional; leave it untouched.

The superseded 30-day authority is retained at `docs/archive/EXECUTION_AUTHORITY_30D_V1.md`; its durable
decisions have been incorporated here and in `04-DECISIONS.md`.
