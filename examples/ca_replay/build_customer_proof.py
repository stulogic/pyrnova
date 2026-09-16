"""Canadian customer-product proof builder (INTERNAL CANADA EVALUATION lens).

Takes the accepted Canadian replay corpus (``examples/ca_replay/corpus.json`` — lawful, clearly-fixture
evidence drawn from PYRNOVA-CA-HISTORICAL-VALIDATION-001/002) and projects it, through the shared national
→ tenant bridge (:mod:`pyrnova.domains.fanout`), into ordinary records of the SHARED ``opportunities``
global stream for one INTERNAL evaluation lens. This is NOT a real customer and asserts NO commercial
relationship: the lens exists only to exercise the real customer product end to end using accepted Canadian
evidence.

Source honesty (SOURCE-RIGHTS): a case is materialized ONLY if its backing Canadian source is rights-approved
for a derived customer projection (ca_canadabuys_dataset: FIXTURE_ONLY at the domain layer, INGEST_DISABLED at
the registry layer — lawful replay-derived use). A case backed by a source without that approval (the
DCB-backed forecast, DECLARED => DENY) is honestly BLOCKED and never silently appears. Historical / public
accessibility is NOT production authorization.

NO Canadian numeric DLT threshold: timing rides as a QUALIFIED class (EXACT/BOUNDED/CONTAMINATED/N_A/UNKNOWN)
only; a BOUNDED / CONTAMINATED interval is never promoted to exact. Bilingual evidence keeps original-language
authority (EN and FR are both original; a translation is PYRNOVA DERIVED). ITB/VP and Canadian Industrial
Position are SEPARATE evidenced fields, never derived from value / ownership / access.
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
EVAL_ID = "eval-ca"
EVAL_NAME = "Evaluation Target (Canada)"
EVAL_REF = "co_eval_ca"
# Onboarded before the earliest corpus case (CC-177, 2006) so the eval lens was "already monitoring".
ONBOARDED = "2005-01-01T00:00:00+00:00"
# The point-in-time cutoff for the proof: after every corpus case became knowable (CPSP is 2024-09-15).
PROOF_AS_OF = "2025-06-01"


def _load_corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def seed_customer(store) -> dict:
    """Provision the internal Canadian evaluation lens into persisted customer state (idempotent)."""
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
    """Project the accepted Canadian corpus into shared opportunity records for the evaluation lens.

    Returns ``{"records": [...], "blocked": [...]}``: ``records`` are the materialized Canadian opportunities
    (rights-approved source), ``blocked`` are the cases honestly withheld because their source is not
    rights-approved for a derived customer projection (fail closed).
    """
    ca = get_domain("CA")
    corpus = _load_corpus()
    records: list[dict] = []
    blocked: list[dict] = []
    for case in corpus["cases"]:
        payload = {"source_ref": f"ca:{case['source_id']}:{case['case_id']}",
                   "archive_uri": f"examples/ca_replay/corpus.json#{case['case_id']}"}
        if case.get("provenance_conflict"):
            payload["provenance_conflict"] = case["provenance_conflict"]
        ev = NationalEvidence(
            case["evidence_id"], case["source_id"], case["available_at"],
            case["lifecycle_stage"], case["route"],
            language=case.get("language", "en"),
            translation=case.get("translation"),
            entity_key=case.get("entity_key"),
            payload=payload)
        mc = derive_material_change_fixture(
            ca, ev, as_of=PROOF_AS_OF, mc_id=f"CA:{case['case_id']}",
            consequential_change_kind=case.get("consequential_change_kind"),
            mechanism=case.get("mechanism"),
            timing_class=case.get("timing_class", "UNKNOWN"),
            itb_vp=case.get("itb_vp", "UNKNOWN"))
        acc = assess_access(ca, access_class=case["access_class"],
                            industrial_position=case["industrial_position"])
        opp = NationalOpportunity(mc, acc, EVAL_ID)
        value = national_value_block(case.get("value_cad"), "CAD") if case.get("value_cad") else None
        try:
            rec = build_national_opportunity_record(
                ca, opp, evidence=[ev], subject_ref=EVAL_REF, subject_name=EVAL_NAME,
                title=f"CA {case['mechanism']} — {case['case_id']}", as_of=PROOF_AS_OF,
                value=value, expected_action_at=case.get("expected_action_at"))
            records.append(rec)
        except PermissionError as exc:
            blocked.append({"case_id": case["case_id"], "source_id": case["source_id"],
                            "reason": str(exc)})
    return {"records": records, "blocked": blocked}


def seed(store) -> dict:
    """Seed the evaluation lens and append the materialized Canadian opportunities to the shared stream."""
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
