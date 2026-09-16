"""Canada national-domain seam.

Authority: PYRNOVA-CA-SPEC-001 v1.0 accepted; historical validation running externally. This seam
declares Canadian national truth so the module can follow without an architecture rewrite. It does NOT
fabricate the validation result: ``validated=False`` and ``dlt_calibration=None`` until recorded.

Preserved Canadian meaning: Canadian acquisition lifecycle and access; Canadian Industrial Position;
ITB (Industrial and Technological Benefits) / Value Proposition; **bilingual evidence with
original-language authority** (English AND French are original; translation is PYRNOVA DERIVED, never
authoritative); Canadian ownership != eligibility and Canadian presence != automatic advantage.
"""

from __future__ import annotations

from .base import NationalDomain, NationalSource, SourceActivation

CA = NationalDomain(
    code="CA",
    name="Canada",
    lifecycle=(
        "FORECAST",             # forecast of tender opportunities
        "ENGAGEMENT",           # industry engagement / RFI
        "SOLICITATION",         # solicitation (RFP / invitation to tender)
        "EVALUATION",
        "AWARD",
        "PERFORMANCE",
        "RECOMPETE",
    ),
    routes={
        "OPEN_COMPETITIVE": "Open competitive solicitation.",
        "SELECTIVE": "Selective tendering (pre-qualified / invited).",
        "SUPPLY_ARRANGEMENT": "Call-up under a supply arrangement / standing offer.",
        "SOLE_SOURCE": "Sole-source / advance contract award notice (ACAN).",
        "NATIONAL_SECURITY_EXCEPTION": "Invoked national security exception.",
    },
    access_classes=("INCUMBENT", "STANDING_OFFER_HOLDER", "PRIME", "SUBCONTRACTOR", "NO_ESTABLISHED_ACCESS", "UNKNOWN"),
    industrial_position_classes=(
        "ITB_OBLIGATED", "VALUE_PROPOSITION_RELEVANT", "SOVEREIGN_CAPABILITY",
        "CANADIAN_PRESENCE", "FOREIGN_OWNED_LOCALLY_PRESENT", "UNKNOWN",
    ),
    important_miss=(
        "ROUTE_CHANGE", "PROGRESSION", "CANCELLATION", "CONSOLIDATION", "RE_SCOPE",
        "ITB_VALUE_PROPOSITION_CHANGE", "NSE_INVOCATION",
    ),
    evidence_languages=("en", "fr"),   # both original; translation is PYRNOVA DERIVED, not authoritative
    sources=(
        NationalSource("ca_canadabuys", "CanadaBuys / Buyandsell tenders", SourceActivation.DECLARED,
                       role="evidence", note="Downstream evidence; activation pending rights review."),
    ),
    dlt_calibration=None,      # historical validation running externally — do NOT invent it
    validated=False,
    build_authority=False,
    notes="Seam prepared. Bilingual original-language authority: FR and EN are both original; any "
          "translation is PYRNOVA DERIVED. Await accepted validation + build authority for the module.",
)
