"""Minimal HTTP helper. Honors environment proxy + CA bundle (REQUESTS_CA_BUNDLE / HTTPS_PROXY)."""

from __future__ import annotations

import json
from typing import Any, Optional

_TIMEOUT = 60


def _session():
    import requests

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
