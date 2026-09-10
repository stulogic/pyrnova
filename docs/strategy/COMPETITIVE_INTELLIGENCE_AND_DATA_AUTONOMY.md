# Pyrnova competitive intelligence & strategic data autonomy doctrine

_Status: canonical strategic authority · effective 2026-09-09 · companion to
`docs/strategy/COMPETITIVE_DOCTRINE.md`_

> **Authority level.** Binding strategic authority (level 1 in `00-INDEX.md`), alongside
> `COMPETITIVE_DOCTRINE.md`. It governs *how* Pyrnova studies competitors and *how* it reasons about
> rented data. It does **not** authorize implementation — `02-EXECUTION.md` alone does — and the
> operational build items below are **roadmap/deferred**, gated by the finishability rule (D-047) and
> Phase 1 non-goals (D-048). The proper-means boundary and rights rules are binding **now**. See D-053.

## Governing principle

Collect aggressively. Analyze ruthlessly. Reverse engineer lawfully. Recreate independently. Replace
dependencies wherever rational. Measure competitors rather than admiring them. Exploit legitimate
weaknesses. Protect Pyrnova's intelligence estate. **Never trade a durable company for a short-term
advantage obtained through unlawful or contaminated information.** The objective is maximum *lawful*
competitive advantage and maximum long-term strategic autonomy.

---

## A. Binding now (operating discipline)

### A1. Proper-means rule (binding)

Competitive aggression is unlimited **inside lawful and contractually permissible acquisition**. Pyrnova
**may** aggressively exploit: public information; open data; public records; FOIA and equivalent lawful
disclosure; lawfully purchased products; ordinary authorized access; independent research; reverse
engineering where legally permitted; independent derivation; public technical artifacts; public
professional information; customer-provided observations they are entitled to share; and Pyrnova's own
experimentation.

Pyrnova **must not** rely on: unauthorized system access; credential theft or misuse; circumvention
outside applicable legal permission; malware; bribery; misrepresentation designed to obtain protected
information; inducing breach of confidentiality; trade-secret theft; stolen databases; leaked
confidential source code; or knowingly receiving improperly acquired information. This boundary is
strategic as well as legal: **an independently developed capability is an asset; a capability dependent
on someone else's stolen secret is a liability.** Reinforces the ethical/legal boundary in
`COMPETITIVE_DOCTRINE.md` and the terms/rights rules in `01-PROJECT-AUTHORITY.md` and
`docs/specs/SOURCE_INGESTION.md`.

### A2. YELLOW edge-case review (binding)

Competitive intelligence should push hard against legitimate boundaries but must not **guess** where they
are. Any proposed collection technique with uncertain terms-of-service, copyright, automated-collection,
reverse-engineering, access-control, database-rights, employee-movement, commercial-data-reuse, or
contractual implications is classified **YELLOW**. YELLOW is **not prohibited** — it means **legal review
before operationalization**. Maintain reusable counsel decisions so identical questions are not
re-reviewed. Where a lawful method produces substantially the same intelligence, prefer it. (Until such a
counsel process exists, YELLOW techniques stay un-operationalized.)

### A3. Clean-room separation (binding where reverse engineering is used)

Where reverse engineering is legally permitted and useful, separate **OBSERVATION** from
**IMPLEMENTATION**. The observation side documents externally observable behavior/specifications obtained
through lawful use. The implementation side builds Pyrnova's solution **independently** from those
observations and public technical knowledge. Do not copy proprietary source code, ingest leaked code, or
use improperly obtained confidential competitor documentation — even when it would save engineering time.
Independent reconstruction is strategically superior because Pyrnova **owns** the resulting capability.

### A4. Personnel intelligence boundary (binding)

Competitor personnel may be studied as commercial actors only where professionally relevant and lawfully
available: role, career history, public bio, public presentations/publications, patents, expertise,
public statements, responsibilities, board/affiliations, and observable hiring/departure patterns. **Do
not** build dossiers around private vulnerability, family members, private communications, personal
leverage, or sensitive private information; **do not** solicit confidential information from employees or
induce breach of confidentiality/fiduciary/contractual/trade-secret obligations. When hiring from a
competitor, the asset is talent and legitimate experience — **never** the former employer's confidential
information.

### A5. Strategic data autonomy (binding operating discipline)

