"""B4.16 — production-equivalent SMTP transport verification (no external network, no credentials).

Real EXTERNAL send to a real inbox stays an explicit credential/infra dependency (and sending to real
prospects is forbidden). This proves the *real* smtplib code path in ``SMTPEmailTransport`` — the seam
shared by BOTH customer delivery and operator alerting — actually transmits a well-formed message over
the SMTP protocol, by driving it against an in-process loopback SMTP sink on 127.0.0.1. That is
production-equivalent: real transport, real protocol, captured on the wire; only the destination is a
local sink instead of a real MX.
"""

from __future__ import annotations

import importlib.util
import socketserver
import threading
from pathlib import Path

import pytest

from pyrnova.alerts import AlertManager, AlertStore, Notifier, Severity, SMTPEmailTransport
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"
PROFILES = Path("examples/profiles")


class _SMTPSink(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        captured: dict = {"rcpt": []}
        self.wfile.write(b"220 pyrnova-test-sink\r\n")
        while True:
            line = self.rfile.readline()
            if not line:
                break
            cmd = line.decode("utf-8", "replace").strip()
            up = cmd.upper()
            if up.startswith(("EHLO", "HELO")):
                self.wfile.write(b"250 pyrnova-test-sink\r\n")
            elif up.startswith("MAIL FROM"):
                captured["from"] = cmd
                self.wfile.write(b"250 OK\r\n")
            elif up.startswith("RCPT TO"):
                captured["rcpt"].append(cmd)
                self.wfile.write(b"250 OK\r\n")
            elif up == "DATA":
                self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                body = []
                while True:
                    dl = self.rfile.readline()
                    if not dl or dl in (b".\r\n", b".\n"):
                        break
                    body.append(dl)
                captured["data"] = b"".join(body).decode("utf-8", "replace")
                self.wfile.write(b"250 OK queued\r\n")
            elif up.startswith("QUIT"):
                self.wfile.write(b"221 Bye\r\n")
                break
            else:  # RSET / NOOP / anything else
                self.wfile.write(b"250 OK\r\n")
        self.server.captured.append(captured)  # type: ignore[attr-defined]


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@pytest.fixture
def smtp_sink():
    server = _Server(("127.0.0.1", 0), _SMTPSink)
    server.captured = []  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def _local_transport(port: int) -> SMTPEmailTransport:
    # Plain local SMTP: no TLS, no auth — the real code path minus a real credentialed MX.
    return SMTPEmailTransport(host="127.0.0.1", port=port, use_tls=False, username="", timeout=5.0)


def _console(tmp_path) -> OperatorConsole:
    store = StateStore(tmp_path / "state")
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)
    return OperatorConsole(store, PROFILES, tmp_path / "o", mc_store=StateStore(STATE),
                           contexts_dir=DEMO, customer_store=store,
                           cmc_store=StateStore(tmp_path / "cmc"),
                           delivery_store=CustomerDeliveryStore(tmp_path / "deliveries"))


def test_customer_delivery_transmits_over_real_smtp(tmp_path, smtp_sink):
    server, port = smtp_sink
    console = _console(tmp_path)
    oid = console.customer_opportunities("torch")["opportunities"][0]["id"]
    console.authorize_delivery_recipient("torch", "ceo@torch.example")
    rec = console.deliver_customer_brief(
        "torch", oid, recipients=["ceo@torch.example"], transport=_local_transport(port),
    )
    assert rec["status"] == "DELIVERED" and rec["delivered_at"] is not None
    assert len(server.captured) == 1
    msg = server.captured[0]
    assert any("ceo@torch.example" in r for r in msg["rcpt"])  # real RCPT TO on the wire
    assert "PYRNOVA DECISION BRIEF" in msg["data"]              # the real brief body transmitted


def test_operator_alert_transmits_over_real_smtp(tmp_path, smtp_sink):
    server, port = smtp_sink
    store = AlertStore(tmp_path / "alerts")
    notifier = Notifier(transport=_local_transport(port), sender="ops@pyrnova.example",
                        recipients=["operator@pyrnova.example"])
    manager = AlertManager(store=store, notifier=notifier)
    event = manager.raise_alert(alert_class="phase1.dead_man", subject="live-ops",
                                severity=Severity.CRITICAL, summary="heartbeat missing")
    assert store.get(event.alert_key)["delivery"]["status"] == "delivered"
    assert len(server.captured) == 1
    assert any("operator@pyrnova.example" in r for r in server.captured[0]["rcpt"])
    assert "heartbeat missing" in server.captured[0]["data"]


def test_smtp_failure_is_visible_never_fabricated(tmp_path):
    # A transport pointed at a closed port fails explicitly; delivery is never fabricated as delivered.
    dead = SMTPEmailTransport(host="127.0.0.1", port=9, use_tls=False, username="", timeout=1.0)
    notifier = Notifier(transport=dead, sender="ops@pyrnova.example",
                        recipients=["operator@pyrnova.example"], max_attempts=1)
    result = notifier.deliver({"severity": "CRITICAL", "alert_class": "x", "subject": "s",
                               "summary": "y", "status": "OPEN"}, "OPENED")
    assert result["status"] == "failed" and result["last_delivered_at"] is None
