# Phase 1.5 Industrial Replay Evidence Pack

Status: evaluation evidence ready; production implementation locked

Version: `industrial_replay_corpus_v1`

Retrieval date: 2026-09-12
Benchmark perspective: synthetic U.S. B2B industrial supplier, $250M-$2B revenue-equivalent, selling automation, process control, electrical/power infrastructure, and monitoring/instrumentation technology into semiconductor facilities.

## 1. Scope and decision boundary

This pack tests whether the current Pyrnova kernel can preserve point-in-time industrial changes and turn them into falsifiable commercial-consequence hypotheses. It does not create a customer, assert any supplier relationship, estimate seller revenue, modify Phase 1 scoring, add source adapters, change production behavior, or open Phase 1.5 execution authority.

The evaluated chain is:

`CHANGE -> RELATIONSHIP -> CONSEQUENCE -> DECISION -> OUTCOME`

Every prospective call is frozen at its stated cutoff. Later evidence is a separate outcome or later assessment. A source is visible only when `available_at <= cutoff`. Unknown first-observed times remain `null`; exact SEC acceptance timestamps are retained only where they are knowable from the filing record.

Direction, magnitude, and horizon use the approved categorical vocabulary. They are not disguised numerical estimates. Sourced project dollars, dates, capacity, and schedules remain separate facts. Evidence strength is about source support; analytical confidence is about the inference.

## 2. Artifacts and method

- `examples/replay/industrial_phase1_5/source_inventory_v1.json` contains 27 authoritative source records, native identifiers, timing, extraction metadata, paraphrased evidence spans, retention decisions, and SHA-256 hashes of those retained spans.
- `examples/replay/industrial_phase1_5/corpus_v1.json` contains seven cases, 18 frozen cutoff assessments, seven stable facility identities, evidence-backed relationships, nine later outcomes, and eleven required negative controls.
- `tests/test_phase1_5_replay_evidence.py` validates schema boundaries, hashes, rights fields, cutoff visibility, immutable outcome separation, approved semantics, facility identity separation, and negative-control coverage. It intentionally does not import production pipeline or scoring modules.

Facility identifiers use site and jurisdiction facts plus a source-native project identity. Brand or owner name alone is insufficient. `SUPPLIES_TO` is never inferred from portfolio fit.

## 3. Corpus status

| Case | Tier | Cutoffs | Status | Principal falsification question |
|---|---:|---:|---|---|
| Intel Ohio | Primary | 3 | REPLAY READY | Does a major initial opportunity get revised downward when schedule evidence deteriorates? |
| TSMC Arizona | Primary | 4 | REPLAY READY | Can additive fab scope be separated from duplicate headlines and schedule revisions? |
| Micron New York | Primary | 3 | REPLAY READY | Is a decades-long $100B headline kept separate from time-phased addressability? |
| Hyundai Georgia | Secondary | 2 | REPLAY READY | Does the consequence chain transfer from fab construction to a smart automotive plant and operating ramp? |
| Toyota North Carolina battery | Secondary | 3 | REPLAY READY | Can added lines and plant production be distinguished from an unallocated national headline? |
| Eli Lilly Lebanon | Secondary | 2 | REPLAY READY | Does facility consequence transfer while regulated-process capability remains a customer-relevance gate? |
| Novo Nordisk North Carolina | Secondary | 2 | REPLAY READY | Can Clayton-specific phasing remain separate from other facilities in the same filing? |

“Replay ready” here means the source-reference fixture, cutoffs, frozen calls, outcomes, and controls are ready for evaluator work. It does not mean automated acquisition is ready or that the existing procurement replay runner can execute this schema unchanged.

## 4. Primary case adjudication

### 4.1 Intel Ohio

Authoritative evidence: Intel’s dated 2022 announcement,[1] the November 2024 final CHIPS award,[2] Intel’s 2024 Form 10-K published in January 2025,[3] and Intel’s February 2025 Ohio schedule update.[4]

| Cutoff | Evidence available then | Frozen consequence call | Reasonable commercial decision |
|---|---|---|---|
| 2022-01-21 | More than $20B, two fabs, 2025 production expectation, supplier ecosystem | POSITIVE / MAJOR / LONG; high evidence, medium confidence | Begin account/site mapping and qualification-window research; do not assume an award. |
| 2024-11-26 | Final federal support, but multi-state and milestone-conditioned | MIXED / MAJOR / LONG; high evidence, medium confidence | Keep active but require a current Ohio schedule before escalating coverage. |
| 2025-02-28 | Demand/financial delay disclosure plus Mod 1 operations in 2030-31 and Mod 2 in 2032 | NEGATIVE / MAJOR / LONG; high evidence and confidence | Rephase pipeline years later, lower near-term priority, retain monitored nurture. |

