"""Australian national domain — first implemented national increment.

Authority: PYRNOVA-AU-SPEC-001 accepted; historical replay passed owner adjudication; owner build
authority granted. This is executable national truth, not interfaces with TODOs.

National truth preserved here (NOT flattened into a universal ontology):
* the Australian acquisition lifecycle and route semantics (open / limited / prequalified panel /
  FMS / GtG / direct) — competitive vs limited vs government-to-government are distinct meanings;
* Australian access position;
* Australian Industrial Position, with **AIC (Australian Industry Capability) distinct from sovereign
  capability**, and **foreign ownership != procurement ineligibility**;
* AusTender is **downstream evidence, NOT the acquisition ontology**;
* Important Miss behaviour: progression, cancellation, consolidation, re-scope, route change,
  FMS/GtG case movement;
* strict AS-OF (enforced by the shared kernel);
* Australian source-rights ownership — activation is fail-closed (UNKNOWN => DENY); production
  acquisition requires rights approval, so live adapters are FIXTURE_ONLY until then.
"""

from __future__ import annotations

from .base import DLTCalibration, NationalDomain, NationalSource, SourceActivation

AU = NationalDomain(
    code="AU",
    name="Australia",
    # Australian Defence/major acquisition lifecycle — its own meaning, not a relabelled US pipeline.
    lifecycle=(
        "CAPABILITY_NEED",        # need / IIP capability stream identified
        "MARKET_APPROACH",        # RFI / industry engagement / EOI
        "APPROACH_TO_MARKET",     # ATM: RFT / RFP / limited approach issued
        "EVALUATION",             # tender evaluation
        "APPROVAL_GATE",          # government / capability approval (e.g. 1st/2nd pass)
        "CONTRACT",               # contract signature
        "DELIVERY_SUSTAINMENT",   # delivery + sustainment
        "RECOMPETE_EXTENSION",    # re-approach / option / sustainment recompete
    ),
    routes={
        "OPEN": "Open approach to market — any eligible supplier may respond.",
        "PREQUALIFIED_PANEL": "Approach limited to members of a standing offer / panel arrangement.",
        "LIMITED": "Limited tender — approach to one or more nominated suppliers (competition constrained).",
        "SOLE_SOURCE": "Direct / sole-source approach to a single supplier.",
        "FMS": "Foreign Military Sales — acquired via a foreign government's sales program (US FMS).",
        "GTG": "Government-to-Government arrangement (distinct from open competition and from FMS).",
    },
    access_classes=(
        "INCUMBENT", "PANEL_MEMBER", "PRIME", "SUBCONTRACTOR", "TEAMING_PARTNER",
        "NO_ESTABLISHED_ACCESS", "UNKNOWN",
    ),
    industrial_position_classes=(
        "AIC_ALIGNED",                    # Australian Industry Capability contribution
        "SOVEREIGN_CAPABILITY",           # sovereign industrial capability (DISTINCT from AIC)
        "RESILIENCE_RELEVANT",            # supply-chain resilience relevance
        "LOCAL_PRESENCE",                 # locally present (may be foreign-owned)
        "FOREIGN_OWNED_LOCALLY_PRESENT",  # foreign ownership does NOT imply ineligibility
        "UNKNOWN",
    ),
    important_miss=(
        "ROUTE_CHANGE",          # e.g. open -> limited, or a shift to FMS/GtG
        "PROGRESSION",           # lifecycle progression a customer must not miss
        "CANCELLATION",          # withdrawn / cancelled approach
        "CONSOLIDATION",         # requirements consolidated across programs
        "RE_SCOPE",              # scope materially changed
        "FMS_GTG_MOVEMENT",      # movement of an FMS / GtG case
        "APPROVAL_GATE_MOVEMENT",  # capability approval gate reached/slipped
    ),
    evidence_languages=("en",),
    sources=(
        # AusTender is downstream EVIDENCE of an acquisition, never the acquisition ontology itself.
        NationalSource("au_austender", "AusTender", SourceActivation.FIXTURE_ONLY, role="evidence",
                       note="Downstream evidence only. Live production acquisition requires rights "
                            "approval; FIXTURE_ONLY until then (UNKNOWN => DENY)."),
        NationalSource("au_defence_iip", "Defence Integrated Investment Program", SourceActivation.DECLARED,
                       role="evidence", note="Forward capability signal; activation pending rights review."),
        NationalSource("au_pgpa_annual", "PGPA / portfolio budget evidence", SourceActivation.DECLARED,
                       role="evidence", note="Appropriations/budget evidence; activation pending rights review."),
    ),
    # Accepted AU historical replay result (owner-adjudicated): 44-case corpus, 24 qualifying DLT cases,
    # median DLT-to-Market 654.5 days, conservative P25 105 days, strict AS-OF PASS, no material future
    # leakage. These numbers are the CITED accepted validation, not invented here.
    dlt_calibration=DLTCalibration(
        median_dlt_to_market_days=654.5,
        p25_days=105.0,
        corpus_size=44,
        qualifying_cases=24,
        source_reference="PYRNOVA-AU-SPEC-001 accepted historical replay (owner-adjudicated PASS)"),
    validated=True,
    build_authority=True,
    notes="AU build authority granted. AusTender is downstream evidence, not the acquisition ontology. "
          "AIC is distinct from sovereign capability; foreign ownership does not imply ineligibility.",
)
