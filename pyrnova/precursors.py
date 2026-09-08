"""Deterministic, source-independent state-capital program chains.

Adapters emit source-faithful signal dictionaries.  This module only links signals when they carry
an explicit shared program identity; it never infers a chain from topical similarity alone.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


PRECURSOR_STAGES = (
    "INTENT",
    "AUTHORIZATION",
    "FUNDING",
    "PROGRAM",
    "MARKET_ENGAGEMENT",
    "PROCUREMENT",
    "AWARD",
    "OUTCOME",
)
_STAGE_ORDER = {stage: index for index, stage in enumerate(PRECURSOR_STAGES)}


def stable_signal_id(source_id: str, source_ref: str, stage: str) -> str:
    """Return a stable cross-run identity without replacing the source-native reference."""
    if stage not in _STAGE_ORDER:
        raise ValueError(f"unknown precursor stage: {stage}")
    basis = f"{source_id}|{source_ref}|{stage}".encode("utf-8")
    return hashlib.sha256(basis).hexdigest()[:24]


@dataclass(frozen=True)
class ProgramSignal:
    source_id: str
    source_ref: str
    stage: str
    program_key: str
    summary: str
    available_at: str | None = None
    agency: str | None = None
    funding_source: str | None = None
    authority: str | None = None
    geography: str | None = None
    capabilities: tuple[str, ...] = ()
    downstream_refs: tuple[str, ...] = ()
    confidence: str = "UNKNOWN"
    meta: dict = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if self.stage not in _STAGE_ORDER:
            raise ValueError(f"unknown precursor stage: {self.stage}")
        if not self.source_id or not self.source_ref or not self.program_key:
            raise ValueError("source_id, source_ref, and explicit program_key are required")

    @property
    def id(self) -> str:
        return stable_signal_id(self.source_id, self.source_ref, self.stage)


@dataclass(frozen=True)
class ProgramChain:
    program_key: str
    signals: tuple[ProgramSignal, ...]

    @property
    def id(self) -> str:
        payload = {"program_key": self.program_key, "signal_ids": [s.id for s in self.signals]}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:24]

    @property
    def stages(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(signal.stage for signal in self.signals))

    @property
    def is_partial(self) -> bool:
        return len(self.stages) < len(PRECURSOR_STAGES)


def build_program_chains(signals: list[ProgramSignal]) -> list[ProgramChain]:
    """Group only explicitly keyed signals and deduplicate exact source-native stage identities."""
    grouped: dict[str, dict[str, ProgramSignal]] = {}
    for signal in signals:
        grouped.setdefault(signal.program_key, {}).setdefault(signal.id, signal)
    chains = []
    for program_key, unique in sorted(grouped.items()):
        ordered = tuple(sorted(
            unique.values(),
            key=lambda s: (_STAGE_ORDER[s.stage], s.available_at or "", s.source_id, s.source_ref),
        ))
        chains.append(ProgramChain(program_key=program_key, signals=ordered))
    return chains
