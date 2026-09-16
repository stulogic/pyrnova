"""National-domain registry — the Global Kernel's view of the national domains it serves.

SHARE MECHANISM. KEEP NATIONAL TRUTH NATIONAL. The kernel resolves a national domain by code and reads
its declared national truth + source-rights activation posture; it never re-implements national meaning.
"""

from __future__ import annotations

from .base import (
    DLTCalibration,
    NationalDomain,
    NationalSource,
    ProhibitedSourceIngestion,
    SourceActivation,
    UNKNOWN,
)
from .us import US
from .au import AU
from .uk import UK
from .ca import CA
from .nz import NZ

# Keyed by national code (ISO-3166 alpha-2). GB is the UK's code; "UK" is accepted as an alias.
_DOMAINS: dict[str, NationalDomain] = {d.code: d for d in (US, AU, UK, CA, NZ)}
_ALIASES = {"UK": "GB"}


def get_domain(code: str) -> NationalDomain:
    """Resolve a national domain by code (case-insensitive; 'UK' aliases to 'GB'). Fail-closed."""
    key = (code or "").strip().upper()
    key = _ALIASES.get(key, key)
    try:
        return _DOMAINS[key]
    except KeyError as exc:
        raise KeyError(f"unknown national domain: {code!r} (known: {sorted(_DOMAINS)})") from exc


def all_domains() -> tuple[NationalDomain, ...]:
    """All registered national domains, in registration order."""
    return tuple(_DOMAINS.values())


def operational_domains() -> tuple[NationalDomain, ...]:
    """Domains that are validated AND have owner build authority (implementable now)."""
    return tuple(d for d in _DOMAINS.values() if d.validated and d.build_authority)


__all__ = [
    "DLTCalibration", "NationalDomain", "NationalSource", "ProhibitedSourceIngestion",
    "SourceActivation", "UNKNOWN",
    "US", "AU", "UK", "CA", "NZ",
    "get_domain", "all_domains", "operational_domains",
]
