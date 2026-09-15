# Source rights authority

Status: `SOURCE-RIGHTS-001 OWNER ACCEPTED/CLOSED` for this bounded authority record. Customer #1 is
`CONDITIONAL GO` on source rights only; this does not authorize Live Ops, deployment, publication, or
overall readiness.

Governing rule: **EXTRACT THE FACT. PRESERVE PROVENANCE. MINIMIZE COPIED EXPRESSION.** The evidence chain
is source evidence -> structured fact -> Pyrnova derivation -> customer consequence -> decision support.
`SOURCE FACT`, `PYRNOVA DERIVED`, `MODEL EXPLANATION`, and `HUMAN ASSESSMENT` remain separate origins;
derived intelligence is not a redistribution permission.

`pyrnova.sources.registry.SourceSpec.source_policy` is the canonical source-rights policy data. A source
without a reviewed policy is unknown and denied. The policy records identity, domain and endpoint scope,
source type, basis, access, commercial and automation posture, raw/normalized/no-storage representation,
historical retention, fact/derived/excerpt/fulltext/redistribution rules, attribution, customer display,
model and third-party use, licence and review facts, class, state, and policy version.

The rights classes are `GREEN`, `GREEN_WITH_CONDITIONS`, `AMBER`, `RED`, and `BLACK`. Automated ingest,
storage, customer display, and model processing require a current `GREEN` or `GREEN_WITH_CONDITIONS`
profile with explicit finite permissions. Unknown, review-due, degraded, expired, disabled, restricted,
unattributed, out-of-scope, or unprofiled material fails closed.

The initial approved substrate is constrained structured official endpoints for USAspending, SAM, and
Federal Register, plus individually reviewed structured paths for OFAC, Grants.gov, SBIR offline replay,
agency artifacts, SEC submissions/company-facts metadata, and the official GovInfo and Congress APIs.
GovInfo/Congress documents remain unreviewed. SAM is API/extract only: HTML, workspace, sensitive or
non-public entity data, FOUO/CUI, and D&B fields are denied. Corporate sources remain AMBER until an
explicit domain profile is GREEN_WITH_CONDITIONS and default to `NORMALIZED_ONLY`; no connector expansion
is implied. SEC filing documents, Reuters/Bloomberg and other premium sources, LinkedIn/X scraping, and
federal HTML/document surfaces remain denied or inactive. Restricted news/social use requires an explicit
recorded rights/licence decision before production. `.gov` does not mean public domain; section 105 applies
only to qualifying federal works and third-party exceptions receive conservative screening.

Excerpt use prefers facts and the minimum useful quote. The internal 25-word convention is not a legal safe
harbour; copied excerpts require attribution and a direct URL. Unknown licence, terms, review, scope, or
model constraints remain unknown and deny permission.

Historical evidence is retained according to the recorded retention rule and hash provenance. A later
rights degradation does not delete history; every current display read checks the current policy and may
return only identifiers, provenance, and a rights diagnostic when source material is blocked.
