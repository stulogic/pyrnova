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
from enum import Enum


class RightsClass(str, Enum):
    """Rights posture for a source profile.

    The class is a policy label, never a legal conclusion.  A missing profile remains
    unknown and therefore denied by the gate.
    """

    GREEN = "GREEN"
    GREEN_WITH_CONDITIONS = "GREEN_WITH_CONDITIONS"
    AMBER = "AMBER"
    RED = "RED"
    BLACK = "BLACK"


class RightsState(str, Enum):
    CURRENTLY_APPROVED = "CURRENTLY_APPROVED"
    REVIEW_DUE = "REVIEW_DUE"
    RIGHTS_DEGRADED = "RIGHTS_DEGRADED"
    INGEST_DISABLED = "INGEST_DISABLED"
    DISPLAY_DISABLED = "DISPLAY_DISABLED"
    LICENSE_EXPIRED = "LICENSE_EXPIRED"


class StorageMode(str, Enum):
    RAW_ALLOWED = "RAW_ALLOWED"
    NORMALIZED_ONLY = "NORMALIZED_ONLY"
    NO_STORAGE = "NO_STORAGE"


@dataclass(frozen=True)
class SourcePolicy:
    """Typed, reviewed rights profile attached to :class:`SourceSpec`.

    Every field is explicit so ``unknown`` cannot silently become permission.  URLs and
    endpoint paths are allowlisted here; callers cannot broaden them by supplying a
    different source id, URL, or classification marker.
    """

    identity: str
    domain: str
    source_type: str
    policy_version: str = "source-rights-v1"
    basis: str = "unknown"
    scope: tuple[str, ...] = ()
    terms_url: str = "unknown"
    terms_version: str = "unknown"
    terms_hash: str = "unknown"
    reviewed_at: str = "unknown"
    review_due_at: str = "unknown"
    access_method: str = "unknown"
    commercial_use: str = "unknown"
    automated_access: str = "unknown"
    raw_storage: StorageMode = StorageMode.NO_STORAGE
    historical_retention: str = "unknown"
    retention_rule: str = "unknown"
    fact_use: str = "unknown"
    derived_use: str = "unknown"
    excerpt_use: str = "unknown"
    excerpt_rule: str = "unknown"
    fulltext_use: str = "unknown"
    redistribution: str = "unknown"
    attribution: str = "unknown"
    customer_display: str = "unknown"
    model_use: str = "unknown"
    model_processing_allowed: bool = False
    model_constraints: tuple[str, ...] = ()
    third_party_use: str = "unknown"
    licence: str = "unknown"
    licence_required: bool | None = None
    licence_reference: str = "unknown"
    licence_valid_until: str = "unknown"
    review_required: bool = True
    review_notes: str = ""
    rights_class: RightsClass | str = RightsClass.AMBER
    state: RightsState | str = RightsState.REVIEW_DUE
    allowed_hosts: tuple[str, ...] = ()
    allowed_methods: tuple[str, ...] = ("GET",)
    allowed_path_prefixes: tuple[str, ...] = ()
    # Public object URLs used only as attribution/provenance references.  They
    # do not authorize retrieval; transport uses allowed_hosts/path_prefixes.
    reference_hosts: tuple[str, ...] = ()
    reference_path_prefixes: tuple[str, ...] = ()
    # Official-publisher domain suffixes (e.g. ".gov", ".mil") accepted ONLY as
    # attribution/provenance references, never for retrieval.  This encodes
    # "authoritative U.S. government publisher" for first-party official-artifact
    # sources without creating any transport/crawling permission.
    reference_host_suffixes: tuple[str, ...] = ()
    attribution_text: str = ""
    max_excerpt_words: int = 25

    def __post_init__(self) -> None:
        if not self.identity.strip() or not self.domain.strip() or not self.source_type.strip():
            raise ValueError("source rights identity, domain, and source_type are required")
        if self.max_excerpt_words < 1:
            raise ValueError("max_excerpt_words must be positive")


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
    source_policy: SourcePolicy | None = None  # canonical reviewed rights profile; missing => deny

    @property
    def policy(self) -> SourcePolicy | None:
        """Compatibility alias used by rights gates and operator inspection."""
        return self.source_policy


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


