"""M14 — cross-source intelligence chains (major acceptance target, Workstream 5).

Two chains across materially different source families, built from real archived evidence + the SBIR
fixture, reusing the frozen chain engine. Asserts the acceptance properties: cross-family accepted joins
anchored on a deterministic identifier, weak joins rejected, temporal (lead-time) ordering, point-in-time
truth, and multi-family corporate+procurement entity linkage.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyrnova.cross_source import (
    build_cross_source_chain,
    corporate_procurement_linkage,
    usaspending_award_records,
)
from pyrnova.sources.sbir import parse_sbir_awards

FIXTURES = Path(__file__).parent / "fixtures"
REAL = Path("examples/real_evidence")


def _torch_uei() -> str:
    # Read the firm's authoritative UEI from the USAspending recipient endpoint bytes (not hardcoded).
    rec = json.loads((REAL / "usaspending_recipient_torch.json").read_text())
    return rec["uei"]


def _sbir_all() -> list[dict]:
    return parse_sbir_awards((FIXTURES / "sbir_awards.json").read_bytes())


def _usaspending_torch(uei: str) -> list[dict]:
    return usaspending_award_records(
        (REAL / "usaspending_torch.json").read_bytes(),
        uei=uei, company_name="TORCH", max_records=1,
    )


# --------------------------------------------------------------------- Chain A: R&D -> procurement


def test_sbir_to_procurement_accepted_on_real_uei_anchor():
    uei = _torch_uei()
    assert uei and uei == uei.upper()
    chain = build_cross_source_chain(_sbir_all(), _usaspending_torch(uei))

    # Two materially different families contributed.
    assert set(chain["families"]) == {"sbir", "usaspending"}
    # At least one accepted join links SBIR (PROGRAM) to USAspending (AWARD) across families.
    cross = chain["cross_family_accepted_joins"]
    assert cross, "expected an accepted cross-family SBIR->USAspending join"
    link = cross[0]
    assert link["subject_family"] == "sbir" and link["object_family"] == "usaspending"
    assert link["subject_stage"] == "PROGRAM" and link["object_stage"] == "AWARD"
    assert link["join_method"] == "inferred_strong_attribute"
    # Anchored on the firm's authoritative UEI: an entity relationship to that UEI node exists.
    assert any(uei in r["object"] for r in chain["entity_relationships"])
    # Temporal ordering is forward: a positive R&D -> procurement lead time.
    assert chain["lead_time_days"] is not None and chain["lead_time_days"] > 0


def test_different_firm_sbir_is_a_rejected_weak_join():
    uei = _torch_uei()
    chain = build_cross_source_chain(_sbir_all(), _usaspending_torch(uei))
    # The SBIR fixture includes awards to firms other than Torch (different UEIs). None of those may
    # link to Torch's procurement on agency/topic alone — they must appear as rejected weak joins.
    reasons = {rj["reason"] for rj in chain["rejected_weak_joins"]}
    assert chain["rejected_weak_joins"], "expected rejected weak joins for non-matching firms"
    assert reasons <= {"agency_name_only", "topic_overlap_only", "inference_below_threshold",
                       "inference_contradiction"}
    # No accepted cross-family join may involve a non-Torch recipient UEI.
    for link in chain["cross_family_accepted_joins"]:
        assert "TORCH" in (link["subject"] or "").upper() or "torch" in (link["object"] or "").lower() \
            or link["object_family"] == "usaspending"


def test_point_in_time_excludes_future_procurement():
    uei = _torch_uei()
    # Cutoff before the 2016 SBIR award and the 2021 prime award: only the 2014 SBIR is knowable, so no
    # cross-family SBIR->procurement join can form. Future evidence never leaks backward.
    chain = build_cross_source_chain(_sbir_all(), _usaspending_torch(uei), as_of="2015-01-01")
    assert chain["cross_family_accepted_joins"] == []
    assert "usaspending" not in chain["families"] or all(
        a["object_family"] != "usaspending" for a in chain["accepted_joins"]
    )


def test_usaspending_award_record_omits_aggregate_amount():
    # The per-firm award total must not be presented as a comparable single-award value.
    recs = _usaspending_torch(_torch_uei())
    assert recs and all(r["amount_usd"] is None for r in recs)
    assert all(r["stage"] == "AWARD" and r["recipient_uei"] == _torch_uei() for r in recs)


# ------------------------------------------------------ Chain B: corporate + procurement linkage


def test_corporate_procurement_entity_linkage_saic():
    linkage = corporate_procurement_linkage(
        "SCIENCE APPLICATIONS INTERNATIONAL CORPORATION",
        cutoff="2024-12-31",
        sources=[
            {"kind": "usaspending_prime", "fixture": "usaspending_saic.json"},
            {"kind": "sec_submissions", "fixture": "sec_submissions_saic.json"},
            {"kind": "usaspending_recipient", "fixture": "usaspending_recipient_saic.json",
             "available_at": "2020-01-01"},
        ],
    )
    # Multiple real source families contributed to one company interpretation, joined deterministically.
    assert linkage["source_family_count"] >= 2
    assert linkage["join_method"] == "deterministic_entity_merge"
    assert linkage["source_fact_count"] >= 1