Material change: the economic mechanism remained plausible, but timing deteriorated enough that a permanent “$20B fab = positive” label would be commercially wrong. The later 10-K and exact schedule update resolve earlier uncertainty without rewriting what was known in 2022 or November 2024.

Seller hypothesis: fab power, controls, automation, and instrumentation packages may be addressable over the build and operating lifecycle. That is a relevance hypothesis, not evidence that the synthetic seller supplies Intel.

Uncertainty and falsifiers: package sequencing, seller qualification, allocation of multi-state support, customer-demand changes, contractor specifications, further delay, cancellation, or no capability fit.

Controls: the 2025 schedule is rejected from the 2022 cutoff; the Intel ecosystem language cannot create a `SUPPLIES_TO` edge; the four-state award cannot be assigned entirely to Ohio.

### 4.2 TSMC Arizona

Authoritative evidence: TSMC’s 2020 one-fab announcement,[5] its 2022 second-fab expansion,[6] its April 2024 SEC-filed third-fab announcement,[7] the same-day Commerce preliminary terms,[8] the November 2024 final award,[9] the March 2025 White House additional-investment announcement,[10] and TSMC’s 2024 annual report published in April 2025.[11]

| Cutoff | Evidence available then | Frozen consequence call | Reasonable commercial decision |
|---|---|---|---|
| 2020-05-15 | One fab, about $12B, 2024 production target | POSITIVE / MAJOR / LONG | Begin site mapping; track execution. |
| 2022-12-06 | Second fab, about $40B total, 2024/2026 targets | POSITIVE / MAJOR / MEDIUM | Increase coverage; separate first-fab commissioning from second-fab build packages. |
| 2024-04-08 | Third fab, more than $65B, schedules revised to 2025/2028/decade-end; same-day nonbinding federal terms | MIXED / TRANSFORMATIVE / LONG | Expand the long-range plan, rephase nearer packages, cluster two sources as one event revision. |
| 2025-04-17 | Final award, additional U.S. plan, first-fab volume production in Q4 2024, second-fab facility progress | POSITIVE / TRANSFORMATIVE / LONG | Separate current operating demand from later construction; validate geography and packages before resourcing. |

Material change: the second and third fabs are additive scope changes. The issuer’s April 2024 filing and Commerce’s same-day release are two evidence records for one underlying expansion/funding event, not additive $65B events. The November final award changes preliminary status but does not add another $6.6B to the preliminary amount. The annual report later supplies operating proof for the first fab.

Seller hypothesis: repeated fab additions create different specification, construction, commissioning, and operating windows. The full site or national investment figure is not seller-addressable value, and the later additional plan requires facility-level allocation.

Uncertainty and falsifiers: later-fab execution, package geography, award milestones, qualification, and whether the additional facilities proceed.

Controls: same-day duplicate cluster; preliminary-to-final award lineage; schedule changes preserved within the project lineage; large additional headline cannot be treated as immediate or fully Arizona-addressable.

### 4.3 Micron New York

Authoritative evidence: Micron’s October 2022 announcement,[12] Commerce’s April 2024 preliminary terms,[13] the December 2024 final award,[14] Micron’s January 2026 groundbreaking release,[15] and its March 2026 Form 10-Q.[16]

| Cutoff | Evidence available then | Frozen consequence call | Reasonable commercial decision |
|---|---|---|---|
| 2022-10-04 | Up to $100B over more than 20 years; first phase about $20B by decade end; construction then expected in 2024 | POSITIVE / MAJOR / LONG | Track site, permitting, first-fab funding, and package release; exclude the total headline from pipeline. |
| 2024-12-10 | Final milestone-conditioned support across Idaho and New York | POSITIVE / MAJOR / LONG | Increase first-fab diligence; keep later phases time-phased and conditional. |
| 2026-03-18 | January groundbreaking; supply expected 2030-plus; later amendment reallocated some federal support to Idaho | MIXED / MAJOR / LONG | Pursue verified first-fab construction packages only; keep later fabs outside committed pipeline. |

