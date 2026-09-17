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
from typing import Iterable, Optional

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


def build_opportunity_records(*, customer_id: str = EVAL_ID, subject_ref: str = EVAL_REF,
                              subject_name: str = EVAL_NAME,
                              case_ids: Optional[Iterable[str]] = None,
                              titles: Optional[dict] = None) -> dict:
    """Project the accepted NZ corpus into shared opportunity records for the evaluation lens.

    Returns ``{"records": [...], "blocked": [...]}``: ``records`` are the materialized NZ opportunities
    (rights-approved source), ``blocked`` are the cases honestly withheld because their source is not
    rights-approved for a derived customer projection (fail closed).

    The lens identity is a PARAMETER so the same accepted projection can serve either this national
    evaluation lens (the defaults) or the shared multinational evaluation estate
    (``examples/evaluation_estate``) — one projection path, no second national implementation.
    ``case_ids`` optionally restricts the projection to a selected subset; the rights gate and every
    national semantic are unchanged either way.
    ``titles`` optionally supplies a human-readable programme title per case (the estate draws these
    from the corpus's own notes); without it the existing route/case title is used unchanged.
    """
    nz = get_domain("NZ")
    corpus = _load_corpus()
    wanted = set(case_ids) if case_ids is not None else None
    records: list[dict] = []
    blocked: list[dict] = []
    for case in corpus["cases"]:
        if wanted is not None and case["case_id"] not in wanted:
            continue
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
        opp = NationalOpportunity(mc, acc, customer_id)
        value = national_value_block(_CASE_VALUE_NZD.get(case["case_id"]), "NZD") \
            if case["case_id"] in _CASE_VALUE_NZD else None
        try:
            rec = build_national_opportunity_record(
                nz, opp, evidence=[ev], subject_ref=subject_ref, subject_name=subject_name,
                title=(titles or {}).get(case["case_id"])
                or f"NZ {case['route']} acquisition — {case['case_id']}", as_of=PROOF_AS_OF,
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
