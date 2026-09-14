# Pyrnova Workstream Registry (Authority)

This document is the authoritative description of the Pyrnova workstream model. The machine-readable definitions live in `tools/workstream-control/registry.json`; live status lives in `tools/workstream-control/state.json`. Definitions and state are kept **separate on purpose** — the registry says what exists, state says where it is.

## Canonical identity

Every workstream has a permanent canonical ID (e.g. `PYR-PROD-ROADMAP-002`). The ID is embedded in the registry **and** in the generated prompt. It never changes.

ChatGPT sidebar conversation titles are **non-authoritative** and may change. A workstream's identity, authority, and state are determined only by its canonical ID and this registry — never by a chat title.

## Fields

| Field | Meaning |
|-------|---------|
| `id` | Permanent canonical ID. Never reused, never changed. |
| `canonical_name` | Human-readable name. |
| `category` | One of the categories below. |
| `priority` | `HIGH` / `MEDIUM` / `LOW`. |
| `status` | Current lifecycle state (overridden by `state.json`). |
| `objective` | Short statement of what the workstream is to achieve. |
| `prompt_file` | File under `prompts/` holding the workstream-specific task body. |
| `dependencies` | List of workstream IDs this depends on (may be empty). |
| `notes` | Free-form operator notes. |

## Status values

- `READY` — defined, not yet launched.
- `ACTIVE` — launched / in progress.
- `BLOCKED` — cannot progress; see notes.
- `CLOSED` — complete; do not reopen without deliberate decision.
- `DEFERRED` — intentionally postponed.

## Categories

`LAUNCH`, `PRODUCT`, `MOBILE`, `GROWTH`, `BRAND`, `MARKET`, `COMPETITIVE`, `INTELLIGENCE`, `SECURITY`, `OPERATIONS`, `COMPANY`, `STRATEGY`.

## Prompt assembly

Each launched prompt is assembled as:

1. **Canonical header** — fixed boilerplate declaring ID, canonical name, `STATUS AT LAUNCH: ACTIVE`, ID permanence, the non-authoritative-sidebar rule, and the instruction to operate from existing Pyrnova authority and not reopen closed decisions.
2. **Shared context** — `prompts/_boilerplate.md` (kept once, not duplicated per workstream).
3. **Workstream body** — the `prompt_file` task (≈150–400 words).
4. **HANDOVER DELTA footer** — the required close-out structure.

Research produced by these chats is advisory and does **not** automatically modify Phase 1 authority. Changes to authority must be surfaced under `MASTER HANDOVER UPDATES` for human review.

## Extending the registry

Adding a workstream normally requires only:

1. one new entry in `registry.json`, and
2. one new prompt file in `prompts/`.

The UI discovers it on restart. No code change required.

## Seeded workstreams

| ID | Name | Category | Priority |
|----|------|----------|----------|
| PYR-PROD-ROADMAP-002 | Current Product Feature & Competitive Roadmap | PRODUCT | HIGH |
| PYR-VISION-GAP-001 | Original Vision vs Current Pyrnova | STRATEGY | HIGH |
| PYR-ADJACENT-STUDY-001 | Adjacent Company Lessons | COMPETITIVE | HIGH |
| PYR-COMMERCIAL-EXPANSION-001 | Commercial Market Expansion | MARKET | HIGH |
| PYR-NETWORK-001 | Founder & Corporate Network Development | GROWTH | HIGH |
| PYR-MEMBERSHIPS-001 | Memberships, Associations & Events | GROWTH | MEDIUM |
| PYR-BRAND-SOCIAL-001 | Social Brand Asset System | BRAND | MEDIUM |
| PYR-SOCIAL-INTEL-001 | Social & Market Monitoring System | INTELLIGENCE | HIGH |
| PYR-AUTH-001 | Authentication, MFA & Identity Roadmap | SECURITY | HIGH |
| PYR-BIZ-TOOLS-001 | Business Operations Tool Stack | COMPANY | MEDIUM |
