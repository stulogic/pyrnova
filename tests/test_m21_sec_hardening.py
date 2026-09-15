"""M21 SEC ingestion hardening: declared identity, access order, accession dedupe, safe 403."""

import pytest

from pyrnova import config
from pyrnova.sources import http, sec_edgar
from pyrnova.sources.sec_edgar import (
    BODY_ENDPOINTS,
    DISCOVERY_ENDPOINTS,
    EdgarClient,
    SEC_ACCESS_ORDER,
    accession_dedupe,
    full_submission_url,
)

ACCESSION = "0001571123-26-000029"
CIK = "0001571123"


def test_declared_identity_is_configured_never_fabricated(monkeypatch):
    for var in ("PYRNOVA_SEC_USER_AGENT", "PYRNOVA_SEC_CONTACT_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(config, "_local_secret", lambda name: "")
    # No configuration -> empty UA, and a live call fails cleanly with an explanation (no anon identity).
    assert config.sec_user_agent() == ""
    with pytest.raises(RuntimeError) as exc:
        EdgarClient(user_agent=None)._headers()
    assert "PYRNOVA_SEC_CONTACT_EMAIL" in str(exc.value)
    # A configured contact email composes a proper declared User-Agent.
    monkeypatch.setenv("PYRNOVA_SEC_CONTACT_EMAIL", "ops@example.com")
    ua = config.sec_user_agent()
    assert "example.com" in ua and config.SEC_PRODUCT_IDENTITY.split("/")[0] in ua
    assert EdgarClient(user_agent=None)._headers()["User-Agent"] == ua
    # An explicit override wins verbatim.
    monkeypatch.setenv("PYRNOVA_SEC_USER_AGENT", "Custom/1.0 (me@example.org)")
    assert config.sec_user_agent() == "Custom/1.0 (me@example.org)"


def test_access_order_and_discovery_vs_body_are_declared():
    assert SEC_ACCESS_ORDER[0].startswith("data.sec.gov")
    assert "curated extract" in SEC_ACCESS_ORDER[-1]
    # Discovery and full-body acquisition are distinct tiers (an entity in metadata is not a body pull).
    assert DISCOVERY_ENDPOINTS == {"submissions", "companyfacts"}
    assert "full_submission" in BODY_ENDPOINTS and not (DISCOVERY_ENDPOINTS & BODY_ENDPOINTS)


def test_full_submission_url_is_the_raw_artifact():
    url = full_submission_url(CIK, ACCESSION)
    assert url == "https://www.sec.gov/Archives/edgar/data/1571123/000157112326000029/0001571123-26-000029.txt"
    assert full_submission_url(CIK, None) is None
    assert full_submission_url(CIK, "not-an-accession") is None


def test_accession_dedupe_skips_archived_and_preserves_amendments():
    archived = {ACCESSION: {"content_hash": "abc", "first_observed_at": "2026-03-16"}}
    # Already archived -> never retrieved again in normal operation.
    d = accession_dedupe(ACCESSION, "10-K", archived)
    assert d["retrieve"] is False and d["reason"] == "already_archived_accession_dedupe"
    # A brand-new accession is retrieved.
    d2 = accession_dedupe("0001571123-26-000099", "10-Q", archived)
    assert d2["retrieve"] is True and d2["is_amendment"] is False
    # An amendment is a NEW artifact (history not rewritten): retrieved and flagged.
    d3 = accession_dedupe("0001571123-26-000100", "10-K/A", archived)
    assert d3["retrieve"] is True and d3["is_amendment"] is True
    assert d3["reason"] == "new_amendment_preserves_history"


def test_403_is_terminal_no_retry_loop_and_spend_is_recorded(monkeypatch):
    calls = {"n": 0}

    def fake_get_json(url, params=None, **kwargs):
        calls["n"] += 1
        return 403, b"", None

    monkeypatch.setattr(http, "get_json", fake_get_json)
    client = EdgarClient(user_agent="Pyrnova/test (ops@example.com)", mode="live-safe", request_budget=5)
    with pytest.raises(RuntimeError) as exc:
        client.submissions(CIK)
    assert "HTTP 403" in str(exc.value)
    # Exactly one call: the client itself never loops/retries a 403 (a terminal, not transient, failure).
    assert calls["n"] == 1
    # The spent call is accounted for (budget/accounting reflects it) — 403 does not vanish silently.
    snap = client.metrics
    assert snap.get("calls_made", 0) >= 1


def test_429_throttle_sets_cooldown_distinct_from_terminal_403(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: (429, b"", None))
    client = EdgarClient(user_agent="Pyrnova/test (ops@example.com)", mode="live-safe",
                         request_budget=5, cooldown_seconds=30.0)
    with pytest.raises(sec_edgar.EdgarRateLimitError):
        client.submissions(CIK)
    # A throttle installs a concrete next-permitted-poll cooldown (backoff), unlike a terminal 403.
    assert client.next_permitted_poll is not None


def test_unapproved_filing_document_denied_before_transport(monkeypatch):
    from pyrnova.sources.rights import SourceRightsDenied
    monkeypatch.setattr(http, "get_bytes", lambda *a, **k: pytest.fail("prohibited transport called"))
    client = EdgarClient(user_agent="Pyrnova/test (ops@example.com)", mode="live-safe")
    with pytest.raises(SourceRightsDenied):
        client.fetch_full_submission(CIK, ACCESSION)
