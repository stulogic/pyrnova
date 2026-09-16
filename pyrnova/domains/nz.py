"""New Zealand national domain — second national customer-product vertical.

Authority: PYRNOVA-NZ-SPEC-001 accepted; historical validation passed owner adjudication; owner NZ build
authority granted. This is executable national truth, not a seam with TODOs.

CRITICAL HARD LOCK — **GETS IS NOT A PYRNOVA INGESTION SOURCE.**
GETS (the NZ Government Electronic Tenders Service) must NEVER be scraped, crawled, systematically
browsed, manually harvested, agent-harvested or reproduced. It is declared here as
``SourceActivation.PROHIBITED`` so any attempt to ingest it fails closed via
:class:`pyrnova.domains.base.ProhibitedSourceIngestion`, and it is ALSO hard-denied at the source-rights
registry layer (see ``pyrnova/sources/registry.py``) — both governance layers fail closed and must agree.
GETS may appear only as a historically established downstream endpoint where lawful retrospective evidence
proves an RFT/RFI occurred; it is never an acquisition feed. NZ intelligence works without GETS.

National truth preserved here (NOT flattened into AU or the US ontology):
* the New Zealand acquisition lifecycle and route semantics (open / all-of-government panel / closed /
  direct-source opt-out / GtG) — distinct national meanings, not a relabelled AU pipeline;
* NZ commercial access, including **Thin Prime as a contracting/access structure ONLY** — a Thin Prime is
  an access class, it is **NOT** an NZ Industrial Position;
* NZ Industrial Position, where **economic benefit != sovereign capability != resilience**, and
  **Australia-mediated supply is not NZ access**;
* Important Miss behaviour: progression, reversal/cancellation, re-scope, route change, Thin Prime shift;
* strict AS-OF (enforced by the shared kernel);
* NZ source-rights ownership — activation is fail-closed (UNKNOWN => DENY). Candidate source families are
  codified with their per-source posture; production acquisition is NOT activated without current rights
  authority, so lawful owner-accepted historical/replay evidence is FIXTURE_ONLY and everything else is
  DECLARED (=> DENY) until a reviewed rights position exists.
"""

from __future__ import annotations

from .base import DLTCalibration, NationalDomain, NationalSource, SourceActivation

