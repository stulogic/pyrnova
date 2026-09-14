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
| `related_to` | Optional. IDs of related workstreams. |
| `supersedes` | Optional. ID this workstream replaces (parent is marked `SUPERSEDED`). |
| `follow_up_to` | Optional. ID of the prior workstream this continues. |

## Status values

- `READY` — defined, not yet launched.
- `ACTIVE` — launched / in progress.
- `BLOCKED` — cannot progress; see notes.
- `CLOSED` — complete; **done and remembered, not deleted**. Preserved as historical memory; hidden from the operational view; visible in ARCHIVE.
- `DEFERRED` — intentionally postponed (stays in the operational view).
- `SUPERSEDED` — replaced by a later workstream. Preserved; hidden from operational view; visible in ARCHIVE.

## Design principle

**CLOSED MEANS DONE AND REMEMBERED, NOT DELETED.** The launcher never auto-deletes or purges completed workstreams. Their definitions, permanent IDs, and status history are preserved so the same Pyrnova work is not accidentally commissioned twice.

## Views

- **Operational** (default): everything except `CLOSED` and `SUPERSEDED`.
- **Archive**: `CLOSED` + `SUPERSEDED` only, searchable, showing ID, name, category, final status, and lineage to follow-up/superseding work.
- **All**: everything.

## Permanent ID rule

An ID may **never** be silently reused. Every ID that has ever existed is recorded in the permanent ledger `state`/`history.json` in addition to `registry.json`. Before importing, the new ID is checked against the active registry, CLOSED, SUPERSEDED, and the archived ledger. If it has ever existed, the import is **rejected** with a message identifying the existing workstream.

## Duplicate-work protection

Before import, likely semantic duplicates are detected deterministically (Python `difflib` + token Jaccard — no embeddings/AI) across ACTIVE, CLOSED and SUPERSEDED, comparing normalized canonical name, objective, category and keywords. A likely duplicate is **not** silently rejected: the UI shows `POSSIBLE DUPLICATE`, names the existing workstream(s), and requires an explicit `CANCEL` or `IMPORT ANYWAY`.

## Versioning / reopening

Completed research is not normally reopened by flipping `CLOSED` back to `ACTIVE`. Instead use **CREATE FOLLOW-UP**, which mints a new permanent ID (e.g. `PYR-PROD-ROADMAP-003` with `follow_up_to: PYR-PROD-ROADMAP-002`), optionally marking the parent `SUPERSEDED`, preserving the historical chain. An explicit **REOPEN** action exists for work closed by mistake, but it is deliberate, never automatic.

## Bulk import safety

Import is two-phase and atomic: validate all IDs → check duplicate IDs → check likely semantic duplicates → present conflicts → import **only** after conflicts are resolved. One bad item never causes silent partial corruption; a hard conflict yields `0 IMPORTED UNTIL RESOLVED` and writes nothing.

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
