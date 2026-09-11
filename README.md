# Pyrnova

**Decision-grade external intelligence for government contractors.**

Pyrnova helps federal contractors identify which external developments matter, understand why they matter, verify the evidence, and decide what to investigate or do next.

Phase 1 is organized around **Material Changes**. It is not CRM, generic procurement search, GovWin with AI, generic company research, generic AI chat/research, or a dashboard-builder product.

The canonical Phase 1 product and commercial authority is `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`.

## Current Phase 1 state

- Phase One Constitution: **locked**.
- M21 and M22: **closed**.
- Opportunity, Access, and Onboarding design-customer P0s: **closed**.
- Sole primary remaining design-customer P0: **Live Operations / Data Volume Readiness**.
- Current Customer #1 target: **IronMountain Solutions**.
- Immediate workstream: **PHASE1-LIVE-OPS-CLOSURE** in `02-EXECUTION.md`.
- Next decision after Live Ops closure: **Customer #1 GO / NO-GO**.

Broad Phase 1 research and broad product expansion are not currently authorized.

## Start here

- **`AGENTS.md`**: anti-drift rules, canonical tree, authority hierarchy, start/end checks.
- **`00-INDEX.md`**: canonical navigation and authority precedence.
- `01-PROJECT-AUTHORITY.md`: mission, boundaries, and locked doctrine.
- `docs/strategy/PHASE_1_PRODUCT_AUTHORITY.md`: canonical Phase 1 product and commercial authority.
- `03-CURRENT-STATE.md`: current implementation and readiness state.
- `02-EXECUTION.md`: the single authorized workstream and acceptance gates.
- `docs/architecture/`: engineering and infrastructure doctrine.
- `docs/specs/`: detailed implementation and acceptance specifications.
- `docs/research/00-RESEARCH-INDEX.md`: non-authoritative research provenance and research-to-decision traceability.

## Phase 1 intelligence lineage

```text
SOURCE
-> EVIDENCE ARTIFACT
-> ASSERTION
-> ASSESSMENT
-> CUSTOMER CONSEQUENCE
-> MATERIAL CHANGE
-> INVESTIGATION / REVIEW
-> ACTION
-> OUTCOME
```

Canonical intelligence truth remains separate from presentation. Raw evidence retains provenance. Unknown, unresolved, stale, degraded, and conflicting states remain explicit rather than being converted into false certainty.

## Customer-facing product

Run the current customer-facing application locally with:

```bash
python -m pyrnova.ops_server
```

Material Changes is served at `/`. The local internal Operator Console is at `/console` where allowed by the access policy.

Customer access and seed-free onboarding are implemented through the current customer/watch/credential tooling. See:

- `docs/specs/M22A_MATERIAL_CHANGES.md`
- `docs/specs/M22B_PERSISTED_CUSTOMER_LIFECYCLE.md`
- `docs/specs/M22C_CUSTOMER_MATERIAL_CHANGE_STREAMS.md`
- `docs/specs/M22D_INVESTIGATION_SEARCH.md`
- `docs/specs/M22E_OPPORTUNITY_MATERIAL_CHANGES.md`
- `docs/specs/M22F_MINIMAL_ACCESS_ONBOARDING.md`
- `docs/OPERATOR_CONSOLE.md`

## Live Operations

The immediate engineering focus is not new product breadth. It is proving that Pyrnova can run continuously on enough real external intelligence to produce repeated customer-specific decision value.

Operating doctrine:

```text
BULK FIRST
-> DELTA SECOND
-> TARGETED LIVE LAST

ARCHIVE ONCE
-> REPLAY MANY
```

Live Ops closure has two separate gates:

1. **ENGINEERING ACCEPTANCE**
2. **OPERATIONAL SOAK ACCEPTANCE**

The second gate requires **7 calendar days / 5 business days of unattended live operation**. Passing tests alone does not satisfy it.

## Existing kernel and evidence lineage

The original Capture Radar and Business Opportunity Pipeline work remains part of Pyrnova's implementation lineage. Existing deterministic engines, archived evidence, replay corpora, source controls, fit logic, opportunity/threat models, and earlier live-operation primitives remain valid where compatible with current authority.

Historical kernel flow:

```text
OBSERVE -> ARCHIVE -> NORMALIZE -> RESOLVE -> DETECT -> MATCH -> REVIEW -> STRIKE -> OUTCOME
```

Do not mistake that historical implementation flow for the current Phase 1 category or customer-facing product definition.

Current source work includes USAspending, SAM.gov, Federal Register, Grants.gov, SEC EDGAR, OFAC, selected official procurement forecasts, and other bounded adapters documented in the source manifest. Source inclusion does not itself authorize new product scope.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Existing deterministic Capture Radar path using live USAspending
python -m pyrnova.cli capture-radar --profile examples/profiles/acme_c4isr.json --live

# Fully offline deterministic fixture path
python -m pyrnova.cli capture-radar --profile examples/profiles/acme_c4isr.json --fixtures

pytest -q
```

The Capture Radar CLI remains useful engineering lineage and testable functionality. It is not a competing current product authority.

## Design rules

- Preserve deterministic identity, provenance, point-in-time truth, and replay.
- Keep observed evidence, assertions, assessments, customer consequences, review state, and outcomes distinct.
- Keep customer-specific relevance/private context separate from global intelligence truth.
- AI is bounded and attributable. Model output is not authoritative fact merely because a model produced it.
- No silent source failure or semantic fallback.
- No broad Phase 1 expansion while Live Operations and Customer #1 readiness remain open.
- New ideas default to **DOCUMENT -> ROADMAP -> DEFER** unless required for correctness, safety, architectural integrity, current acceptance, or valid Customer #1 measurement.

## Repository authority

The canonical local working tree is `/Users/stu/Documents/Pyrnova` on `main`; GitHub `origin/main` is repository authority. `/Users/stu/pyrnova` is not the authorized local tree.

Historical execution authorities, old offers, old targets, and prior "next action" sections remain provenance only when stored under lower-authority historical locations. They do not override the current authority hierarchy.
