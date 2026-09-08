import json
import threading
from pathlib import Path
from urllib.request import urlopen

import pytest

from pyrnova.ops import OperatorConsole
from pyrnova.ops_server import make_handler
from pyrnova.state import StateStore
from http.server import ThreadingHTTPServer


def _opportunity(opportunity_id="opp-1", target="Acme"):
    return {
        "id": opportunity_id,
        "run_id": "run-1",
        "title": "C4ISR support requirement",
        "customer_id": target,
        "agency": "US Army",
        "state": "reviewing",
        "relevance_score": 0.8,
        "confidence": 0.7,
        "attractiveness": 0.6,
        "falsification": "",
        "recommended_action": "verify acquisition path",
        "catalyst": {"kind": "sources_sought", "detected_by": "test", "summary": "Direct notice"},
        "evidence": [{"source_id": "sam_opportunities", "content_sha256": "a" * 64, "archive_uri": "local://a", "retention_tier": "A", "source_ref": "SAM-1", "source_url": "https://sam.gov/example"}],
        "meta": {"system_disposition": "WATCH", "review_status": "pending_human"},
    }


def _console(tmp_path):
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "acme.json").write_text(json.dumps({"name": "Acme"}))
    store = StateStore(tmp_path / "state")
    store.append("opportunities", _opportunity())
    return OperatorConsole(store, profiles, tmp_path / "out")


def test_snapshot_adjudication_and_outcome_are_append_only(tmp_path):
    console = _console(tmp_path)
    console.store.append("commercial_consequences", {
        "id": "cons-1", "program_key": "program-1", "mechanism": "PROCUREMENT_DEMAND",
        "directness": "DIRECT", "confidence": 0.72, "screened_disposition": "WATCH",
    })
    latest = console.store.latest("opportunities", "opp-1")
    latest.pop("_ts", None)
    latest["meta"]["program_key"] = "program-1"
    console.store.append("opportunities", latest)
    snapshot = console.snapshot("Acme")
    assert snapshot["queue"][0]["system_disposition"] == "WATCH"
    assert snapshot["queue"][0]["m7_consequence"]["mechanism"] == "PROCUREMENT_DEMAND"
    assert snapshot["source_health"][0]["status"] == "not_observed"

    result = console.adjudicate(
        "opp-1", decision="ACCEPT", reviewer="analyst", posture="PRIME",
        notes="Call program office", falsification="Scope excludes our capability",
    )
    assert result["state"] == "strike"
    row = console.snapshot("Acme")["queue"][0]
    assert row["human_decision"] == "ACCEPT"
    assert row["posture"] == "PRIME"
    assert row["notes"] == "Call program office"
    assert console.store.count("opportunities") == 3

    console.record_outcome("opp-1", status="QUALIFIED", notes="Discovery booked")
    assert console.snapshot("Acme")["queue"][0]["outcome"]["status"] == "QUALIFIED"


def test_signal_brief_uses_existing_renderer(tmp_path):
    console = _console(tmp_path)
    console.adjudicate("opp-1", decision="ACCEPT", reviewer="analyst", posture="TEAM")
    result = console.export_signal_brief("Acme")
    assert result["items"] == 1
    assert "Pyrnova Signal Brief" in result["markdown"]
    assert Path(result["path"]).exists()


def test_local_http_snapshot(tmp_path):
    console = _console(tmp_path)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(console))
    except (PermissionError, OSError) as exc:
        # Some sandboxes forbid binding a loopback socket; the handler/console logic is covered by the
        # non-socket tests above. Skip only the live-port integration path here.
        pytest.skip(f"loopback socket bind not permitted in this environment: {exc}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/api/snapshot?target=Acme") as response:
            payload = json.load(response)
        assert payload["queue"][0]["id"] == "opp-1"
    finally:
        server.shutdown()
        server.server_close()


def test_handler_routing_without_a_live_port(tmp_path):
    """Exercise make_handler's GET routing/serialization without binding a socket (sandbox-safe)."""
    import io

    console = _console(tmp_path)
    handler_cls = make_handler(console)
    handler = handler_cls.__new__(handler_cls)  # bypass the socket-bound __init__
    handler.path = "/api/snapshot?target=Acme"
    handler.headers = {}
    handler.wfile = io.BytesIO()
    handler.send_response = lambda *a, **k: None
    handler.send_header = lambda *a, **k: None
    handler.end_headers = lambda *a, **k: None
    handler.do_GET()
    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert payload["queue"][0]["id"] == "opp-1"
    assert payload["target"] == "Acme"


def test_stale_import_metadata_keeps_unknown_scores_explicit(tmp_path):
    console = _console(tmp_path)
    row = console.store.latest("opportunities", "opp-1")
    row.pop("_ts", None)
    row["meta"].update({
        "data_origin": "stale_report", "source_status": "STALE DRAFT",
        "source_as_of": "2026-09-08", "score_status": "unavailable",
    })
    console.store.append("opportunities", row)
    item = console.snapshot("Acme")["queue"][0]
    assert item["data_origin"] == "stale_report"
    assert item["source_status"] == "STALE DRAFT"
    assert item["score_status"] == "unavailable"
