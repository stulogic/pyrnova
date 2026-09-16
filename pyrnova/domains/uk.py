"""United Kingdom national domain — third national customer-product vertical.

Authority: PYRNOVA-UK-SPEC-001 v1.1 accepted; PYRNOVA-UK-HISTORICAL-VALIDATION-001 owner-accepted/closed;
owner UK build authority granted. Executable UK national truth, not a seam with TODOs.

Accepted validation result (owner-adjudicated): a 49-case adversarial corpus qualified strict
precursor-before-market DLT in only **3/49** cases (Type 31e 9d, New Medium Helicopter 234d, NHS Federated
Data Platform 195d). n=3 is NOT sufficient for a national numeric DLT threshold, so **NO UK NUMERIC DLT
THRESHOLD IS AUTHORIZED** — DLT remains an observed attribute where defensible, never the primary success
gate (``dlt_calibration=None`` even though ``validated=True``). The broader accepted UK thesis IS supported:
the strongest validated proposition is decision-relevant acquisition STATE + consequential change + access +
incumbent/prime position + UK Industrial Position + Decision Window + POST-AWARD intelligence +
customer-specific action. The UK product is NOT primarily a pre-tender prediction engine.

Hard distinctions preserved (executable, tested):
  Material Change != Opportunity;  Opportunity != Access;  Access != customer decision;
  programme exists != Opportunity;  Industrial Position != Access;  Award != terminal state;
  direct award != QDC;  single source != automatically QDC;  QDC != commercial access;
  international / GtG != ordinary UK competition.
"""

from __future__ import annotations

from .base import NationalDomain, NationalSource, SourceActivation

