"""M17 — the selectivity funnel is wired into NORMAL scheduler operation and persisted per run.

Proves the funnel can run as part of continuous source operation: each run is decorated with source-run
operational context (run id, timing, calls made/avoided, records) and persisted durably (append-only,
bounded), and a report rolls the runs up across sources. Uses the real committed OFAC fixture; the engine
stays selective (benign monitored companies against a large event batch emit zero threats).
"""

from __future__ import annotations

from pathlib import Path

from pyrnova import selectivity
from pyrnova.scheduler import SourceScheduler
from pyrnova.sources import ofac
from pyrnova.sources.source_state import SourceStateStore

DESIGNATIONS = ofac.parse_ofac_csv(
    Path("tests/fixtures/ofac_sdn_sample.csv").read_bytes(), list_name="sdn")

# Benign monitored companies with non-sanctioned counterparties: a large event batch must not emit a
# threat for them (selectivity), while the funnel + operational context are still recorded.
MONITORED = [
    {"ref": "co_benign_a", "name": "Benign Alpha Systems",
     "counterparty_records": [{"name": "Trusted Domestic Supplier LLC", "relation": "SUPPLIER"}]},
    {"ref": "co_benign_b", "name": "Benign Beta Corp",
     "counterparty_records": [{"name": "Reputable Parts Co", "relation": "SUPPLIER"}]},
]


def _scheduler(tmp_path):
    return SourceScheduler(SourceStateStore(tmp_path / "src_state"))


def test_run_funnel_carries_operational_context():
    result = selectivity.run_selectivity(MONITORED, designations=DESIGNATIONS,
                                         raw_event_count=len(DESIGNATIONS), stream_name="sanctions_ofac")
    record = selectivity.source_run_funnel(
        result, source_id="sanctions_ofac", run_id="run-001",
        started_at="2026-09-09T00:00:00", finished_at="2026-09-09T00:00:03",
        calls_made=1, calls_avoided=4, records_received=len(DESIGNATIONS), changed_records=0)
    assert record["run_id"] == "run-001"
    assert record["source_id"] == "sanctions_ofac"
    assert record["calls_made"] == 1 and record["calls_avoided"] == 4
    assert record["records_received"] == len(DESIGNATIONS)
    assert record["funnel"]["raw_events"] == len(DESIGNATIONS)
    # Selectivity: benign monitored companies emit no threats from a large event batch.
    assert record["funnel"]["threats_emitted"] == 0
    assert record["threat_emission_rate"] == 0.0


def test_runs_persist_and_report_rolls_up(tmp_path):
    sched = _scheduler(tmp_path)
    result = selectivity.run_selectivity(MONITORED, designations=DESIGNATIONS,
                                         raw_event_count=len(DESIGNATIONS), stream_name="sanctions_ofac")
    for i in range(3):
        rec = selectivity.source_run_funnel(result, source_id="sanctions_ofac", run_id=f"run-{i}",
                                            calls_made=(1 if i == 0 else 0), calls_avoided=(0 if i == 0 else 1))
        sched.record_selectivity_run("sanctions_ofac", rec)

    runs = sched.selectivity_runs("sanctions_ofac")
    assert len(runs) == 3
    assert [r["run_id"] for r in runs] == ["run-0", "run-1", "run-2"]  # append-only order preserved

    report = sched.selectivity_report(["sanctions_ofac"])
    assert report["sources_with_runs"] == 1
    assert report["total_runs"] == 3
    assert report["totals"]["threats_emitted"] == 0
    assert report["totals"]["raw_events"] == 3 * len(DESIGNATIONS)
    assert report["totals"]["calls_made"] == 1                # only the first run spent a call
    assert report["totals"]["calls_avoided"] == 2             # the two repeats were served from cache
    assert report["threat_emission_rate"] == 0.0
    assert report["per_source"][0]["latest_run_id"] == "run-2"


def test_persistence_survives_reload_and_is_bounded(tmp_path):
    sched = _scheduler(tmp_path)
    result = selectivity.run_selectivity(MONITORED, designations=DESIGNATIONS,
                                         raw_event_count=len(DESIGNATIONS))
    for i in range(5):
        sched.record_selectivity_run(
            "sanctions_ofac",
            selectivity.source_run_funnel(result, source_id="sanctions_ofac", run_id=f"r{i}"),
            keep_last=3)
    # A fresh scheduler over the same durable state reads the persisted, bounded history.
    reloaded = _scheduler(tmp_path)
    runs = reloaded.selectivity_runs("sanctions_ofac")
    assert [r["run_id"] for r in runs] == ["r2", "r3", "r4"]   # only the last keep_last retained


def test_report_empty_safe(tmp_path):
    report = _scheduler(tmp_path).selectivity_report(["sanctions_ofac"])
    assert report["sources_with_runs"] == 0
    assert report["total_runs"] == 0
    assert report["threat_emission_rate"] is None            # no divide-by-zero on an empty operation
