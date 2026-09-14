# Pyrnova Workstream Control

Local, single-user dispatch console for launching Pyrnova strategy workstreams into ChatGPT with canonical, self-identifying prompts. Isolated developer tooling — it does **not** touch the Pyrnova product runtime, the Phase 1 soak, or any evidence directory.

## HOW STU USES THIS

1. Double-click `launch.command`.
2. Click `LAUNCH`.
3. ChatGPT opens.
4. Press `Cmd+V`.
5. Press `Enter`.
6. Return the completed HANDOVER DELTA to the dispatch chat.

That's the whole loop. Everything below is reference.

## What LAUNCH does

Retrieves the canonical prompt → copies it to the clipboard → marks the workstream `ACTIVE` → persists state → opens `https://chatgpt.com/` → shows **PROMPT COPIED / PASTE INTO CHATGPT AND PRESS ENTER**.

It does not automate ChatGPT's page. You paste and press Enter.

## Secondary controls (per card)

- `COPY PROMPT` — copy the canonical prompt without changing state.
- `COPY HANDOVER HEADER` — copy the handover header to paste your result under.
- `MARK READY / ACTIVE / BLOCKED / CLOSED` — set status manually.

## Canonical IDs

Every workstream has a permanent ID embedded in both the registry and its prompt. ChatGPT sidebar titles are **non-authoritative** — identity comes from the ID, never the tab name.

## CLOSED means done and remembered, not deleted

Completed work is never purged. `CLOSED` and `SUPERSEDED` workstreams are preserved (definition, permanent ID, status history) and simply hidden from the default **OPERATIONAL** view. Switch the view toggle to **ARCHIVE** to see them (searchable, with lineage).

- **Permanent IDs** are never silently reused. Importing an ID that has ever existed is rejected.
- **Duplicate protection:** before import, likely semantic duplicates (deterministic `difflib` matching — no AI) are flagged as `POSSIBLE DUPLICATE`; you must choose `CANCEL` or `IMPORT ANYWAY`.
- **Bulk import** is atomic: validate all → resolve conflicts → then import. One bad item never corrupts the registry (`0 IMPORTED UNTIL RESOLVED`).
- **CREATE FOLLOW-UP** mints a new permanent ID linked to the parent (`follow_up_to`), optionally marking the parent `SUPERSEDED`, instead of reopening finished work. **REOPEN** exists for accidental closes but is deliberate.

The point: stop accidentally commissioning the same Pyrnova work twice.

## Files

- `launch.command` — double-click launcher (starts `server.py`, opens the UI).
- `server.py` — stdlib-only local server + JSON API (127.0.0.1).
- `registry.json` — canonical workstream definitions (source of truth for *what exists*).
- `state.json` — persisted status + status history (source of truth for *current state*). Kept separate from the registry.
- `history.json` — permanent ID ledger; every ID that has ever existed, so IDs are never silently reused.
- `static/` — the UI (`index.html`, `app.js`, `styles.css`).
- `prompts/` — `_boilerplate.md` (shared context) + one body file per workstream.

## Adding a workstream

1. Add one entry to `registry.json` (with a `prompt_file`).
2. Add that one prompt file under `prompts/`.
3. Restart. The UI discovers it automatically.

Canonical field reference lives in `docs/authority/PYRNOVA_WORKSTREAM_REGISTRY.md`.

## Setup / requirements

- macOS, Python 3 (stdlib only — no install step).
- One-time: make the launcher runnable — `chmod +x launch.command` (already set in-repo). If Finder blocks it, right-click → Open once.
- Clipboard uses the browser on `localhost` plus a server-side `pbcopy` fallback, so the prompt is reliably copied.
- Port defaults to `8787` (`PYRNOVA_WSC_PORT` to override).
