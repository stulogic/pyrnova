import random

import pytest

from pyrnova.sources.control import (
    AcceptanceCacheForbidden,
    CircuitOpen,
    CircuitState,
    CircuitBreaker,
    ExternalCallBlocked,
    RequestBudget,
    RequestBudgetExceeded,
    RetryPolicy,
    SourceControl,
    SourceMode,
    request_fingerprint,
    sanitized_request,
)


def test_request_fingerprint_is_deterministic_and_redacts_credentials():
    first = request_fingerprint(
        "get",
        "HTTPS://API.example.test/search?token=url-secret&b=2",
        params={"api_key": "first-secret", "q": "alpha"},
        headers={"Authorization": "Bearer first-secret", "Accept": "application/json"},
        payload={"client_secret": "payload-secret", "items": [2, 1]},
    )
    second = request_fingerprint(
        "GET",
        "https://api.example.test/search?b=2&token=other-secret",
        params={"q": "alpha", "api_key": "other-secret"},
        headers={"accept": "application/json", "authorization": "Bearer other-secret"},
        payload={"items": [2, 1], "client_secret": "another-secret"},
    )

    assert first == second
    safe = sanitized_request(
        "GET",
        "https://api.example.test/search?token=url-secret",
        params={"api_key": "first-secret"},
        headers={"Authorization": "Bearer first-secret"},
        payload={"client_secret": "payload-secret"},
    )
    rendered = repr(safe)
    assert "first-secret" not in rendered
    assert "payload-secret" not in rendered
    assert "url-secret" not in rendered


def test_modes_cache_accounting_and_budget():
    offline = SourceControl(SourceMode.OFFLINE)
    assert offline.prepare(cache_hit=True).action == "cache_hit"
    assert offline.snapshot()["cache_hits"] == 1
    assert offline.snapshot()["calls_avoided"] == 1
    with pytest.raises(ExternalCallBlocked):
        offline.prepare()

    live = SourceControl("LIVE-SAFE", max_calls=1)
    assert live.prepare(request_fingerprint="abc").action == "live_call"
    assert live.calls_made == 1
    with pytest.raises(RequestBudgetExceeded):
        live.prepare()

    acceptance = SourceControl("acceptance", max_calls=2)
    with pytest.raises(AcceptanceCacheForbidden):
        acceptance.prepare(cache_hit=True)
    assert acceptance.prepare().reason == "authorized in ACCEPTANCE"


def test_retry_metadata_is_bounded_and_does_not_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(random, "uniform", lambda _low, _high: 0.5)
    policy = RetryPolicy(max_attempts=4, base_delay_seconds=2, max_delay_seconds=5)
    control = SourceControl("LIVE_SAFE", retry_policy=policy)
    metadata = control.retry_metadata(
        2, reason="HTTP 429", retry_after_seconds=4, retryable=True
    )
    assert metadata.attempt == 2
    assert metadata.max_attempts == 4
    assert metadata.delay_seconds == 4.5
    assert metadata.provider_retry_after_seconds == 4
    assert metadata.retryable is True
    assert sleeps == []
    assert control.retry_metadata(2, reason="HTTP 429", retry_after_seconds=90).delay_seconds == 90
    assert control.retry_metadata(4, reason="final").retryable is False


def test_circuit_breaker_records_failures_and_next_poll():
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=10)
    control = SourceControl("LIVE_SAFE", breaker=breaker)
    control.prepare(now=100)
    control.record_failure("throttle", now=100)
    control.prepare(now=101)
    control.record_failure("service", now=101)

    assert breaker.state == CircuitState.OPEN
    assert breaker.next_permitted_poll == 111
    with pytest.raises(CircuitOpen):
        control.prepare(now=110)
    assert control.prepare(now=111).action == "live_call"
    assert breaker.state == CircuitState.HALF_OPEN
    control.record_success(now=111)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.next_permitted_poll is None


def test_snapshot_keeps_unknown_quota_and_exposes_metrics():
    control = SourceControl("LIVE_SAFE", budget=RequestBudget(max_calls=3))
    control.prepare()
    control.record_failure("terminal", now=12)
    snapshot = control.snapshot()
    assert snapshot["mode"] == "LIVE_SAFE"
    assert snapshot["budget_limit"] == 3
    assert snapshot["budget_remaining"] == 2
    assert snapshot["terminal_errors"] == 1
    assert snapshot["quota_state"] == "unknown"


def test_cache_hit_accounting_can_be_reported_after_lookup():
    control = SourceControl("LIVE_SAFE")
    control.record_cache_hit(request_fingerprint="same-request")
    assert control.cache_hits == 1
    assert control.calls_avoided == 1
    assert control.calls_made == 0
