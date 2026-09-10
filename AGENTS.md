# Pyrnova — agent operating rules (anti-drift)

This file is the mandatory entrypoint for any agent (Claude, Codex, or other) beginning substantive work
in Pyrnova. It exists to catch scope drift **before** tokens and code are spent. It is lightweight by
design — not process theatre.

## Canonical working tree

Pyrnova's only local implementation authority is **`/Users/stu/Documents/Pyrnova` on `main`**
(GitHub `origin/main` is repository authority). A separate clone at `/Users/stu/pyrnova` is **not**
authoritative — it lacks credentials and real evidence and must not be used for milestone work. If your
session started elsewhere, switch first. The untracked `.codex/` directory is intentional; leave it.

## Authority hierarchy (resolve conflicts in this order)

1. **Current product / strategic authority** — `01-PROJECT-AUTHORITY.md`,
   `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`, and `docs/strategy/COMPETITIVE_DOCTRINE.md`.
2. **Current milestone work order** — `02-EXECUTION.md`.
3. **Durable decisions** — `04-DECISIONS.md`.
4. **Current state** — `03-CURRENT-STATE.md`.
5. **Architectural authority** — `docs/architecture/` (including the binding engineering doctrine
   `ENGINEERING_DOCTRINE.md` and infrastructure & capital doctrine `INFRASTRUCTURE_DOCTRINE.md`, D-059),
   `db/`, relevant `docs/specs/`.
6. **Roadmap** — `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md`, then `05-BACKLOG.md`.
7. **Research** — `docs/research/` (informs authority; never authorizes implementation).
8. **Historical / superseded** — `06-HISTORY.md`, `docs/handovers/`, `docs/archive/`.

Rules:
- **Research can inform authority; it does not independently authorize implementation.**
- **Roadmap entries do not belong to the current milestone unless `02-EXECUTION.md` explicitly says so.**
- **Historical documents never override current authority.**

## Reading order (read only what the task needs)

`00-INDEX.md` → `01-PROJECT-AUTHORITY.md` → `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md` →
`03-CURRENT-STATE.md` → `02-EXECUTION.md` → the relevant `docs/specs/` document. Consult `04-DECISIONS.md`
when a prior choice affects the task; consult roadmap/research only for future-scope questions.

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
