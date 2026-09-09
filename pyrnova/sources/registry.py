"""Source registry + durable manifest with rights, retention, and M14 operating metadata.

Rights and retention must be known at OBSERVE time. The registry is the single source of truth for
which sources exist, what family/economic-domain they observe, how they are accessed and refreshed,
and their operating budget/cadence/reliability/priority. It is deliberately declarative: it performs no
HTTP and holds no secrets. Only sources marked ``active`` are fetched in the current commercial phase
(anti-accumulation rule); others are declared for forward compatibility and manifest completeness.

M14 adds the richer manifest fields (family, signal types, access method, incremental mechanism,
identifiers, cross-source linking potential, source-native + recommended cadence, live-call budget,
reliability state, implementation status, intelligence priority, and rights/licensing notes) required
by ``docs/specs/M14_MULTI_SOURCE_EXPANSION.md``. All new fields are optional with conservative defaults,
so the M2–M13 entries, ``scheduler.health()``, and adapters that read only the original fields are
unchanged. Facts that are genuinely unknown are recorded as ``"unknown"`` — never inferred.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpec:
    # --- original fields (unchanged; read by adapters and scheduler.health) ---
    id: str
    name: str
    base_url: str
    rights: str            # 'us_gov_work' (public domain) etc.
    retention_tier: str    # 'A' version-sensitive | 'B' durable | 'C' ephemeral
    active: bool           # active in the initial commercial phase?
    notes: str = ""

    # --- M14 manifest fields (all optional; "unknown" is a valid, honest value) ---
    family: str = "unknown"            # economic-domain family (see FAMILIES below)
    signals: tuple[str, ...] = ()      # signal types this source contributes
    access_method: str = "unknown"     # 'rest_api' | 'bulk_download' | 'feed' | 'snapshot' | 'stream'
    auth: str = "none"                 # 'none' | 'api_key' | 'unknown'
    incremental: str = "unknown"       # incremental/checkpoint mechanism (cursor/window/date/full-diff)
    identifiers: tuple[str, ...] = ()  # stable identifiers this source carries (for entity linking)
    links_to: tuple[str, ...] = ()     # other source ids it can deterministically/near-deterministically link to
    historical_depth: str = "unknown"  # how far back / replay depth
    native_cadence: str = "unknown"    # source-native update cadence
    recommended_poll: str = "unknown"  # conservative recommended polling cadence
    call_budget: str = "unknown"       # recommended live-call budget posture
    reliability: str = "unknown"       # 'live_proven' | 'archive_operational' | 'fixture_only' | 'unverified'
    status: str = "declared"           # 'operational' | 'adapter_ready' | 'declared' | 'blocked'
    priority: str = "unknown"          # intelligence priority: 'high' | 'medium' | 'low'
    precursor_stage: str = ""          # dominant capital-lifecycle stage this source observes, if any
    rights_note: str = ""              # licensing / commercial-use note ("unknown" allowed)


# Canonical economic-domain families (materially different observation surfaces, not endpoints).
FAMILIES = (
    "procurement_spend",          # executed federal awards / spend
    "procurement_opportunities",  # active solicitations / pre-RFP
    "procurement_forecast",       # agency-published forward demand
    "appropriations_budget",      # authorization / appropriation / program funding
    "regulation_policy",          # rules, notices, regulatory change
    "funding_assistance",         # grants / assistance opportunities
    "corporate_intelligence",     # SEC filings / company disclosures
    "sanctions_trade",            # sanctions / export controls / trade restrictions
    "science_rd",                 # federal R&D / SBIR-STTR / innovation precursors
)


REGISTRY: dict[str, SourceSpec] = {
    "usaspending": SourceSpec(
        id="usaspending",
        name="USAspending.gov Award Search",
        base_url="https://api.usaspending.gov/api/v2",
        rights="us_gov_work",
        retention_tier="A",  # agencies restate/resubmit award data
        active=True,
        notes="Award history, incumbency, contract end dates, IDV relationships, recompete detection.",
        family="procurement_spend",
        signals=("executed_award", "incumbency", "contract_end", "recompete", "recipient_scale"),
        access_method="rest_api",
        auth="none",
        incremental="date_window + award_id cursor",
        identifiers=("uei", "recipient_id", "award_id", "naics", "psc", "parent_uei"),
        links_to=("sam_opportunities", "sec_edgar", "sbir", "appropriations", "acquisition_forecast"),
        historical_depth="FY2008+",
        native_cadence="daily-to-weekly agency submission; monthly restatements",
        recommended_poll="weekly",
        call_budget="tight: delta windows only; archive-first (M13 proved 2-call live op)",
        reliability="live_proven",
        status="operational",
        priority="high",
        precursor_stage="AWARD",
        rights_note="Public domain US government work.",
    ),
    "sam_opportunities": SourceSpec(
        id="sam_opportunities",
        name="SAM.gov Contract Opportunities (Get Opportunities API v2)",
        base_url="https://api.sam.gov/opportunities/v2",
        rights="us_gov_work",
        retention_tier="A",  # amendments / cancellations / transitions
        active=True,
        notes="Requires SAM_API_KEY. Sources Sought, RFI, Presolicitation, Special Notices, transitions.",
        family="procurement_opportunities",
        signals=("sources_sought", "rfi", "presolicitation", "special_notice", "amendment", "cancellation"),
        access_method="rest_api",
        auth="api_key",
        incremental="postedFrom/postedTo date window + noticeId dedupe",
        identifiers=("notice_id", "solicitation_number", "uei", "naics", "psc"),
        links_to=("usaspending", "acquisition_forecast", "federal_register", "appropriations"),
        historical_depth="rolling; API date-window limited",
        native_cadence="continuous business-day postings + amendments",
        recommended_poll="daily (delta window)",
        call_budget="strict (authenticated quota): delta-only; never historical backfill via live calls",
        reliability="live_proven",
        status="operational",
        priority="high",
        precursor_stage="PROCUREMENT",
        rights_note="Public domain data; API governed by SAM.gov terms — respect quota, no key rotation.",
    ),
    "federal_register": SourceSpec(
        id="federal_register",
        name="Federal Register API",
        base_url="https://www.federalregister.gov/api/v1",
        rights="us_gov_work",
        retention_tier="B",  # durable immutable publication
        active=True,
        notes="Procurement-adjacent upstream evidence; agency/topic links never prove procurement intent.",
        family="regulation_policy",
        signals=("rule", "proposed_rule", "notice", "presidential_document", "agency_action"),
        access_method="rest_api",
        auth="none",
        incremental="publication_date window + document_number dedupe",
        identifiers=("document_number", "agency_ids", "regulation_id_number"),
        links_to=("appropriations", "sam_opportunities", "sanctions_ofac"),
        historical_depth="1994+ (documents.json)",
        native_cadence="daily on Federal Register publication days",
        recommended_poll="daily (agency/topic-filtered window)",
        call_budget="loose (keyless) but windowed: one filtered page per due poll",
        reliability="fixture_only",
        status="adapter_ready",
        priority="medium",
        precursor_stage="AUTHORIZATION",
        rights_note="Public domain US government work; keyless public API.",
    ),
    "sec_edgar": SourceSpec(
        id="sec_edgar",
        name="SEC EDGAR Submissions and Company Facts",
        base_url="https://data.sec.gov",
        rights="us_gov_work",
        retention_tier="A",  # filings and company facts can be amended/restated
        active=True,
        notes="Corporate-change and capex-adjacent filing evidence; never creates a candidate without other source evidence.",
        family="corporate_intelligence",
        signals=("8k_material_event", "10k", "10q", "s1", "segment_change", "capex", "m_and_a"),
        access_method="rest_api",
        auth="none",  # requires a descriptive User-Agent, not a key
        incremental="submissions cursor by accession number; companyfacts snapshot diff",
        identifiers=("cik", "ticker", "company_name", "sic"),
        links_to=("usaspending", "sbir", "sanctions_ofac"),
        historical_depth="EDGAR full-text 2001+; submissions per-CIK full history",
        native_cadence="continuous filing acceptance (business hours)",
        recommended_poll="daily per watched CIK",
        call_budget="tight: per-CIK submissions, descriptive User-Agent required; archive-first",
        reliability="archive_operational",  # real SAIC submissions bytes archived (examples/real_evidence)
        status="operational",
        priority="high",
        precursor_stage="",
        rights_note="Public domain filings; SEC fair-access policy requires a descriptive User-Agent.",
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
        family="procurement_forecast",
        signals=("forecast_requirement", "estimated_value", "expected_solicitation_quarter", "set_aside_intent"),
        access_method="bulk_download",  # agency-published artifacts (CSV/XLSX)
        auth="none",
        incremental="per-artifact version replace; row hash dedupe",
        identifiers=("agency", "naics", "forecast_id", "place_of_performance"),
        links_to=("sam_opportunities", "usaspending", "appropriations"),
        historical_depth="per-agency; typically current + prior fiscal year",
        native_cadence="quarterly-to-annual agency republication",
        recommended_poll="monthly artifact check",
        call_budget="minimal: bulk artifact download, replace on change",
        reliability="fixture_only",
        status="adapter_ready",
        priority="medium",
        precursor_stage="MARKET_ENGAGEMENT",
        rights_note="Public domain agency artifacts; per-agency column mappings required.",
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
        family="funding_assistance",
        signals=("funding_opportunity", "assistance_listing", "close_date", "award_ceiling"),
        access_method="rest_api",
        auth="none",
        incremental="Search2 keyword/date window + opportunity number dedupe",
        identifiers=("opportunity_number", "cfda", "agency_code"),
        links_to=("appropriations", "usaspending", "sbir"),
        historical_depth="rolling open + recently closed opportunities",
        native_cadence="continuous postings + amendments",
        recommended_poll="daily (filtered window)",
        call_budget="loose (keyless), windowed",
        reliability="fixture_only",
        status="adapter_ready",
        priority="medium",
        precursor_stage="FUNDING",
        rights_note="Public domain US government work; keyless API.",
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
        family="appropriations_budget",
        signals=("budget_request", "authorization", "appropriation", "program_funding", "reprogramming"),
        access_method="bulk_download",  # official structured budget artifacts
        auth="none",
        incremental="per-artifact version; TAS/federal-account row identity dedupe",
        identifiers=("tas", "federal_account", "cfda", "program_element", "budget_line_item"),
        links_to=("usaspending", "grants_gov", "federal_register", "sam_opportunities"),
        historical_depth="per enacted/requested fiscal year artifact",
        native_cadence="annual budget cycle + supplemental/reprogramming events",
        recommended_poll="monthly artifact check (event-driven around budget milestones)",
        call_budget="minimal: bulk artifact download",
        reliability="fixture_only",
        status="adapter_ready",
        priority="high",
        precursor_stage="AUTHORIZATION",
        rights_note="Public domain budget artifacts.",
    ),
    # ---------------------------------------------------------------- M14 new families ---
    "sbir": SourceSpec(
        id="sbir",
        name="SBIR/STTR Awards (SBIR.gov public API)",
        base_url="https://api.www.sbir.gov/public/api",
        rights="us_gov_work",
        retention_tier="B",  # historical awards are durable/immutable once published
        active=True,
        notes=(
            "M14: federal R&D awards — the earliest observable capability/commercialization precursor. "
            "Keyless JSON; carries firm UEI/DUNS + agency/phase/topic, enabling a deterministic "
            "SBIR-award -> USAspending-prime-award entity chain (R&D precursor -> procurement lead time). "
            "This source enriches capability evidence and precursor chains; it never independently creates "
            "a candidate or STRIKE."
        ),
        family="science_rd",
        signals=("sbir_award", "sttr_award", "rd_topic", "phase_progression", "commercialization_precursor"),
        access_method="rest_api",
        auth="none",
        incremental="award_year window + agency_tracking_number dedupe; start/rows pagination",
        identifiers=("uei", "duns", "firm", "agency_tracking_number", "solicitation_number", "topic_code"),
        links_to=("usaspending", "sec_edgar", "grants_gov", "sam_opportunities"),
        historical_depth="1983+ (multi-decade award history)",
        native_cadence="awards published as agencies report (batched)",
        recommended_poll="monthly (award_year window)",
        call_budget="tight: one connectivity/schema call + narrow firm/year window; archive-first",
        reliability="unverified",  # 2026-09-09 connectivity probe returned HTTP 403 (maintenance/bot-block)
        status="blocked",
        priority="high",
        precursor_stage="PROGRAM",
        rights_note=(
            "Public domain US government work; keyless public API. 2026-09-09: single connectivity probe "
            "to api.www.sbir.gov/public/api/awards returned HTTP 403 (provider maintenance / bot-block); "
            "adapter validated offline on fixtures. Retry connectivity when the provider is available."
        ),
    ),
    "sanctions_ofac": SourceSpec(
        id="sanctions_ofac",
        name="OFAC Sanctions Lists (SDN + Consolidated)",
        base_url="https://www.treasury.gov/ofac/downloads",
        rights="us_gov_work",
        retention_tier="A",  # designations are added/removed; each snapshot is point-in-time truth
        active=True,
        notes=(
            "M14: Treasury OFAC sanctions designations — a first-class exposure/threat evidence family "
            "(entity sanctioned, program, designation/removal). Bulk fixed-field/CSV + XML download "
            "(archive-first, near-zero call amplification). Entity exposure is matched conservatively by "
            "authoritative identity; a name-only match is a rejected weak join, never a silent collapse. "
            "This source contributes threat/exposure evidence; it never creates a procurement candidate."
        ),
        family="sanctions_trade",
        signals=("sdn_designation", "consolidated_designation", "program", "designation_change"),
        access_method="bulk_download",
        auth="none",
        incremental="full-list snapshot per publication; ent_num identity + content-hash diff",
        identifiers=("ent_num", "sdn_name", "program", "sdn_type"),
        links_to=("sec_edgar", "usaspending", "sbir"),
        historical_depth="current list snapshots; point-in-time via retained dated snapshots",
        native_cadence="irregular, event-driven (designations as issued)",
        recommended_poll="daily list snapshot (content-hash gated; only re-archive on change)",
        call_budget="minimal: one bulk file per changed publication",
        reliability="archive_operational",  # 2026-09-09: 1 bulk download -> 19,365 real designations parsed
        status="operational",
        priority="high",
        precursor_stage="",
        rights_note=(
            "Public domain US government work. Sanctions screening for compliance decisions has legal "
            "weight; Pyrnova uses it only as intelligence evidence, not as an authoritative screening tool. "
            "2026-09-09: host www.treasury.gov/ofac/downloads/sdn.csv confirmed (HTTP 200, 5.68MB, 19,365 "
            "designations); real bytes archived offline (git-ignored var/). Develop against the archive."
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


def sources_by_family() -> dict[str, list[SourceSpec]]:
    """Group registered sources by economic-domain family (manifest / operator view)."""
    grouped: dict[str, list[SourceSpec]] = {}
    for spec in REGISTRY.values():
        grouped.setdefault(spec.family, []).append(spec)
    return {fam: sorted(specs, key=lambda s: s.id) for fam, specs in sorted(grouped.items())}


def families() -> list[str]:
    """Distinct families that currently have at least one registered source."""
    return sorted({s.family for s in REGISTRY.values()})
