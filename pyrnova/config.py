"""Runtime configuration, read from environment (see .env.example).

No secrets are hard-coded. Cloud storage and Postgres are optional; absence forces the local
filesystem / JSONL development path so work continues offline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _local_secret(name: str) -> str:
    """Read one value from the repository-local, gitignored ``.env`` file."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    prefix = f"{name}="
    for raw_line in lines:
        line = raw_line.strip()
        if not line.startswith(prefix):
            continue
        value = line[len(prefix):].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value
    return ""


def _sam_api_key() -> str:
    """Prefer an explicit process value, then Pyrnova's private local file."""
    return _get("SAM_API_KEY") or _local_secret("SAM_API_KEY")


# SEC EDGAR / data.sec.gov require a declared, contact-bearing User-Agent (SEC access policy). Pyrnova
# NEVER hardcodes a contact address or invents one: the contact email is read from configuration
# (process env or the gitignored .env), and live SEC acquisition fails cleanly with an explanation when
# it is absent. This is a declared identity, not a credential — it is safe to send in the request header,
# but it is still read from config so no owner address is baked into the tree.
SEC_PRODUCT_IDENTITY = "Pyrnova/Capture-Radar"


def _sec_contact_email() -> str:
    return _get("PYRNOVA_SEC_CONTACT_EMAIL") or _local_secret("PYRNOVA_SEC_CONTACT_EMAIL")


def sec_user_agent() -> str:
    """The configured SEC ``User-Agent``, or ``""`` when no contact identity is configured.

    Preference order: an explicit ``PYRNOVA_SEC_USER_AGENT`` (used verbatim), else
    ``<product> (<configured contact email>)``. Returns ``""`` — never a fabricated address — when
    nothing is configured, so a live SEC path can fail cleanly and explain the fix rather than send an
    anonymous or invented identity.
    """
    explicit = _get("PYRNOVA_SEC_USER_AGENT")
    if explicit:
        return explicit
    email = _sec_contact_email()
    if email:
        return f"{SEC_PRODUCT_IDENTITY} ({email})"
    return ""


@dataclass(frozen=True)
class Config:
    sam_api_key: str
    archive_backend: str
    archive_dir: Path
    s3_endpoint_url: str
    s3_bucket: str
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_region: str
    database_url: str
    state_dir: Path
    out_dir: Path

    @property
    def has_sam(self) -> bool:
        return bool(self.sam_api_key)

    @property
    def uses_s3(self) -> bool:
        return self.archive_backend.lower() == "s3"


def load_config() -> Config:
    return Config(
        sam_api_key=_sam_api_key(),
        archive_backend=_get("PYRNOVA_ARCHIVE_BACKEND", "local"),
        archive_dir=Path(_get("PYRNOVA_ARCHIVE_DIR", "./var/archive")),
        s3_endpoint_url=_get("PYRNOVA_S3_ENDPOINT_URL"),
        s3_bucket=_get("PYRNOVA_S3_BUCKET"),
        s3_access_key_id=_get("PYRNOVA_S3_ACCESS_KEY_ID"),
        s3_secret_access_key=_get("PYRNOVA_S3_SECRET_ACCESS_KEY"),
        s3_region=_get("PYRNOVA_S3_REGION", "auto"),
        database_url=_get("PYRNOVA_DATABASE_URL"),
        state_dir=Path(_get("PYRNOVA_STATE_DIR", "./var/state")),
        out_dir=Path(_get("PYRNOVA_OUT_DIR", "./out")),
    )


