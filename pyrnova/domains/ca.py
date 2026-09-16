"""Canada national domain — fifth national customer-product vertical.

Authority: PYRNOVA-CA-SPEC-001 v1.0 owner-accepted/closed; PYRNOVA-CA-HISTORICAL-VALIDATION-001 + 002
owner-accepted/closed; owner Canadian build authority GRANTED. Executable Canadian national truth, not a
seam with TODOs.

Accepted validation doctrine (owner-adjudicated), implemented here:
  * Canadian acquisition behaviour is MECHANISM-SPECIFIC — competitive/open, directed/OEM, FMS/GtG,
    strategic-source and digital/ICT mechanisms carry DIFFERENT timing/access/industrial meaning and are
    NOT flattened into one "competition" model.
  * Calibration is CONFIDENCE-WEIGHTED and NON-UNIVERSAL. **NO Canadian national numeric DLT threshold is
    authorized or required** (``dlt_calibration=None`` even though ``validated=True``). DLT-to-Market and
    DLT-to-Commitment remain distinct where applicable; some mechanisms have no meaningful open-market DLT.
  * Timing evidence is QUALIFIED, never fabricated as exact: EXACT / BOUNDED / CONTAMINATED / N_A / UNKNOWN.
  * Bilingual evidence is a core evidentiary requirement: EN original and FR original are BOTH original
    evidence; a translation is PYRNOVA DERIVED and must never silently become evidentiary authority.
  * Retrospective evidence may invalidate a historical measurement, but must never be back-projected as
    knowledge available at an earlier AS-OF date.

Hard distinctions preserved (executable, tested):
  MATERIAL CHANGE != OPPORTUNITY;  OPPORTUNITY != ACCESS;  ACCESS != CUSTOMER FIT;  CUSTOMER FIT !=
  CUSTOMER DECISION;  Canadian ownership != eligibility;  Canadian presence != automatic advantage;
  Canadian Industrial Position != nationality;  ITB relevance != prime access;  ITB obligation != Value
  Proposition competitive effect;  public availability != production-source authorization;  translation
  != original evidence;  inaccessible prime route != absence of commercial opportunity.
"""

from __future__ import annotations

from .base import NationalDomain, NationalSource, SourceActivation