Material change: physical activity eventually strengthened the first-fab thesis, but construction began later than the original expectation, production remained 2030-plus, and an award amendment affected allocation. The $100B ceiling never becomes an immediate opportunity.

Seller hypothesis: infrastructure and process packages may recur over several fabs, but only authorized, funded, and physically progressing phases should drive commercial prioritization.

Uncertainty and falsifiers: environmental and construction progress, New York-specific funding, later-phase authorization, memory-cycle demand, seller qualification, stalled construction, or out-of-profile packages.

Controls: headline-versus-near-term addressability; preliminary/final/amended funding lineage; multi-state allocation; later groundbreaking and 10-Q evidence excluded from earlier cutoffs.

## 5. Secondary generalization findings

### Hyundai Georgia

Georgia’s 2022 announcement described a $5.54B smart factory, a first-half 2025 target, and separate anticipated supplier investment.[17] Hyundai later reported that first production began in October 2024 and documented the plant opening and planned capacity expansion.[18] The same change/relationship/consequence representation works: the commercial mechanism moves from greenfield construction to commissioning, operations, and capacity ramp. Supplier ecosystem language still does not prove a relationship.

### Toyota North Carolina battery

Toyota moved from a $1.29B, four-line battery plant announced in 2021,[19] to $13.9B and fourteen lines phased through 2030 in 2023,[20] and then to production in 2025.[21] Added lines are new economic information; the same 2025 release’s separate “up to $10B” U.S. plan lacks site allocation and is a negative control, not an additive Liberty event.

### Eli Lilly Lebanon

Lilly’s 2022 $2.1B, two-site announcement[22] expanded to $9B total in 2024 with explicit API capacity.[23] Facility expansion, timing, evidence, consequence, and decision remain coherent. The material generalization caveat is customer relevance: a generic industrial seller cannot be assumed qualified for regulated API manufacturing.

### Novo Nordisk North Carolina

Novo announced a $4.1B second fill-and-finish facility in Clayton in 2024.[24] Its 2024 Form 20-F later supplied a 2029 full-operation target and separated expected total spend from spend-to-date.[25] The filing also lists other facilities; these must not collide with Clayton merely because the owner and general “manufacturing facility” label match.

Conclusion: the consequence abstraction remains credible across automotive/battery and biopharma without new sector-specific core objects. What varies is the evidence-backed facility capability and seller qualification. That belongs in identity, capability, and customer-relevance grounding, not bespoke sector architecture.

## 6. Source rights and retention

Public access is not treated as unrestricted copying permission. No full third-party page, PDF, or filing body is committed. Each record retains citation metadata and a short paraphrased structured fact; `content_sha256` covers only that fact. `source_artifact_sha256` is explicitly `null`. Full-content archival would require a separate rights decision and actual acquisition hash.

| Source ID | Family | Retention status |
|---|---|---|
| `intel_2022_ohio_announcement` | Corporate release PDF | EXCERPT_STRUCTURED_FACTS_ONLY |
| `intel_2024_form_10k_delay` | SEC filing | EXCERPT_STRUCTURED_FACTS_ONLY |
| `intel_2025_ohio_timeline_update` | Corporate update | EXCERPT_STRUCTURED_FACTS_ONLY |
| `commerce_2024_intel_final_award` | Federal release | METADATA_REFERENCE_AND_STRUCTURED_FACTS |
| `tsmc_2020_arizona_initial` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `tsmc_2022_arizona_second_fab` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `tsmc_2024_arizona_third_fab_6k` | SEC filing | EXCERPT_STRUCTURED_FACTS_ONLY |
| `commerce_2024_tsmc_preliminary_terms` | Federal release | METADATA_REFERENCE_AND_STRUCTURED_FACTS |
| `commerce_2024_tsmc_final_award` | Federal release | METADATA_REFERENCE_AND_STRUCTURED_FACTS |
| `tsmc_2024_annual_report_arizona_output` | Annual report | EXCERPT_STRUCTURED_FACTS_ONLY |
| `white_house_2025_tsmc_additional_investment` | Federal release | METADATA_REFERENCE_AND_STRUCTURED_FACTS |
| `micron_2022_new_york_announcement` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `commerce_2024_micron_preliminary_terms` | Federal release | METADATA_REFERENCE_AND_STRUCTURED_FACTS |
| `commerce_2024_micron_final_award` | Federal release | METADATA_REFERENCE_AND_STRUCTURED_FACTS |
| `micron_2026_new_york_groundbreaking` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `micron_2026_q2_form_10q` | SEC filing | EXCERPT_STRUCTURED_FACTS_ONLY |
| `georgia_2022_hyundai_metaplant` | State economic-development release | INTERNAL_ARCHIVAL_PENDING_REVIEW |
| `hyundai_2025_hmgma_opening` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `toyota_2021_north_carolina_initial` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `toyota_2023_north_carolina_expansion` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `toyota_2025_north_carolina_production` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `lilly_2022_lebanon_initial` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `lilly_2024_lebanon_api_expansion` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `novo_2024_clayton_expansion` | Corporate release | EXCERPT_STRUCTURED_FACTS_ONLY |
| `novo_2024_form_20f_clayton` | SEC filing | EXCERPT_STRUCTURED_FACTS_ONLY |
| `meta_2021_name_change_8k` | SEC filing, identity control | EXCERPT_STRUCTURED_FACTS_ONLY |
| `commerce_2024_semiconductor_aggregate` | Federal release, macro control | METADATA_REFERENCE_AND_STRUCTURED_FACTS |

