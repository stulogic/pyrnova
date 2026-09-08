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
        active=True,
        notes="Procurement-adjacent upstream evidence; agency/topic links never prove procurement intent.",
    ),
    "sec_edgar": SourceSpec(
        id="sec_edgar",
        name="SEC EDGAR Submissions and Company Facts",
        base_url="https://data.sec.gov",
        rights="us_gov_work",
        retention_tier="A",  # filings and company facts can be amended/restated
        active=True,
        notes="Corporate-change and capex-adjacent filing evidence; never creates a candidate without other source evidence.",
    ),
    "acquisition_forecast": SourceSpec(
        id="acquisition_forecast",
        name="Official Agency Procurement Forecasts",
        base_url="https://www.acquisition.gov/procurement-forecasts",
        rights="us_gov_work",
        retention_tier="A",
        active=True,
        notes=(
            "M4: agency-published forecast artifacts normalized conservatively as MARKET_ENGAGEMENT; "
            "per-agency mappings are required and forecast rows cannot independently create STRIKEs."
        ),
    ),
    "grants_gov": SourceSpec(
        id="grants_gov",
        name="Grants.gov Search2 API",
        base_url="https://api.grants.gov/v1/api",
        rights="us_gov_work",
        retention_tier="A",  # opportunity status and terms can be amended
        active=True,
        notes=(
            "M4: attributable federal funding opportunities. Search results are "
            "mutable and may provide direct opportunities, precursor funding context, "
            "or enrichment only; this source does not independently create candidates."
        ),
    ),
    "appropriations": SourceSpec(
        id="appropriations",
        name="Federal Appropriations / Program Funding (official budget artifacts)",
        base_url="https://www.usaspending.gov/",
        rights="us_gov_work",
        retention_tier="A",  # enacted/appropriated amounts can be restated or reprogrammed
        active=True,
        notes=(
            "M6: official structured budget artifacts (President's Budget request lines, enacted "
            "authorization/appropriation act lines, appropriated accounts) normalized conservatively "
            "as distinct INTENT/AUTHORIZATION/FUNDING precursor stages, moving Pyrnova earlier in the "
            "capital lifecycle. Rows carry the most authoritative structured identifier present "
            "(TAS > federal account > CFDA/assistance listing > program element > budget line item) "
            "as inference anchors; this source cannot independently create candidates or STRIKEs."
        ),
    ),
}


def get_spec(source_id: str) -> SourceSpec:
    try:
        return REGISTRY[source_id]
    except KeyError as exc:
        raise KeyError(f"unknown source {source_id!r}") from exc


def active_sources() -> list[SourceSpec]:
    return [s for s in REGISTRY.values() if s.active]
