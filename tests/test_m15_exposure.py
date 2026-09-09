"""M15 — exposure graph: evidence-safe linkage, weak-match rejection, point-in-time filtering."""

from __future__ import annotations

from pyrnova import threat
from pyrnova.sources import ofac


DESIGNATIONS = ofac.parse_ofac_csv(
    open("tests/fixtures/ofac_sdn_sample.csv", "rb").read(), list_name="sdn"
)


def _ent(designations, ent_num):
    return next(d for d in designations if d["ent_num"] == ent_num)


def test_deterministic_ident_link_is_confirmed():
    # A counterparty record that explicitly resolves to an OFAC ent_num is a CONFIRMED exposure.
    records = [{
        "source_ref": "sam:reg:acme:2023", "available_at": "2023-06-01",
        "counterparty_name": "Global Defense Supply LLC", "counterparty_ofac_ent_num": 10002,
        "relation": "SUPPLIER", "evidence_id": "ev1",
    }]
    exposures, weak = threat.sanctions_exposures("co_acme", "Acme Corp", records, DESIGNATIONS)
    assert len(exposures) == 1 and not weak
    exp = exposures[0]
    assert exp.link_class == "CONFIRMED"
    assert exp.join_method == "deterministic_identifier"
    assert exp.relation_type == "SANCTIONED_COUNTERPARTY"
    assert exp.confidence >= 0.9
    assert "ofac:sdn:10002" in exp.target_ref
    # Deterministic identity.
    assert exp.id == threat.exposure_id("co_acme", "SANCTIONED_COUNTERPARTY", exp.target_ref)


def test_name_only_overlap_is_weak_candidate_never_confirmed():
    records = [{
        "source_ref": "sam:reg:northstar_logistics", "available_at": "2023-06-01",
        "counterparty_name": "Northstar Logistics of Ohio",  # shares 'northstar' with a designation
        "relation": "CUSTOMER",
    }]
    exposures, weak = threat.sanctions_exposures("co_x", "X", records, DESIGNATIONS)
    assert not exposures            # no authoritative exposure emitted
    assert len(weak) == 1
    assert "northstar" in weak[0]["shared_tokens"]


def test_generic_token_alone_does_not_match():
    records = [{
        "source_ref": "r", "available_at": "2023-06-01",
        "counterparty_name": "Global Group Holdings",  # only generic tokens
        "relation": "SUPPLIER",
    }]
    exposures, weak = threat.sanctions_exposures("co_x", "X", records, DESIGNATIONS)
    assert not exposures and not weak


def test_identity_tuple_name_plus_country_confirms():
    records = [{
        "source_ref": "r", "available_at": "2023-06-01",
        "counterparty_name": "Northstar Trading Group", "counterparty_country": "IRAN",
        "relation": "SUPPLIER",
    }]
    exposures, weak = threat.sanctions_exposures("co_x", "X", records, DESIGNATIONS)
    assert len(exposures) == 1
    assert exposures[0].join_method == "deterministic_identifier"
    assert exposures[0].link_class == "CONFIRMED"


def test_point_in_time_excludes_future_counterparty_evidence():
    records = [{
        "source_ref": "r", "available_at": "2025-01-01",
        "counterparty_name": "Global Defense Supply LLC", "counterparty_ofac_ent_num": 10002,
        "relation": "SUPPLIER",
    }]
    exposures, _ = threat.sanctions_exposures("co_x", "X", records, DESIGNATIONS, as_of="2024-01-01")
    assert not exposures  # the relationship is not yet knowable at the cutoff


def test_incumbency_exposure_from_own_award_history():
    awards = [{
        "source_ref": "usa:award:1", "available_at": "2020-05-01", "recipient_uei": "ya63j5pveze6",
        "program_key": "prog:army-seta", "program_name": "Army SETA", "agency": "Army",
        "amount_usd": 5_000_000, "period_end": "2025-05-01",
    }]
    exposures = threat.incumbency_exposures("co_torch", "Torch", "YA63J5PVEZE6", awards)
    relations = {e.relation_type for e in exposures}
    assert relations == {"PROGRAM", "INCUMBENT_POSITION"}
    assert all(e.join_method == "deterministic_native_id" and e.link_class == "CONFIRMED"
               for e in exposures)


def test_incumbency_requires_uei_match():
    awards = [{"source_ref": "a", "available_at": "2020-05-01", "recipient_uei": "OTHER",
               "program_key": "prog:x"}]
    assert threat.incumbency_exposures("co_torch", "Torch", "YA63J5PVEZE6", awards) == []


def test_declared_regulation_exposure_inferred_vs_confirmed():
    recs = [
        {"relation": "REGULATION", "target_ref": "fr:rule:cmmc", "target_name": "CMMC rule",
         "available_at": "2024-01-01", "deterministic": True, "source_ref": "fr:1"},
        {"relation": "CERTIFICATION", "target_ref": "cert:cmmc-l2", "target_name": "CMMC L2",
         "available_at": "2024-01-01", "source_ref": "sam:1"},
    ]
    exps = threat.declared_exposures("co_x", "X", recs)
    by_rel = {e.relation_type: e for e in exps}
    assert by_rel["REGULATION"].link_class == "CONFIRMED"
    assert by_rel["CERTIFICATION"].link_class == "INFERRED"
