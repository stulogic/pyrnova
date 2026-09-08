"""M7 capital catalysts and commercial consequences."""

from pyrnova.catalysts import (
    build_catalysts_and_consequences,
    classify_mechanisms,
    resolve_participants,
)
from pyrnova.chains import resolve_chain, signals_from_records
from pyrnova.metrics import summarize_results
from pyrnova.replay import (
    load_corpus,
    run_consequence_corpus,
    run_consequence_replay,
    run_corpus,
    summarize_consequence_results,
)

M4, M5, M6, M7 = (f"examples/replay/corpus_{c}.json" for c in ("m4", "m5", "m6", "m7"))


def _build(records):
    resolution = resolve_chain(signals_from_records(records))
    return build_catalysts_and_consequences(records, resolution)


def _rec(**kw):
    base = {"source_role": "primary", "url": "https://example.gov/x", "strength": 3, "available_at": "2024-01-01T00:00:00+00:00"}
    base.update(kw)
    return base


# --- catalyst identity / grouping ----------------------------------------------

def test_one_catalyst_per_chain_with_deterministic_identity():
    records = [
        _rec(source_id="appropriations", source_ref="A1", record_kind="appropriation", stage="FUNDING",
             program_key="navy:radar", agency="Department of the Navy"),
        _rec(source_id="sam_opportunities", source_ref="S1", record_kind="solicitation", stage="PROCUREMENT",
             program_key="navy:radar", agency="Department of the Navy", available_at="2024-06-01T00:00:00+00:00"),
    ]
    c1, _ = _build(records)
    c2, _ = _build(records)
    assert len(c1) == 1
    assert c1[0].id == c2[0].id and c1[0].id.startswith("cat_")


def test_inferred_cross_program_join_yields_one_catalyst_collapsing_keys():
    records = [
        _rec(source_id="appropriations", source_ref="A1", record_kind="appropriation", stage="FUNDING",
             program_key="doe:approp", program_identifier="81.086", agency="Department of Energy"),
        _rec(source_id="usaspending", source_ref="U1", record_kind="award", stage="AWARD",
             program_key="doe:award", program_identifier="81.086", agency="Department of Energy",
             available_at="2024-06-01T00:00:00+00:00"),
    ]
    catalysts, _ = _build(records)
    assert len(catalysts) == 1
    assert sorted(catalysts[0].meta["program_keys"]) == ["doe:approp", "doe:award"]


# --- mechanism classification --------------------------------------------------

def test_direct_procurement_mechanism_is_direct_and_strikes():
    records = [
        _rec(source_id="sam_opportunities", source_ref="S1", record_kind="solicitation", stage="PROCUREMENT",
             program_key="navy:radar", agency="Department of the Navy", naics="334511",
             description="radar component production", amount_usd=52000000),
        _rec(source_id="usaspending", source_ref="U1", record_kind="award", stage="AWARD", program_key="navy:radar",
             agency="Department of the Navy", recipient_uei="RDR1", place_of_performance="Portsmouth, VA",
             available_at="2024-06-01T00:00:00+00:00"),
    ]
    _, consequences = _build(records)
    direct = [c for c in consequences if c.mechanism == "DIRECT_PROCUREMENT"]
    assert direct and direct[0].directness == "DIRECT"
    assert direct[0].screened_disposition == "STRIKE"
    assert direct[0].capability_classes  # radar capability resolved
    assert direct[0].value["status"] == "KNOWN"


def test_funded_downstream_demand_is_downstream_watch():
    records = [
        _rec(source_id="grants_gov", source_ref="G1", record_kind="grant_nofo", stage="FUNDING",
             program_key="doe:battery", agency="Department of Energy", naics="335910",
             description="battery manufacturing", program_amount=200000000, project_fraction=[0.05, 0.20]),
    ]
    _, consequences = _build(records)
    assert [c.mechanism for c in consequences] == ["FUNDED_DOWNSTREAM_DEMAND"]
    assert consequences[0].directness == "DOWNSTREAM"
    assert consequences[0].screened_disposition == "WATCH"
    assert consequences[0].value["status"] == "BOUNDED"


def test_compliance_mechanism_from_regulatory_obligation():
    records = [
        _rec(source_id="federal_register", source_ref="R1", record_kind="rule", stage="MARKET_ENGAGEMENT",
             program_key="epa:pfas", agency="Environmental Protection Agency", obligation=True,
             regulated_entity="public water utilities", naics="562910", description="environmental remediation"),
    ]
    _, consequences = _build(records)
    assert consequences[0].mechanism == "FORCED_COMPLIANCE_SPEND"
    assert any(p["role"] == "REGULATED_ENTITY" for p in consequences[0].participants)


def test_second_order_capex_stays_watch_with_speculative_falsifier():
    records = [
        _rec(source_id="sec_edgar", source_ref="E1", record_kind="capex", stage="PROGRAM",
             program_key="acme:plant", agency="Acme Industrials Inc", capex_disclosed=True,
             naics="333242", description="semiconductor assembly plant"),
    ]
    _, consequences = _build(records)
    c = consequences[0]
    assert c.mechanism == "CAPITAL_EXPANSION" and c.directness == "SECOND_ORDER"
    assert c.screened_disposition == "WATCH"
    assert any(f["code"] == "speculative_second_order" for f in c.falsifiers)


