# M15 — first-class threat intelligence + exposure graph

_Status: CLOSED 2026-09-09 · canonical semantic definition for Pyrnova threat objects._

This is the **canonical** definition of Pyrnova's threat concept. Other documents reference it rather
than repeating it. M15 restores and develops the THREAT side of the mission
(`docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md` area 1) and lays foundations for the company threat
surface (area 4) and thesis evolution (area 10) without prematurely building them.

## Concept

Threat is a **first-class peer** of commercial opportunity/consequence — not a negated opportunity, a
rejected fit, a generic risk score, or a scary alert. The conceptual chain:

    EXPOSURE -> CATALYST -> THREAT MECHANISM -> AFFECTED SUBJECT -> ECONOMIC EFFECT
    -> CONFIDENCE / SEVERITY -> TIME HORIZON -> MITIGATION -> EVIDENCE -> OBSERVED OUTCOME

Pyrnova should be able to tell a company: *something changed; you are exposed; here is the mechanism by
which it may hurt you; here is how severe it could be; here is how confident we are; here is when it
matters; here is every piece of evidence; here is what would falsify the warning; and we will remember
whether we were right.* At the same time it recognises when the **same catalyst** creates an
opportunity elsewhere (duality).

## Objects (`pyrnova/models.py`, additive)

- **`Exposure`** — an explicit, evidence-backed edge: WHO/WHAT is exposed to WHAT. Carries
  `relation_type` (one of `threat.EXPOSURE_RELATIONS`), `join_method`, `link_class`
  (`CONFIRMED | INFERRED | CANDIDATE | REJECTED`), `confidence` (join strength, not severity),
  `evidence_ids`, and point-in-time `available_at`/`valid_from`/`valid_to`. A weak fuzzy-name
  resemblance is a **CANDIDATE**, never a CONFIRMED exposure.
- **`Threat`** — the first-class threat. `severity` and `confidence` are **orthogonal ordinals**,
  never one number: severity = how bad the effect could be *if true*; confidence = how strongly
  evidence supports the thesis. `UNKNOWN` is valid for severity/confidence/horizon. Deterministic
  identity via `threat.threat_id`. Carries `dual_opportunity_ref` for duality.
- **`ThreatRejection`** — zero-threat is first-class, auditable output (a peer of `Threat`).

## Engine (`pyrnova/threat.py`)

Exposure builders: `sanctions_exposures` (OFAC `ent_num` / name+country identity tuple => deterministic
CONFIRMED; name-token overlap => weak CANDIDATE returned separately for rejection; generic tokens alone
never match), `incumbency_exposures` (deterministic native-id from a subject's own award `recipient_uei`
=> `PROGRAM` + `INCUMBENT_POSITION`), `declared_exposures` (REGULATION/CERTIFICATION/CUSTOMER/... from
explicit structured fields, CONFIRMED vs INFERRED).

`assess_threats(subject, exposures, catalyst_records, *, weak_candidates, as_of)` runs every mechanism
assessor and returns `(threats, rejections)`.

### Mechanisms implemented (evidence-safe, deterministic)

| Mechanism | Requires | Zero-threat rejection |
|---|---|---|
| `SANCTIONS_EXPOSURE` | CONFIRMED/INFERRED sanctioned-counterparty exposure | weak name match => `WEAK_NAME_MATCH_ONLY`; no linkage => silence |
| `INCUMBENT_DISPLACEMENT` | incumbency exposure + recompete + a **displacement signal** | recompete alone => `RECOMPETE_NOT_A_THREAT`; not incumbent => `NO_EXPOSURE` |
| `PROGRAM_CONTRACTION` | program dependency + funding-reduction catalyst | no dependency => `NO_EXPOSURE` |
| `PROGRAM_CANCELLATION_OR_DELAY` | program dependency + cancellation/delay catalyst | no dependency => `NO_EXPOSURE` |
| `REGULATORY_COMPLIANCE_EXPOSURE` | regulation/cert exposure + mandate referencing that exact ref | irrelevant mandate => `NO_EXPOSURE` |
| `ELIGIBILITY_OR_CERTIFICATION_RISK` | as above with `eligibility_gated` | as above |
| `CUSTOMER_CONCENTRATION` | CUSTOMER exposure ≥25% revenue + adverse change | non-concentrated => `IMMATERIAL` |

### Severity vs confidence

- **Severity** is a magnitude BAND of a KNOWN dollar figure at risk (`severity_from_amount`:
  >$100M CRITICAL, >$25M HIGH, >$5M MODERATE, >0 LOW, none UNKNOWN) — evidence, not invented
  probability. No numeric probabilities are fabricated.
- **Confidence** is an ordinal from exposure `link_class` + catalyst evidence strength. A CANDIDATE-only
  exposure caps confidence at LOW and can never carry an ACTIVE/HIGH threat.