def _structured_policy(
    *,
    identity: str,
    domain: str,
    source_type: str,
    rights_class: RightsClass = RightsClass.GREEN_WITH_CONDITIONS,
    state: RightsState = RightsState.CURRENTLY_APPROVED,
    storage: StorageMode = StorageMode.RAW_ALLOWED,
    hosts: tuple[str, ...],
    paths: tuple[str, ...],
    methods: tuple[str, ...] = ("GET",),
    reference_hosts: tuple[str, ...] = (),
    reference_paths: tuple[str, ...] = (),
    reference_host_suffixes: tuple[str, ...] = (),
    attribution: str = "Official source; retain a direct source URL.",
    notes: str = "",
) -> SourcePolicy:
    """Build a deliberately narrow reviewed profile without inventing licence terms."""
    return SourcePolicy(
        identity=identity,
        domain=domain,
        source_type=source_type,
        basis="Owner-approved constrained structured endpoint profile; licence and terms facts remain UNKNOWN.",
        scope=paths,
        access_method="structured_official_endpoint",
        commercial_use="owner_approved_constrained_structured_use",
        automated_access="conditional_reviewed_endpoint",
        raw_storage=storage,
        historical_retention="retain_point_in_time_evidence_when_permitted",
        retention_rule="retain hash and reviewed representation; never delete history for a later rights change",
        fact_use="structured_facts_only",
        derived_use="permitted_derived_with_attribution",
        excerpt_use="limited_excerpt_with_attribution",
        excerpt_rule="at most 25 words with direct source URL and attribution",
        fulltext_use="unknown",
        redistribution="unknown",
        attribution="required",
        customer_display="permitted_current_policy_only",
        model_use="derived_or_structured_only",
        model_processing_allowed=True,
        model_constraints=("structured facts or permitted derived content only", "retain attribution"),
        third_party_use="unknown",
        licence="unknown",
        licence_required=False,
        review_notes=notes,
        rights_class=rights_class,
        state=state,
        allowed_hosts=hosts,
        allowed_methods=methods,
        allowed_path_prefixes=paths,
        reference_hosts=reference_hosts,
        reference_path_prefixes=reference_paths,
        reference_host_suffixes=reference_host_suffixes,
        attribution_text=attribution,
    )


