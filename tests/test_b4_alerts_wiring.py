"""B4.9 — operator alerts production/release wiring verification (no redesign).

The alerting capability + independent dead-man watcher are accepted and covered by test_operator_alerts.py
(lifecycle, dedupe/no-storm, INFO-never-emails, transport failure/recovery, redaction, heartbeat + watchdog
restart safety). This pins the release-wiring aspects: the production transport is config-resolved, the
severity doctrine holds end-to-end through build_manager, and operator alerts are DECOUPLED from customer
email delivery (distinct factories/config — never confused).
"""

from __future__ import annotations

from pyrnova import config
from pyrnova.alerts import DisabledTransport, RecordingTransport, Severity
from pyrnova.config import AlertConfig
from pyrnova.watchdog import build_manager, build_transport


def _cfg(tmp_path, **over):
    base = dict(enabled=True, recipients=("ops@pyrnova",), sender="alerts@pyrnova",
                smtp_host="smtp.example.gov", smtp_port=587, smtp_username="u", smtp_password="p",
                smtp_use_tls=True, max_attempts=3, alert_state_dir=tmp_path / "alerts",
                heartbeat_dir=tmp_path / "hb", deadman_component="live_ops",
                deadman_max_silence_seconds=900.0)
    base.update(over)
    return AlertConfig(**base)


def test_build_transport_is_real_smtp_when_configured(tmp_path):
    from pyrnova.alerts import SMTPEmailTransport
    t = build_transport(_cfg(tmp_path))
    assert isinstance(t, SMTPEmailTransport) and t.host == "smtp.example.gov"
    # No sending identity -> explicit disabled (never a silent/fabricated delivery).
    assert isinstance(build_transport(_cfg(tmp_path, smtp_host="", recipients=())), DisabledTransport)


def test_severity_doctrine_end_to_end_via_build_manager(tmp_path):
    mgr = build_manager(_cfg(tmp_path))
    rec = RecordingTransport()
    mgr.notifier.transport = rec  # inject a controlled transport (no real SMTP)
    # INFO stays in durable logs/status and never emails an operator.
    mgr.raise_alert(alert_class="source_health", subject="usaspending", severity=Severity.INFO,
                    summary="minor")
    assert rec.sent == []
    # OPERATOR_ATTENTION / CRITICAL reach the operator inbox.
    mgr.raise_alert(alert_class="persistence", subject="state", severity=Severity.CRITICAL,
                    summary="write failure")
    assert len(rec.sent) == 1


def test_operator_alerts_decoupled_from_customer_delivery(tmp_path, monkeypatch):
    # Distinct factories + distinct configuration surfaces — operator alerts are never customer delivery.
    assert build_transport is not config.build_customer_delivery_transport
    monkeypatch.setenv("PYRNOVA_DELIVERY_SENDER", "briefs@pyrnova")
    monkeypatch.setenv("PYRNOVA_ALERT_SENDER", "alerts@pyrnova")
    monkeypatch.setenv("PYRNOVA_SMTP_HOST", "smtp.example.gov")
    monkeypatch.setenv("PYRNOVA_ALERT_RECIPIENTS", "ops@pyrnova")
    delivery = config.load_customer_delivery_config()
    alerts = config.load_alert_config()
    assert delivery.sender == "briefs@pyrnova" and alerts.sender == "alerts@pyrnova"
    # Alert recipients come from config; customer-delivery recipients are NOT config-sourced (operator-authorized).
    assert alerts.recipients == ("ops@pyrnova",)
    assert not hasattr(delivery, "recipients")
