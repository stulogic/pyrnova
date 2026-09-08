# Milestone 7 — economic event graph and commercial consequence engine

_Status: IN PROGRESS 2026-09-08 · authority: `01-PROJECT-AUTHORITY.md`, activated by `02-EXECUTION.md`._

## Core question

Can Pyrnova take an evidence-backed economic chain and derive commercially useful consequences —
_who controls the spend, who receives the award, which downstream suppliers see demand, what
capability is required, when, and by what evidence-backed route value may be captured_ — without
turning structured intelligence into generic AI business brainstorming?

M7 makes this progression explicit and evidence-gated:

    EVENTS / RELATIONSHIPS -> CAPITAL CATALYST -> COMMERCIAL CONSEQUENCE
    -> SCREENING / FALSIFICATION -> STRIKE / WATCH / REJECT

STRIKE generation never bypasses consequence-level evidence.

## The hard rule (anti-generic-idea)

Pyrnova must not see "$500m semiconductor program" and invent consulting/software/logistics/catering
opportunities. Commercial consequences are generated **only** from explicit structured evidence:
procurement language, funding type, regulatory obligation, capability codes/phrases, spend history,
program structure, disclosed capex. A bare appropriation with no procurement/grant/regulation/policy
record produces a catalyst and **zero** consequences — by construction, not by heuristic. Unknown stays
unknown.

## Capital catalyst (`pyrnova/catalysts.py`, `models.CapitalCatalyst`)

An evidence-backed change likely to alter economic behavior. **One catalyst per resolved program
chain**: program keys connected by any accepted relationship (deterministic native-id or accepted
inferred crosswalk) collapse into one component, so a chain never yields duplicate catalysts.
Deterministic identity `cat_<hash(sorted program_keys)>`. It references canonical signals/relationships
(does not duplicate them) and carries `catalyst_type`, controlling institution, participants, geography,
effective date, `stages_present`, a catalyst confidence (distinct from scoring), `first_observed_at`/
`available_at`, `status` (active|contradicted|superseded), and contradiction evidence.

`catalyst_type` ∈ { BUDGET_APPROPRIATION, PROGRAM_ESTABLISHMENT, PROCUREMENT_LIFECYCLE,
REGULATORY_MANDATE, CAPACITY_BUILDOUT, SUPPLY_DISRUPTION }.

## Commercial consequence (`models.CommercialConsequence`, distinct from Opportunity/STRIKE)

One economically distinct behavior a catalyst is likely to cause. A catalyst yields **0..N**
consequences; a catalyst produces multiple consequences only where they are economically distinct and
separately evidenced (e.g. an industrial-capacity program with both an explicit facility-construction
procurement and a funded fabricator). Each consequence carries: mechanism, directness,
mechanism confidence + rationale, participant roles, capability classes, likely spend category, timing,
value estimate, evidence ids, assumptions, structured falsifiers, a consequence confidence, a
recommended `screened_disposition`, and `first_supportable_at`.

## Commercial mechanism taxonomy (v1, deterministic and explainable)

| Mechanism | Trigger (structured) | Typical directness |
|---|---|---|
| DIRECT_PROCUREMENT | procurement/award record with a named buyer | DIRECT |
| FUNDED_DOWNSTREAM_DEMAND | grant/NOFO funding a recipient's downstream spend | DOWNSTREAM |
| FORCED_COMPLIANCE_SPEND | regulatory record with an obligation | DOWNSTREAM |
| CAPITAL_EXPANSION | disclosed capex/facility project | DOWNSTREAM / SECOND_ORDER |
| SUPPLY_DISPLACEMENT | cancellation/closure/recall/shortage/sanction | SECOND_ORDER |
| TECHNOLOGY_MIGRATION | deprecation/standard-change/migration mandate | DOWNSTREAM |
| INDUSTRIAL_CAPACITY_BUILDOUT | policy/program capacity designation | DOWNSTREAM / SECOND_ORDER |

Classification is rule-backed from stage + record_kind + source + explicit flags — never topical
similarity. A subsumption rule drops the same money already captured by a stronger, more direct
mechanism (an appropriation funding an observed direct procurement is not also a separate downstream
consequence; grant-anchored downstream demand and genuine capacity buildout survive as distinct).

## Directness doctrine

- **DIRECT** — explicit buyer/spend path → STRIKE-eligible (requires a resolved BUYER/PRIME_RECIPIENT
  and a specific capability).
- **DOWNSTREAM** — supported but one step removed → WATCH.
- **SECOND_ORDER** — plausible but materially inferential → held internal/WATCH unless corroborated.

## Participant roles (`resolve_participants`)

FUNDING_AUTHORITY, PROGRAM_OWNER, BUYER, PRIME_RECIPIENT, BENEFICIARY, REGULATED_ENTITY are resolved
from authoritative structured fields (stage, source, agency, recipient/parent UEI, regulated entity).
SUPPLIER / SUBCONTRACTOR are never inferred without explicit evidence.

## Capability classes (`pyrnova/capabilities.py`) and value (`pyrnova/value.py`)

Capabilities are specific normalized labels from NAICS/PSC and curated phrases; broad labels
(technology, consulting, services, manufacturing, …) are rejected, so a record whose only signal is a
broad word yields none. Value is KNOWN / ESTIMATED / BOUNDED / UNKNOWN, each with method, inputs,
confidence, provenance, and range. A precise amount is asserted only when explicitly evidenced; the
program total is treated as an upper bound, and inadequate evidence yields UNKNOWN.

## Negative commercial evidence

`ConsequenceFalsifier` records structured kill/reduce reasons (no_identifiable_buyer,
no_executable_procurement_path, funding_restricted_from_commercial_use, incumbent_lock_in,
internal_self_performance, already_awarded, expired_timing, capability_mismatch,
no_downstream_commercial_mechanism, saturated_supply, geographic_restriction, regulatory_exemption,
funding_not_appropriated, program_cancelled, speculative_second_order). A fatal falsifier rejects the
consequence with a reason; it is never a silent confidence reduction.

## Scoring discipline

`scoring_v1` is unchanged and frozen. Catalyst/consequence/mechanism/capability confidences are new,
internal, and distinct from opportunity attractiveness. `screened_disposition` is a recommendation the
corpus checks for consistency with `scoring_v1`, not an override. Any scoring change still requires a
full-corpus comparison, aggregate improvement, no unacceptable regression, and Opus approval.

## Acceptance and validation

`examples/replay/corpus_m7.json` extends the frozen `corpus_m6.json` with eight consequence cases;
each declares `expected_consequences` (catalyst count/type, mechanism, directness, roles, capability,
value status, screened dispositions, rejection expectation) carrying consequence-level ground truth, so
consequence precision is graded only where that truth exists. Results are in
`docs/replay/M7_CONSEQUENCE_REPORT.md`.

```bash
python -m pyrnova.cli consequences        --case <case.json>
python -m pyrnova.cli consequence-corpus  --corpus examples/replay/corpus_m7.json --verbose
python -m pyrnova.cli replay-corpus       --corpus examples/replay/corpus_m7.json   # scoring_v1 unchanged
```