_USASPENDING_POLICY = _structured_policy(
    identity="usaspending", domain="api.usaspending.gov", source_type="structured_award_index",
    rights_class=RightsClass.GREEN, hosts=("api.usaspending.gov",),
    paths=("/api/v2/search/", "/api/v2/recipient/", "/api/v2/award/", "/api/v2/subawards/"),
    methods=("GET", "POST"),
    reference_hosts=("www.usaspending.gov",),
    reference_paths=("/award/", "/recipient/"),
)
_SAM_POLICY = _structured_policy(
    identity="sam_opportunities", domain="api.sam.gov", source_type="structured_opportunity_index",
    rights_class=RightsClass.GREEN_WITH_CONDITIONS, hosts=("api.sam.gov",),
    paths=("/opportunities/v2/search",), methods=("GET",),
    reference_hosts=("sam.gov",), reference_paths=("/opp/",),
    notes="Reject SAM HTML/workspace and sensitive entity APIs; validate payloads before archive/normalization.",
)
_FR_POLICY = _structured_policy(
    identity="federal_register", domain="www.federalregister.gov", source_type="structured_register_index",
    rights_class=RightsClass.GREEN, hosts=("www.federalregister.gov",),
    paths=("/api/v1/documents.json",),
    reference_hosts=("www.federalregister.gov",), reference_paths=("/documents/",),
)
_SEC_POLICY = _structured_policy(
    identity="sec_edgar", domain="data.sec.gov", source_type="structured_government_index_metadata",
    rights_class=RightsClass.GREEN_WITH_CONDITIONS, storage=StorageMode.NORMALIZED_ONLY,
    hosts=("data.sec.gov",), paths=("/submissions/", "/api/xbrl/companyfacts/"),
    reference_hosts=("www.sec.gov", "sec.gov"), reference_paths=("/Archives/edgar/data/",),
    notes="SEC structured submissions/company-facts metadata only; filing documents/fulltext are not blanket-approved.",
)
_OFAC_POLICY = _structured_policy(
    identity="sanctions_ofac", domain="www.treasury.gov", source_type="fixed_structured_sanctions_csv",
    rights_class=RightsClass.GREEN_WITH_CONDITIONS, hosts=("www.treasury.gov",),
    paths=("/ofac/downloads/sdn.csv", "/ofac/downloads/consolidated/"),
)
_GRANTS_POLICY = _structured_policy(
    identity="grants_gov", domain="api.grants.gov", source_type="structured_funding_index",
    rights_class=RightsClass.GREEN_WITH_CONDITIONS, hosts=("api.grants.gov",),
    paths=("/v1/api/",), methods=("POST",),
)
_SBIR_POLICY = _structured_policy(
    identity="sbir", domain="api.www.sbir.gov", source_type="structured_award_index",
    rights_class=RightsClass.GREEN_WITH_CONDITIONS, state=RightsState.INGEST_DISABLED,
    hosts=("api.www.sbir.gov",), paths=("/public/api/awards",),
    notes="Existing connector is retained for offline replay; live ingest remains disabled pending provider review.",
)
# Australian national domain (INTERNATIONAL-GOVERNMENT-ROLLOUT-001). AusTender is DOWNSTREAM
# EVIDENCE of an Australian acquisition, never the acquisition ontology. Live production ingestion
# of AusTender requires Australian source-rights approval that has NOT been granted, so the state is
# INGEST_DISABLED: live transport fails closed (UNKNOWN => DENY), while lawful owner-accepted
# historical/replay evidence may still back a DERIVED customer projection with attribution and may be
# displayed under current policy — exactly the SBIR replay posture. This registry policy governs
# rights (transport/derived/display); the national domain (pyrnova/domains/au.py) independently
# governs acquisition activation posture (FIXTURE_ONLY). Both fail closed and must agree.
_AU_AUSTENDER_POLICY = _structured_policy(
    identity="au_austender", domain="www.tenders.gov.au", source_type="structured_tender_notice_index",
    rights_class=RightsClass.GREEN_WITH_CONDITIONS, state=RightsState.INGEST_DISABLED,
    storage=StorageMode.NORMALIZED_ONLY,  # no raw-storage rights for AusTender; normalized facts only
    hosts=("www.tenders.gov.au",), paths=("/api/",),
    reference_hosts=("www.tenders.gov.au",), reference_paths=("/",),
    attribution="AusTender (Commonwealth of Australia); retain a direct source URL.",
    notes="AusTender is downstream evidence only. Live production ingestion requires Australian "
          "source-rights approval (not granted): INGEST_DISABLED. Lawful owner-accepted replay/"
          "historical evidence may back a derived, attributed customer projection.",
)
# PRELAUNCH-CONVERGENCE-001 Bundle 2 owner rights-posture ruling: OFFICIAL FIRST-PARTY
# U.S. GOVERNMENT APPROPRIATIONS AND ACQUISITION-FORECAST ARTIFACTS may be ingested when
# obtained directly from the authoritative U.S. government publisher (a .gov/.mil domain),
# access is public and un-circumvented, provenance + acquisition timestamp are retained,
# and rate/access constraints are respected.  Transport stays exact-host allowlisted; the
# .gov/.mil suffix authorizes only attribution/provenance references, never retrieval or
# blanket government-site crawling.  Third-party mirrors / commercial substitutes / copied
# paywalled material remain prohibited (unknown/conflicting rights still fail closed).
_OFFICIAL_GOV_PUBLISHER_SUFFIXES = (".gov", ".mil")
_APPROPRIATIONS_POLICY = _structured_policy(
    identity="appropriations", domain="www.usaspending.gov",
    source_type="official_us_gov_budget_artifact",
    rights_class=RightsClass.GREEN_WITH_CONDITIONS, state=RightsState.CURRENTLY_APPROVED,
    storage=StorageMode.RAW_ALLOWED,
    hosts=("www.usaspending.gov", "www.acquisition.gov"), paths=("/artifacts/", "/api/"),
    reference_host_suffixes=_OFFICIAL_GOV_PUBLISHER_SUFFIXES, reference_paths=("/",),
    notes=(
        "Owner ruling (PRELAUNCH-CONVERGENCE-001 Bundle 2): first-party official appropriations/"
        "budget artifacts from the authoritative U.S. government publisher only; bounded and auditable; "
        "not blanket crawling; SBIR/STTR and third-party mirrors remain out of scope."
    ),
)
_ACQUISITION_FORECAST_POLICY = _structured_policy(
    identity="acquisition_forecast", domain="www.acquisition.gov",
    source_type="official_us_gov_forecast_artifact",
    rights_class=RightsClass.GREEN_WITH_CONDITIONS, state=RightsState.CURRENTLY_APPROVED,
    storage=StorageMode.RAW_ALLOWED,
    hosts=("www.acquisition.gov",), paths=("/procurement-forecasts",),
    reference_host_suffixes=_OFFICIAL_GOV_PUBLISHER_SUFFIXES, reference_paths=("/",),
    notes=(
        "Owner ruling (PRELAUNCH-CONVERGENCE-001 Bundle 2): first-party official agency acquisition-"
        "forecast artifacts from the authoritative U.S. government publisher only; per-agency column "
        "mappings required; forecast rows cannot independently create candidates/STRIKEs."
    ),
)