# --- the anti-generic-idea guarantee -------------------------------------------

def test_bare_appropriation_produces_catalyst_but_zero_consequences():
    records = [
        _rec(source_id="appropriations", source_ref="A1", record_kind="appropriation", stage="FUNDING",
             program_key="doe:quantum", agency="Department of Energy", amount_usd=500000000),
    ]
    catalysts, consequences = _build(records)
    assert len(catalysts) == 1 and consequences == []  # no procurement/grant/regulation -> no invented ideas


def test_internal_self_performance_kills_the_consequence():
    records = [
        _rec(source_id="sam_opportunities", source_ref="P1", record_kind="presolicitation", stage="PROCUREMENT",
             program_key="va:depot", agency="Department of Veterans Affairs", naics="811310",
             internal_self_performance=True, description="in-house depot maintenance"),
    ]
    _, consequences = _build(records)
    assert consequences[0].screened_disposition == "REJECT"
    assert any(f["code"] == "internal_self_performance" and f["fatal"] for f in consequences[0].falsifiers)


def test_contradiction_marks_catalyst_and_rejects_consequence():
    records = [
        _rec(source_id="sam_opportunities", source_ref="S1", record_kind="solicitation", stage="PROCUREMENT",
             program_key="navy:x", agency="Department of the Navy", naics="334511", recipient_uei="R1"),
        _rec(source_id="sam_opportunities", source_ref="S2", record_kind="cancellation", stage="AWARD",
             program_key="navy:x", agency="Department of the Navy", contradicts=True,
             available_at="2024-06-01T00:00:00+00:00", summary="solicitation cancelled"),
    ]
    catalysts, consequences = _build(records)
    assert catalysts[0].status == "contradicted"
    assert any(c.screened_disposition == "REJECT" for c in consequences)


# --- participant roles ---------------------------------------------------------

def test_roles_are_distinguished_and_supplier_not_inferred():
    records = [
        _rec(source_id="appropriations", source_ref="A1", record_kind="appropriation", stage="FUNDING",
             program_key="af:radar", agency="Department of the Air Force"),
        _rec(source_id="sam_opportunities", source_ref="S1", record_kind="solicitation", stage="PROCUREMENT",
             program_key="af:radar", agency="Department of the Air Force", available_at="2024-03-01T00:00:00+00:00"),
        _rec(source_id="usaspending", source_ref="U1", record_kind="award", stage="AWARD", program_key="af:radar",
             agency="Department of the Air Force", recipient_uei="PR1", recipient="Prime Co",
             available_at="2024-09-01T00:00:00+00:00"),
    ]
    participants = resolve_participants(records)
    roles = {p.role for p in participants}
    assert {"FUNDING_AUTHORITY", "PROGRAM_OWNER", "BUYER", "PRIME_RECIPIENT"} <= roles
    assert "SUPPLIER" not in roles and "SUBCONTRACTOR" not in roles


# --- value ---------------------------------------------------------------------

def test_value_unknown_when_no_amount_evidence():
    records = [
        _rec(source_id="sam_opportunities", source_ref="S1", record_kind="solicitation", stage="PROCUREMENT",
             program_key="af:de", agency="Department of the Air Force", psc="5865", description="directed energy",
             recipient_uei="X1"),
    ]
    _, consequences = _build(records)
    assert consequences[0].value["status"] == "UNKNOWN"
    assert consequences[0].value["provenance"]  # provenance retained even when unknown


# --- corpus acceptance ---------------------------------------------------------

def test_multi_consequence_chips_case():
    case = next(c for c in load_corpus(M7) if c["case_id"] == "m7-multi-consequence-chips-2022")
    result = run_consequence_replay(case)
    mechs = {c["mechanism"] for c in result["consequences"]}
    assert result["consequence_count"] >= 2
    assert "DIRECT_PROCUREMENT" in mechs and len(mechs) >= 2


def test_m7_corpus_expected_consequences_all_pass_and_precision_clean():
    results = run_consequence_corpus(load_corpus(M7))
    summary = summarize_consequence_results(results)
    assert summary["expected_consequence_passing"] == summary["expected_consequence_cases"] == 8
    assert summary["consequence_precision"] == 1.0
    assert summary["false_consequence_rate"] == 0.0
    assert summary["zero_consequence_catalysts"] >= 1
    assert summary["multi_consequence_cases"] >= 1
    assert summary["rejected_consequences"] >= 1
    assert len(summary["mechanism_families_exercised"]) >= 4
    assert {"KNOWN", "BOUNDED", "UNKNOWN"} <= set(summary["value_status_distribution"])
    assert summary["small_sample_warning"]


def test_scoring_v1_stable_and_frozen_corpora_unchanged():
    m7 = summarize_results(run_corpus(load_corpus(M7)))
    assert m7["case_count"] == 43
    assert m7["false_negative_rate"] == 0.0
    assert m7["confusion_matrix"]["false_strike"] == 1  # no new false positive; no STRIKE explosion
    assert m7["strike_precision"] == 0.875
    for corpus, cases, prec in ((M4, 23, 0.6667), (M5, 27, 0.75), (M6, 35, 0.8)):
        m = summarize_results(run_corpus(load_corpus(corpus)))
        assert m["case_count"] == cases and m["strike_precision"] == prec