### Duality, surface, outcome

- `link_duality(threats, opportunities)` cross-links a threat and an opportunity sharing a `catalyst_id`
  **without duplicating source facts** (both point back to the common catalyst).
- `company_threat_surface(subject_ref, threats)` groups active threats by
  mechanism/severity/confidence/horizon over the shared entity layer — the M15 foundation for the
  Company Opportunity/Threat Surface (roadmap area 4). Not the full product.
- Outcome linkage: append-only `threat_outcome_observation` + point-in-time `resolve_threat_outcome`.
  Future-dated observations are excluded; an unresolved threat is **never** auto-labelled a false alarm;
  terminal/negative labels require an explicit dated source (mirrors `pyrnova/outcomes.py`).

## Corpus & replay

`examples/replay/corpus_m15.json` — 17 threat cases **extending** (never altering) the frozen corpus
lineage, with a distinct threat schema and its own point-in-time replay
(`threat.run_threat_corpus`); it never touches `scoring_v1`. Sanctions cases run **real linkage
semantics** against the committed illustrative OFAC fixture for deterministic CI;
`tests/test_m15_real_ofac.py` (guarded, skips without the git-ignored archive) proves the same code on
the **19,365 real archived SDN designations** (archive-operational since M14) and that a name resemblance
is never a hit. Cases flagged `synthetic_probe` use a clearly-labelled controlled catalyst; the real
Torch incumbency case is grounded in committed real award evidence
(`examples/real_evidence/`, award `W31P4Q21F0038`, $623M).

## Operations Panel

`OperatorConsole.threat_operations(subject_ref=None)` — thin, read-only, empty-safe view over the
append-only `threats`/`threat_rejections`/`exposures` streams: active threats grouped, zero-threat
rejection reasons, exposure confirmed/total, dual-sided count, and per-company threat surfaces. Operators
can see WHY a threat exists (economic effect + evidence + affected exposure). The existing panel is
unchanged.

## Invariants preserved

`scoring_v1`, `fit.py`, `replay.py`, and all frozen M4–M11 corpora are **byte-for-byte unchanged**
(additive edits only to `models.py` and `ops.py`; new `threat.py`). Point-in-time truth
(`available_at <= as_of`) on exposures, catalysts, and outcomes; no temporal leakage; no fabricated
relationships; no secret leakage; UNKNOWN valid; absence never treated as evidence.

## Acceptance gate (all met — see `docs/replay/M15_THREAT_INTELLIGENCE.md`)

Threat is first-class and durable (1); exposure explicitly modelled (2); distinct from negative
fit/rejection (3); ≥4 mechanisms — **7** implemented (4); sanctions evidence-safe (5); weak sanctions
linkage rejected (6); procurement/program threat represented (7); ZERO THREAT valid + exercised (8);
confidence and severity distinct (9); no invented probability precision (10); point-in-time threat
replay works (11); future evidence excluded (12); threat history/evolution preserved (13); company
threat surface queryable (14); threat links to eventual outcome (15); ≥1 real company evidence-backed
threat — Torch (16); **2** dual-sided cases (17); `corpus_m15` exists (18); earlier corpora byte-identical
(19); `scoring_v1` unchanged (20); `fit.py` unchanged (21); false/weak exposure rejection demonstrated
(22); no threat explosion (23); no temporal leakage (24); no secret leakage (25); focused tests pass (26);
full suite passes — 373 (27); Operations Panel functional (28); limitations explicit (29); every block
committed + pushed (30–31); roadmap/backlog updated (32).

## Limitations (explicit)

- The corpus is deliberately mechanism-dense (17 cases, 11 threats / 4 rejections; `threat_to_event_ratio`
  ~0.73). This is a **semantic-coverage** corpus, not a live-feed selectivity measurement — the
  explosion guardrail concerns live feeds, where most events must reject. Distributions are directional,
  not stable rates (small-sample warning surfaced, never hidden).
- Sanctions **positive** cases are `synthetic_probe`s attached to designations: no public evidence
  exposes a real US mid-market contractor's sanctioned counterparty, so a confirmed positive uses a
  clearly-labelled controlled counterparty relationship. The linkage semantics and the real-designation
  archive are real; the specific counterparty relationship is a probe and is never described as real.
- The one real-company threat (Torch) is evidence-backed on the **exposure** side (real award); its
  displacement **catalyst** is a labelled probe (no archived real displacement event).
- Exposure families exercised: sanctioned-counterparty, program/incumbency, regulation/certification,
  customer-concentration. Other `EXPOSURE_RELATIONS` (supplier-dependency, geography, facility,
  commodity-input, technology, procurement-vehicle) are modelled but not yet corpus-exercised.
- Mitigation candidates are static, evidence-adjacent suggestions, not executed actions (no autonomous
  action on threats — a roadmap boundary).
