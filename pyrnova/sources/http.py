"""Minimal HTTP helper. Honors environment proxy + CA bundle (REQUESTS_CA_BUNDLE / HTTPS_PROXY)."""

from __future__ import annotations

import json
from typing import Any, Optional

_TIMEOUT = 60


def _authorize(method: str, url: str, source_id: str | None) -> None:
    if not source_id:
        from .rights import SourceRightsDenied
        raise SourceRightsDenied("HTTP source_id is required", reason_code="SOURCE_ID_REQUIRED")
    from .rights import authorize_request
    authorize_request(source_id, method, url)


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


def post_json_response(url: str, payload: dict, *, headers: Optional[dict] = None,
                       timeout: int = _TIMEOUT, source_id: str | None = None) -> tuple[int, bytes, Any, dict]:
    """POST JSON and include response headers for transport policy such as Retry-After."""
    _authorize("POST", url, source_id)
    sess = _session()
    resp = sess.post(url, json=payload, headers=headers or {}, timeout=timeout, allow_redirects=False)
    raw = resp.content
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = None
    return resp.status_code, raw, parsed, dict(resp.headers)


def post_json(url: str, payload: dict, *, headers: Optional[dict] = None, timeout: int = _TIMEOUT, source_id: str | None = None) -> tuple[int, bytes, Any]:
    """POST json, return (status_code, raw_bytes, parsed_json_or_None). Raw bytes are what we archive."""
    status, raw, parsed, _ = post_json_response(url, payload, headers=headers, timeout=timeout, source_id=source_id)
    return status, raw, parsed


def get_json(url: str, params: dict, *, headers: Optional[dict] = None, timeout: int = _TIMEOUT, source_id: str | None = None) -> tuple[int, bytes, Any]:
    _authorize("GET", url, source_id)
    sess = _session()
    resp = sess.get(url, params=params, headers=headers or {}, timeout=timeout, allow_redirects=False)
    raw = resp.content
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = None
    return resp.status_code, raw, parsed


def get_bytes(url: str, params: Optional[dict] = None, *, headers: Optional[dict] = None,
              timeout: int = _TIMEOUT, source_id: str | None = None) -> tuple[int, bytes]:
    """GET arbitrary source bytes for archival (CSV/PDF/etc.) without decoding or mutation."""
    _authorize("GET", url, source_id)
    sess = _session()
    resp = sess.get(url, params=params or {}, headers=headers or {}, timeout=timeout, allow_redirects=False)
    return resp.status_code, resp.content


def get_bytes_response(url: str, params: Optional[dict] = None, *, headers: Optional[dict] = None,
                       timeout: int = _TIMEOUT, source_id: str | None = None) -> tuple[int, bytes, dict]:
    """GET bytes and include response headers for transport policy such as Retry-After."""
    _authorize("GET", url, source_id)
    sess = _session()
    resp = sess.get(url, params=params or {}, headers=headers or {}, timeout=timeout, allow_redirects=False)
    return resp.status_code, resp.content, dict(resp.headers)
