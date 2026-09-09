"""M16 — real event-stream selectivity: a large drop from raw events to emitted threats."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyrnova import selectivity
from pyrnova.sources import ofac

FIXTURE = ofac.parse_ofac_csv(Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")
_REAL = sorted(Path("var/m14_archive/sanctions_ofac").glob("sdn_*.csv"))


def _benign(ref, counterparty):
    return {"ref": ref, "name": ref, "counterparty_records": [
        {"source_ref": f"reg:{ref}", "available_at": "2023-01-01", "relation": "SUPPLIER",
         "counterparty_name": counterparty}]}


def test_funnel_drops_and_most_companies_have_no_threat():
    monitored = [
        _benign("co_clean_a", "Reliable Midwest Fasteners"),
        _benign("co_clean_b", "Anytown County Water District"),
        {"ref": "co_exposed", "name": "Exposed Importer", "counterparty_records": [
            {"source_ref": "reg:exp", "available_at": "2023-01-01", "relation": "SUPPLIER",
             "counterparty_name": "Global Defense Supply LLC", "counterparty_ofac_ent_num": 10002}]},
    ]
    res = selectivity.run_selectivity(monitored, designations=FIXTURE, stream_name="ofac_fixture")
    f = res["funnel"]
    assert f["raw_events"] == len(FIXTURE)
    assert f["accepted_exposures"] == 1          # only the ent_num-linked company
    assert f["threats_emitted"] == 1
    # Most monitored companies emit nothing.
    zero = [c for c in res["per_company"] if c["threats"] == 0]
    assert len(zero) == 2
    assert res["threat_emission_rate"] is not None


@pytest.mark.skipif(not _REAL, reason="real OFAC archive absent (git-ignored); replay-from-archive only")
def test_real_stream_emits_near_zero_threats():
    designations = ofac.parse_ofac_csv(_REAL[0].read_bytes(), list_name="sdn")
    assert len(designations) > 10000
    # A monitored set of ordinary US companies with benign counterparties.
    monitored = [
        _benign("co_torch", "Reliable Midwest Fasteners"),
        _benign("co_mtsi", "Huntsville Office Supplies"),
        _benign("co_saic", "Northern Virginia Staffing"),
        _benign("co_generic", "Standard Industrial Parts"),
    ]
    res = selectivity.run_selectivity(monitored, designations=designations, stream_name="ofac_real")
    f = res["funnel"]
    # 19k+ real events, four monitored companies, ZERO confirmed exposures => ZERO threats.
    assert f["raw_events"] > 10000
    assert f["accepted_exposures"] == 0
    assert f["threats_emitted"] == 0
    assert res["threat_emission_rate"] == 0.0    # the selectivity proof at scale
