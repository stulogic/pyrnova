"""New Zealand national-domain seam.

Authority: PYRNOVA-NZ-SPEC-001 accepted; historical validation passed.

CRITICAL HARD LOCK — **GETS IS NOT A PYRNOVA INGESTION SOURCE.**
GETS (the NZ Government Electronic Tenders Service) must NEVER be scraped, crawled, systematically
browsed, manually harvested, agent-harvested or reproduced. It is declared here as
``SourceActivation.PROHIBITED`` so any attempt to ingest it fails closed via
:class:`pyrnova.domains.base.ProhibitedSourceIngestion`. NZ intelligence must work from lawful
alternative sources only.

Preserved NZ meaning: NZ national truth and access; Thin Prime semantics; the distinctions between
economic benefit, sovereign capability and resilience; route-aware progression; source-rights
fail-closed behaviour.
"""

from __future__ import annotations

from .base import NationalDomain, NationalSource, SourceActivation

NZ = NationalDomain(
    code="NZ",
    name="New Zealand",
    lifecycle=(
        "PLANNING",             # procurement planning / forward capability
        "MARKET_ENGAGEMENT",    # ROI / market engagement
        "APPROACH_TO_MARKET",   # RFx approach
        "EVALUATION",
        "AWARD",
        "MANAGEMENT",           # contract management
        "RECOMPETE",
    ),
    routes={
        "OPEN": "Open competitive approach.",
        "PANEL": "Approach via a syndicated / all-of-government panel.",
        "CLOSED": "Closed / invited approach (limited competition).",
        "DIRECT_SOURCE": "Direct source / opt-out from open advertising.",
        "GTG": "Government-to-Government arrangement.",
    },
    access_classes=(
        "INCUMBENT", "PANEL_MEMBER", "PRIME", "THIN_PRIME", "SUBCONTRACTOR",
        "NO_ESTABLISHED_ACCESS", "UNKNOWN",
    ),
    industrial_position_classes=(
        "ECONOMIC_BENEFIT",       # broad economic benefit (distinct from sovereign capability)
        "SOVEREIGN_CAPABILITY",   # sovereign capability (distinct)
        "RESILIENCE_RELEVANT",    # resilience relevance (distinct)
        "LOCAL_PRESENCE", "FOREIGN_OWNED_LOCALLY_PRESENT", "UNKNOWN",
    ),
    important_miss=(
        "ROUTE_CHANGE", "PROGRESSION", "CANCELLATION", "CONSOLIDATION", "RE_SCOPE", "THIN_PRIME_SHIFT",
    ),
    evidence_languages=("en",),
    sources=(
        # HARD LOCK: GETS is national truth but NOT an ingestion source. Fail-closed enforcement.
        NationalSource("nz_gets", "GETS (Government Electronic Tenders Service)", SourceActivation.PROHIBITED,
                       role="prohibited",
                       note="HARD LOCK. Not an ingestion source. No scrape/crawl/browse/harvest/reproduce."),
        NationalSource("nz_lawful_alt", "Lawful alternative NZ sources", SourceActivation.DECLARED,
                       role="evidence",
                       note="NZ must work from lawful alternatives; specific adapters pending rights review."),
    ),
    dlt_calibration=None,      # validation passed but numeric calibration not asserted here; do not invent
    validated=True,
    build_authority=False,     # a bounded explicit owner build-authority marker is requested (see report)
    notes="GETS HARD LOCK enforced (PROHIBITED ingestion). Validation passed; a bounded owner "
          "build-authority marker is requested before implementing the NZ module.",
)