NZ = NationalDomain(
    code="NZ",
    name="New Zealand",
    # NZ acquisition lifecycle — its own meaning (planning -> market engagement -> RFx -> evaluation ->
    # award -> contract management -> recompete), not an AU or US pipeline under NZ labels.
    lifecycle=(
        "PLANNING",             # procurement planning / forward capability
        "MARKET_ENGAGEMENT",    # ROI / market / industry engagement
        "APPROACH_TO_MARKET",   # RFx approach (RFP/RFT/RFQ)
        "EVALUATION",           # evaluation
        "AWARD",                # award / notification of successful supplier
        "MANAGEMENT",           # contract management
        "RECOMPETE",            # re-approach / extension / recompete
    ),
    routes={
        "OPEN": "Open competitive approach — any eligible supplier may respond.",
        "PANEL": "Approach via a syndicated / all-of-government (AoG) panel or standing arrangement.",
        "CLOSED": "Closed / invited approach — limited competition to nominated suppliers.",
        "DIRECT_SOURCE": "Direct source — opt-out from open advertising to a single supplier.",
        "GTG": "Government-to-Government arrangement (distinct from open competition).",
    },
    access_classes=(
        # Thin Prime is a contracting/access structure ONLY — an access class, never an Industrial Position.
        "INCUMBENT", "PANEL_MEMBER", "PRIME", "THIN_PRIME", "SUBCONTRACTOR", "TEAMING_PARTNER",
        "NO_ESTABLISHED_ACCESS", "UNKNOWN",
    ),
    industrial_position_classes=(
        "ECONOMIC_BENEFIT",       # broad economic benefit — DISTINCT from sovereign capability
        "SOVEREIGN_CAPABILITY",   # sovereign capability — DISTINCT
        "RESILIENCE_RELEVANT",    # supply-chain resilience relevance — DISTINCT
        "LOCAL_PRESENCE",         # locally present (may be foreign-owned)
        "FOREIGN_OWNED_LOCALLY_PRESENT",  # foreign ownership does NOT imply ineligibility
        "UNKNOWN",
    ),
    important_miss=(
        "ROUTE_CHANGE",       # e.g. open -> closed, or a shift to direct-source
        "PROGRESSION",        # lifecycle progression a customer must not miss
        "CANCELLATION",       # withdrawn / cancelled approach (reversal)
        "CONSOLIDATION",      # requirements consolidated
        "RE_SCOPE",           # scope materially changed
        "THIN_PRIME_SHIFT",   # a shift in the Thin Prime / access structure
    ),
    evidence_languages=("en",),
    sources=(
        # HARD LOCK: GETS is national truth but NOT an ingestion source. Fail-closed enforcement.
        NationalSource("nz_gets", "GETS (Government Electronic Tenders Service)", SourceActivation.PROHIBITED,
                       role="prohibited",
                       note="HARD LOCK. Not an ingestion source. No scrape/crawl/browse/harvest/reproduce. "
                            "May appear only as a historically established downstream endpoint proven by "
                            "lawful retrospective evidence; never an acquisition feed."),
        # Defence lawful owner-accepted historical/replay evidence — the strongest validated rights position
        # (the accepted NZ historical validation was strongest in Defence). FIXTURE_ONLY: lawful for
        # replay-derived customer projection; live production acquisition is NOT authorized (pending rights).
        NationalSource("nz_mod", "New Zealand Ministry of Defence (lawful historical/replay evidence)",
                       SourceActivation.FIXTURE_ONLY, role="evidence",
                       note="Candidate family with a potentially favorable rights position; live production "
                            "acquisition NOT authorized. FIXTURE_ONLY: lawful owner-accepted historical/"
                            "replay evidence may back a derived, attributed customer projection."),
        # Candidate civil-sector source families — codified but NOT activated. Historical research found
        # potentially favorable rights positions, but that does NOT authorize production acquisition:
        # UNKNOWN => DENY until a reviewed rights position exists (also caps NZ non-Defence coverage).
        NationalSource("nz_treasury", "New Zealand Treasury", SourceActivation.DECLARED, role="evidence",
                       note="Candidate family; activation pending rights review (UNKNOWN => DENY). "
                            "Access permission != retention/commercial use/customer display/redistribution."),
        NationalSource("nz_linz", "Land Information New Zealand (LINZ)", SourceActivation.DECLARED,
                       role="evidence",
                       note="Candidate family; activation pending rights review (UNKNOWN => DENY)."),
        NationalSource("nz_greater_wellington", "Greater Wellington Regional Council", SourceActivation.DECLARED,
                       role="evidence",
                       note="Candidate family; activation pending rights review (UNKNOWN => DENY)."),
        # Explicit caution areas (NZ-SPEC-001): rights are NOT generalized between families. DENY.
        NationalSource("nz_police", "New Zealand Police (ordinary website material)", SourceActivation.DECLARED,
                       role="evidence",
                       note="CAUTION: ordinary website material rights are unresolved; do not generalize "
                            "from other families. UNKNOWN => DENY."),
        NationalSource("nz_nzta", "NZ Transport Agency (NZTA)", SourceActivation.DECLARED, role="evidence",
                       note="CAUTION: NZTA terms are unresolved. UNKNOWN => DENY."),
    ),
    # Accepted NZ historical validation (owner-adjudicated): 36-case mixed corpus, 17 sufficiently clean
    # DLT-to-Market cases (15/17 >= 60 actionable days), median DLT-to-Market 491 days, lower quartile 292
    # days (min 18, max 2,077). These are the CITED accepted validation numbers, not invented here. The
    # evidence supports commercially material lead time for a MEANINGFUL SUBSET without GETS — NOT
    # comprehensive coverage, NOT guaranteed early discovery, NOT civil-sector parity with Defence (only 3
    # clean non-Defence cases satisfied the full standard). That limitation is preserved, not inflated.
    dlt_calibration=DLTCalibration(
        median_dlt_to_market_days=491.0,
        p25_days=292.0,
        corpus_size=36,
        qualifying_cases=17,
        source_reference="PYRNOVA-NZ-SPEC-001 accepted historical validation (owner-adjudicated)"),
    validated=True,
    build_authority=True,
    notes="NZ build authority granted. GETS HARD LOCK enforced (PROHIBITED ingestion, both governance "
          "layers). Thin Prime is a contracting/access structure only, not an NZ Industrial Position; "
          "economic benefit != sovereign capability != resilience; Australia-mediated supply is not NZ "
          "access. Calibration supports material lead time for a meaningful subset without GETS, not "
          "comprehensive coverage and not civil-sector parity with Defence.",
)
