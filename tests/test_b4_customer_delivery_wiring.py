"""B4.3 — customer email delivery: internal production wiring readiness.

Real EXTERNAL delivery verification remains an explicit genuine-credential dependency (no production SMTP
credentials are available to this environment, and personal mail is not a permitted workaround). These
tests prove the internal production wiring/configuration contract is complete and correct so that, the
moment real SMTP credentials exist, delivery works with no code change:

* config resolves a real SMTP transport when configured, else an explicit DisabledTransport;
* a configured transport drives PENDING -> transport attempt -> DELIVERED with a deterministic delivery id,
  the intended tenant + recipient, and no duplicate mail on retry (idempotent);
* a controlled failure path is visible (FAILED, durably audited, never fabricated as delivered);
* with no configuration the default transport is DisabledTransport (send recorded FAILED, not delivered).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from pyrnova.alerts import DisabledTransport, RecordingTransport, SMTPEmailTransport
from pyrnova.config import build_customer_delivery_transport, load_customer_delivery_config
from pyrnova.customer_delivery import CustomerDeliveryStore
from pyrnova.ops import OperatorConsole
from pyrnova.state import StateStore

DEMO = Path("examples/material_changes_demo")
STATE = DEMO / "state"
PROFILES = Path("examples/profiles")

SMTP_ENV = ("PYRNOVA_SMTP_HOST", "PYRNOVA_SMTP_PORT", "PYRNOVA_SMTP_USERNAME",
            "PYRNOVA_SMTP_PASSWORD", "PYRNOVA_SMTP_USE_TLS", "PYRNOVA_DELIVERY_SENDER")


def _console(tmp_path):
    store = StateStore(tmp_path / "state")
    spec = importlib.util.spec_from_file_location("demo_seed_customers", DEMO / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)
    return OperatorConsole(store, PROFILES, tmp_path / "o", mc_store=StateStore(STATE),
                           contexts_dir=DEMO, customer_store=store,
                           cmc_store=StateStore(tmp_path / "cmc"),
                           delivery_store=CustomerDeliveryStore(tmp_path / "deliveries"))


def _first_opp(console):
    return console.customer_opportunities("torch")["opportunities"][0]["id"]


def test_config_resolves_real_transport_only_when_configured(monkeypatch):
    for k in SMTP_ENV:
        monkeypatch.delenv(k, raising=False)
    # No SMTP configured -> explicit DisabledTransport (never a silent/fabricated delivery).
    cfg = load_customer_delivery_config()
    assert cfg.transport_configured is False
    assert isinstance(build_customer_delivery_transport(cfg), DisabledTransport)
    # SMTP configured -> a real production SMTP transport, credentials sourced from config only.
    monkeypatch.setenv("PYRNOVA_SMTP_HOST", "smtp.example.gov")
    monkeypatch.setenv("PYRNOVA_SMTP_USERNAME", "pyrnova")
    monkeypatch.setenv("PYRNOVA_SMTP_PASSWORD", "secret")
    cfg2 = load_customer_delivery_config()
    assert cfg2.transport_configured is True
    t = build_customer_delivery_transport(cfg2)
    assert isinstance(t, SMTPEmailTransport) and t.host == "smtp.example.gov"


def test_configured_transport_delivers_deterministically_no_duplicate(tmp_path):
    console = _console(tmp_path)
    oid = _first_opp(console)
    console.authorize_delivery_recipient("torch", "capture@torch.example")
    rec = RecordingTransport()
    d1 = console.deliver_customer_brief("torch", oid, recipients=["capture@torch.example"], transport=rec)
    assert d1["status"] == "DELIVERED"
    assert d1["customer_id"] == "torch" and d1["recipients"] == ["capture@torch.example"]
    assert d1["delivery_id"] and len(rec.sent) == 1
    # Re-issuing the identical brief must not send a second mail (idempotent, deterministic id).
    d2 = console.deliver_customer_brief("torch", oid, recipients=["capture@torch.example"], transport=rec)
    assert d2["delivery_id"] == d1["delivery_id"] and d2["status"] == "DELIVERED"
    assert len(rec.sent) == 1  # no duplicate transport handoff


def test_controlled_failure_is_visible_and_never_fabricated(tmp_path):
    console = _console(tmp_path)
    oid = _first_opp(console)
    console.authorize_delivery_recipient("torch", "capture@torch.example")
    failing = RecordingTransport(fail_times=99)  # every attempt raises TransportError
    d = console.deliver_customer_brief("torch", oid, recipients=["capture@torch.example"],
                                       transport=failing, max_attempts=2)
    assert d["status"] == "FAILED" and d["last_failure"]
    assert d["attempts"] == 2 and not failing.sent  # nothing was delivered
    # The failure is durably audited (never silently lost).
    audit = console.list_customer_deliveries("torch")["deliveries"]
    assert any(x["delivery_id"] == d["delivery_id"] and x["status"] == "FAILED" for x in audit)


def test_default_unconfigured_delivery_records_failed_not_delivered(tmp_path, monkeypatch):
    for k in SMTP_ENV:
        monkeypatch.delenv(k, raising=False)
    console = _console(tmp_path)
    oid = _first_opp(console)
    console.authorize_delivery_recipient("torch", "capture@torch.example")
    # No transport injected + no SMTP config -> DisabledTransport resolved from config.
    d = console.deliver_customer_brief("torch", oid, recipients=["capture@torch.example"])
    assert d["status"] == "FAILED"  # explicit, never fabricated as delivered
    assert d["transport"] == "DisabledTransport"