The Georgia record is intentionally more restrictive pending source-family archival review. No source in this pack carries an assertion of unrestricted commercial redistribution.

## 7. Existing kernel fit

The classification below is based on current code behavior, not UI presentation.

| Failure class | Intel | TSMC | Micron | Current fit / proven limitation |
|---|---|---|---|---|
| SOURCE ACQUISITION | Gap | Gap | Gap | Production acquisition is federal/procurement-oriented; there is no governed corporate IR, state economic-development, or general SEC filing-body intake for these records. |
| ARCHIVAL | Partial | Partial | Partial | `Evidence` can hold source ID, content hash, archive URI, timing, and retention tier. This pack can represent reference-only sources, but acquisition-time artifact hashing, rights decisions, and source-version lineage are not automated for these families. |
| IDENTITY | Partial | Partial | Partial | Generic `Entity` can carry metadata, but its documented kinds are procurement-centered and facility is not first-class. Stable site identities can be fixture metadata only. |
| ENTITY RESOLUTION | Gap | Gap | Gap | No facility grounder handles campus/fab/phase aliases, owner/name changes, site collisions, or native project identifiers across heterogeneous sources. |
| RELATIONSHIP GROUNDING | Partial | Partial | Partial | Generic evidence-backed `Relationship` exists and propagation traverses explicit edges. Approved direction/canonicalization and facility-specific `OWNS`/`OPERATES`/capability grounding are not enforced. Supplier roles are correctly not inferred in catalyst code. |
| EVENT REPRESENTATION | Partial | Partial | Partial | Generic `Event`, capacity-buildout catalysts, capex/facility expansion mechanisms, contradictions, and status fields can express core changes. Multi-source event clustering, additive scope versus amendment, fab phase lineage, and schedule revision are not native. |
| CONSEQUENCE REPRESENTATION | Partial | Partial | Partial | `CommercialConsequence` already has mechanism, directness, timing, value, evidence, assumptions, falsifiers, confidence, disposition, and first-supportable time. Approved direction, magnitude band, and horizon are not first-class enforced fields. |
| CUSTOMER RELEVANCE | Gap | Gap | Gap | Current capability logic is procurement-oriented; it cannot validate this non-procurement seller’s facility, geography, channel, and qualification fit without an evaluation extension. |
| SCORING | Not evaluated | Not evaluated | Not evaluated | Phase 1 `scoring_v1` was intentionally untouched. The pack supplies adjudicated categories but makes no production-scoring claim. |
| PREDICTION | Partial | Partial | Partial | Frozen replay snapshots exist, but the current prediction vocabulary is aimed at procurement disposition rather than industrial schedule/direction/magnitude/horizon revisions. |
| OUTCOME | Partial | Partial | Partial | Append-only, point-in-time outcome resolution and strict future exclusion already exist. Current labels emphasize capture outcomes, not facility milestones such as delayed, groundbreaking, construction, or operating. |
| REPLAY EVALUATOR | Gap | Gap | Gap | Existing replay provides deterministic cutoff exclusion and metrics, but its required case schema and scorer are procurement-specific. This industrial fixture is validated but not executed through production scoring. |
| PRESENTATION ONLY | None proven | None proven | None proven | Display polish was not mistaken for an architectural gap, and no Phase 1 UI change is proposed. |

