# B4.12 — Commercial rehearsal (exact candidate)

**This is a rehearsal, not outreach.** No prospect communication was sent, no legal seller was created,
no intake was enabled, and no soak was started or claimed passed. It proves the candidate product and
the locked commercial package can support the real Customer #1 sequence **without inventing product
state**.

Reproduce: `PYTHONPATH=. <venv>/python docs/evidence/bundle4/rehearsal_capture.py` → writes
`docs/evidence/bundle4/rehearsal_capture.json` and fails loudly on any truthfulness violation.

## Locked commercial authority (verbatim, owner-provided)

- Customer sequence: **MTSI → Torch → Celestar → ShorePoint → HyerTek**
- Offer: **PYRNOVA LIVE INTELLIGENCE** — **$15,000**, **60 days**, one Customer Lens, bounded
  intelligence surface, up to **10 Named Users**.
- Billing: 100% invoiced after signature · Net 15 default · activation normally after cleared payment.
- Continuation: **$18,000 quarterly prepaid**. Optional annual: **$72,000**.
- **No free pilot. No default discount.**
- The old **$2,500 Intelligence Sprint is obsolete and must not appear.**

## Rehearsed path (Customer #1 = MTSI), against tracked candidate state

| Step | Result | Truthful? |
|---|---|---|
| Customer identity | `customer_lens("mtsi")` → id `mtsi`, name "Modern Technology Solutions" | onboarded via `create_customer` (canonical entity `co_mtsi` only) |
| Customer Lens | resolves, tenant-scoped | yes |
| Persisted opportunity state | **2** real recompetes surface | from `usaspending_mtsi.json` via the real `detect_recompetes` engine (B4.2) — **not** fabricated |
| Decision intelligence | first opp: **PURSUE / MEDIUM**, evidence-backed | self-incumbent recompete recomputed from persisted evidence (B4.1) |
| Evidence Inspector | opens first evidence item | yes |
| AS-OF | `as_of=2026-08-01` (before first-seen 2026-09-01) → **0** opportunities | honest empty-before-known, not a bug |
| Brief generation | deterministic, rights `ALLOWED/PARTIAL`, **no "Intelligence Sprint" copy** | brief.py obsolete-Sprint footer corrected in this commit |
| Authorized external delivery capability | `DELIVERED` via in-memory `RecordingTransport` (records, **never sends externally**) | delivery-state path proven; real external send is a credential/infra dependency, not claimed |
| Commercial offer | locked package presented verbatim | matches locked authority exactly |

## Requirement conformance

1. Commercial copy/offer matches locked authority exactly — ✔ (`LOCKED_OFFER` in the capture).
2. No obsolete Intelligence Sprint language — ✔ (removed from `pyrnova/brief.py`; capture asserts the
   generated brief contains none; repo product code carries none).
3. No fake opportunity inserted to populate MTSI — ✔ (MTSI's 2 opportunities are its own real archived
   awards; the script fails if any is not MTSI-sourced).
4. If MTSI had no qualifying opportunity: ingestion/fanout proof + truthful empty state, never
   manufactured — covered by B4.14 (`test_b4_mtsi_fanout.py`); here MTSI genuinely qualifies, so the
   populated path is shown honestly.
5. Torch supplies additional populated RC proof where real persisted data exists — ✔ (6 opportunities
   from `usaspending_torch.json`).
6. Customer-facing capability is labelled **IMPLEMENTED/TESTED PRODUCT CAPABILITY**, distinct from
   **PRODUCTION/LIVE-OPS ACCEPTED** — ✔ (`capability_status_legend` in the capture). Nothing here is
   claimed as live-ops accepted.
7. The final soak is **not** claimed passed — ✔.
8. No prospect communications sent — ✔.

## Distinction preserved

Everything proven here is **IMPLEMENTED / TESTED PRODUCT CAPABILITY** on the exact candidate. It is
**not** PRODUCTION / LIVE-OPS ACCEPTED — that gate requires the final replacement soak, which has not
started. Real external customer-email delivery remains a credential/infra dependency (see B4.3).
