"""UK customer-product proof builder (INTERNAL UNITED KINGDOM EVALUATION lens).

Takes the accepted UK replay corpus (``examples/uk_replay/corpus.json`` — lawful, clearly-fixture evidence
drawn from PYRNOVA-UK-HISTORICAL-VALIDATION-001) and projects it, through the shared national → tenant
bridge (:mod:`pyrnova.domains.fanout`), into ordinary records of the SHARED ``opportunities`` global stream
for one INTERNAL evaluation lens. This is NOT a real customer and asserts NO commercial relationship: the
lens exists only to exercise the real customer product end to end using accepted UK evidence.

Source honesty (SOURCE-RIGHTS): a case is materialized ONLY if its backing UK source is rights-approved for
a derived customer projection (uk_contracts_finder / uk_gov_uk: FIXTURE_ONLY at the domain layer,
INGEST_DISABLED at the registry layer — lawful replay-derived use). A case backed by a source without that
approval (e.g. the SSRO-backed QDC case, DECLARED => DENY) is honestly BLOCKED and never silently appears —
QDC evidence cannot be laundered in through a denied source. Historical accessibility is NOT production
authorization.

No UK numeric DLT threshold: DLT benchmarks ride as observed attributes only; zero-DLT cases (post-award,
industrial restructuring, framework/access) still project as valuable consequential-change intelligence.
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
EVAL_ID = "eval-uk"
EVAL_NAME = "Evaluation Target (UK)"
EVAL_REF = "co_eval_uk"
# Onboarded before the earliest corpus case so the eval lens was "already monitoring" (deterministic).
ONBOARDED = "2019-01-01T00:00:00+00:00"
# The point-in-time cutoff for the proof: after every corpus case became knowable.
PROOF_AS_OF = "2024-01-01"

# National contract values (GBP) for the strong cases — carried in the national value block, never coerced
# into the US value_usd field. Deterministic, part of the fixture.
_CASE_VALUE_GBP = {
    "uk-nmh-precursor": 1_000_000_000.0,
    "uk-fss-industrial": 1_600_000_000.0,
    "uk-tempest-gcap": 2_000_000_000.0,
}


def _load_corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def seed_customer(store) -> dict:
    """Provision the internal UK evaluation lens into persisted customer state (idempotent)."""
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
    """Project the accepted UK corpus into shared opportunity records for the evaluation lens.

    Returns ``{"records": [...], "blocked": [...]}``: ``records`` are the materialized UK opportunities
    (rights-approved source), ``blocked`` are the cases honestly withheld because their source is not
    rights-approved for a derived customer projection (fail closed).
    """
    uk = get_domain("GB")
    corpus = _load_corpus()
    records: list[dict] = []
    blocked: list[dict] = []
    for case in corpus["cases"]:
        ev = NationalEvidence(
            case["evidence_id"], case["source_id"], case["available_at"],
            case["lifecycle_stage"], case["route"],
            payload={"source_ref": f"uk:{case['source_id']}:{case['case_id']}",
                     "archive_uri": f"examples/uk_replay/corpus.json#{case['case_id']}"})
        mc = derive_material_change_fixture(
            uk, ev, as_of=PROOF_AS_OF, mc_id=f"GB:{case['case_id']}",
            consequential_change_kind=case.get("consequential_change_kind"),
            sscr_qdc=case.get("sscr_qdc", "UNKNOWN"))
        acc = assess_access(uk, access_class=case["access_class"],
                            industrial_position=case["industrial_position"])
        opp = NationalOpportunity(mc, acc, EVAL_ID)
        value = national_value_block(_CASE_VALUE_GBP.get(case["case_id"]), "GBP") \
            if case["case_id"] in _CASE_VALUE_GBP else None
        try:
            rec = build_national_opportunity_record(
                uk, opp, evidence=[ev], subject_ref=EVAL_REF, subject_name=EVAL_NAME,
                title=f"UK {case['route']} — {case['case_id']}", as_of=PROOF_AS_OF,
                value=value, expected_action_at=case.get("anchors", {}).get("benchmark_b"))
            records.append(rec)
        except PermissionError as exc:
            blocked.append({"case_id": case["case_id"], "source_id": case["source_id"],
                            "reason": str(exc)})
    return {"records": records, "blocked": blocked}


def seed(store) -> dict:
    """Seed the evaluation lens and append the materialized UK opportunities to the shared stream."""
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
