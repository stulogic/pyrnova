"""Minimal HTTP helper. Honors environment proxy + CA bundle (REQUESTS_CA_BUNDLE / HTTPS_PROXY)."""

from __future__ import annotations

import json
from typing import Any, Optional

_TIMEOUT = 60


def _session():
    try:
        import requests
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The 'requests' package is required for live runs but is not installed.\n"
            "Fix (from the repo root, inside your venv):\n"
            "    pip install -r requirements.txt\n"
            "  or:  pip install requests\n"
            "  or:  pip install --upgrade pip && pip install -e ."
        ) from exc

    return requests.Session()


def post_json(url: str, payload: dict, *, headers: Optional[dict] = None, timeout: int = _TIMEOUT) -> tuple[int, bytes, Any]:
    """POST json, return (status_code, raw_bytes, parsed_json_or_None). Raw bytes are what we archive."""
    sess = _session()
    resp = sess.post(url, json=payload, headers=headers or {}, timeout=timeout)
    raw = resp.content
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = None
    return resp.status_code, raw, parsed


def get_json(url: str, params: dict, *, headers: Optional[dict] = None, timeout: int = _TIMEOUT) -> tuple[int, bytes, Any]:
    sess = _session()
    resp = sess.get(url, params=params, headers=headers or {}, timeout=timeout)
    raw = resp.content
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = None
    return resp.status_code, raw, parsed


def get_bytes(url: str, params: Optional[dict] = None, *, headers: Optional[dict] = None,
              timeout: int = _TIMEOUT) -> tuple[int, bytes]:
    """GET arbitrary source bytes for archival (CSV/PDF/etc.) without decoding or mutation."""
    sess = _session()
    resp = sess.get(url, params=params or {}, headers=headers or {}, timeout=timeout)
    return resp.status_code, resp.content
