"""B4.7 — production security posture guards.

Pins the launch-relevant control invariants asserted in docs/operations/PRODUCTION_SECURITY_MATRIX.md so
they cannot silently regress: a non-local bind always enforces auth and never exposes operator surfaces;
enabling auth cannot be undone remotely; and secrets are never fabricated when unset.
"""

from __future__ import annotations

from pyrnova import config
from pyrnova.ops_server import AccessPolicy
from pyrnova.state import StateStore


def test_non_local_bind_forces_auth_and_hides_operator(tmp_path):
    store = StateStore(tmp_path / "state")
    policy = AccessPolicy.decide("0.0.0.0", store)
    assert policy.require_auth is True       # cannot be turned off for a remote bind
    assert policy.expose_operator is False   # operator/console surface not exposed remotely


def test_local_bind_exposes_operator_but_may_still_require_auth(tmp_path):
    store = StateStore(tmp_path / "state")
    policy = AccessPolicy.decide("127.0.0.1", store)
    assert policy.expose_operator is True    # local dev convenience only


def test_env_flag_forces_auth_even_on_local_bind(tmp_path, monkeypatch):
    store = StateStore(tmp_path / "state")
    monkeypatch.setenv("PYRNOVA_REQUIRE_AUTH", "1")
    assert AccessPolicy.decide("127.0.0.1", store).require_auth is True


def test_provisioned_credential_forces_auth_on_local_bind(tmp_path):
    from pyrnova import access
    store = StateStore(tmp_path / "state")
    access.create_credential(store, customer_id="torch", actor_label="t")
    # Once any credential exists, auth is enforced even on a local bind (no silent open posture).
    assert AccessPolicy.decide("127.0.0.1", store).require_auth is True


def test_unset_delivery_secret_is_never_fabricated(monkeypatch):
    for k in ("PYRNOVA_SMTP_HOST", "PYRNOVA_SMTP_PASSWORD", "PYRNOVA_DELIVERY_SENDER"):
        monkeypatch.delenv(k, raising=False)
    cfg = config.load_customer_delivery_config()
    assert cfg.smtp_password == ""            # no fabricated credential
    assert cfg.transport_configured is False  # no host => explicitly not configured