CA = NationalDomain(
    code="CA",
    name="Canada",
    # Canadian federal acquisition lifecycle — its own meaning, not a relabelled US/UK pipeline. Award is
    # NOT terminal (sustainment / in-service support and industrial consequence continue).
    lifecycle=(
        "FORECAST",              # forecast / planning signal (programme exists != opportunity)
        "ENGAGEMENT",            # industry engagement / RFI / LOI / Price & Availability
        "SOLICITATION",          # solicitation issued (RFP / ITT / invitation to tender)
        "EVALUATION",            # evaluation
        "AWARD",                 # contract award (not terminal)
        "SUSTAINMENT",           # delivery / in-service support / industrial consequence (post-award)
        "RECOMPETE",             # re-approach / recompete / successor programme
    ),
    routes={
        "OPEN_COMPETITIVE": "Open competitive solicitation — full supplier competition.",
        "SELECTIVE": "Selective tendering (pre-qualified / invited suppliers only).",
        "SUPPLY_ARRANGEMENT": "Call-up under a supply arrangement / standing offer.",
        "SOLE_SOURCE_ACAN": "Sole-source / Advance Contract Award Notice (ACAN) — directed to one supplier.",
        "DIRECTED_OEM": "Directed to an OEM / design authority (route crystallized around one supplier).",
        "FMS": "Foreign Military Sales — acquired via a foreign government's sales programme (US FMS).",
        "GTG": "Government-to-Government arrangement (distinct from open competition and from FMS).",
        "STRATEGIC_PARTNERSHIP": "Nested competition beneath an already-selected strategic prime/shipyard "
                                 "(e.g. NSS): WHO CAN COMPETE is decided by strategic-source allocation.",
        "NATIONAL_SECURITY_EXCEPTION": "Invoked national security exception (route/competition constrained).",
    },
    access_classes=(
        "OPEN_COMPETITION",         # open supplier competition
        "INCUMBENT",                # incumbent position
        "STANDING_OFFER_HOLDER",    # supply-arrangement / standing-offer holder
        "PRIME",                    # prime access
        "SUBCONTRACTOR",            # subcontract / supply-chain access (prime closure != supply-chain closure)
        "OEM_CONTROLLED",           # route controlled by an OEM / design authority (open prime unavailable)
        "QUALIFIED_SUPPLIER",       # holds a qualification gate needed to compete
        "STRATEGIC_SOURCE_PRIME",   # is the already-selected strategic prime/shipyard
        "NESTED_SUBCOMPETITION",    # can compete only in the nested competition beneath a strategic prime
        "GTG_CONSTRAINED",          # government-to-government constrained route
        "NO_ESTABLISHED_ACCESS",
        "UNKNOWN",
    ),
    # Canadian Industrial Position — a CATEGORICAL reasoning object, NOT a nationality flag and NOT a
    # synthetic score. DISTINCT from Access, Eligibility, Customer Fit, ITB obligation and VP effect
    # (cross-assignment fails loudly via assess_access / the evidenced ITB/VP field).
    industrial_position_classes=(
        "OEM_AUTHORITY",            # OEM authority
        "DESIGN_AUTHORITY",         # design authority
        "TECHNICAL_DATA_CONTROL",   # technical-data control
        "IP_CONTROL",               # IP control
        "CERTIFICATION_AUTHORITY",  # certification authority
        "INCUMBENCY",               # incumbency
        "CANADIAN_FACILITIES",      # existing Canadian facilities
        "QUALIFIED_SUPPLIER",       # qualified-supplier status (industrial attribute)
        "STRATEGIC_SOURCE_STATUS",  # strategic-source / strategic-shipyard status
        "PLATFORM_COMMONALITY",     # platform commonality
        "INTEGRATION_RESPONSIBILITY",  # integration responsibility
        "CANADIAN_SUPPLY_CHAIN",    # existing Canadian supply chain
        "DOMESTIC_PRODUCTION",      # domestic production
        "SUSTAINMENT_POSITION",     # sustainment position
        "FOREIGN_OWNED_LOCALLY_PRESENT",  # Canadian presence != advantage; ownership != eligibility
        "UNKNOWN",
    ),
    # CONSEQUENTIAL-CHANGE state model (CA-SPEC-001 v1.0). A Material Change need NOT create an Opportunity;
    # it may expand/narrow it, change access/route/industrial position/ITB-VP relevance/qualification, move
    # the Decision Window, open a capability insertion or supply-chain access, close/cancel, or reissue.
    # Domain-neutral names reused where an equivalent already exists (OPPORTUNITY_* / ACCESS_CHANGED /
    # DECISION_WINDOW_CHANGED / OPPORTUNITY_CLOSED / CAPABILITY_INSERTION_OPENED).
    consequential_states=(
        "OPPORTUNITY_CREATED",
        "OPPORTUNITY_EXPANDED",
        "OPPORTUNITY_NARROWED",
        "ACCESS_CHANGED",
        "ROUTE_CHANGED",
        "INDUSTRIAL_POSITION_CHANGED",
        "ITB_VP_RELEVANCE_CHANGED",
        "QUALIFICATION_CHANGED",
        "DECISION_WINDOW_CHANGED",
        "OPPORTUNITY_CLOSED",
        "CAPABILITY_INSERTION_OPENED",
        "SUPPLY_CHAIN_ACCESS_CHANGED",
        "PROGRAMME_CANCELLED",
        "PROGRAMME_REISSUED",       # a reissue is a FRESH opportunity — never silent continuity of a cancel
    ),
    # Canadian MECHANISM families (A–E). Different mechanisms have different timing/access/industrial truth.
    mechanisms=(
        "COMPETITIVE_OPEN",     # A: open/competitive — DLT-to-Market only when both endpoints defensible
        "DIRECTED_OEM",         # B: directed / OEM / incumbent — open prime competition may be absent
        "FMS_GTG",              # C: FMS / government-to-government — open-market DLT may be N_A
        "STRATEGIC_SOURCE",     # D: strategic source / access — WHO CAN COMPETE dominates
        "DIGITAL_ICT",          # E: digital / cyber / ICT — iterative multi-event market
    ),
    # Canadian TIMING classes — NO numeric national DLT threshold. Timing is QUALIFIED, never fabricated.
    timing_classes=("EXACT", "BOUNDED", "CONTAMINATED", "N_A", "UNKNOWN"),
    # ITB / Value-Proposition EVIDENCED states — a SEPARATE evidenced field. NEVER inferred from contract
    # value, Canadian ownership, presence, or access. ITB applying does NOT imply prime access; ITB
    # obligation is distinct from a Value-Proposition competitive effect.
    itb_vp_states=(
        "UNKNOWN",
        "ITB_OBLIGATION_APPLIES",       # ITB obligation applies (may apply even to an FMS acquisition)
        "ITB_NOT_APPLICABLE",
        "VALUE_PROPOSITION_RELEVANT",   # VP changes competitive strategy (distinct from ITB obligation)
        "VALUE_PROPOSITION_NOT_RELEVANT",
    ),
    important_miss=(
        "RFP_AS_FIRST_MARKET_EVENT",        # treating an RFP/RFP-date as the first supplier-market event
        "BACK_PROJECTED_DCB_METADATA",      # back-projecting current DCB/planning metadata to an earlier date
        "LATER_HISTORY_AS_EARLIER_KNOWLEDGE",  # later procurement history projected as earlier knowledge
        "ITB_INFERRED_FROM_VALUE",          # ITB inferred automatically (from value / ownership / access)
        "OWNERSHIP_AS_ADVANTAGE",           # Canadian ownership / presence inferred as advantage/eligibility
        "FMS_AS_ORDINARY_COMPETITION",      # FMS / GtG treated as ordinary open competition
        "INACCESSIBLE_ROUTE_AS_NO_OPPORTUNITY",  # inaccessible prime route treated as no opportunity
        "STRATEGIC_SOURCE_RFP_AS_OPEN_PRIME",    # strategic-source downstream RFP treated as open prime access
        "SILENT_CANCEL_REISSUE_CONTINUITY",  # cancellation/reissue/rename identity silently erased
        "BOUNDED_AS_EXACT",                 # bounded/contaminated timing converted into exact evidence
        "TRANSLATION_AS_ORIGINAL",          # a translation treated as original evidence
        "RESURRECTED_2006_SIX_DAY_DLT",     # resurrecting the invalidated three 6-day 2006 exact DLT values
    ),
    evidence_languages=("en", "fr"),   # EN and FR are BOTH original; a translation is PYRNOVA DERIVED
    sources=(
        # CanadaBuys downloadable / open datasets — strong candidate for future live production use, but the
        # EXACT dataset licensing must be verified before activation: FIXTURE_ONLY (lawful replay-derived).
        NationalSource("ca_canadabuys_dataset", "CanadaBuys downloadable / open datasets",
                       SourceActivation.FIXTURE_ONLY, role="evidence",
                       note="Downstream evidence; open-dataset posture likely favourable but EXACT record/"
                            "dataset licensing must be verified before activation. FIXTURE_ONLY (lawful "
                            "replay-derived only); live production NOT activated. Public availability is NOT "
                            "production-source authorization."),
        # Candidate families with UNRESOLVED production rights — UNKNOWN => DENY. Codified, not activated.
        NationalSource("ca_canadabuys_portal", "CanadaBuys portal pages", SourceActivation.DECLARED,
                       role="evidence",
                       note="Portal scraping / automation rights are NOT presumed. UNKNOWN => DENY."),
        NationalSource("ca_dnd_web", "DND / CAF ordinary web publications", SourceActivation.DECLARED,
                       role="evidence",
                       note="Ordinary web publications; commercial redistribution NOT presumed. UNKNOWN => DENY."),
        NationalSource("ca_canada_ca", "Canada.ca pages", SourceActivation.DECLARED, role="evidence",
                       note="Ordinary Canada.ca commercial redistribution rights are NOT presumed. UNKNOWN => DENY."),
        NationalSource("ca_dcb", "Defence Capabilities Blueprint / planning sources", SourceActivation.DECLARED,
                       role="evidence",
                       note="DCB automation rights are NOT presumed; DCB metadata must not be back-projected. "
                            "UNKNOWN => DENY."),
        NationalSource("ca_parliament", "Parliamentary / Senate material", SourceActivation.DECLARED,
                       role="evidence",
                       note="Parliamentary/Senate material; blanket automated/commercial reuse NOT presumed. "
                            "UNKNOWN => DENY."),
        NationalSource("ca_thirdparty_mirror", "Third-party tender mirrors", SourceActivation.DECLARED,
                       role="evidence",
                       note="Third-party mirrors remain DENIED unless explicitly authorized. UNKNOWN => DENY."),
    ),
    # NO Canadian national numeric DLT threshold is authorized or required. Calibration is confidence-
    # weighted, mechanism-specific and non-universal — never a single national number. Never fabricate one.
    dlt_calibration=None,
    validated=True,
    build_authority=True,
    notes="Canadian build authority granted. NO national numeric DLT threshold (calibration is confidence-"
          "weighted, mechanism-specific, non-universal). Mechanism-specific semantics (competitive/open, "
          "directed/OEM, FMS/GtG, strategic-source, digital/ICT). Timing is QUALIFIED (EXACT/BOUNDED/"
          "CONTAMINATED/N_A/UNKNOWN), never fabricated as exact. Bilingual: EN and FR are both original; a "
          "translation is PYRNOVA DERIVED, never evidentiary authority. Canadian Industrial Position is a "
          "categorical object distinct from nationality and Access. ITB/VP is a separate evidenced field; "
          "ITB != prime access. FMS/GtG and strategic-source cases can be commercially important without "
          "open-prime access. Cancellation/reissue must not create silent false continuity. Source rights "
          "fail closed (UNKNOWN => DENY); CanadaBuys datasets are FIXTURE_ONLY pending licence verification.",
)