def _bool(name: str, default: bool) -> bool:
    raw = _get(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    raw = _get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    raw = _get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class AlertConfig:
    """Operator-alert + dead-man configuration. All values come from the environment / gitignored ``.env``;
    no credentials are ever baked into the tree. When ``recipients``/``sender``/``smtp_host`` are absent the
    transport is explicitly *disabled* (alerts still persist durably; delivery is reported not_configured)."""

    enabled: bool
    recipients: tuple[str, ...]
    sender: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    max_attempts: int
    alert_state_dir: Path
    heartbeat_dir: Path
    deadman_component: str
    deadman_max_silence_seconds: float

    @property
    def delivery_configured(self) -> bool:
        """True only when a real sending identity exists (host + sender + at least one recipient)."""
        return bool(self.smtp_host) and bool(self.sender) and bool(self.recipients)


def load_alert_config() -> AlertConfig:
    recipients_raw = _get("PYRNOVA_ALERT_RECIPIENTS")
    recipients = tuple(r.strip() for r in recipients_raw.split(",") if r.strip())
    return AlertConfig(
        enabled=_bool("PYRNOVA_ALERT_ENABLED", True),
        recipients=recipients,
        sender=_get("PYRNOVA_ALERT_SENDER"),
        smtp_host=_get("PYRNOVA_SMTP_HOST"),
        smtp_port=_int("PYRNOVA_SMTP_PORT", 587),
        smtp_username=_get("PYRNOVA_SMTP_USERNAME"),
        # Password is a credential: prefer process env, then the gitignored local .env; never the tree.
        smtp_password=_get("PYRNOVA_SMTP_PASSWORD") or _local_secret("PYRNOVA_SMTP_PASSWORD"),
        smtp_use_tls=_bool("PYRNOVA_SMTP_USE_TLS", True),
        max_attempts=_int("PYRNOVA_ALERT_MAX_ATTEMPTS", 3),
        alert_state_dir=Path(_get("PYRNOVA_ALERT_STATE_DIR", "./var/alerts")),
        heartbeat_dir=Path(_get("PYRNOVA_HEARTBEAT_DIR", "./var/heartbeat")),
        deadman_component=_get("PYRNOVA_DEADMAN_COMPONENT", "live_ops"),
        deadman_max_silence_seconds=_float("PYRNOVA_DEADMAN_MAX_SILENCE_SECONDS", 900.0),
    )


@dataclass(frozen=True)
class CustomerDeliveryConfig:
    """B4.3 — customer decision-brief email delivery configuration.

    Distinct from :class:`AlertConfig` (operator alerts are a separate concern): customer-delivery
    recipients are NOT read from configuration — they are operator-authorized per tenant at runtime — so
    only the sending identity + SMTP transport come from here. All values come from the environment /
    gitignored ``.env``; no credentials are ever baked into the tree. When ``smtp_host`` is absent the
    transport is explicitly disabled (a send is recorded FAILED, never fabricated as delivered)."""

    sender: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    max_attempts: int

    @property
    def transport_configured(self) -> bool:
        """True only when a real SMTP sending endpoint exists (host + sender)."""
        return bool(self.smtp_host) and bool(self.sender)


def load_customer_delivery_config() -> CustomerDeliveryConfig:
    """Resolve customer-delivery config from the environment (SMTP transport shared with alerts; a
    dedicated delivery sender). Never returns fabricated credentials."""
    return CustomerDeliveryConfig(
        sender=_get("PYRNOVA_DELIVERY_SENDER", "briefs@pyrnova"),
        smtp_host=_get("PYRNOVA_SMTP_HOST"),
        smtp_port=_int("PYRNOVA_SMTP_PORT", 587),
        smtp_username=_get("PYRNOVA_SMTP_USERNAME"),
        # Password is a credential: prefer process env, then the gitignored local .env; never the tree.
        smtp_password=_get("PYRNOVA_SMTP_PASSWORD") or _local_secret("PYRNOVA_SMTP_PASSWORD"),
        smtp_use_tls=_bool("PYRNOVA_SMTP_USE_TLS", True),
        max_attempts=_int("PYRNOVA_DELIVERY_MAX_ATTEMPTS", 3),
    )


def build_customer_delivery_transport(config: "CustomerDeliveryConfig | None" = None):
    """Return the production customer-delivery transport resolved from configuration.

    A real :class:`~pyrnova.alerts.SMTPEmailTransport` when SMTP is configured, else an explicit
    :class:`~pyrnova.alerts.DisabledTransport` (a missing sending identity is NEVER treated as a delivered
    mail — the delivery is recorded FAILED). This is the single production wiring seam for B4.3."""
    from .alerts import DisabledTransport, SMTPEmailTransport
    config = config or load_customer_delivery_config()
    if config.transport_configured:
        return SMTPEmailTransport(host=config.smtp_host, port=config.smtp_port,
                                  username=config.smtp_username, password=config.smtp_password,
                                  use_tls=config.smtp_use_tls)
    return DisabledTransport(reason="customer delivery email transport not configured")
