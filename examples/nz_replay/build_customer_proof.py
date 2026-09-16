"""NZ customer-product proof builder (INTERNAL NEW ZEALAND EVALUATION lens).

Takes the accepted New Zealand replay corpus (``examples/nz_replay/corpus.json`` — lawful, clearly-fixture
evidence for PYRNOVA-NZ-SPEC-001; no live ingestion, no fabricated source activation, and NO GETS) and
projects it, through the shared national → tenant bridge (:mod:`pyrnova.domains.fanout`), into ordinary
records of the SHARED ``opportunities`` global stream for one INTERNAL evaluation lens. This is NOT a real
customer and asserts NO commercial relationship: the lens exists only to exercise the real customer product
end to end using accepted New Zealand evidence.

Source honesty (SOURCE-RIGHTS): a case is materialized ONLY if its backing NZ source is rights-approved for
a derived customer projection (nz_mod: FIXTURE_ONLY at the domain layer, INGEST_DISABLED at the registry
layer — lawful replay-derived use). A case backed by a source without that approval (e.g. the non-Defence
nz_treasury civil case, DECLARED => DENY) is honestly BLOCKED and never silently appears in the product —
which preserves the accepted limitation that NZ civil-sector coverage is not equivalent to Defence. GETS is
PROHIBITED and never a source.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyrnova.customers import CustomerProfile, upsert_customer
from pyrnova.domains import get_domain
from pyrnova.domains.fanout import build_national_opportunity_record, national_value_block
from pyrnova.domains.pipeline import (
    NationalEvidence, NationalOpportunity, assess_access, derive_material_change_fixture,
)

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus.json"

# Internal evaluation lens — NOT a real customer, NO commercial relationship asserted.
EVAL_ID = "eval-nz"
EVAL_NAME = "Evaluation Target (NZ)"
EVAL_REF = "co_eval_nz"
# Onboarded before the earliest corpus case so the eval lens was "already monitoring" (deterministic).
ONBOARDED = "2019-01-01T00:00:00+00:00"
# The point-in-time cutoff for the proof: after every corpus case became knowable.
PROOF_AS_OF = "2024-01-01"

# National contract values (NZD) for the two strong cases — carried in the national value block, never
# coerced into the US value_usd field. Deterministic, part of the fixture.
_CASE_VALUE_NZD = {
    "nz-mod-early-warning": 220_000_000.0,
    "nz-mod-thin-prime-closed": 95_000_000.0,
}


def _load_corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def seed_customer(store) -> dict:
    """Provision the internal NZ evaluation lens into persisted customer state (idempotent)."""
    from pyrnova.customers import get_customer
    created = 0
    if get_customer(store, EVAL_ID) is None:
        upsert_customer(store, CustomerProfile(
            customer_id=EVAL_ID, name=EVAL_NAME, entity_refs=[EVAL_REF],
            provenance="internal_evaluation", effective_from=ONBOARDED,
            created_at=ONBOARDED, updated_at=ONBOARDED))
        created = 1
    return {"customer_id": EVAL_ID, "created": created}


def build_opportunity_records() -> dict:
    """Project the accepted NZ corpus into shared opportunity records for the evaluation lens.

    Returns ``{"records": [...], "blocked": [...]}``: ``records`` are the materialized NZ opportunities
    (rights-approved source), ``blocked`` are the cases honestly withheld because their source is not
    rights-approved for a derived customer projection (fail closed).
    """
    nz = get_domain("NZ")
    corpus = _load_corpus()
    records: list[dict] = []
    blocked: list[dict] = []
    for case in corpus["cases"]:
        ev = NationalEvidence(
            case["evidence_id"], case["source_id"], case["available_at"],
            case["lifecycle_stage"], case["route"],
            payload={"source_ref": f"nz:{case['source_id']}:{case['case_id']}",
                     "archive_uri": f"examples/nz_replay/corpus.json#{case['case_id']}"})
        mc = derive_material_change_fixture(
            nz, ev, as_of=PROOF_AS_OF, important_miss_kind=case.get("important_miss_kind"),
            mc_id=f"NZ:{case['case_id']}")
        acc = assess_access(nz, access_class=case["access_class"],
                            industrial_position=case["industrial_position"])
        opp = NationalOpportunity(mc, acc, EVAL_ID)
        value = national_value_block(_CASE_VALUE_NZD.get(case["case_id"]), "NZD") \
            if case["case_id"] in _CASE_VALUE_NZD else None
        try:
            rec = build_national_opportunity_record(
                nz, opp, evidence=[ev], subject_ref=EVAL_REF, subject_name=EVAL_NAME,
                title=f"NZ {case['route']} acquisition — {case['case_id']}", as_of=PROOF_AS_OF,
                value=value, expected_action_at=case.get("anchors", {}).get("benchmark_b"))
            records.append(rec)
        except PermissionError as exc:
            # Source not rights-approved for a derived customer projection — honestly blocked.
            blocked.append({"case_id": case["case_id"], "source_id": case["source_id"],
                            "reason": str(exc)})
    return {"records": records, "blocked": blocked}


def seed(store) -> dict:
    """Seed the evaluation lens and append the materialized NZ opportunities to the shared stream."""
    cust = seed_customer(store)
    built = build_opportunity_records()
    for rec in built["records"]:
        store.append("opportunities", rec)
    return {"customer": cust, "materialized": len(built["records"]),
            "blocked": built["blocked"], "as_of": PROOF_AS_OF}


def main() -> int:
    from pyrnova.config import load_config
    from pyrnova.state import StateStore

    store = StateStore(load_config().state_dir)
    print(json.dumps(seed(store), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