_RESTRICTED_POLICIES = {
    "reuters": SourcePolicy(identity="reuters", domain="reuters.com", source_type="premium_news",
                             rights_class=RightsClass.BLACK, state=RightsState.INGEST_DISABLED),
    "bloomberg": SourcePolicy(identity="bloomberg", domain="bloomberg.com", source_type="premium_news",
                               rights_class=RightsClass.BLACK, state=RightsState.INGEST_DISABLED),
    "linkedin": SourcePolicy(identity="linkedin", domain="linkedin.com", source_type="platform_scrape",
                              rights_class=RightsClass.RED, state=RightsState.INGEST_DISABLED),
    "x": SourcePolicy(identity="x", domain="x.com", source_type="platform_scrape",
                      rights_class=RightsClass.RED, state=RightsState.INGEST_DISABLED),
    "generic_corporate": SourcePolicy(identity="generic_corporate", domain="unknown",
                                       source_type="corporate_disclosure", rights_class=RightsClass.AMBER,
                                       state=RightsState.DISPLAY_DISABLED,
                                       raw_storage=StorageMode.NORMALIZED_ONLY,
                                       review_notes="No connector; explicit domain profile required before use."),
}


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
        source_policy=_USASPENDING_POLICY,
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
        source_policy=_SAM_POLICY,
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
        reliability="archive_operational",  # 2026-09-09: HTTP 200 filtered probe; real documents archived
        status="operational",
        priority="medium",
        precursor_stage="AUTHORIZATION",
        rights_note=(
            "Public domain US government work; keyless public API. 2026-09-09: filtered connectivity "
            "probe returned HTTP 200 with real documents; bytes archived offline (git-ignored var/)."
        ),
        source_policy=_FR_POLICY,
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
        rights_note="Reviewed structured SEC metadata only; corporate filings are not blanket public domain. Descriptive User-Agent required.",
        source_policy=_SEC_POLICY,
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
        source_policy=_ACQUISITION_FORECAST_POLICY,
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
        source_policy=_GRANTS_POLICY,
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
        source_policy=_APPROPRIATIONS_POLICY,
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
            "Keyless JSON; carries firm UEI + agency/phase/topic, enabling a deterministic "
            "SBIR-award -> USAspending-prime-award entity chain (R&D precursor -> procurement lead time). "
            "This source enriches capability evidence and precursor chains; it never independently creates "
            "a candidate or STRIKE."
        ),
        family="science_rd",
        signals=("sbir_award", "sttr_award", "rd_topic", "phase_progression", "commercialization_precursor"),
        access_method="rest_api",
        auth="none",
        incremental="award_year window + agency_tracking_number dedupe; start/rows pagination",
        identifiers=("uei", "firm", "agency_tracking_number", "solicitation_number", "topic_code"),
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
        source_policy=_SBIR_POLICY,
    ),
    "au_austender": SourceSpec(
        id="au_austender",
        name="AusTender (Australian Government tender notices)",
        base_url="https://www.tenders.gov.au",
        rights="unknown",  # Australian source-rights approval not granted; fail closed for live use
        retention_tier="A",  # notices are amended/withdrawn; each observation is point-in-time truth
        active=False,        # not active for live production ingestion (INGEST_DISABLED)
        notes=(
            "INTERNATIONAL-GOVERNMENT-ROLLOUT-001: AusTender is DOWNSTREAM EVIDENCE of an Australian "
            "acquisition, never the acquisition ontology. Live ingestion requires Australian rights "
            "approval (not granted): INGEST_DISABLED. Owner-accepted historical/replay evidence may "
            "back a derived, attributed customer projection and be displayed under current policy."
        ),
        family="procurement_opportunities",
        signals=("tender_notice", "amendment", "cancellation", "contract_notice"),
        access_method="rest_api",
        auth="unknown",
        reliability="fixture_only",
        status="blocked",
        priority="medium",
        rights_note="Australian rights approval pending; live ingest disabled, replay-derived use only.",
        source_policy=_AU_AUSTENDER_POLICY,
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
        source_policy=_OFAC_POLICY,
    ),
    # Explicitly represented restricted/unreviewed families have no connectors and are inactive.
    **{
        key: SourceSpec(
            id=key,
            name=key.replace("_", " ").title(),
            base_url=("https://www.govinfo.gov" if key == "govinfo" else
                      "https://www.congress.gov" if key == "congress" else
                      "https://" + policy.domain),
            rights="unknown",
            retention_tier="C",
            active=False,
            status="blocked",
            rights_note=policy.review_notes or "No connector; inactive until a fixed reviewed profile exists.",
            source_policy=policy,
        )
        for key, policy in {
            **_RESTRICTED_POLICIES,
            "govinfo": SourcePolicy(identity="govinfo", domain="api.govinfo.gov",
                                     source_type="structured_government_api", rights_class=RightsClass.GREEN_WITH_CONDITIONS,
                                     state=RightsState.INGEST_DISABLED,
                                     allowed_hosts=("api.govinfo.gov",), allowed_methods=("GET",),
                                     allowed_path_prefixes=("/",),
                                     review_notes="Inactive official API profile only; full documents remain unreviewed/default denied."),
            "congress": SourcePolicy(identity="congress", domain="api.congress.gov",
                                      source_type="structured_government_api", rights_class=RightsClass.GREEN_WITH_CONDITIONS,
                                      state=RightsState.INGEST_DISABLED,
                                      allowed_hosts=("api.congress.gov",), allowed_methods=("GET",),
                                      allowed_path_prefixes=("/",),
                                      review_notes="Inactive official API profile only; full documents remain unreviewed/default denied."),
        }.items()
    },
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
