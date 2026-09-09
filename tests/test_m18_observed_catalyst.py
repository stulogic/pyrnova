"""M18 — the OBSERVED adverse catalyst and the INDEPENDENT relationships are REAL (honesty gate).

Analogue of tests/test_m17_real_propagation.py for M18. It proves the two flagship export-control chains
are not asserted out of thin air:

* the OBSERVED catalyst used in the corpus is a real, archived Federal Register BIS rule (reproducible
  from examples/real_evidence/federal_register_bis_export_controls.json via pyrnova.adverse_events), and
* the Parsons->Torch and Intuitive->Torch propagation edges are the SAME program-anchored edges
  pyrnova.relationships.ground_subaward_edges derives from the archived sub-award bytes, with the prime's
  incumbency established from the authoritative sub-award PRIME fields (0 new calls), and
* the same real rule produces NO threat where there is no evidenced exposure (Workstream D/P), and
* observed-vs-modeled catalyst authority is durable and distinct.

No network access; everything replays from committed evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyrnova.adverse_events import (
    catalyst_class,
    parse_federal_register_adverse,
    regulation_target_ref,
    to_regulatory_catalyst,
)
from pyrnova.grounding_subawards import parse_subawards
from pyrnova.relationships import (
    exposed_prime_awards_from_subawards,
    ground_subaward_edges,
    independence_metrics,
)
from pyrnova.threat import assess_threats, declared_exposures

_FR_EVIDENCE = Path("examples/real_evidence/federal_register_bis_export_controls.json")
_SUBAWARDS = Path("examples/real_evidence/usaspending_subawards_torch.json")
_CORPUS = json.loads(Path("examples/replay/corpus_m18.json").read_text())

_PARSONS = "PARSONS GOVERNMENT SERVICES INC."
_INTUITIVE = "INTUITIVE RESEARCH AND TECHNOLOGY CORPORATION"


def _case(case_id):
    return next(c for c in _CORPUS["threat_cases"] if c["case_id"] == case_id)


def _parsed():
    return parse_subawards(_SUBAWARDS.read_bytes(), company_name="TORCH TECHNOLOGIES INC")


def test_observed_catalyst_is_a_real_archived_federal_register_rule():
    """The corpus OBSERVED catalyst reproduces a real archived FR BIS rule via adverse_events."""
    parsed = parse_federal_register_adverse(_FR_EVIDENCE.read_bytes())
    event = next(e for e in parsed["events"] if e["event_id"] == "2026-17231")
    assert event["catalyst_class"] == "OBSERVED"
    assert event["agency"] == "Industry and Security Bureau"
    assert event["publication_date"] == "2026-08-24"
    assert regulation_target_ref(event) == "EAR:0694-AK49"

    cat = to_regulatory_catalyst(event)
    corpus_cat = _case("m18-obs-export-control-parsons-torch")["catalyst_records"][0]
    assert cat["catalyst_class"] == corpus_cat["catalyst_class"] == "OBSERVED"
    assert cat["target_ref"] == corpus_cat["target_ref"]
    assert cat["available_at"] == corpus_cat["available_at"]
    assert cat["source_ref"] == corpus_cat["source_ref"] == "fr:doc:2026-17231"


def test_independent_edges_match_grounded_real_edges():
    """Parsons->Torch and Intuitive->Torch corpus edges match program-anchored grounded edges, and both
    are INDEPENDENT of SAIC."""
    parsed = _parsed()
    anchors = (exposed_prime_awards_from_subawards(parsed, _PARSONS)
               | exposed_prime_awards_from_subawards(parsed, _INTUITIVE))
    assert "HQ085821C0015" in anchors           # Parsons MDA prime award, from the sub-award PRIME fields
    edges = ground_subaward_edges(
        parsed, sub_ref="co_torch", sub_name="Torch Technologies Inc",
        prime_refs={_PARSONS: "co_parsons", _INTUITIVE: "co_intuitive"},
        exposed_prime_award_ids=anchors)
    real_sub_ids = {str(s["sub_award_id"]) for s in parsed["subawards"]}
    for cid, ref in (("m18-obs-export-control-parsons-torch", "co_parsons"),
                     ("m18-obs-export-control-intuitive-torch", "co_intuitive")):
        grounded = next(e for e in edges if e["from_ref"] == ref)
        assert grounded["link_class"] == "CONFIRMED"
        assert grounded["join_method"] == "deterministic_native_id"
        assert ref != "co_saic"
        edge = _case(cid)["relationships"][0]
        assert edge["to_ref"] == grounded["to_ref"] == "co_torch"
        assert edge["link_class"] == grounded["link_class"]
        for ev in edge["evidence_ids"]:
            assert ev.split(":")[-1] in real_sub_ids


def test_two_independent_real_company_pairs():
    """The two real observed chains use two DISTINCT company pairs, neither of which is SAIC<->Torch."""
    pairs = set()
    for cid in ("m18-obs-export-control-parsons-torch", "m18-obs-export-control-intuitive-torch"):
        e = _case(cid)["relationships"][0]
        pairs.add((e["from_ref"], e["to_ref"]))
    assert len(pairs) == 2
    assert ("co_saic", "co_torch") not in pairs
    metrics = independence_metrics([{**_case(c)["relationships"][0]} for c in
                                    ("m18-obs-export-control-parsons-torch",
                                     "m18-obs-export-control-intuitive-torch")])
    assert metrics["unique_company_pairs"] == 2


def test_real_rule_no_exposure_no_threat():
    """The SAME real observed rule threatens a company ONLY where there is an evidenced exposure to it."""
    case = _case("m18-obs-export-control-no-exposure-negative")
    exposures = declared_exposures(case["subject"]["ref"], case["subject"]["name"],
                                   case["exposure_records"], as_of=case["replay_as_of"])
    threats, rejections = assess_threats(case["subject"]["ref"], case["subject"]["name"], exposures,
                                         case["catalyst_records"], as_of=case["replay_as_of"])
    assert threats == []
    assert [r.reason_code for r in rejections] == ["NO_EXPOSURE"]


def test_observed_vs_modeled_catalyst_authority_is_durable():
    """A threat from an OBSERVED catalyst is labelled OBSERVED; an absent class defaults to MODELED."""
    assert catalyst_class({"catalyst_class": "OBSERVED"}) == "OBSERVED"
    assert catalyst_class({}) == "MODELED"                 # never silently promoted
    assert catalyst_class({"catalyst_class": "bogus"}) == "MODELED"

    case = _case("m18-obs-export-control-parsons-torch")
    exposures = declared_exposures("co_parsons", "Parsons Government Services Inc.",
                                   case["exposure_records"], as_of=case["replay_as_of"])
    threats, _ = assess_threats("co_parsons", "Parsons Government Services Inc.", exposures,
                                case["catalyst_records"], as_of=case["replay_as_of"])
    assert threats and threats[0].meta.get("catalyst_class") == "OBSERVED"
