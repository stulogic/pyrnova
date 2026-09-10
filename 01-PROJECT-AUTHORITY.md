# Pyrnova project authority

_Status: canonical · effective 2026-09-08_

## Mission

Pyrnova is an economic and commercial intelligence company. It turns attributable, time-bounded
external evidence into explainable commercial opportunity judgments and learns from later outcomes.

The first product is **Capture Radar**: human-supervised pre-RFP and recompete intelligence for
mid-market US federal and defense contractors. The current commercial objective remains the first
**$100,000 collected**; infrastructure and product scope must earn their place against that objective.

## Long-term thesis vs. Phase 1 (binding)

**Long-term direction (not Phase 1 scope):** Pyrnova aims to become a continuously updated, historically
auditable model of what external change means economically to a specific organization. This preserves
optionality; it does not authorize building breadth now.

**Current differentiated thesis (Phase 1):** the loop **external change → customer-specific consequence
→ opportunity / threat / monitoring → evidence → review / action → outcome → learning.** Pyrnova is
*not* differentiated by broad data aggregation, generic company research, generic AI search, a knowledge
graph by itself, dashboards, or alerts by themselves.

**Phase 1 wedge:** US federal contractors (defense, industrial, technology, engineering, infrastructure),
working ideal customer ≈ **$50M–$300M revenue** with lean BD/capture capacity. The dominant customer
question is **"What materially changed since I last looked?"**, with **Material Changes** as the dominant
surface and dossier/search/graph as supporting surfaces.

The full current-product authority — customer, product surfaces, required loop, explicit non-goals,
finishability, and moat — is **`docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`** (canonical; informed by the
2026-09-09 red team review and strategic data research in `docs/research/`). See D-044…D-050.

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
product language is not complete. See D-041. The customer-facing voice is the customer face of the
corporate posture doctrine (`docs/strategy/CORPORATE_POSTURE_AND_BRAND.md`, D-054): discretion +
intelligence + competence + control, never menace toward customers.

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

## Finishability rule (binding)

A missing capability may block the current phase **only if**: correctness requires it; safety requires
it; architectural integrity requires it; existing acceptance criteria require it; or a real Phase 1
customer cannot receive the promised Phase 1 decision value without it. Research curiosity, architectural
elegance, theoretical future usefulness, competitor feature parity, "while we are here", an interesting
dataset, or an agent noticing another useful relationship/event/source do **not** qualify. Default
handling: **DOCUMENT → ROADMAP → DEFER.** Expansion is pulled by demonstrated user value, not pushed by
architectural possibility. Finishability is the greatest founder-controlled risk (2026-09-09 red team
review). See D-047; this hardens the phase-control rule D-042.

## Defensibility / moat (binding)

Candidate durable moats, in priority order: historical "what could have been known then?" state;
customer-specific exposure/outcome history; longitudinal outcome calibration; rights-safe relationship
history; rejected-intelligence history; customer-contributed context; accumulated event/consequence
performance; evidence and decision lineage. The following are **not** durable moats by themselves: AI,
prompts, agents, dashboards, graph visualization, natural-language search, company dossiers, alerts, RAG,
citations, generic entity resolution, generic knowledge graphs. Stored data is not itself proof of a
moat; the test is measurable predictive and commercial lift. See D-049.

## Competitive doctrine (binding)

Pyrnova is built to **displace incumbents**, not to reach parity. The Phase 1 commercial test is whether
Pyrnova can repeatedly tell an existing GovWin/GovTribe/equivalent customer something materially
important their workflow missed — early and clearly enough to change what they do. Seek positions that
are CLEARLY BETTER, UNIQUELY CAPABLE, or STRUCTURALLY ADVANTAGED; assume visible features are copied and
invest in imitation-surviving advantages (the candidate moats above). Attack the adjacent problem
incumbents solve poorly — "what changed, how does it affect this organization, what consequence follows,
how certain, what evidence, what happened after" — and do not fight Bloomberg/AlphaSense/Dataminr/Kpler/
Altana/Exiger/PitchBook where their structural advantage is overwhelming (rent that evidence instead).
The evidence standard is **displaced spend**. Competitive aggression never authorizes unlawful access,
misrepresentation, IP theft, system interference, customer-data misuse, license/contract violation, or
deceptive practice, and never overrides the finishability rule or Phase 1 non-goals. Full doctrine:
`docs/strategy/COMPETITIVE_DOCTRINE.md` (D-052).

Competitive intelligence is a first-class capability studied by **lawful means only** (public/open data,
FOIA, lawfully purchased products, independent research, reverse engineering where permitted, independent
derivation), never by unauthorized access, credential misuse, malware, bribery, misrepresentation,
inducing breach of confidentiality, or trade-secret/leaked-code/stolen-database use. Uncertain collection
techniques are **YELLOW** — legal review before operationalization. Rented data is a challenged
dependency held under rights-safe, technically separable provenance so Pyrnova can always answer "if we
terminate this supplier tomorrow, what do we lose?" Full doctrine:
`docs/strategy/COMPETITIVE_INTELLIGENCE_AND_DATA_AUTONOMY.md` (D-053; operating discipline binding now,
product build deferred).

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