Every rented dataset is a dependency, and dependencies are continuously challenged. For every material
commercial data source, maintain an assessment of: **VALUE, COST, RIGHTS, UNIQUENESS, REPLICABILITY,
SUBSTITUTION DIFFICULTY, CUSTOMER IMPORTANCE, EXIT COST** — and keep asking **"Why are we still paying
for this?"** Continue licensing a source only when it provides durable strategic value that cannot
economically be recreated; otherwise open a replacement program (A-roadmap B1). Distinguish whether a
paid source's value derives from **exclusive underlying information** (licensing may stay rational) or
**merely difficult engineering** (strongly consider recreating). Do not pay indefinitely for commodity
information because buying it was convenient; do not spend years reproducing genuinely proprietary
infrastructure when license economics are attractive. Extends "own the intelligence layer, rent evidence
selectively" (strategic data research; D-008).

### A6. Rights contamination (binding)

**No commercial source may silently contaminate Pyrnova's permanent intelligence estate.** For
strategically significant sources, understand raw-data retention rights, derived-data rights, model-input
rights, AI-extraction rights, customer-display rights, historical-archival rights, termination rights,
deletion requirements, and whether derived assertions survive cancellation. Maintain **technically
separable provenance** where necessary so Pyrnova can always answer **"If we terminate this supplier
tomorrow, exactly what intelligence do we lose?"** — and the answer should become *less every year*.
Implements the rights-metadata / evidence-independence principles in `01-PROJECT-AUTHORITY.md` and
`PHASE_1_PRODUCT_AUTHORITY.md`.

---

## B. Roadmap / deferred (product capability — NOT current authority)

These are strategically endorsed but **not** Phase 1 scope; they are recorded so nothing material is
silently dropped, and they are gated by `02-EXECUTION.md`, D-047, and D-048. See roadmap area 23.

### B1. Living competitor dossiers + change detection

Maintain living, intelligence-history dossiers on strategically relevant competitors from lawful sources
(public disclosures; procurement/contract records; regulatory filings; patents; litigation; websites and
archives; product/API/developer docs; publicly observable product behavior; pricing; conference/academic
material; interviews; earnings; job postings; public bios; partnership/acquisition activity; customer
reviews and public communities; security disclosures; lawfully observable public-internet infrastructure;
and Pyrnova's own observations from legitimate product use). Monitor competitors for material change (new
products, pricing, APIs, hires, departures, customer/government wins, funding, acquisitions, partnerships,
new data suppliers, changed terms, patents, coverage, retirements, rebrands, dissatisfaction, outages,
security incidents, positioning). **Competitors are themselves entities in the external world Pyrnova
models** — eventually Pyrnova applies its own intelligence architecture to its competitive environment.
Extends roadmap area 5 (competitor intent inference).

### B2. Product acquisition, teardown & reproducible benchmarks

Where lawful, treat a competing product as an intelligence source: purchase legitimate subscriptions or
use ordinary trials where justified; systematically observe functionality, workflow, latency, result
quality, data freshness, coverage, failure modes, search/ranking/entity-resolution, citations, alerting,
exports, integrations, customer-available API behavior, exposed provenance, UI decisions, limitations,
and version-to-version changes — recorded as structured competitive intelligence. Determine what problem
the competitor actually solves, how well, what information is necessary to produce the result, what can be
recreated independently, and whether Pyrnova can build a superior implementation. Maintain **reproducible
competitive benchmarks**; treat marketing claims as evidence to investigate, not facts to accept.

### B3. Vendor displacement program

For important paid sources: identify exactly what intelligence the source contributes; separate valuable
signal from unnecessary volume; identify authoritative/public upstream sources; determine which
normalization/entity-resolution/enrichment/inference creates the vendor's apparent value; build an
independent parallel pipeline; run it against the commercial source; and measure coverage, precision,
recall (where measurable), freshness, historical depth, entity quality, customer decision value,
reliability, operating cost, and legal rights. **Do not cancel because Pyrnova recreated ~80% of the
rows; cancel when the internally controlled alternative delivers sufficient decision value.** The target
is strategic independence, not superficial data parity.

---

## Adversary mindset & corporate self-interest

Assume important competitors would prefer Pyrnova not to exist and will react when it takes meaningful
customers; assume successful features are copied; assume data suppliers raise prices as dependence becomes
obvious; assume incumbents use distribution, bundling, and relationships against Pyrnova. Identify what
they rent vs. own, where their moat is real vs. theatre, and where their scale makes them slow — then
attack the latter. Within legal, contractual, and ethical boundaries, decisions favor Pyrnova's ownership
of strategic capabilities, independence, margins, data estate, customers, speed, defensibility, and
long-term enterprise value. Do not preserve a competitor's comfort, maintain unnecessary vendor dependency
out of politeness, avoid a superior feature because an incumbent shipped something similar first, or
surrender lawful advantages. The desired competitor reaction — **"they are coming after the parts of our
business that matter"** — is earned through lawful execution, never unlawful behavior.
