"""B3.11 — customer brief delivery contract (tenant-safe, deduped, auditable, fail-closed)."""

from datetime import datetime, timezone

import pytest

from pyrnova.alerts import RecordingTransport
from pyrnova.customer_delivery import (
    DELIVERED,
    FAILED,
    RIGHTS_BLOCKED,
    CustomerDeliveryStore,
    DeliveryRefused,
    deliver_customer_brief,
)

AUTH = ["ceo@torch.example", "capture@torch.example"]
NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def _deliver(store, transport, **kw):
    params = dict(customer_id="torch", artifact_ref="mc-1", subject="Material change",
                  body="Recompete expiry imminent.", recipients=["ceo@torch.example"],
                  authorized_recipients=AUTH, sender="briefs@pyrnova.example",
                  transport=transport, now=NOW)
    params.update(kw)
    return deliver_customer_brief(store, **params)


def test_successful_delivery_records_delivered_state(tmp_path):
    store = CustomerDeliveryStore(tmp_path)
    transport = RecordingTransport()
    rec = _deliver(store, transport)
    assert rec["status"] == DELIVERED
    assert rec["delivered_at"] is not None
    assert len(transport.sent) == 1
    assert transport.sent[0]["to"] == ["ceo@torch.example"]


def test_disabled_transport_is_failed_never_fabricated_as_delivered(tmp_path):
    store = CustomerDeliveryStore(tmp_path)
    rec = _deliver(store, transport=None)  # default DisabledTransport
    assert rec["status"] == FAILED
    assert rec["delivered_at"] is None
    assert rec["last_failure"]
    # durably recorded as a failure — no silent loss
    assert (tmp_path / "delivery_failures.jsonl").exists()


def test_idempotent_no_duplicate_mail_on_reissue(tmp_path):
    store = CustomerDeliveryStore(tmp_path)
    transport = RecordingTransport()
    first = _deliver(store, transport)
    second = _deliver(store, transport)  # identical brief + recipients
    assert first["delivery_id"] == second["delivery_id"]
    assert second["status"] == DELIVERED
    assert len(transport.sent) == 1  # no duplicate spam


def test_retry_resumes_same_delivery_then_succeeds(tmp_path):
    store = CustomerDeliveryStore(tmp_path)
    failing = RecordingTransport(fail_times=5)  # exceeds max_attempts
    first = _deliver(store, failing, max_attempts=2)
    assert first["status"] == FAILED and first["attempts"] == 2
    # a real transport becomes available; a later call RESUMES the same delivery, not a duplicate
    working = RecordingTransport()
    second = _deliver(store, working, max_attempts=2)
    assert second["delivery_id"] == first["delivery_id"]
    assert second["status"] == DELIVERED
    assert second["attempts"] == 3  # continued from the two prior failed attempts
    assert len(working.sent) == 1


def test_unauthorized_recipient_is_hard_refusal(tmp_path):
    store = CustomerDeliveryStore(tmp_path)
    with pytest.raises(DeliveryRefused, match="not authorized"):
        _deliver(store, RecordingTransport(), recipients=["stranger@evil.example"])
    # nothing durable was written for a refused request
    assert store.list_deliveries("torch") == []


def test_rights_blocked_content_is_never_transported(tmp_path):
    store = CustomerDeliveryStore(tmp_path)
    transport = RecordingTransport()
    rec = _deliver(store, transport, rights_display="BLOCKED")
    assert rec["status"] == RIGHTS_BLOCKED
    assert transport.sent == []  # fail closed — restricted expression not sent


def test_tenant_isolation_on_reads(tmp_path):
    store = CustomerDeliveryStore(tmp_path)
    rec = _deliver(store, RecordingTransport())
    did = rec["delivery_id"]
    # the owning tenant can read it
    assert store.get_delivery("torch", did) is not None
    # another tenant cannot — indistinguishable from absent
    assert store.get_delivery("mtsi", did) is None
    assert store.list_deliveries("mtsi") == []


def test_missing_customer_or_recipients_refused(tmp_path):
    store = CustomerDeliveryStore(tmp_path)
    with pytest.raises(DeliveryRefused):
        _deliver(store, RecordingTransport(), customer_id="")
    with pytest.raises(DeliveryRefused):
        _deliver(store, RecordingTransport(), recipients=[])
