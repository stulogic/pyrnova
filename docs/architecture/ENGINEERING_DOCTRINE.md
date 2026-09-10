# Pyrnova engineering doctrine

_Status: canonical engineering authority · adopted 2026-09-10 (D-059)_

This is the binding software-engineering doctrine for Pyrnova. It sits at **architectural authority**
level in the hierarchy (`00-INDEX.md`): it does not override current product/strategic authority
(`01-PROJECT-AUTHORITY.md`, `PHASE_1_PRODUCT_AUTHORITY.md`), the current milestone work order
(`02-EXECUTION.md`), or durable decisions (`04-DECISIONS.md`), but it governs *how* code and
architecture are built beneath them. It binds every contributor — Claude, Codex, other agents, and human
engineers alike. See the companion `INFRASTRUCTURE_DOCTRINE.md` for capital/infrastructure doctrine.

## Mantra

- **Start cheap. Architect expensive.**
- **Prefer boring, explicit, testable engineering.**
- **One concept, one canonical pattern.**
- **No vibecoded foundations. No rewrite-at-scale handwaving.**
- **Infrastructure may change. Intelligence semantics must not.**
- **Optimize for the engineer debugging this later, not the agent writing it now.**

AI-assisted development does not lower engineering standards. Pyrnova is not disposable prototype
software.

## 1. Decision order (when several implementations are correct)

Choose in this order: (1) established language/framework best practice; (2) existing Pyrnova canonical
pattern; (3) simplest implementation preserving correctness; (4) most readable; (5) most testable;
(6) lowest unnecessary coupling; (7) adequate *measured* performance; (8) only then clever optimization.

Do not choose novelty because it is interesting, abstraction because it looks sophisticated, or shorter
code that materially reduces clarity.

## 2. Existing patterns are default authority

If Pyrnova already has an accepted way to solve a class of problem — StateStore behavior, append-only
history, deterministic IDs, temporal reconstruction, customer overlays, provenance references, computed
read projections, API patterns, migration conventions, lifecycle handling — reuse it. An agent may not
introduce a competing architectural pattern merely because another implementation is also valid.
Deviation requires explicit, recorded justification.

## 3. One concept, one implementation

Avoid parallel near-duplicate concepts (e.g. `EntityResolver` / `EntityMatcher` / `CanonicalResolverV2`
/ `EntityLookupService`) that substantially solve the same problem. Prefer one authoritative
implementation with clear extension points. Duplicate truth is a defect; duplicate architecture is
technical debt. (This is why M22-A/C/D built *computed read projections* over the existing streams
rather than second truth systems — see D-055/D-057/D-058.)

## 4. Simplicity over premature abstraction

Do not abstract before the repeated concept is understood. Three explicit lines may beat an inappropriate
generic framework. Introduce abstraction only when it removes real duplication, clarifies ownership,
stabilizes an interface, enables a known substitution, or meaningfully improves testing/maintainability.

## 5. Function and module discipline

Prefer small coherent functions with obvious inputs/outputs, limited side effects, readable control flow,
and domain-focused modules. Avoid giant multi-purpose functions, god classes, modules owning unrelated
responsibilities, deep nesting, implicit mutation, and unexplained global state. A function's name must
describe what it does; **a read function must not quietly mutate durable state.**

## 6. Explicit state ownership

Every durable piece of truth has one obvious authoritative owner (global intelligence; customer-private
configuration; review state; outcome state; raw evidence; read projections). No shadow ownership. UI
state is never authoritative intelligence. Do not duplicate global truth into customer truth for
convenience (the global-vs-customer-private boundary is binding — D-056/D-057).

## 7. Explicit data flow

Prefer traceable flow: INPUT → NORMALIZATION → DOMAIN LOGIC → PERSISTENCE / PROJECTION → API → UI. Avoid
hidden mutation across layers. For intelligence-sensitive paths preserve provenance, temporal meaning,
customer boundary, observation-vs-inference separation, and identity.

## 8. Type important boundaries

Type domain objects, persistence interfaces, API contracts, intelligence structures, customer-scoped
structures, and migration boundaries. Do not type everything to satisfy tooling; type where mistakes are
expensive.

## 9. Error handling

Errors must be intentional. Avoid broad `except Exception: pass` or silent continuation unless it is a
specifically designed, documented containment boundary (e.g. per-customer/per-item failure isolation in
fan-out, `# noqa: BLE001` with a stated reason). Prefer precise exceptions, bounded recovery, explicit
logging, fail-safe behavior, and idempotent retry where appropriate. **A failure must not silently change
intelligence meaning.**

