# B4.15 — Full regression (exact candidate)

**Result: 863 passed / 0 failed / 2 skipped (both adjudicated). Exit 0.**

- SHA at run: `3ce6c72` (tip after B4.10–14; brief.py customer-facing correction included, so this is a
  fresh full run against the exact candidate, not a stale count).
- Command: `PYTHONPATH=. <venv>/python -m pytest -rs`.
- No historical test-count target was chased; this is the meaningful exact-candidate suite.

## Skip adjudication (every skip explained)

| Test | Skip reason | Classification |
|---|---|---|
| `test_m15_real_ofac.py:23` | real OFAC archive absent (git-ignored); replay-from-archive only | **Legitimately deferred — environment/data availability.** The real OFAC archive is intentionally git-ignored (not committed). The offline replay path is covered; the live-archive path skips when the archive is not present. Not a defect; not a candidate regression. |
| `test_m16_selectivity.py:41` | real OFAC archive absent (git-ignored); replay-from-archive only | Same class as above. |

Zero unexplained failures. Zero unexplained skips.

## Required-domain coverage (all present and passing)

| Domain | Representative passing tests |
|---|---|
| Source-rights / security | `test_source_rights.py`, `test_source_expansion.py`, `test_sec_edgar.py`, `test_b4_security_posture.py` |
| Customer isolation / auth | `test_m22f_server_auth.py`, `test_m22f_access.py`, `test_b3_customer_product.py` (tenant isolation) |
| Authenticated integrated product flow | `test_b3_integrated_flow.py`, `test_b3_customer_product.py` |
| B2 decision chain | `test_decision_object.py`, `test_customer_intelligence.py`, `test_buyer_intelligence.py`, `test_competitive_intelligence.py`, `test_vehicle_access.py`, `test_fit_reasoning.py`, `test_pursuit.py`, `test_material_change_consequence.py`, `test_budget_lineage.py`, `test_lineage.py` |
| Customer delivery | `test_customer_delivery.py`, `test_b4_customer_delivery_wiring.py` |
| Alert lifecycle / transport | `test_operator_alerts.py`, `test_b4_alerts_wiring.py` |
| Backup / restore | `test_backup_restore.py`, `test_b4_backup_release.py` |
| Durable-state safety | `test_b4_durability.py` |
| Immutable release / deploy | `test_b4_release.py` (incl. `/healthz` probe), `test_b4_backup_release.py` |
| Soak immutability / provenance | `test_b4_soak_provenance.py`, `test_live_ops_acceptance.py` |
| Browser / API smoke | `test_m22f_server_auth.py`, `test_b3_customer_product.py` (route enforcement), `test_b3_integrated_flow.py`, `test_ops.py` |

## Correction-after-evidence discipline

The only executable correction in this bundle after evidence gathering was the `brief.py` obsolete-Sprint
fix (B4.12). Affected evidence was re-run at the corrected SHA: the rehearsal capture, the MTSI/Torch
product-surface tests, and this full regression all executed against `3ce6c72` (post-fix). No evidence in
this package predates a later code change.
