# Pyrnova — agent operating rules (anti-drift)

This file is the mandatory entrypoint for any agent (Claude, Codex, or other) beginning substantive work
in Pyrnova. It exists to catch scope drift **before** tokens and code are spent. It is lightweight by
design — not process theatre.

## Canonical working tree

Pyrnova's only local implementation authority is **`/Users/stu/Documents/Pyrnova` on `main`**
(GitHub `origin/main` is repository authority). A separate clone at `/Users/stu/pyrnova` is **not**
authoritative — it lacks credentials and real evidence and must not be used for milestone work. If your
session started elsewhere, switch first. The untracked `.codex/` directory is intentional; leave it.

## Repository-first context

Begin Pyrnova work by inspecting current GitHub/repository authority and the relevant state on
`origin/main`; preserve unrelated branches, worktrees, staged files, and untracked work while doing so.
The repository is the primary operational source of truth. Conversation history is supplemental context
only when current repository canon is silent or the owner explicitly asks to recover a recent,
unreconciled decision. Do not trawl old chats for decisions that should already be canonical.

When an owner decision made in chat materially changes product architecture, commercial authority,
brand/design doctrine, implementation constraints, or operating rules, reconcile it promptly through the
smallest coherent repository authority update and push it when repository workflow permits. This rule
does not change the authority hierarchy below: current owner decisions remain highest authority; it makes
the repository the first place future work consults for their durable expression.

## Authority hierarchy (resolve conflicts in this order)

1. **Owner decisions / Phase One Constitution** — highest authority; the locked Constitution is
   incorporated in `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`.
2. **Cross-phase product / commercial authority** — `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md`
   and the locked platform/product boundaries in `docs/strategy/PLATFORM_PRODUCT_ARCHITECTURE.md`.
3. **Phase 1 product / implementation authority** — `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` is sole
   authority within Phase 1 scope. `01-PROJECT-AUTHORITY.md` and the compatible strategy companions
   summarize or specialize current doctrine; none may erase or redefine cross-phase authority outside
   Phase 1.
4. **Execution / state / milestone / evidence** — `02-EXECUTION.md`, `03-CURRENT-STATE.md`,
   `04-DECISIONS.md`, and relevant `docs/specs/` implement or record higher authority.
5. **Architectural authority** — `docs/architecture/` (including the binding engineering doctrine
   `ENGINEERING_DOCTRINE.md` and infrastructure & capital doctrine `INFRASTRUCTURE_DOCTRINE.md`, D-059),
   and `db/`.
6. **Roadmap** — `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`, then `05-BACKLOG.md`.
7. **Research** — `docs/research/` (informs authority; never authorizes implementation).
8. **Historical / superseded** — `06-HISTORY.md`, `docs/handovers/`, `docs/archive/`.

Rules:
- **Research can inform authority; it does not independently authorize implementation.**
- **Roadmap entries do not belong to the current milestone unless `02-EXECUTION.md` explicitly says so.**
- **Historical documents never override current authority.**

## Reading order (read only what the task needs)

`00-INDEX.md` → `01-PROJECT-AUTHORITY.md` → `docs/strategy/PRODUCT_COMMERCIAL_AUTHORITY.md` →
`docs/strategy/PLATFORM_PRODUCT_ARCHITECTURE.md` → `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` →
`03-CURRENT-STATE.md` → `02-EXECUTION.md` → the relevant `docs/specs/` document. Consult
`04-DECISIONS.md` when a prior choice affects the task; consult
roadmap/research only for future-scope questions. Read `PRODUCT_COMMERCIAL_AUTHORITY.md` before using
research or roadmap material to make any product/commercial decision.

For brand, visual-identity, UI presentation, or asset-generation work, also read
`docs/strategy/CORPORATE_POSTURE_AND_BRAND.md` and the relevant material under `docs/brand/` before using
concept boards, generated assets, or conversational descriptions.

Core and PyrAI are shared platform layers. Scout, Strike, Vector, and Atlas are complementary products,
not mandatory sequential pipeline stages. Product work must not fork shared canonical truth or infer that
all four products are current Phase 1 SKUs; only `02-EXECUTION.md` may open implementation.

Current Phase 1 is **Pyrnova / Strategic Change Pilot** and is Strike-led, not Strike-owned (D-068).
Product identity, implemented capability, integrated Phase 1 capability, standalone readiness and
commercial availability are different states. Do not rename the offer to Strike, advertise a product as
separately available, or invent entitlement/pricing/bundling before recorded readiness and owner approval.

## Do NOT treat as higher authority than current repository authority

README marketing language; stale plans; historical work orders; future-roadmap items; research
recommendations; comments in old code; previous chat prompts. If any of these conflict with current
authority, **stop the conflicting interpretation** and use the hierarchy above. If a conflict is
genuinely unresolved, **record the conflict** (in `04-DECISIONS.md` or the current work order) rather
than silently choosing the broader scope.

## Start-of-work check (state these before implementing)

