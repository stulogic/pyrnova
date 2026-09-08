"""Source registry with rights + retention-tier metadata.

Rights and retention must be known at OBSERVE time. Only the initial-phase sources are active; others
are declared for forward compatibility but not fetched (anti-accumulation rule).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpec:
    id: str
    name: str
    base_url: str
    rights: str            # 'us_gov_work' (public domain) etc.
    retention_tier: str    # 'A' version-sensitive | 'B' durable | 'C' ephemeral
    active: bool           # active in the initial commercial phase?
    notes: str = ""


REGISTRY: dict[str, SourceSpec] = {
    "usaspending": SourceSpec(
        id="usaspending",
        name="USAspending.gov Award Search",
        base_url="https://api.usaspending.gov/api/v2",
        rights="us_gov_work",
        retention_tier="A",  # agencies restate/resubmit award data
        active=True,
        notes="Award history, incumbency, contract end dates, IDV relationships, recompete detection.",
    ),
    "sam_opportunities": SourceSpec(
        id="sam_opportunities",
        name="SAM.gov Contract Opportunities (Get Opportunities API v2)",
        base_url="https://api.sam.gov/opportunities/v2",
        rights="us_gov_work",
        retention_tier="A",  # amendments / cancellations / transitions
        active=True,
        notes="Requires SAM_API_KEY. Sources Sought, RFI, Presolicitation, Special Notices, transitions.",
    ),
    # --- Declared, NOT active in the initial phase (P0-B, added only where they materially help) ---
    "federal_register": SourceSpec(
        id="federal_register",
        name="Federal Register API",
        base_url="https://www.federalregister.gov/api/v1",
        rights="us_gov_work",
        retention_tier="B",  # durable immutable publication
        active=False,
        notes="P0-B. Add only where it enriches Capture Radar without jeopardizing the core.",
    ),
    "grants_gov": SourceSpec(
        id="grants_gov",
        name="Grants.gov Search2 API",
        base_url="https://api.grants.gov/v1/api",
        rights="us_gov_work",
        retention_tier="B",
        active=False,
        notes="P0-B.",
    ),
}


def get_spec(source_id: str) -> SourceSpec:
    try:
        return REGISTRY[source_id]
    except KeyError as exc:
        raise KeyError(f"unknown source {source_id!r}") from exc


def active_sources() -> list[SourceSpec]:
    return [s for s in REGISTRY.values() if s.active]
