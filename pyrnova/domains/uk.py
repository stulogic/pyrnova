"""United Kingdom national-domain seam.

Authority: PYRNOVA-UK-SPEC-001 v1.1 accepted; historical validation is running externally. This seam
declares UK national truth so a UK module can follow without another architecture rewrite. It does NOT
fabricate the validation result: ``validated=False`` and ``dlt_calibration=None`` until the accepted
result is recorded.

Preserved UK meaning: consequential-change intelligence; acquisition context; access; incumbent/prime
position; UK Industrial Position; Decision Window; post-award intelligence; and the hard distinctions
Material Change != Opportunity, Opportunity != Access, Access != customer decision, and direct award
!= automatic SSCR/QDC (a direct award does not itself imply Single Source Contract Regulations / the
Qualifying Defence Contract regime).
"""

from __future__ import annotations

from .base import NationalDomain, NationalSource, SourceActivation

UK = NationalDomain(
    code="GB",  # ISO-3166 alpha-2 for the United Kingdom
    name="United Kingdom",
    lifecycle=(
        "PIPELINE",             # published commercial pipeline / forward plan
        "PRIOR_INFORMATION",    # PIN / early engagement
        "TENDER",               # tender / competitive procedure
        "AWARD",                # contract award
        "PERFORMANCE",          # delivery / contract management
        "POST_AWARD_CHANGE",    # modifications, extensions, in-life change (post-award intelligence)
        "RECOMPETE",
    ),
    routes={
        "OPEN": "Open procedure.",
        "RESTRICTED": "Restricted procedure (selection stage then invited tender).",
        "COMPETITIVE_FLEXIBLE": "Competitive flexible / negotiated procedure.",
        "FRAMEWORK_CALLOFF": "Call-off under an existing framework.",
        "DIRECT_AWARD": "Direct award — does NOT itself imply SSCR / a Qualifying Defence Contract.",
        "SINGLE_SOURCE": "Single-source; SSCR/QDC applicability is a separate determination.",
    },
    access_classes=("INCUMBENT", "FRAMEWORK_SUPPLIER", "PRIME", "SUBCONTRACTOR", "NO_ESTABLISHED_ACCESS", "UNKNOWN"),
    industrial_position_classes=(
        "UK_PRIME", "SME", "SOVEREIGN_CAPABILITY", "FOREIGN_OWNED_LOCALLY_PRESENT", "UNKNOWN",
    ),
    important_miss=(
        "ROUTE_CHANGE", "PROGRESSION", "CANCELLATION", "CONSOLIDATION", "RE_SCOPE",
        "POST_AWARD_MODIFICATION", "SSCR_QDC_DETERMINATION",
    ),
    evidence_languages=("en",),
    sources=(
        NationalSource("uk_contracts_finder", "Contracts Finder / Find a Tender", SourceActivation.DECLARED,
                       role="evidence", note="Downstream evidence; activation pending rights review."),
    ),
    dlt_calibration=None,      # historical validation running externally — do NOT invent it
    validated=False,
    build_authority=False,     # seam only; national module build pending accepted validation + authority
    notes="Seam prepared. Await accepted UK historical validation + explicit build authority before "
          "implementing the national module. No validation result fabricated.",
)
