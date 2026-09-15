"""B4.2 — MTSI ingestion / fan-out adjudication.

Bundle 3 found the MTSI lens honestly empty. The exact cause: the demo materialized recompete
opportunities for Torch only — MTSI's own archived evidence was never run through the fan-out. This is a
real operational gap, NOT a legitimate empty: the same accepted ``detect_recompetes`` engine over the real
archived ``usaspending_mtsi.json`` with the SAME accepted parameters used for Torch surfaces genuine MTSI
recompete opportunities. These tests pin that adjudication and prove the fixture stays deterministic and
tenant-isolated (no Torch records copied into MTSI).
"""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

from pyrnova.engines.recompete import detect_recompetes
from pyrnova.normalize import normalize_award

RE = Path("examples/real_evidence")
DEMO = Path("examples/material_changes_demo")


def _seed_module():
    spec = importlib.util.spec_from_file_location("demo_build_seed", DEMO / "build_seed.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mtsi_evidence_legitimately_produces_recompetes():
    # The accepted engine + accepted parameters over the real MTSI archive is NOT empty.
    b = _seed_module()
    awards = [normalize_award(r) for r in json.loads((RE / "usaspending_mtsi.json").read_bytes())["results"]]
    opps = detect_recompetes(awards, as_of=b.OPP_AS_OF, window_days=b.OPP_WINDOW_DAYS,
                             min_amount=b.OPP_MIN_AMOUNT)
    assert len(opps) >= 1  # the empty lens was a fan-out gap, not a legitimate empty
    for o in opps:
        assert "MODERN TECHNOLOGY SOLUTIONS" in (o.incumbent or "").upper()


def test_build_seed_is_byte_reproducible_and_tenant_isolated(tmp_path):
    b = _seed_module()
    torch = b._torch_recompete_opportunities()
    mtsi = b._mtsi_recompete_opportunities()
    assert torch and mtsi
    # Deterministic: rebuilding yields identical records.
    assert b._mtsi_recompete_opportunities() == mtsi
    # Tenant isolation + no cross-tenant copying.
    assert {r["customer_id"] for r in torch} == {"torch"}
    assert {r["customer_id"] for r in mtsi} == {"mtsi"}
    torch_awards = {r["meta"]["award_id"] for r in torch}
    mtsi_awards = {r["meta"]["award_id"] for r in mtsi}
    assert torch_awards.isdisjoint(mtsi_awards)
    # MTSI evidence points at the MTSI archive, never Torch's.
    for r in mtsi:
        for e in r["evidence"]:
            assert "usaspending_mtsi.json" in e["archive_uri"]
    # Evidence observation time is pinned (not wall-clock) so the AS-OF cutoff is deterministic.
    assert all(e["first_seen_at"] == f"{b.OPP_AS_OF.isoformat()}T00:00:00"
               for r in (torch + mtsi) for e in r["evidence"])