## 10. No silent fallback that changes semantics

Prohibited: failed deterministic identity → silent LLM guess; missing evidence → invented default;
unresolved entity → automatic merge; source failure → stale data presented as fresh; parsing failure →
fabricated normalized value. Fallbacks must be explicit and semantically safe. **UNKNOWN is preferable to
false certainty** (continuous with the core doctrine in `01-PROJECT-AUTHORITY.md`).

## 11. Dependency discipline

Before adding a dependency ask: can the standard library do this adequately? does Pyrnova already depend
on something that solves it? is it mature and maintained? what is the security/upgrade burden and
coupling? what happens if it disappears? Do not add a package to save ten lines. Prefer mature, boring
dependencies. (See also the infrastructure change gate, `INFRASTRUCTURE_DOCTRINE.md` §37.)

## 12. Dead code / experiment cleanliness

Do not leave abandoned experiments in production paths. Delete unused branches, superseded helpers,
obsolete adapters, dead flags, duplicate implementations, and old agent experiments once safely
superseded. Historical decisions belong in `04-DECISIONS.md`/`06-HISTORY.md`, not as unexplained dead
code (see D-040 for the canonical example).

## 13. No speculative generalization

Build for the current requirement, known accepted extension points, and explicit roadmap compatibility.
Do not design frameworks for hypothetical future markets or generalize every structure to arbitrary
entity/event/source types unless the current architecture genuinely requires it. This is the
finishability rule applied to code (D-047).

## 14. Performance standard

Correct → clear → measured → optimized if needed. Do not prematurely optimize without evidence; do not
knowingly ship pathological approaches. Performance claims require measurement.

## 15. Comments and documentation

Structure explains WHAT; comments explain WHY — invariants, historical reason, non-obvious edge cases,
legal/rights constraints, temporal semantics, and why a simpler-looking approach is unsafe. Avoid
comments that restate the code.

## 16. Testing doctrine

Tests validate contracts, invariants, failure modes, boundary conditions, security/tenant boundaries,
temporal truth, migration behavior, historical replay, customer isolation, and provenance. Avoid tests
that merely mirror implementation internals. Test count is not quality; a thousand weak tests are not
evidence. **Risk-proportional testing is binding.**

## 17. Refactoring discipline

Separate BEHAVIORAL CHANGE from BROAD REFACTOR. Where practical: establish current behavior → refactor
without semantic change (prove tests remain equivalent) → then add the feature. Do not hide large cleanup
inside feature work unless necessary.

## 18. TODO / temporary-hack policy

Temporary code must not become invisible sediment. Any temporary compromise documents why it exists, its
limitation, its removal/replacement trigger, the relevant roadmap/decision, and (where useful) an owner
or milestone. No permanent `TODO someday`.

## 19. Human-developer standard

A new engineer should enter the repository and quickly understand how Pyrnova is built. The codebase must
not reveal stylistic/architectural fragmentation between Claude, Codex, human-written, and future
staff-engineer code. Conventions are stable enough that the code appears to belong to one engineering
organization.

## 20. Debuggability standard

Optimize for the engineer debugging production under pressure: obvious control flow, deterministic
behavior, explicit state transitions, useful logs, stable identifiers, reproducible failures, clear
module boundaries. Avoid clever designs that save code but obscure execution.

## 21. Code-review question (apply to every substantive implementation)

**"Is this merely working code, or is this the best-practice Pyrnova way to solve this problem?"** Where
several approaches exist, compare briefly against language/framework convention, current Pyrnova pattern,
readability, coupling, testability, performance, migration impact, and failure behavior. Choose
deliberately.

## 22. Static quality controls

Where already supported or low-cost, preserve/improve formatting, linting, static typing on important
boundaries, import/module-boundary checks, dependency checks, security scanning, migration validation,
dead-code detection, and complexity warnings. Only introduce tooling that materially improves quality —
no toolchain theatre, and no broad new toolchain inside an unrelated feature milestone.

## 23. Engineering completion standard

A feature is not complete because the happy path works, a UI renders, tests pass, or an agent declares it
"production ready". Completion considers correctness, readability, architectural consistency, failure
behavior, persistence, security boundaries, temporal semantics, migration implications, rollback, tests,
and documentation. This extends the acceptance rule that copy quality is part of completion (D-041).
