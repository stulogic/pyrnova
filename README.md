# Pyrnova

Economic and commercial intelligence. **Initial commercial phase: Business Opportunity Pipeline only.**

The first product is **Pyrnova Capture Radar** — human-supervised intelligence, backed by software, for
Growth / BD / Capture leaders at ~$20m–$250m US federal & defense contractors. It surfaces recompetes,
contract expirations, and pre-solicitation demand (Sources Sought, RFIs, Presolicitation, Special
Notices) *before* the obvious RFP stage, matched to a customer's actual capabilities, with evidence,
falsification, and a recommended action.

## Governing documents

- **`docs/EXECUTION_AUTHORITY_30D.md`** — CONTROLLING for the next 30 days. Read this first.
- `docs/ADJUDICATION_EVALUATION.md` — how the strategy was stress-tested.
- `docs/IMPLEMENTATION_SPEC_CAPTURE_RADAR_V1.md` — technical spec for the kernel.

## The kernel pipeline

```
OBSERVE → ARCHIVE → NORMALIZE → RESOLVE → DETECT → MATCH → REVIEW → STRIKE → OUTCOME
```

Sources (initial): **USAspending** (keyless) and **SAM.gov** (needs `SAM_API_KEY`). Federal Register /
Grants.gov added only where they materially improve output.

## Quickstart (local, no cloud)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

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
