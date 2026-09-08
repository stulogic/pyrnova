# Pyrnova — Handover / State of Play

_Last updated 2026-09-08. Branch: `claude/pyrnova-strategy-review-hgyii0`. Everything below is committed
and pushed._

## What Pyrnova is (one line)
Economic/commercial intelligence company. First product: **Capture Radar** — human-supervised
pre-RFP + recompete intelligence for mid-market US federal/defense contractors. Governing doc:
`docs/EXECUTION_AUTHORITY_30D.md` (CONTROLLING). Objective: **first $100k collected**.

## Where we are RIGHT NOW
- The kernel is **live and working** end-to-end: USAspending + SAM.gov → evidence archive → recompete +
  pre-solicitation engines → capability match → human review → STRIKE → Signal Brief. 24 tests pass.
- First real target: **Torch Technologies** (`examples/profiles/torch_technologies.json`).
- On the founder's Mac, a live run produced **80 STRIKEs** (46 recompete, 34 pre-sol) and a clean,
  human-reviewed **Signal Brief** leading with 3 real SAM notices in Torch's lane.
- The finished, human-reviewed outbound package is at **`docs/outbound/torch_technologies_brief.md`**
  (brief + email + $2,500 Sprint ask + verify-before-send checklist).

## The 3 STRIKEs in the current Torch brief (all real, live SAM notices)
1. **MEO Missile Warning/Tracking EPOCH 3&4 RFI** — Space Systems Command / PEO Space Sensing (SSC/SNK),
   response ~2026-10-31. relevance 0.85.
2. **Resilient MW/T LEO Ground Entry Points** — Space Development Agency (presolicitation).
3. **Forward-Based Mode Radar Next Prototype** — MDA (presolicitation).
Honest review verdict baked into the brief: Torch's realistic role on all three is
**support / SE&I / M&S / T&E / teaming, NOT hardware/satellite prime.** Say that or a VP dismisses it.

## THE NEXT ACTION (highest leverage toward first $100k)
Get the brief in front of one named human:
1. Clear the "Verify before send" checklist in `docs/outbound/torch_technologies_brief.md`.
2. Find Torch's current **VP Business Development / Capture** (leadership page / LinkedIn) — don't guess.
3. Open the 3 SAM links, confirm live + dates.
4. Send the email + brief; ask for 20 min; offer the $2,500 Sprint.

## How to reproduce the live run (fresh machine)
```bash
git clone https://github.com/stulogic/pyrnova && cd pyrnova
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
SAM_API_KEY=<your_key> python -m pyrnova.cli capture-radar \
  --profile examples/profiles/torch_technologies.json --live --window-days 540 --min-amount 1000000
cat out/signal_brief_torchtechnologies.md
```
USAspending needs no key; SAM does. Full runbook: `docs/LIVE_RUN.md`. Outputs in `out/`; proprietary
accumulation (predictions, reviews, scoreboard, evidence) in `var/` (both gitignored — local only).
**Note:** the SAM key was pasted in chat during setup — regenerate it at sam.gov when convenient.

## Open threads / next build candidates (do NOT build without need — anti-accumulation rule holds)
- **Target #2** (AMERICAN SYSTEMS or MTSI): create a profile like Torch's; run; produce a 2nd brief so
  outreach isn't single-threaded. This is the recommended next execution block.
- Residual pre-sol noise in the tail (some DoD environmental/space-adjacent items still pass the domain
  gate). Human review handles it; only tighten if it recurs across targets.
- Deferred by authority (do NOT build yet): Postgres adapter, dashboard/frontend, Enterprise & Strategic
  pipelines, FLOW/SHIFT/RISK, external precursor connectors, CRM/outbound automation, premium data.
- Retrospective precursor casebook (`docs/PRECURSOR_CASEBOOK.md`): 3 cases drafted; verify specifics
  before customer use; add one missile/defense-adjacent verified case when able.

## Repo map
- `docs/EXECUTION_AUTHORITY_30D.md` — CONTROLLING strategy for 30 days.
- `docs/IMPLEMENTATION_SPEC_CAPTURE_RADAR_V1.md` — technical spec.
- `docs/LIVE_RUN.md` — run instructions.
- `docs/REVIEW_TEMPLATE.md` — human review discipline.
- `docs/PRECURSOR_CASEBOOK.md` — retrospective proof.
- `docs/targets/torch_technologies.md` — target rationale.
- `docs/outbound/torch_technologies_brief.md` — the outbound package to send.
- `pyrnova/` — the kernel (sources, engines, match, review, pipeline, brief, cli).
- `db/schema.sql` — Postgres canonical schema (prod; local dev uses JSONL state).

## Commit trail (branch `claude/pyrnova-strategy-review-hgyii0`)
- `a249e37` first human-reviewed outbound (Torch brief + Sprint ask)
- `d5a5c45` novelty-first ranking + NAICS-noise domain gate (learned from live run)
- `f6943f1` DEFEND vs CAPTURE posture
- `cc50f42` install UX fix (old pip / missing requests)
- `d7801b9` live-run readiness (Torch profile, runbook, casebook)
- `bb33758` Capture Radar kernel v1
- `664b64e` authority lock + scaffolding