UK = NationalDomain(
    code="GB",  # ISO-3166 alpha-2 for the United Kingdom
    name="United Kingdom",
    lifecycle=(
        "PIPELINE",             # published commercial pipeline / forward plan (programme exists != opportunity)
        "PRIOR_INFORMATION",    # PIN / early engagement
        "TENDER",               # tender / competitive procedure
        "AWARD",                # contract award (NOT a terminal state)
        "PERFORMANCE",          # delivery / contract management (post-award)
        "POST_AWARD_CHANGE",    # modifications, extensions, options, in-life change (post-award intelligence)
        "RECOMPETE",
    ),
    routes={
        "OPEN": "Open procedure — full open supplier competition.",
        "RESTRICTED": "Restricted procedure (selection stage then invited tender).",
        "COMPETITIVE_FLEXIBLE": "Competitive flexible / negotiated procedure.",
        "FRAMEWORK_CALLOFF": "Call-off under an existing framework (framework membership is a hard access variable).",
        "DIRECT_AWARD": "Direct award — does NOT itself imply SSCR / a Qualifying Defence Contract.",
        "SINGLE_SOURCE": "Single-source; SSCR/QDC applicability is a SEPARATE evidenced determination.",
        "INTERNATIONAL_GTG": "International programme / government-to-government — NOT ordinary UK competition.",
    },
    access_classes=(
        "OPEN_COMPETITION",         # open supplier competition
        "FRAMEWORK_SUPPLIER",       # framework-constrained access (membership is a hard variable)
        "PRIME",                    # prime access
        "SUPPLY_CHAIN",             # supply-chain access (prime closure != supply-chain closure)
        "INCUMBENT",                # incumbent position
        "DESIGN_AUTHORITY",         # embedded sovereign / design-authority position
        "INTERNATIONAL_PROGRAMME",  # international programme access
        "GTG_CONSTRAINED",          # government-to-government constrained route
        "SUBCONTRACTOR",
        "NO_ESTABLISHED_ACCESS",
        "UNKNOWN",
    ),
    industrial_position_classes=(
        # A national reasoning object, NOT a numeric score.
        "SOVEREIGN_CAPABILITY",         # sovereign industrial capability
        "UK_BUILD_WORKSHARE",           # UK build / workshare requirement (workshare != prime access)
        "DESIGN_AUTHORITY",             # established design authority
        "INTEGRATION_RESPONSIBILITY",   # integration responsibility
        "INCUMBENT_ARCHITECTURE",       # incumbent programme architecture
        "INTERNATIONAL_UK_ROLE",        # internationally allocated UK industrial role
        "UK_PRIME", "SME",
        "FOREIGN_OWNED_LOCALLY_PRESENT",  # UK ownership != Industrial Position; UK establishment != advantage
        "UNKNOWN",
    ),
    # CONSEQUENTIAL-CHANGE state model (UK-SPEC-001 v1.1 §2). A Material Change need NOT create an
    # Opportunity — it may expand, narrow, change access/prime, move the Decision Window, raise post-award
    # risk, open a capability insertion, or CLOSE an opportunity (cancellation / direct award / framework
    # exclusion / route closure remove opportunity).
    consequential_states=(
        "OPPORTUNITY_CREATED",
        "OPPORTUNITY_EXPANDED",
        "OPPORTUNITY_NARROWED",
        "ACCESS_CHANGED",
        "PRIME_POSITION_CHANGED",
        "DECISION_WINDOW_CHANGED",
        "OPPORTUNITY_CLOSED",
        "POST_AWARD_RISK_INCREASED",
        "CAPABILITY_INSERTION_OPENED",
    ),
    # Important-Miss FAILURE taxonomy (UK-SPEC-001 v1.1 §10) — the misclassifications the product must never
    # commit. DISTINCT from the consequential-change state model above.
    important_miss=(
        "HIDDEN_PRIOR_ENGAGEMENT_AS_DLT",     # hidden prior engagement credited as DLT
        "PROGRAMME_PROMOTED_TO_OPPORTUNITY",  # programme existence promoted to Opportunity
        "INDUSTRIAL_IMPORTANCE_AS_ACCESS",    # industrial importance mistaken for Access
        "PRIME_ROUTE_AS_MARKET_CLOSURE",      # prime route mistaken for total market closure
        "DIRECT_AWARD_AS_QDC",                # direct award mistaken for QDC
        "AWARD_AS_TERMINAL",                  # award treated as terminal
        "FRAMEWORK_IGNORED",                  # framework ignored
        "LATER_PAGE_PROJECTED_BACKWARD",      # later webpage content projected backward (mutable GOV.UK)
        "LONG_CHRONOLOGY_AS_DLT",             # long programme chronology presented as actionable DLT
        "WRONG_CUSTOMER_ACTION",              # wrong customer action generated
    ),
    evidence_languages=("en",),
    sources=(
        # OGL-covered / structured procurement data — potentially favourable production posture, subject to
        # ACTUAL record-level coverage (not yet confirmed): FIXTURE_ONLY (lawful replay-derived; live
        # production NOT activated). Historical accessibility is NOT production authorization.
        NationalSource("uk_contracts_finder", "Contracts Finder / Find a Tender",
                       SourceActivation.FIXTURE_ONLY, role="evidence",
                       note="Structured procurement data (OGL posture likely). Downstream evidence, not the "
                            "acquisition ontology. Live production pending record-level coverage confirmation; "
                            "FIXTURE_ONLY (lawful replay-derived only)."),
        NationalSource("uk_gov_uk", "GOV.UK OGL material", SourceActivation.FIXTURE_ONLY, role="evidence",
                       note="OGL-covered GOV.UK material. FIXTURE_ONLY (lawful replay-derived). Version-level "
                            "AS-OF required — first-published date is NOT proof the current page body existed then."),
        # Candidate families with UNRESOLVED production rights — UNKNOWN => DENY. Codified, not activated.
        NationalSource("uk_dsp", "Defence Sourcing Portal (DSP)", SourceActivation.DECLARED, role="evidence",
                       note="DSP-specific ingestion UNKNOWN => DENY. Activation pending rights review."),
        NationalSource("uk_ssro", "Single Source Regulations Office (SSRO)", SourceActivation.DECLARED,
                       role="evidence",
                       note="Blanket automated/commercial reuse UNKNOWN => DENY."),
        NationalSource("uk_nao", "National Audit Office (NAO)", SourceActivation.DECLARED, role="evidence",
                       note="Unrestricted commercial ingestion NOT established => DENY."),
        NationalSource("uk_vdr_attachments", "Tender attachments / VDR documents", SourceActivation.DECLARED,
                       role="evidence",
                       note="Attachments / VDR do NOT inherit notice rights automatically. UNKNOWN => DENY."),
        NationalSource("uk_supplier_material", "Supplier-published material", SourceActivation.DECLARED,
                       role="evidence",
                       note="Supplier copyright applies. UNKNOWN => DENY."),
        NationalSource("uk_archive_mirror", "Archive / search mirrors", SourceActivation.DECLARED,
                       role="evidence",
                       note="Archive/search mirrors UNKNOWN => DENY (also a mutable-page / back-projection risk)."),
    ),
    # NO UK NUMERIC DLT THRESHOLD is authorized (n=3 strict-qualifying cases). DLT stays an observed
    # attribute; it is NOT the primary UK success gate. Never fabricate a calibration.
    dlt_calibration=None,
    validated=True,
    build_authority=True,
    notes="UK build authority granted. NO numeric DLT threshold (n=3 strict-qualifying; DLT is an observed "
          "attribute, not the success gate). Strongest proposition: acquisition STATE + consequential "
          "change + access + incumbent/prime + UK Industrial Position + Decision Window + POST-AWARD "
          "intelligence + customer action. Award is not terminal; direct award != QDC; SSCR/QDC is a "
          "separate evidenced field; prime closure != supply-chain closure; international/GtG != ordinary "
          "competition. Version-level AS-OF (mutable GOV.UK): do not back-project later page revisions.",
)
