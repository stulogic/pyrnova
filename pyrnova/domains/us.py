"""United States national domain — a *declaration* over the accepted US implementation.

This module changes no US semantics. The US product (USAspending / SAM / Federal Register / SEC /
OFAC, the Capture Radar + Material Change pipeline, the customer product) remains the operational
implementation; here it is simply expressed in the shared National Domain contract so the kernel can
treat US as one national domain among several without a per-country fork.
"""

from __future__ import annotations

from .base import NationalDomain, NationalSource, SourceActivation

US = NationalDomain(
    code="US",
    name="United States",
    # Federal acquisition lifecycle as embodied by the accepted US pipeline (evidence -> pre-solicitation
    # -> solicitation -> award -> performance -> recompete). National truth, not a universal ontology.
    lifecycle=(
        "FORECAST", "PRE_SOLICITATION", "SOLICITATION", "AWARD", "PERFORMANCE", "RECOMPETE",
    ),
    routes={
        "FULL_AND_OPEN": "Full and open competition (FAR Part 15).",
        "SET_ASIDE": "Small-business / socioeconomic set-aside.",
        "SOLE_SOURCE": "Justified sole-source / limited-competition award.",
        "IDIQ_TASK_ORDER": "Task/delivery order under an existing IDIQ vehicle.",
        "GWAC_SCHEDULE": "Order under a GWAC / GSA Schedule vehicle.",
        "OTA": "Other Transaction Authority agreement.",
    },
    access_classes=("INCUMBENT", "VEHICLE_HOLDER", "PRIME", "SUBCONTRACTOR", "NO_ESTABLISHED_ACCESS", "UNKNOWN"),
    industrial_position_classes=(
        "DOMESTIC_PRIME", "CLEARED_CONTRACTOR", "SMALL_BUSINESS", "FOREIGN_OWNED_LOCALLY_PRESENT", "UNKNOWN",
    ),
    important_miss=(
        "RECOMPETE_WINDOW", "INCUMBENT_CHANGE", "VEHICLE_EXPIRY", "PROGRAM_CANCELLATION",
        "SCOPE_CHANGE", "CONSOLIDATION", "SET_ASIDE_CHANGE",
    ),
    evidence_languages=("en",),
    sources=(
        NationalSource("usaspending", "USAspending", SourceActivation.ACTIVE, role="evidence",
                       note="Public-domain US Government work; live-proven."),
        NationalSource("sam_opportunities", "SAM.gov Opportunities", SourceActivation.ACTIVE, role="evidence",
                       note="Live with SAM_API_KEY; pre-solicitation intelligence."),
        NationalSource("federal_register", "Federal Register", SourceActivation.ACTIVE, role="evidence"),
    ),
    # US DLT is deterministic-on-read (carried by the accepted opportunity-lifecycle validation and the
    # shared DLT engine), not a fixed national median — so no constant calibration is asserted here.
    dlt_calibration=None,
    validated=True,
    build_authority=True,
    notes="Accepted US Phase 1 Release Candidate. Operational implementation; do not reopen semantics.",
)
