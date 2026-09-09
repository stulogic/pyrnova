"""M19 — the deterministic OBSERVED exposure and the second adverse-event family are REAL (honesty gate).

Analogue of tests/test_m18_observed_catalyst.py for M19. It proves the flagship deterministic chain is
not asserted out of thin air:

* the OBSERVED contract-modification catalyst used in the corpus is a real, archived USAspending
  deobligation (reproducible from
  examples/real_evidence/usaspending_contract_mods_saic_47QFSA20F0057.json via
  pyrnova.adverse_events.parse_usaspending_contract_modifications), and
* SAIC's exposure is DETERMINISTIC — its own award recipient UEI (MMLKPW9JLX64) joined to the exact
  deobligated PIID (47QFSA20F0057) by a native identifier, never a name/industry/geography resemblance —
  yielding a HIGH-confidence PROGRAM_CONTRACTION direct threat, and
* the SAIC->Torch propagation edge is the SAME program-anchored edge
  pyrnova.relationships.ground_subaward_edges derives from the archived sub-award bytes on that PIID, and
* deterministic identity is NOT by itself a threat: a trivially small real deobligation is IMMATERIAL and
  a material deobligation on a DIFFERENT award the subject does not hold is NO_EXPOSURE.

No network access; everything replays from committed evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyrnova.adverse_events import (
    contract_target_ref,
    parse_usaspending_contract_modifications,
    to_contract_contraction_catalyst,
)
from pyrnova.grounding_subawards import parse_subawards
from pyrnova.relationships import exposed_prime_awards_from_subawards, ground_subaward_edges
from pyrnova.threat import assess_threats, exposure_join_class, incumbency_exposures

_MODS = Path("examples/real_evidence/usaspending_contract_mods_saic_47QFSA20F0057.json")
_SUBAWARDS = Path("examples/real_evidence/usaspending_subawards_torch.json")
_CORPUS = json.loads(Path("examples/replay/corpus_m19.json").read_text())

_SAIC = "SCIENCE APPLICATIONS INTERNATIONAL CORPORATION"
_SAIC_UEI = "MMLKPW9JLX64"
_PIID = "47QFSA20F0057"


def _case(case_id):
    return next(c for c in _CORPUS["threat_cases"] if c["case_id"] == case_id)


def _event(mod_number):
    parsed = parse_usaspending_contract_modifications(_MODS.read_bytes())
    assert parsed["family"] == "contract_modification"
    return next(e for e in parsed["events"] if e["modification_number"] == mod_number)


def test_observed_catalyst_is_a_real_archived_usaspending_deobligation():
    """The corpus OBSERVED contract catalyst reproduces a real archived USAspending deobligation."""
    ev = _event("P00256")
    assert ev["catalyst_class"] == "OBSERVED"
    assert ev["piid"] == _PIID and ev["recipient_uei"] == _SAIC_UEI
    assert ev["event_type"] == "CONTRACT_DEOBLIGATION"
    assert ev["federal_action_obligation"] == -5152916.35
    assert ev["amount_delta_usd"] == 5152916.35
    assert ev["available_at"] == "2024-05-06"
    assert contract_target_ref(ev) == _PIID

    cat = to_contract_contraction_catalyst(ev)
    corpus_cat = _case("m19-det-contraction-saic-torch")["catalyst_records"][0]
    assert cat["catalyst_class"] == corpus_cat["catalyst_class"] == "OBSERVED"
    assert cat["target_ref"] == corpus_cat["target_ref"] == _PIID
    assert cat["amount_delta_usd"] == corpus_cat["amount_delta_usd"]
    assert cat["available_at"] == corpus_cat["available_at"]
    assert cat["source_ref"] == corpus_cat["source_ref"] == f"usaspending:txn:{_PIID}:P00256"
    assert cat["family"] == corpus_cat["family"] == "contract_modification"


def test_exposure_is_deterministic_and_threat_is_high_confidence():
    """SAIC's incumbency on the exact PIID is a deterministic native-id exposure; with the OBSERVED
    deobligation it yields a HIGH-confidence PROGRAM_CONTRACTION (MODERATE severity = the >$5M
    deobligated magnitude)."""
    awards = [{"recipient_uei": _SAIC_UEI, "program_key": _PIID, "amount_usd": 1432695358.81,
               "available_at": "2020-05-05", "period_end": "2025-11-04",
               "source_ref": f"usaspending:award:{_PIID}"}]
    exposures = incumbency_exposures("co_saic", _SAIC, _SAIC_UEI, awards, as_of="2024-06-01")
    program = [e for e in exposures if e.relation_type == "PROGRAM"]
    assert program and program[0].link_class == "CONFIRMED"
    assert program[0].join_method == "deterministic_native_id"
    assert exposure_join_class(exposures) == "deterministic"

    cat = to_contract_contraction_catalyst(_event("P00256"))
    threats, rejections = assess_threats("co_saic", _SAIC, exposures, [cat], as_of="2024-06-01")
    assert len(threats) == 1 and not rejections
    t = threats[0]
    assert t.mechanism == "PROGRAM_CONTRACTION"
    assert t.confidence == "HIGH"                       # deterministic exposure + observed catalyst
    assert t.severity == "MODERATE"                     # the deobligated dollar magnitude ($5.15M)
    assert t.meta["catalyst_class"] == "OBSERVED"
    assert t.meta["exposure_join_class"] == "deterministic"
    assert t.meta["adverse_event_family"] == "contract_modification"


def test_saic_torch_edge_is_the_real_program_anchored_edge_on_this_piid():
    """The corpus SAIC->Torch propagation edge is the SAME program-anchored edge grounded from the
    archived sub-award bytes on PIID 47QFSA20F0057."""
    parsed = parse_subawards(_SUBAWARDS.read_bytes(), company_name="TORCH TECHNOLOGIES INC")
    anchors = exposed_prime_awards_from_subawards(parsed, _SAIC)
    assert _PIID in anchors                              # SAIC is the prime recipient on this PIID
    edges = ground_subaward_edges(
        parsed, sub_ref="co_torch", sub_name="Torch Technologies Inc",
        prime_refs={_SAIC: "co_saic"}, exposed_prime_award_ids={_PIID})
    edge = next(e for e in edges if e["from_ref"] == "co_saic")
    assert edge["link_class"] == "CONFIRMED"
    assert edge["join_method"] == "deterministic_native_id"
    assert _PIID in edge["provenance"]["program_anchor_award_ids"]

    corpus_edge = _case("m19-det-contraction-saic-torch")["relationships"][0]
    assert corpus_edge["from_ref"] == "co_saic" and corpus_edge["to_ref"] == "co_torch"
    assert corpus_edge["link_class"] == "CONFIRMED"
    assert corpus_edge["join_method"] == "deterministic_native_id"


def test_deterministic_identity_alone_is_not_a_threat():
    """Immaterial deobligation -> IMMATERIAL; a material deobligation on a DIFFERENT award the subject
    does not hold -> NO_EXPOSURE. Exact identity never manufactures a threat by itself."""
    # Immaterial: the same deterministic incumbency, a real -$31,616 pull-back within the PoP.
    awards = [{"recipient_uei": _SAIC_UEI, "program_key": _PIID, "amount_usd": 1432695358.81,
               "available_at": "2020-05-05", "period_end": "2025-11-04",
               "source_ref": f"usaspending:award:{_PIID}"}]
    exposures = incumbency_exposures("co_saic", _SAIC, _SAIC_UEI, awards, as_of="2024-10-01")
    cat_small = to_contract_contraction_catalyst(_event("P00281"))
    threats, rejections = assess_threats("co_saic", _SAIC, exposures, [cat_small], as_of="2024-10-01")
    assert not threats
    assert [r.reason_code for r in rejections] == ["IMMATERIAL"]

    # Wrong award: incumbent on a DIFFERENT PIID; the material deobligation is on 47QFSA20F0057.
    other = [{"recipient_uei": _SAIC_UEI, "program_key": "W31P4Q21F0095", "amount_usd": 825826653.29,
              "available_at": "2021-03-01", "source_ref": "usaspending:award:W31P4Q21F0095"}]
    exp2 = incumbency_exposures("co_saic", _SAIC, _SAIC_UEI, other, as_of="2024-06-01")
    cat_big = to_contract_contraction_catalyst(_event("P00256"))
    threats2, rejections2 = assess_threats("co_saic", _SAIC, exp2, [cat_big], as_of="2024-06-01")
    assert not threats2
    assert [r.reason_code for r in rejections2] == ["NO_EXPOSURE"]