## 8. Actual architecture gaps

Only five bounded gaps are supported by the replay:

1. **Governed heterogeneous source intake and version lineage.** Acquire corporate releases, filings, federal/state records, record rights decisions, hash actual artifacts where retained, and cluster duplicates/amendments without treating them as additive events.
2. **Facility identity and lifecycle grounding.** Resolve campus, fab, line, phase, site aliases, ownership/operation/capability, and collisions from site-native facts while preserving ambiguity.
3. **Industrial event revision model.** Represent announced scope, added facility/line, schedule change, funding status, construction, commissioning, production, supersession, and contradictions as one point-in-time lineage.
4. **Explicit consequence revision semantics and seller relevance.** Preserve direction, magnitude band, horizon, evidence strength, analytical confidence, capability/geography fit, assumptions, and falsifiers without turning headline project value into seller value or inferring relationships.
5. **Evaluation-only industrial replay runner and outcome vocabulary.** Execute frozen cutoff calls against later facility milestones, duplicate controls, schedule revisions, and time-phased addressability without changing `scoring_v1` or production disposition.

These are extensions of existing evidence, graph, catalyst, consequence, replay, and outcome primitives. The corpus does not demonstrate a need for a second platform or sector-specific core architecture.

## 9. Negative controls

The machine-readable corpus includes all required controls:

1. future Intel schedule evidence rejected from the 2022 cutoff;
2. same-day TSMC issuer/Commerce sources clustered as one underlying event;
3. Micron preliminary/final/amended funding preserved as version lineage;
4. Novo’s different facilities kept distinct despite shared ownership and generic naming;
5. Facebook-to-Meta identity preserved by stable SEC CIK;[26]
6. Toyota’s unallocated national investment barred from Liberty consequence;
7. non-U.S. Novo investments excluded from the U.S. Clayton seller case;
8. regulated API/sterile capability treated as a relevance gate, not assumed fit;
9. a national semiconductor investment aggregate barred from company events;[27]
10. no `SUPPLIES_TO` edge created for the synthetic seller;
11. Micron’s $100B headline decomposed by phase and horizon.

## 10. Readiness determination

| Gate | Status | Basis |
|---|---|---|
| ARCHITECTURE READY | READY FOR BOUNDED IMPLEMENTATION AFTER PHASE 1 GATE | Existing primitives cover the core abstraction; replay proves five bounded extensions rather than a new platform. |
| REPLAY READY | YES, AS AN EVIDENCE/ADJUDICATION FIXTURE | Seven cases, cutoffs, outcomes, controls, rights records, and fixture tests are complete. The production replay runner is not claimed compatible. |
| PHASE 1 OPERATIONALLY READY | NOT ESTABLISHED BY THIS WORK | This research run supplies no unattended acceptance/soak evidence. |
| CUSTOMER #1 GO | NOT ESTABLISHED | No owner GO evidence was supplied or inferred. |
| PRODUCTION IMPLEMENTATION AUTHORIZED | NO | No execution authority was opened; no production implementation was made. |

Recommended next technical step, only after the Phase 1 and owner gates open: implement the smallest evaluation-only loader/runner for this frozen schema, prove that the negative controls fail correctly, and use those results to decide whether any of the five extensions merit production design.

## Sources

