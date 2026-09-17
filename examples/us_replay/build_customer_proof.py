"""US customer-product proof builder (INTERNAL UNITED STATES EVALUATION lens).

The US has no national replay *directory*: its accepted historical material lives in the adjudicated US
replay corpora (``examples/replay/corpus_*.json``, PYRNOVA-US-HISTORICAL-VALIDATION). This module projects
a SELECTED subset of those accepted cases into ordinary records of the SHARED ``opportunities`` stream
through the same national → tenant bridge every other country uses
(:mod:`pyrnova.domains.fanout`) — no US fork, no second projection implementation, no copied fixture data.

Honesty rules enforced here (read this before adding a case):

* **No duplicated fixtures.** Evidence is read live from the accepted corpus file named in
  ``_SELECTION[...]["source_file"]``. Nothing is transcribed; source_ref / URL / availability dates /
  agency / amounts are exactly what the adjudicated case records.
* **Source rights, fail closed.** Only records whose ``source_id`` is a declared US national source
  (usaspending / sam_opportunities / federal_register) may back a derived customer projection. A case's
  other records (grants_gov, appropriations, sec_edgar, agency pages, …) are NOT declared US national
  sources, so they are honestly WITHHELD and reported in ``withheld_evidence`` — never laundered in, and
  never a reason to widen the US domain's declared source list.
* **Assigned vs evidenced.** The accepted US corpora record evidence and adjudication, not the national
  route/access vocabulary. ``route`` and ``access_class`` below are therefore an explicit, reviewable
  READING of each case's own adjudicated ``expected_commercial_mechanism`` text and record kinds — stated
  per case in ``basis``. They are an evaluation-estate assignment, NOT a source fact. Anything the accepted
  case does not support stays at the non-committal value (``NO_ESTABLISHED_ACCESS`` / ``UNKNOWN``); an
  assignment never invents a favourable position, a value, or a date.
* **Real companies are not projected.** Entity-specific accepted cases (the ``m9-*`` Torch / MTSI fit
  cases) are deliberately EXCLUDED: their subject is a real company, and re-attributing their position to
  an internal evaluation lens would assert a relationship that does not exist.
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
CORPUS_DIR = HERE.parent / "replay"

# Internal evaluation lens — NOT a real customer, NO commercial relationship asserted.
EVAL_ID = "eval-us"
EVAL_NAME = "Evaluation Target (US)"
EVAL_REF = "co_eval_us"
ONBOARDED = "2018-01-01T00:00:00+00:00"
# After every selected case's latest accepted record became knowable, and before today.
PROOF_AS_OF = "2026-09-01"

# Declared US national sources. Anything else in an accepted case is withheld (fail closed).
_RIGHTS_APPROVED = ("usaspending", "sam_opportunities", "federal_register")


# Case selection. `route` / `access_class` / `industrial_position` / `important_miss_kind` are an explicit
# READING of the named accepted case (see `basis`), not source facts. `value_usd` is carried only where the
# accepted case records an amount; where the case's point is that value must remain unknown, it stays None.
_SELECTION = {
    "m8-fit-navy-radar-2024": {
        "source_file": "corpus_m8.json",
        "title": "US Navy radar component procurement — awarded, in performance",
        "lifecycle_stage": "AWARD",
        "route": "FULL_AND_OPEN",
        "access_class": "NO_ESTABLISHED_ACCESS",
        "industrial_position": "UNKNOWN",
        "important_miss_kind": None,
        "value_usd": 54_000_000.0,
        "expected_action_at": None,
        "basis": "adjudicated as 'direct radar-component procurement'; a SAM competitive solicitation "
                 "followed by a USAspending award. No access evidence for any subject => "
                 "NO_ESTABLISHED_ACCESS.",
    },
    "m8-fit-radar-recompete-defend-2024": {
        "source_file": "corpus_m8.json",
        "title": "US Navy radar sustainment recompete — incumbent-held, defend window",
        "lifecycle_stage": "RECOMPETE",
        "route": "FULL_AND_OPEN",
        "access_class": "INCUMBENT",
        "industrial_position": "UNKNOWN",
        # The one US Important-Miss kind the accepted case explicitly supports.
        "important_miss_kind": "RECOMPETE_WINDOW",
        "value_usd": 34_000_000.0,
        "expected_action_at": None,
        "basis": "adjudicated as 'recompete of an incumbent-held sustainment contract' — the case states "
                 "incumbency and a recompete window; both are read directly from that adjudication.",
    },
    "m8-fit-directed-energy-open-2024": {
        "source_file": "corpus_m8.json",
        "title": "US Air Force directed-energy procurement — open competition",
        "lifecycle_stage": "SOLICITATION",
        "route": "FULL_AND_OPEN",
        "access_class": "NO_ESTABLISHED_ACCESS",
        "industrial_position": "UNKNOWN",
        "important_miss_kind": None,
        "value_usd": 25_000_000.0,
        "expected_action_at": None,
        "basis": "adjudicated as 'direct directed-energy procurement' backed by an open SAM solicitation.",
    },
    "m8-fit-directed-energy-closed-2023": {
        "source_file": "corpus_m8.json",
        "title": "US Air Force directed-energy procurement — awarded, window passed",
        "lifecycle_stage": "PERFORMANCE",
        "route": "FULL_AND_OPEN",
        "access_class": "NO_ESTABLISHED_ACCESS",
        "industrial_position": "UNKNOWN",
        "important_miss_kind": None,
        "value_usd": 19_000_000.0,
        "expected_action_at": None,
        "basis": "adjudicated as 'direct procurement already awarded; window passed' — a closed route, "
                 "retained so the estate is not uniformly attractive. One agency-page record is withheld.",
    },
    "m7-unknown-value-directed-energy-2024": {
        "source_file": "corpus_m7.json",
        "title": "US Air Force directed-energy award — contract value not evidenced",
        "lifecycle_stage": "AWARD",
        "route": "FULL_AND_OPEN",
        "access_class": "NO_ESTABLISHED_ACCESS",
        "industrial_position": "UNKNOWN",
        "important_miss_kind": None,
        # The point of this accepted case: value must remain UNKNOWN. No value block is emitted.
        "value_usd": None,
        "expected_action_at": None,
        "basis": "adjudicated as 'direct procurement whose value must remain UNKNOWN' — no amount is "
                 "asserted, proving the product shows unknown value rather than inventing one.",
    },
    "m6-defer-fragment-ambiguous-gsa-2024": {
        "source_file": "corpus_m6.json",
        "title": "US GSA cloud requirement — ambiguous linkage, monitoring only",
        "lifecycle_stage": "PRE_SOLICITATION",
        "route": "GWAC_SCHEDULE",
        "access_class": "NO_ESTABLISHED_ACCESS",
        "industrial_position": "UNKNOWN",
        "important_miss_kind": None,
        "value_usd": None,
        "expected_action_at": None,
        "basis": "adjudicated WATCH/DEFER: 'same-agency records sharing a specific number fragment but no "
                 "authoritative program identifier'. Deliberately evidence-thin and uncertain; the GSA "
                 "acquisition-forecast record is withheld (not a declared US national source).",
    },
}


def _load_case(case_id: str, source_file: str) -> dict:
    corpus = json.loads((CORPUS_DIR / source_file).read_text(encoding="utf-8"))
    for case in corpus["cases"]:
        if case["case_id"] == case_id:
            return case
    raise KeyError(f"accepted US case {case_id!r} not found in {source_file}")


def seed_customer(store) -> dict:
    """Provision the internal US evaluation lens into persisted customer state (idempotent)."""
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
                              case_ids: Optional[Iterable[str]] = None) -> dict:
    """Project the selected accepted US cases into shared opportunity records for an evaluation lens.

    Returns ``{"records": [...], "blocked": [...], "withheld_evidence": [...]}``. ``withheld_evidence``
    names every accepted record that exists in the source case but is NOT backed by a declared US national
    source — withheld, never laundered, and never silently dropped.
    """
    us = get_domain("US")
    wanted = set(case_ids) if case_ids is not None else None
    records: list[dict] = []
    blocked: list[dict] = []
    withheld: list[dict] = []
    for case_id, sel in _SELECTION.items():
        if wanted is not None and case_id not in wanted:
            continue
        case = _load_case(case_id, sel["source_file"])
        evidence: list[NationalEvidence] = []
        for rec in case.get("records", []):
            if rec.get("source_id") not in _RIGHTS_APPROVED:
                withheld.append({"case_id": case_id, "source_id": rec.get("source_id"),
                                 "source_ref": rec.get("source_ref"),
                                 "reason": "not a declared US national source (UNKNOWN => DENY)"})
                continue
            evidence.append(NationalEvidence(
                # Deterministic, source-linked evidence identity — the accepted record's own reference.
                f"us-ev:{rec['source_id']}:{rec['source_ref']}",
                rec["source_id"], rec["available_at"],
                sel["lifecycle_stage"], sel["route"],
                payload={"source_ref": rec["source_ref"], "source_url": rec.get("url"),
                         "archive_uri": f"examples/replay/{sel['source_file']}#{case_id}"}))
        if not evidence:
            blocked.append({"case_id": case_id,
                            "reason": "no record in this accepted case is backed by a declared US "
                                      "national source (fail closed)"})
            continue
        anchor = evidence[0]
        mc = derive_material_change_fixture(
            us, anchor, as_of=PROOF_AS_OF, mc_id=f"US:{case_id}",
            important_miss_kind=sel["important_miss_kind"])
        acc = assess_access(us, access_class=sel["access_class"],
                            industrial_position=sel["industrial_position"])
        opp = NationalOpportunity(mc, acc, customer_id)
        value = national_value_block(sel["value_usd"], "USD") if sel["value_usd"] else None
        try:
            rec = build_national_opportunity_record(
                us, opp, evidence=evidence, subject_ref=subject_ref, subject_name=subject_name,
                title=sel["title"], as_of=PROOF_AS_OF, value=value,
                expected_action_at=sel["expected_action_at"],
                buyer=case.get("expected_buyer_program_owner"))
            records.append(rec)
        except PermissionError as exc:
            blocked.append({"case_id": case_id, "reason": str(exc)})
    return {"records": records, "blocked": blocked, "withheld_evidence": withheld}


def seed(store) -> dict:
    """Seed the evaluation lens and append the materialized US opportunities to the shared stream."""
    cust = seed_customer(store)
    built = build_opportunity_records()
    for rec in built["records"]:
        store.append("opportunities", rec)
    return {"customer": cust, "materialized": len(built["records"]),
            "blocked": built["blocked"], "withheld_evidence": built["withheld_evidence"],
            "as_of": PROOF_AS_OF}


def main() -> int:
    from pyrnova.config import load_config
    from pyrnova.state import StateStore

    store = StateStore(load_config().state_dir)
    print(json.dumps(seed(store), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