1. Current milestone.
2. Current customer.
3. Current product goal.
4. Explicit non-goals.
5. Relevant acceptance criteria.
6. Files/documents treated as authoritative for this task.
7. Whether the proposed work is **CURRENT** or **ROADMAP**. If ROADMAP, stop and get authority.

## End-of-work check (verify before closing a work block)

- Work stayed within current authority.
- No deferred feature became an accidental dependency.
- Relevant decision/state docs were updated.
- Newly discovered future ideas were roadmapped, not silently implemented.
- Current-state documentation still matches the code.
- Tests remain proportional to risk; no acceptance criterion was weakened.

## Competitive governing question (apply to every major Phase 1 capability)

**"Why would a rational customer already paying for the incumbent (GovWin/GovTribe/equivalent) switch
budget, workflow, or attention to Pyrnova?"** A weak answer means the capability is not finished; do not
ship parity. Build advantages that survive imitation (accumulated history, outcome calibration, rejection
history, customer-specific exposure, rights-safe relationships, evidence lineage). Attack the adjacent
problem incumbents solve poorly; do not fight them where their structural advantage is overwhelming. Full
doctrine: `docs/strategy/COMPETITIVE_DOCTRINE.md` (D-052). This never authorizes scope expansion (see the
finishability rule below) or any unlawful/deceptive practice.

## Lawful competitive intelligence (binding)

Study competitors and challenge rented data by **lawful means only**: public/open data, FOIA, lawfully
purchased products, ordinary authorized access, independent research, reverse engineering where legally
permitted, and independent derivation. **Never** use unauthorized access, credential misuse, malware,
bribery, misrepresentation to obtain protected information, inducement to breach confidentiality, or
trade-secret / leaked-code / stolen-database material. Any collection technique with uncertain
terms-of-service, copyright, automated-collection, access-control, database-rights, or contractual
implications is **YELLOW → legal review before operationalization** (not before study). Keep clean-room
OBSERVATION separate from IMPLEMENTATION; keep rented-data provenance separable. Building the competitor-
dossier / benchmark / vendor-displacement *product* is **roadmap-deferred** (D-053, roadmap area 23) —
not current implementation authority. Full doctrine:
`docs/strategy/COMPETITIVE_INTELLIGENCE_AND_DATA_AUTONOMY.md`.

## Disclosure & voice (binding)

Any customer-facing or external-facing artifact follows the Product Language Authority (D-041) and the
customer face of the corporate posture doctrine (`docs/strategy/CORPORATE_POSTURE_AND_BRAND.md`, D-054):
discretion + intelligence + competence + control, never menace toward customers. External disclosure
defaults to **need-to-know** — do not publish roadmap, datasets, methods, competitive dossiers, pricing,
or strategic weaknesses externally without a commercial reason. This does **not** weaken *internal*
record-keeping: keep the repository's authority/decisions/state full, honest, and current.

## Visual identity (binding for assets and UI)

Before generating or changing a Pyrnova asset or UI, read the visual identity authority in
`docs/strategy/CORPORATE_POSTURE_AND_BRAND.md` (D-069) and preserve the product hierarchy in
`docs/strategy/PLATFORM_PRODUCT_ARCHITECTURE.md`. Cyan is the default parent/platform accent; Strike is
red/orange, Scout green, Vector blue and Atlas violet/purple. PyrAI is a subordinate blue/violet shared
layer, not a fifth product. Apply the recorded typography classes and hierarchy; do not promote a concept
board's slogans, filler copy, photography, icon geometry, unapproved fonts or proposed tokens into
authority. The master Pyrnova mark and wordmark on the current owner-approved concept board are the
**CURRENT WORKING LOGO CONCEPT**: preserve and reuse them by default; do not redesign, replace,
reinterpret or improve them without explicit owner authorization. Exact Scout, Strike, Vector and Atlas
marks and role-specific imagery remain approval-gated. The missing canonical master-asset requirement is
recorded under `docs/brand/master/`.

## Engineering & infrastructure doctrine (binding)

*How* you build is governed, not just what. Before substantive implementation or infrastructure work,
read `docs/architecture/ENGINEERING_DOCTRINE.md` (decision order; one concept, one canonical pattern;
simplicity over premature abstraction; explicit state ownership; **no silent fallback that changes
semantics**; risk-proportional testing; the completion standard) and
`docs/architecture/INFRASTRUCTURE_DOCTRINE.md` (capacity follows utilization; reliability follows
consequence; permanent-vs-replaceable; migration invariants). **Start cheap, architect expensive; prefer
boring, explicit, testable engineering; infrastructure may change but intelligence semantics must not.**
Reuse the existing canonical pattern rather than inventing a competing one; a deviation must be recorded
(D-059).

## Finishability rule (binding)

A missing capability may block a phase **only** for correctness, safety, architectural integrity,
existing acceptance criteria, or real Phase 1 customer decision value. Research curiosity, elegance,
theoretical usefulness, competitor parity, "while we are here", an interesting dataset, or an agent
noticing another useful relationship/event/source do **not** qualify. Default: **DOCUMENT → ROADMAP →
DEFER.** See `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` and D-047.
