# Pyrnova

Economic and commercial intelligence. **Initial commercial phase: Business Opportunity Pipeline only.**

The first product is **Pyrnova Capture Radar** — human-supervised intelligence, backed by software, for
Growth / BD / Capture leaders at ~$20m–$250m US federal & defense contractors. It surfaces recompetes,
contract expirations, and pre-solicitation demand (Sources Sought, RFIs, Presolicitation, Special
Notices) *before* the obvious RFP stage, matched to a customer's actual capabilities, with evidence,
falsification, and a recommended action.

## Start here

- **`00-INDEX.md`** — canonical navigation, reading order, and authority precedence.
- `01-PROJECT-AUTHORITY.md` — mission, product boundaries, and locked doctrine.
- `03-CURRENT-STATE.md` — verified implementation and milestone truth.
- `02-EXECUTION.md` — current work and active constraints.
- `docs/specs/CAPTURE_RADAR_V1.md` — detailed kernel specification.

## Going live (founder)

- **`docs/specs/LIVE_RUN.md`** — fresh checkout → live intelligence in ~5 minutes.
- First real target: `examples/profiles/torch_technologies.json` (rationale + provenance in
  `docs/targets/torch_technologies.md`).
- Review discipline: `docs/specs/REVIEW_TEMPLATE.md`. Supporting precursor research:
  `docs/research/PRECURSOR_CASEBOOK.md`.

## The kernel pipeline

```
OBSERVE → ARCHIVE → NORMALIZE → RESOLVE → DETECT → MATCH → REVIEW → STRIKE → OUTCOME
```

Active sources: **USAspending** (keyless), **SAM.gov** (needs `SAM_API_KEY`), and bounded Federal
Register context. Grants.gov and other M4 sources are not implemented.

## Quickstart (local, no cloud)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # runtime = just `requests`; `pip install -e ".[dev]"` also works on a modern pip

# Deterministic recompete intelligence from LIVE USAspending (no API key needed):
python -m pyrnova.cli capture-radar --profile examples/profiles/acme_c4isr.json --live

# Fully offline demo (bundled fixtures, deterministic, used by tests):
python -m pyrnova.cli capture-radar --profile examples/profiles/acme_c4isr.json --fixtures

pytest -q
```

Output: a **Pyrnova Signal Brief** (Markdown) under `out/`, plus an append-only prediction log and
scoreboard events — the proprietary history that must start accumulating on Day 1.

## Design rules (from the authority)

- Deterministic core is authoritative (IDs, timestamps, evidence, calculations, state). AI is a bounded
  reasoning layer producing **claims**, never authoritative facts, always routed through human review.
- Point-in-time evidence archive is content-addressed and immutable; retention is **tiered** per source.
- No self-serve dashboard, no premium data, no dormant-pipeline engineering before the first $100k.
- Every customer-facing item is human-reviewed; every review is recorded as labeled intelligence work.

## Configuration

Copy `.env.example` → `.env`. Cloud storage is optional; without it the evidence archive uses a local
filesystem adapter, so all work continues offline. See **EXTERNAL ACTIONS** in the spec for the exact
credentials needed to move to production storage.

Historical evaluation commands and the current empirical baseline are documented in
`docs/replay/M3_BASELINE.md`. The canonical challenge corpus is `examples/replay/corpus_v1.json`.