1. [Intel, “Intel Announces Next U.S. Site with Landmark Investment in Ohio,” 2022-01-21](https://download.intel.com/newsroom/archive/2025/en-us-2022-01-21-intel-announces-next-us-site-with-landmark-investment-in-ohio.pdf)
2. [U.S. Department of Commerce, Intel CHIPS final award, 2024-11-26](https://www.commerce.gov/news/press-releases/2024/11/biden-harris-administration-announces-chips-incentives-award-intel)
3. [Intel 2024 Form 10-K, SEC accession 0000050863-25-000009](https://www.sec.gov/Archives/edgar/data/50863/000005086325000009/intc-20241228.htm)
4. [Intel, “Ohio One Construction Timeline Update,” 2025-02-28](https://www.intel.com/content/www/us/en/newsroom/news/corporate/ohio-one-construction-timeline-update.html)
5. [TSMC Arizona initial announcement, 2020-05-15](https://pr.tsmc.com/english/news/2033)
6. [TSMC Arizona second-fab expansion, 2022-12-06](https://pr.tsmc.com/english/news/2977)
7. [TSMC April 2024 Form 6-K exhibit, SEC accession 0001046179-24-000040](https://www.sec.gov/Archives/edgar/data/1046179/000104617924000040/a20240408.htm)
8. [U.S. Department of Commerce, TSMC preliminary terms, 2024-04-08](https://www.commerce.gov/news/press-releases/2024/04/biden-harris-administration-announces-preliminary-terms-tsmc-expanded)
9. [U.S. Department of Commerce, TSMC CHIPS final award, 2024-11-15](https://www.commerce.gov/news/press-releases/2024/11/biden-harris-administration-announces-chips-incentives-award-tsmc)
10. [The White House, TSMC additional U.S. investment announcement, 2025-03-03](https://www.whitehouse.gov/releases/2025/03/another-historic-investment-secured-under-president-trump/)
11. [TSMC 2024 Annual Report](https://investor.tsmc.com/sites/ir/annual-report/2024/2024%20Annual%20Report.E.pdf)
12. [Micron New York megafab announcement, 2022-10-04](https://investors.micron.com/news/press-release/2022/Micron-Announces-Historic-Investment-of-up-to-100-Billion-to-Build-Megafab-in-Central-New-York-10-04-2022/default.aspx)
13. [U.S. Department of Commerce, Micron preliminary terms, 2024-04-25](https://www.commerce.gov/news/press-releases/2024/04/biden-harris-administration-announces-preliminary-terms-micron-onshore)
14. [U.S. Department of Commerce, Micron CHIPS final award, 2024-12-10](https://www.commerce.gov/news/press-releases/2024/12/department-commerce-awards-chips-incentives-micron-idaho-and-new-york)
15. [Micron New York groundbreaking announcement, 2026-01-07](https://investors.micron.com/news/press-release/2026/Micron-Announces-Groundbreaking-for-Historic-New-York-Megafab-01-07-2026/default.aspx)
16. [Micron fiscal Q2 2026 Form 10-Q, SEC accession 0000723125-26-000006](https://www.sec.gov/Archives/edgar/data/723125/000072312526000006/mu-20260226.htm)
17. [Georgia Department of Economic Development, Hyundai metaplant announcement, 2022-05-20](https://georgia.org/press-releases/2022/hyundai-motor-group-invest-554-billion-georgia-first-fully-dedicated-electric)
18. [Hyundai Motor Group, HMGMA grand opening, 2025-03-26](https://www.hyundaimotorgroup.com/en/news/hyundai-motor-group-metaplant-america-celebrates-grand-opening-powering-us-economic-growth)
19. [Toyota, North Carolina battery plant selection, 2021-12-06](https://pressroom.toyota.com/toyota-selects-north-carolina-greensboro-randolph-site-for-new-u-s-automotive-battery-plant/)
20. [Toyota, North Carolina battery plant expansion, 2023-10-31](https://pressroom.toyota.com/toyota-supercharges-north-carolina-battery-plant-with-new-8-billion-investment/)
21. [Toyota, North Carolina battery production, 2025-11-12](https://pressroom.toyota.com/toyota-charges-into-u-s-battery-manufacturing/)
22. [Eli Lilly, Lebanon initial sites, 2022-05-25](https://investor.lilly.com/node/47326)
23. [Eli Lilly, Lebanon API expansion, 2024-05-24](https://investor.lilly.com/node/50776)
24. [Novo Nordisk, Clayton expansion, 2024-06-24](https://www.novonordisk.com/content/nncorp/global/en/news-and-media/news-and-ir-materials/news-details.html?id=168528)
25. [Novo Nordisk 2024 Form 20-F, SEC accession 0001628280-25-003920](https://www.sec.gov/Archives/edgar/data/353278/000162828025003920/nvo-20241231.htm)
26. [Meta Platforms Form 8-K company-name change, SEC accession 0001326801-21-000071](https://www.sec.gov/Archives/edgar/data/1326801/000132680121000071/fb-20211028.htm)
27. [U.S. Department of Commerce, national semiconductor/electronics investment aggregate, 2024-12-20](https://www.commerce.gov/news/press-releases/2024/12/secretary-raimondo-applauds-release-inaugural-white-house-quadrennial)
