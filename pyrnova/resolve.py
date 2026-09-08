"""RESOLVE — minimal deterministic entity resolution (name/UEI canonicalization).

Sufficient for a narrow customer domain. Ambiguous cases are left for human/AI review (not automated
here). No full Capability/Entity Graph is built (deferred).
"""

from __future__ import annotations

import re

from .models import Entity

_SUFFIXES = {
    "inc", "incorporated", "llc", "llp", "lp", "corp", "corporation", "co", "company",
    "ltd", "limited", "plc", "gmbh", "sa", "the", "group", "holdings",
}
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")


def canonicalize_name(name: str) -> str:
    if not name:
        return ""
    s = name.lower()
    s = _PUNCT.sub(" ", s)
    tokens = [t for t in _WS.sub(" ", s).strip().split(" ") if t and t not in _SUFFIXES]
    return " ".join(tokens)


def resolve_entity(name: str, kind: str, uei: str | None = None) -> Entity:
    return Entity(kind=kind, name=name or "", canonical_name=canonicalize_name(name or ""), uei=uei)


def same_entity(a: str, b: str) -> bool:
    return bool(a) and canonicalize_name(a) == canonicalize_name(b)
