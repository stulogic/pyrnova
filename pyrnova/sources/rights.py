"""Canonical source-rights policy gates.

The registry owns source policy.  This module owns the reusable checks at transport,
storage, customer-display, and model-call boundaries.  Unknown sources and unknown
rights facts fail closed; callers cannot turn a URL or a classification label into
permission.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

from .registry import (
    RightsClass,
    RightsState,
    SourcePolicy,
    StorageMode,
    get_spec,
)


class SourceRightsError(RuntimeError):
    """Base error for a denied source operation."""


class SourceRightsDenied(SourceRightsError):
    def __init__(self, message: str, *, reason_code: str = "RIGHTS_DENIED"):
        super().__init__(message)
        self.reason_code = reason_code


class ProhibitedSourcePayload(SourceRightsDenied):
    pass


_LEGACY_KEYS = re.compile(
    r"(?:^|_)(?:duns|dnb|dun(?:s|ning)|parent[_-]?duns|parent[_-]?dnb|legacy[_-]?duns)(?:$|_)",
    re.IGNORECASE,
)
_CLASSIFICATION_KEYS = re.compile(
    r"(?:classification|handling|caveat|dissemination|security[_-]?mark|distribution)",
    re.IGNORECASE,
)
_RESTRICTED_MARKERS = re.compile(
    r"\b(?:CUI|CONTROLLED\s+UNCLASSIFIED|FOUO|ITAR|CLASSIFIED|SECRET|TOP\s+SECRET|NOFORN)\b",
    re.IGNORECASE,
)
_RAW_KEYS = re.compile(
    r"(?:^|_)(?:raw|raw_response|fulltext|full_text|body|document|html|source_content|content_bytes)(?:$|_)",
    re.IGNORECASE,
)
_SOURCE_PROSE_KEYS = {
    "title", "event_summary", "summary", "description", "detail", "mechanism", "consequence",
    "reason", "note", "notes", "text", "excerpt", "explanation", "rationale", "fulltext",
}
_DERIVED_KEYS = {"assessment", "uncertainty", "propagation", "materiality", "confidence", "model_explanation"}
_ALLOWED_FACT_KEYS = {
    "id", "source_id", "source_ref", "source_url", "url", "type", "record_kind", "status", "stage",
    "title", "name", "agency", "program", "program_key", "notice_id", "solicitation_number", "award_id",
    "uei", "cik", "ticker", "form", "accession_number", "date", "published_at", "posted_at", "filed_at",
    "observed_at", "available_at", "period_start", "period_end", "fiscal_year", "fiscal_period", "amount",
    "amount_usd", "value", "value_usd", "naics", "psc", "signal", "content_sha256", "original_content_sha256",
}
_ALLOWED_META_KEYS = {
    "source_id", "source_ref", "source_url", "request_fingerprint", "fetched_at", "retrieved_at", "media_type",
    "content_sha256", "original_content_sha256", "source_policy_version", "representation", "published_at",
}
_MODEL_OUTER_KEYS = {
    "representation", "normalized", "derived", "metadata", "source_url", "excerpt", "attribution",
    "source_ids", "source_id", "evidence_ids", "content_sha256", "original_content_sha256", "id", "source_ref",
}
_MODEL_DERIVED_KEYS = {"id", "source_ref", "source_ids", "evidence_ids", "assessment_code", "confidence", "materiality"}
_KEEP_REF_KEYS = {
    "id", "record_id", "material_change_id", "customer_id", "source_id", "source_ids", "evidence_ids",
    "refs", "provenance", "source_refs", "archive_hash", "content_sha256", "available_at", "observed_at",
    "event_time", "valid_from", "valid_to", "source_rights", "subject_ref", "program", "catalyst_id",
    "source_ref", "root_change_id", "policy_version",
}
_SOURCE_ALIASES = {
    "ofac": "sanctions_ofac",
    "usaspending_v2": "usaspending",
    "usaspending_subawards": "usaspending",
    "sam": "sam_opportunities",
}
_EVIDENCE_SOURCE_PREFIXES = {
    "ofac", "usaspending", "usaspending_v2", "sam", "sam_opportunities",
    "federal_register", "sec", "sec_edgar", "grants_gov", "sbir", "acquisition_forecast",
}


@dataclass(frozen=True)
class PayloadScreen:
    allowed: bool
    reason: str = ""
    path: str = ""


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    reason: str
    source_ids: tuple[str, ...] = ()
    policy_versions: tuple[str, ...] = ()
    reason_code: str = ""


def source_policy(source_id: str) -> SourcePolicy:
    """Resolve only the registry-owned policy; unknown/unprofiled is denied."""
    try:
        spec = get_spec(str(source_id))
    except KeyError as exc:
        raise SourceRightsDenied(f"unknown source policy: {source_id!r}", reason_code="UNKNOWN_SOURCE") from exc
    if spec.policy is None or spec.policy.identity != spec.id:
        raise SourceRightsDenied(f"source has no reviewed rights profile: {source_id!r}", reason_code="UNPROFILED_SOURCE")
    return spec.policy


def _parse_date(value: str, field: str) -> datetime | None:
    if value in (None, "", "unknown", "UNKNOWN"):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SourceRightsDenied(f"invalid {field}", reason_code="INVALID_POLICY_DATE") from exc
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _current_permission(policy: SourcePolicy, *, operation: str) -> None:
    try:
        state = RightsState(policy.state)
        rights_class = RightsClass(policy.rights_class)
        storage = StorageMode(policy.raw_storage)
    except ValueError as exc:
        raise SourceRightsDenied("invalid source policy enum", reason_code="INVALID_POLICY") from exc
    if rights_class in {RightsClass.RED, RightsClass.BLACK}:
        raise SourceRightsDenied(f"{rights_class.value} source is denied", reason_code=f"CLASS_{rights_class.value}")
    if rights_class is RightsClass.AMBER:
        raise SourceRightsDenied("AMBER source is not approved for automated ingest/display/model use", reason_code="AMBER_RESTRICTED")
    if (state is RightsState.INGEST_DISABLED and operation in {"customer display", "derived use"}
            or state is RightsState.DISPLAY_DISABLED and operation == "derived use"):
        # Explicit historical/customer display permission is independent of ingest state.
        pass
    elif state is not RightsState.CURRENTLY_APPROVED:
        code = {RightsState.DISPLAY_DISABLED: "DISPLAY_DISABLED"}.get(state, f"STATE_{state.value}")
        raise SourceRightsDenied(f"source policy state {state.value} denies {operation}", reason_code=code)
    due = _parse_date(policy.review_due_at, "review_due_at")
    if due is not None and due <= datetime.now(timezone.utc):
        raise SourceRightsDenied("source policy review is due", reason_code="REVIEW_DUE")
    if policy.review_required:
        _parse_date(policy.reviewed_at, "reviewed_at")
        if policy.reviewed_at in (None, "", "unknown", "UNKNOWN") and not policy.basis.lower().startswith("owner-approved"):
            raise SourceRightsDenied("policy review date is unknown", reason_code="REVIEW_DATE_UNKNOWN")
    if policy.licence_required is True:
        if policy.licence in (None, "", "unknown", "UNKNOWN") or policy.licence_reference in (None, "", "unknown", "UNKNOWN"):
            raise SourceRightsDenied("required licence facts are unknown", reason_code="LICENCE_UNKNOWN")
        expiry = _parse_date(policy.licence_valid_until, "licence_valid_until")
        if expiry is None:
            raise SourceRightsDenied("licence expiry is unknown", reason_code="LICENCE_EXPIRY_UNKNOWN")
        if expiry <= datetime.now(timezone.utc):
            raise SourceRightsDenied("licence has expired", reason_code="LICENSE_EXPIRED")
    elif policy.licence_required is not False:
        # A missing licence decision is unknown; it cannot authorize use.
        raise SourceRightsDenied("licence requirement is unknown", reason_code="LICENCE_UNKNOWN")
    if policy.commercial_use != "owner_approved_constrained_structured_use":
        raise SourceRightsDenied("commercial use is not an approved constrained scope", reason_code="COMMERCIAL_USE_DENIED")
    if policy.automated_access not in {"conditional_reviewed_endpoint", "explicit_domain_profile"}:
        raise SourceRightsDenied("automated access is not an approved constrained scope", reason_code="AUTOMATION_DENIED")


def authorize_request(source_id: str, method: str, url: str) -> RightsDecision:
    """Authorize a concrete request against the registry profile before transport.

    Host, scheme, method, and path all come from the canonical profile.  A redirect is
    not an authorized second request; callers must use a separately allowlisted URL.
    """
    policy = source_policy(source_id)
    _current_permission(policy, operation="ingest")
    parts = urlsplit(str(url))
    if parts.scheme.lower() != "https" or not parts.hostname or parts.username or parts.password:
        raise SourceRightsDenied("source request must use credential-free HTTPS URL")
    host = parts.hostname.lower().rstrip(".")
    allowed_hosts = {h.lower().rstrip(".") for h in policy.allowed_hosts}
    if host not in allowed_hosts:
        raise SourceRightsDenied(f"host {host!r} is outside source policy")
    verb = str(method).upper()
    if verb not in {m.upper() for m in policy.allowed_methods}:
        raise SourceRightsDenied(f"method {verb!r} is outside source policy")
    path = parts.path or "/"
    if not any(path.startswith(prefix) for prefix in policy.allowed_path_prefixes):
        raise SourceRightsDenied(f"path {path!r} is outside source policy")
    return RightsDecision(True, "authorized reviewed endpoint", (str(source_id),), (policy.policy_version,), "ALLOWED")


def authorize_source_url(source_id: str, url: str) -> RightsDecision:
    """Validate a provenance URL without authorizing retrieval.

    A reviewed public object URL may be retained as attribution even when the
    transport profile deliberately permits only an official structured API.
    Retrieval callers must use :func:`authorize_request`.
    """
    policy = source_policy(source_id)
    if _url_allowed_for_policy(policy, url, reference=True):
        return RightsDecision(True, "authorized reviewed provenance reference", (str(source_id),), (policy.policy_version,), "ALLOWED_REFERENCE")
    if not policy.allowed_methods:
        raise SourceRightsDenied("source policy has no allowed method", reason_code="METHOD_SCOPE_UNKNOWN")
    return authorize_request(source_id, policy.allowed_methods[0], url)


def _walk(value: Any, path: str = ""):
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            yield str(key), item, child
            yield from _walk(item, child)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            child = f"{path}[{index}]"
            yield from _walk(item, child)


def screen_payload(value: Any) -> PayloadScreen:
    """Reject D&B legacy identifiers and explicit sensitive classification markers.

    Ordinary prose containing a token such as ``CUI`` is not enough to classify data;
    the marker must occur in a classification/handling field.  Legacy identifier keys
    are prohibited regardless of their value and are checked recursively.
    """
    for key, item, path in _walk(value):
        field = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
        field = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", field).replace("-", "_")
        if _LEGACY_KEYS.search(field):
            return PayloadScreen(False, "prohibited legacy D&B identifier field", path)
        if _CLASSIFICATION_KEYS.search(key) and isinstance(item, str) and _RESTRICTED_MARKERS.search(item):
            return PayloadScreen(False, "explicit restricted classification marker", path)
    return PayloadScreen(True)


def validate_source_payload(source_id: str, value: Any) -> Any:
    screen = screen_payload(value)
    if not screen.allowed:
        raise ProhibitedSourcePayload(f"{screen.reason} at {screen.path}")
    return value


def _screen_bytes(content: bytes) -> None:
    """Screen non-JSON bytes too; a hash-only fallback cannot hide prohibited fields."""
    text = bytes(content or b"").decode("utf-8", errors="ignore")
    if bytes(content or b"").lstrip().lower().startswith((b"<html", b"<!doctype html", b"%pdf")):
        raise ProhibitedSourcePayload("HTML/PDF source document is outside structured policy")
    # Match field/header positions only; a normal fact or prose mentioning a legacy
    # identifier name is not itself a prohibited field.
    if re.search(r"(?i)(?:[\"']?(?:parent[_-]?duns|duns|dnb|legacy[_-]?duns)[\"']?\s*[:=])", text):
        raise ProhibitedSourcePayload("prohibited legacy D&B identifier in source bytes")
    if re.search(r"(?i)(?:classification|handling|caveat|dissemination|security[_-]?mark)\s*[=:,]\s*[\"']?(?:CUI|FOUO|ITAR|CLASSIFIED|SECRET|NOFORN)\b", text):
        raise ProhibitedSourcePayload("explicit restricted classification marker in source bytes")


def _normalized_only(value: Any, path: str = "", *, metadata: bool = False) -> Any:
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            name = str(key)
            allowed = _ALLOWED_META_KEYS if metadata else _ALLOWED_FACT_KEYS
            if name not in allowed:
                raise SourceRightsDenied(f"field {path + '.' if path else ''}{name} is not an allowlisted normalized field", reason_code="NORMALIZED_FIELD_DENIED")
            if _RAW_KEYS.search(name) or name.casefold() in {"raw", "fulltext", "body", "document", "html"}:
                raise SourceRightsDenied(f"raw/fulltext field is not allowed in normalized storage: {path}.{name}", reason_code="RAW_FIELD_DENIED")
            if name.casefold() in {"source_content", "content", "content_bytes"}:
                raise SourceRightsDenied(f"source content field is not allowed in normalized storage: {path}.{name}", reason_code="RAW_FIELD_DENIED")
            out[name] = _normalized_only(item, f"{path}.{name}" if path else name, metadata=metadata)
        return out
    if isinstance(value, (list, tuple)):
        return [_normalized_only(item, f"{path}[{i}]", metadata=metadata) for i, item in enumerate(value)]
    if isinstance(value, str):
        if len(value) > 512 or re.search(r"<\/?[A-Za-z][^>]*>", value):
            raise SourceRightsDenied(f"unbounded or markup value at {path}", reason_code="NORMALIZED_VALUE_DENIED")
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    raise SourceRightsDenied(f"unsupported normalized value at {path}")


def representation_for_storage(
    source_id: str,
    content: bytes,
    *,
    normalized: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    source_url: str | None = None,
    excerpt: str | None = None,
    attribution: str | None = None,
) -> tuple[bytes, dict]:
    """Return the only representation allowed by the source's storage policy."""
    policy = source_policy(source_id)
    _current_permission(policy, operation="ingest")
    if RightsClass(policy.rights_class) not in {RightsClass.GREEN, RightsClass.GREEN_WITH_CONDITIONS}:
        raise SourceRightsDenied("source class does not permit durable storage", reason_code="STORAGE_CLASS_DENIED")
    _screen_bytes(content)
    validate_source_payload(source_id, _json_or_hash(content))
    if source_url:
        authorize_source_url(source_id, source_url)
    digest = hashlib.sha256(content).hexdigest()
    if policy.raw_storage is StorageMode.RAW_ALLOWED:
        if policy.source_type.startswith("structured_"):
            try:
                json.loads(content)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise SourceRightsDenied("structured source response is not JSON", reason_code="STRUCTURED_PAYLOAD_DENIED") from exc
        return content, {"representation": StorageMode.RAW_ALLOWED.value, "content_sha256": digest,
                         "source_policy_version": policy.policy_version}
    if policy.raw_storage is StorageMode.NO_STORAGE:
        raise SourceRightsDenied("source policy forbids durable storage")
    if not isinstance(normalized, Mapping):
        raise SourceRightsDenied("NORMALIZED_ONLY requires an explicit normalized mapping")
    for candidate, label in ((normalized, "normalized"), (metadata or {}, "metadata")):
        screen = screen_payload(candidate)
        if not screen.allowed:
            raise ProhibitedSourcePayload(f"{screen.reason} in {label} at {screen.path}")
    normalized_safe = _normalized_only(copy.deepcopy(dict(normalized)))
    metadata_safe = _normalized_only(copy.deepcopy(dict(metadata or {})), metadata=True)
    if excerpt:
        if not str(policy.excerpt_use).startswith("limited_excerpt"):
            raise SourceRightsDenied("excerpt use is not permitted", reason_code="EXCERPT_DENIED")
        if not source_url or not attribution or not str(attribution).strip():
            raise SourceRightsDenied("excerpt requires direct URL and attribution", reason_code="EXCERPT_ATTRIBUTION_REQUIRED")
        authorize_source_url(source_id, source_url)
        words = excerpt.split()
        if len(words) > policy.max_excerpt_words:
            raise SourceRightsDenied("excerpt exceeds policy word limit", reason_code="EXCERPT_LIMIT")
        excerpt_safe = " ".join(words)
    else:
        excerpt_safe = None
    if excerpt_safe and not attribution and not policy.attribution_text:
        raise SourceRightsDenied("excerpt requires attribution", reason_code="EXCERPT_ATTRIBUTION_REQUIRED")
    stored = {
        "normalized": normalized_safe,
        "metadata": metadata_safe,
        "original_content_sha256": digest,
        "source_url": source_url,
        "excerpt": excerpt_safe,
        "attribution": attribution or policy.attribution_text or None,
        "source_policy_version": policy.policy_version,
        "representation": StorageMode.NORMALIZED_ONLY.value,
    }
    return json.dumps(stored, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(), stored


def _collect_source_ids(value: Any, out: set[str] | None = None) -> set[str]:
    if out is None:
        out = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = str(key).casefold()
            if name in {"source_id", "sourceid"} and isinstance(item, str) and item.strip():
                out.add(_SOURCE_ALIASES.get(item.strip(), item.strip()))
            elif name == "source" and isinstance(item, str) and item.strip():
                out.add(_SOURCE_ALIASES.get(item.strip(), item.strip()))
            elif name in {"source_ids", "sources"} and isinstance(item, (list, tuple, set)):
                out.update(_SOURCE_ALIASES.get(str(v).strip(), str(v).strip()) for v in item if isinstance(v, str) and v.strip())
            elif name == "evidence_ids" and isinstance(item, (list, tuple, set)):
                aliases = {"ofac": "sanctions_ofac", "usaspending_v2": "usaspending", "sam": "sam_opportunities"}
                for evidence_id in item:
                    if isinstance(evidence_id, str) and ":" in evidence_id:
                        prefix = evidence_id.split(":", 1)[0]
                        if prefix in _EVIDENCE_SOURCE_PREFIXES:
                            out.add(_SOURCE_ALIASES.get(aliases.get(prefix, prefix), aliases.get(prefix, prefix)))
            _collect_source_ids(item, out)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _collect_source_ids(item, out)
    return out


def _source_prose_present(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in _SOURCE_PROSE_KEYS and item not in (None, "", [], {}):
                return True
            if _source_prose_present(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_source_prose_present(item) for item in value)
    return False


def _derived_projection(value: Any) -> bool:
    """Recognize only the canonical structured Pyrnova projection envelopes."""
    if not isinstance(value, Mapping):
        return False
    material_keys = {
        "id", "kind", "title", "disposition", "observed", "assessment", "relevance", "evidence",
        "uncertainty", "lifecycle_state", "outcome_state", "propagation", "refs", "provenance", "available_at",
        "review", "investigation", "first_seen", "customer_overlay",
    }
    version_keys = {
        "customer_id", "material_change_id", "source_kind", "content_version", "content_hash", "disposition",
        "relevance_basis", "relevance_reasons", "assessment_snapshot", "outcome_state", "outcome_ref",
        "intelligence_observed_at", "first_relevant_at", "delivered_at", "last_updated_at", "source_refs",
        "change_kind", "valid_from", "ingest_run_id", "schema_version", "record_id", "review",
    }
    if isinstance(value.get("assessment"), Mapping) and isinstance(value.get("observed"), Mapping):
        return set(value).issubset(material_keys) and isinstance(value.get("evidence"), Mapping)
    if isinstance(value.get("assessment_snapshot"), Mapping) and isinstance(value.get("source_refs"), Mapping):
        return set(value).issubset(version_keys)
    return False


def _has_key(value: Any, names: set[str]) -> bool:
    if isinstance(value, Mapping):
        if any(str(k).casefold() in names and v not in (None, "", [], {}) for k, v in value.items()):
            return True
        return any(_has_key(v, names) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_key(item, names) for item in value)
    return False


def _values_for_keys(value: Any, names: set[str]) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in names:
                found.append(item)
            found.extend(_values_for_keys(item, names))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_values_for_keys(item, names))
    return found


def _display_decision(value: Any, source_ids: Sequence[str] | None = None) -> RightsDecision:
    ids = set(source_ids or ()) | _collect_source_ids(value)
    versions: list[str] = []
    if not ids:
        return RightsDecision(False, "source-bearing projection has no attributable source", (), (), "UNKNOWN_SOURCE")
    if _has_key(value, {"raw", "raw_response", "html", "source_content", "content_bytes"}):
        return RightsDecision(False, "raw source representation is not customer display content", tuple(sorted(ids)), (), "SOURCE_CONTENT_DENIED")
    try:
        for source_id in sorted(ids):
            policy = source_policy(source_id)
            _current_permission(policy, operation="customer display")
            if policy.customer_display not in {"permitted_current_policy_only", "permitted_with_attribution"}:
                raise SourceRightsDenied("customer display is not permitted by current policy", reason_code="DISPLAY_NOT_PERMITTED")
            fulltexts = _values_for_keys(value, {"fulltext", "full_text", "document_body", "body"})
            if fulltexts and str(policy.fulltext_use).lower() not in {"permitted", "permitted_with_attribution"}:
                raise SourceRightsDenied("fulltext display is not permitted", reason_code="FULLTEXT_DENIED")
            excerpts = [str(v) for v in _values_for_keys(value, {"excerpt"}) if v not in (None, "")]
            if any(len(text.split()) > policy.max_excerpt_words for text in excerpts):
                raise SourceRightsDenied("excerpt exceeds policy word limit", reason_code="EXCERPT_LIMIT")
            source_prose = _source_prose_present(value)
            if _derived_projection(value):
                # The observed block is SOURCE FACT; assessment/relevance are
                # PYRNOVA DERIVED or HUMAN ASSESSMENT. Only explicit copied
                # content fields below remain source prose.
                source_prose = any(_has_key(value, {k}) for k in {
                    "excerpt", "fulltext", "full_text", "document_body", "raw_response",
                    "source_content", "content_bytes",
                })
            if source_prose:
                if not str(policy.excerpt_use).startswith("limited_excerpt"):
                    raise SourceRightsDenied("source prose display is not permitted", reason_code="PROSE_DISPLAY_DENIED")
                if not _derived_projection(value):
                    prose = _values_for_keys(value, {"title", "event_summary", "summary", "description", "detail", "text", "excerpt"})
                    if sum(len(item.split()) for item in prose if isinstance(item, str)) > policy.max_excerpt_words:
                        raise SourceRightsDenied("copied expression exceeds policy word limit", reason_code="EXCERPT_LIMIT")
                if not _has_key(value, {"source_url", "url"}) or not _has_key(value, {"attribution"}):
                    raise SourceRightsDenied("source prose requires attribution and direct URL", reason_code="ATTRIBUTION_REQUIRED")
                urls = [u for u in _values_for_keys(value, {"source_url", "url"}) if isinstance(u, str)]
                if not urls or not any(_url_allowed_for_policy(policy, u) for u in urls):
                    raise SourceRightsDenied("source URL is outside the source policy", reason_code="SOURCE_URL_MISMATCH")
            versions.append(policy.policy_version)
    except SourceRightsError as exc:
        return RightsDecision(False, str(exc), tuple(sorted(ids)), tuple(versions), getattr(exc, "reason_code", "RIGHTS_DENIED"))
    return RightsDecision(True, "current source policies permit display", tuple(sorted(ids)), tuple(versions), "ALLOWED")


def _host_matches_suffixes(host: str, suffixes: Sequence[str]) -> bool:
    """True only when ``host`` is, or is a sub-domain of, an official publisher suffix.

    Matched on domain labels so a substring such as ``evilgov.com`` never satisfies
    ``.gov``; a lone suffix is compared as an exact host too.
    """
    for suffix in suffixes:
        label = str(suffix).lower().lstrip(".").rstrip(".")
        if label and (host == label or host.endswith("." + label)):
            return True
    return False


def _url_allowed_for_policy(policy: SourcePolicy, url: str, *, reference: bool = False) -> bool:
    parts = urlsplit(url)
    if parts.scheme.lower() != "https" or not parts.hostname:
        return False
    hosts = policy.reference_hosts if reference and policy.reference_hosts else policy.allowed_hosts
    prefixes = policy.reference_path_prefixes if reference and policy.reference_path_prefixes else policy.allowed_path_prefixes
    host = parts.hostname.lower().rstrip(".")
    host_ok = host in {h.lower().rstrip(".") for h in hosts}
    if not host_ok and reference:
        # Official-publisher suffixes authorize a provenance REFERENCE only (no retrieval).
        host_ok = _host_matches_suffixes(host, policy.reference_host_suffixes)
    if not host_ok:
        return False
    return any((parts.path or "/").startswith(prefix) for prefix in prefixes)


def _minimal_projection(value: Any) -> Any:
    """Retain only stable identifiers/provenance when source material is denied."""
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            name = str(key).casefold()
            if name in _KEEP_REF_KEYS:
                if name in {"refs", "provenance", "source_refs"}:
                    out[key] = _minimal_projection(item)
                elif name in {"evidence_ids", "source_ids"} and isinstance(item, (list, tuple)):
                    out[key] = list(item)
                elif name in {"archive_hash", "content_sha256", "available_at", "observed_at", "event_time", "valid_from", "valid_to"}:
                    out[key] = item
                else:
                    out[key] = _minimal_projection(item)
        return out
    if isinstance(value, list):
        return [_minimal_projection(item) for item in value]
    if isinstance(value, tuple):
        return [_minimal_projection(item) for item in value]
    return value


def gate_customer_display(value: Mapping[str, Any], *, source_ids: Sequence[str] | None = None) -> dict:
    """Gate an actual customer projection while retaining references and a diagnostic decision."""
    decision = _display_decision(value, source_ids)
    payload = copy.deepcopy(dict(value)) if decision.allowed else _minimal_projection(value)
    payload["source_rights"] = {
        "display": "ALLOWED" if decision.allowed else "BLOCKED",
        "reason": decision.reason,
        "reason_code": decision.reason_code,
        "source_ids": list(decision.source_ids),
        "policy_versions": list(decision.policy_versions),
    }
    return payload


def authorize_derived_projection(value: Mapping[str, Any], *, source_ids: Sequence[str] | None = None) -> RightsDecision:
    """Check a derived persistence projection without granting source display.

    Derived fan-out requires explicit attributable source ids and an approved
    derived-use scope.  Raw/fulltext/excerpt fields are rejected here; current
    display state is evaluated separately when the customer reads the record.
    """
    ids = set(source_ids or ()) | _collect_source_ids(value)
    if not ids:
        return RightsDecision(False, "derived projection lacks attributable source", (), (), "UNKNOWN_SOURCE")
    if _has_key(value, {"raw", "raw_response", "fulltext", "full_text", "excerpt", "source_content", "content_bytes"}):
        return RightsDecision(False, "derived projection contains source content", tuple(sorted(ids)), (), "SOURCE_CONTENT_DENIED")
    versions: list[str] = []
    try:
        for source_id in sorted(ids):
            policy = source_policy(source_id)
            _current_permission(policy, operation="derived use")
            if policy.derived_use != "permitted_derived_with_attribution":
                raise SourceRightsDenied("derived use is not explicitly permitted", reason_code="DERIVED_USE_DENIED")
            versions.append(policy.policy_version)
    except SourceRightsError as exc:
        return RightsDecision(False, str(exc), tuple(sorted(ids)), tuple(versions), getattr(exc, "reason_code", "RIGHTS_DENIED"))
    return RightsDecision(True, "derived projection permitted", tuple(sorted(ids)), tuple(versions), "ALLOWED")


def _authorize_model_payload(value: Any) -> None:
    if isinstance(value, (bytes, bytearray, str)):
        raise SourceRightsDenied("model input must be structured normalized/derived content", reason_code="MODEL_RAW_DENIED")
    if not isinstance(value, Mapping):
        raise SourceRightsDenied("model input must be a structured mapping", reason_code="MODEL_SHAPE_DENIED")
    unknown_outer = set(value) - _MODEL_OUTER_KEYS
    if unknown_outer:
        raise SourceRightsDenied("model envelope contains unsupported fields", reason_code="MODEL_SCHEMA_DENIED")
    embedded_ids = _collect_source_ids(value)
    declared_ids = set()
    for key in ("source_ids", "source_id"):
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            declared_ids.add(item.strip())
        elif isinstance(item, (list, tuple, set)):
            declared_ids.update(str(v).strip() for v in item if str(v).strip())
    if not declared_ids and not embedded_ids:
        raise SourceRightsDenied("model envelope lacks source identity", reason_code="MODEL_PROVENANCE_REQUIRED")
    representation = str(value.get("representation") or "").upper()
    if representation == StorageMode.NORMALIZED_ONLY.value:
        normalized = value.get("normalized")
        if not isinstance(normalized, Mapping):
            raise SourceRightsDenied("NORMALIZED_ONLY model input lacks normalized facts", reason_code="MODEL_SCHEMA_DENIED")
        _normalized_only(normalized)
        if value.get("excerpt"):
            if not value.get("source_url") or not value.get("attribution"):
                raise SourceRightsDenied("model excerpt requires URL and attribution", reason_code="MODEL_ATTRIBUTION_REQUIRED")
            if len(str(value["excerpt"]).split()) > 25:
                raise SourceRightsDenied("model excerpt exceeds word limit", reason_code="EXCERPT_LIMIT")
    elif representation == "DERIVED":
        derived = value.get("derived")
        if not isinstance(derived, Mapping):
            raise SourceRightsDenied("DERIVED model input lacks structured derived data", reason_code="MODEL_SCHEMA_DENIED")
        if not value.get("evidence_ids"):
            raise SourceRightsDenied("derived model input requires evidence references", reason_code="MODEL_PROVENANCE_REQUIRED")
        if set(derived) - _MODEL_DERIVED_KEYS:
            raise SourceRightsDenied("derived model envelope contains unsupported fields", reason_code="MODEL_SCHEMA_DENIED")
        for key, item in derived.items():
            _normalized_only(item, f"derived.{key}")
        _normalized_only({"id": value.get("id"), "source_ref": value.get("source_ref")})
    else:
        raise SourceRightsDenied("model input representation must be NORMALIZED_ONLY or DERIVED", reason_code="MODEL_REPRESENTATION_DENIED")
    screen = screen_payload(value)
    if not screen.allowed:
        raise SourceRightsDenied(screen.reason, reason_code="MODEL_PAYLOAD_DENIED")


def authorize_model_input(source_ids: Sequence[str], value: Any) -> RightsDecision:
    ids = tuple(sorted({str(i) for i in source_ids if str(i).strip()}))
    try:
        policies = [source_policy(i) for i in ids]
        if not policies:
            raise SourceRightsDenied("model input has no attributable source")
        for policy in policies:
            _current_permission(policy, operation="model processing")
            if policy.model_processing_allowed is not True:
                raise SourceRightsDenied("model processing is not explicitly permitted")
            if not policy.model_constraints:
                raise SourceRightsDenied("model constraints are unknown", reason_code="MODEL_CONSTRAINTS_UNKNOWN")
            if "structured facts or permitted derived content only" not in policy.model_constraints or "retain attribution" not in policy.model_constraints:
                raise SourceRightsDenied("model input constraint is not recognized", reason_code="MODEL_CONSTRAINTS_DENIED")
            embedded = _collect_source_ids(value)
            if embedded and not embedded.issubset(ids):
                raise SourceRightsDenied("embedded source identity is outside authorized sources", reason_code="MODEL_SOURCE_MISMATCH")
            if isinstance(value, Mapping) and value.get("source_url") and not _url_allowed_for_policy(policy, str(value["source_url"])):
                raise SourceRightsDenied("model source URL is outside source policy", reason_code="SOURCE_URL_MISMATCH")
            if isinstance(value, Mapping) and value.get("excerpt") and (not value.get("attribution") or len(str(value["excerpt"]).split()) > policy.max_excerpt_words):
                raise SourceRightsDenied("model excerpt attribution or limit failed", reason_code="MODEL_ATTRIBUTION_REQUIRED")
        _authorize_model_payload(value)
    except SourceRightsError as exc:
        return RightsDecision(False, str(exc), ids, tuple(p.policy_version for p in locals().get("policies", [])), getattr(exc, "reason_code", "RIGHTS_DENIED"))
    return RightsDecision(True, "model processing permitted by current source policies", ids,
                          tuple(p.policy_version for p in policies), "ALLOWED")


def guarded_model_call(callback: Callable[..., Any], *, source_ids: Sequence[str], value: Any, **kwargs: Any) -> Any:
    """Check source rights before invoking a model callback; denied callbacks are never called."""
    decision = authorize_model_input(source_ids, value)
    if not decision.allowed:
        raise SourceRightsDenied(decision.reason)
    allowed_kwargs = {"temperature", "max_tokens", "purpose", "model"}
    if set(kwargs) - allowed_kwargs:
        raise SourceRightsDenied("model call kwargs may not carry source content", reason_code="MODEL_KWARGS_DENIED")
    if "purpose" in kwargs and kwargs["purpose"] != "explanation":
        raise SourceRightsDenied("model purpose is not approved for Phase 1", reason_code="MODEL_PURPOSE_DENIED")
    if "model" in kwargs and (not isinstance(kwargs["model"], str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", kwargs["model"])):
        raise SourceRightsDenied("model identifier is invalid", reason_code="MODEL_ID_DENIED")
    if "temperature" in kwargs and (not isinstance(kwargs["temperature"], (int, float)) or not 0 <= kwargs["temperature"] <= 2):
        raise SourceRightsDenied("temperature is invalid", reason_code="MODEL_KWARGS_DENIED")
    if "max_tokens" in kwargs and (not isinstance(kwargs["max_tokens"], int) or not 1 <= kwargs["max_tokens"] <= 8192):
        raise SourceRightsDenied("max_tokens is invalid", reason_code="MODEL_KWARGS_DENIED")
    return callback(value, **kwargs)


def _json_or_hash(content: bytes) -> Any:
    try:
        return json.loads(content)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"content_sha256": hashlib.sha256(content).hexdigest()}


__all__ = [
    "SourceRightsError", "SourceRightsDenied", "ProhibitedSourcePayload", "PayloadScreen",
    "RightsDecision", "source_policy", "authorize_request", "screen_payload", "validate_source_payload",
    "representation_for_storage", "authorize_source_url", "gate_customer_display", "authorize_model_input", "guarded_model_call",
]
