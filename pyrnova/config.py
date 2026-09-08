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
