# M22-D — Company / program investigation + deterministic entity search

**Status:** implemented, CLOSED 2026-09-10. Governs `pyrnova/investigation.py`, the investigation read
methods on `pyrnova/ops.py`, the `/api/search` · `/api/company` · `/api/program` routes in
`pyrnova/ops_server.py`, the `investigation.{html,js,css}` surfaces, the `pyrnova search` CLI, and
`tests/test_m22d_investigation.py`. See D-058 (extends D-055/D-056/D-057).

## Purpose

M22-A/B/C answered *what materially changed for this customer, who the customer is, and how we keep
delivering it*. M22-D completes the first investigation path beneath a Material Change: from a change, a
user reaches the **affected company or program**, sees what Pyrnova knows (identity, current
intelligence, government activity, relationships, evidence, history) and — explicitly — what it does
**not** know, and can arrive there by **searching the Pyrnova estate deterministically**.

This is the *minimum useful* investigation surface required by the existing workflow, not a maximum
corporate dossier. Company/program pages are **supporting** surfaces: every section answers *what is
this / why relevant / what changed / what relationships / what consequence / what evidence / what is
unknown / what happened before*.

## Architecture

```
AUTHORITATIVE INTELLIGENCE STREAMS (threats / propagated_threats / opportunities / relationships)
  → IntelligenceEstate  (deterministic point-in-time READ PROJECTION; pyrnova/investigation.py)
      → search(estate, query)                → deterministic resolution
      → company_intelligence(estate, ref)    → company page
      → program_intelligence(estate, key)    → program page
  → OperatorConsole read methods → JSON API → frontend
```

The estate is a **computed read model** — the same pattern as `build_material_changes` and the
Operations Panel views — not a second persisted truth system. It reuses the shared change normalizers
(`material_changes._threat_change` / `_opportunity_change` / `_visible`), so the investigation view and
the Material Changes feed can never diverge. References back to authoritative objects (entity refs,
program keys, evidence ids, archive hashes) are preserved throughout; no evidence body is duplicated.

Ordinary search and page rendering require **no runtime strong-model reasoning** — no import from
`pyrnova.ai`, verified by a test that poisons the LLM helper.

## Canonical identity (§10)

No second entity-resolution system. Entities are the canonical refs already in the graph (`co_*` /
`co_uei_*`); programs are source-native program/contract keys (PIIDs). Identifiers are read from
**structured** provenance only:

* `co_uei_<UEI>` ref shape → UEI;
* a `SUBSIDIARY_OF` hop's provenance → each endpoint's `child_uei` / `parent_uei` / recipient id, and the
  parent/subsidiary linkage;
* structured evidence tokens (`uei:` / `cik:` / `cage:` / `lei:`) **only** on a *direct* threat, whose
  single subject makes attribution unambiguous.

A bare token on a multi-entity record (e.g. a propagated threat carrying both a child and parent UEI) is
never harvested. Missing identifiers stay missing — never fabricated. `_merge_ident` never overwrites an
already-asserted value, so identity is not silently mutated.

## Deterministic search (§6–§9, §11)

`search(estate, query)` resolves in a fixed, deterministic order — **exact identifier → exact
name/alias → scored partial name** — and returns one honest resolution state:

| Resolution   | Meaning |
|--------------|---------|
| `EXACT`      | a single unambiguous match (identifier, or exact canonical/alias name) |
| `PROBABLE`   | scored partial name match(es), best first, each with an explicit `confidence` |
| `AMBIGUOUS`  | several equally-valid matches — all surfaced, **never merged** |
| `UNRESOLVED` | nothing matched (empty/malformed queries included) — a first-class answer |

* **Exact identifiers resolve by dictionary lookup — never an LLM.** Supported: Pyrnova entity id, UEI,
  CAGE, CIK, LEI, contract/program id.
* **Name search is deterministic scored matching.** No silent canonicalization: two same-named entities
  are returned as two (`AMBIGUOUS`), never collapsed. Partial scoring is token-overlap with a coverage
  floor so a single common token ("technologies") does not mint a match.
* **Reversible resolution (§11):** a query is not evidence of identity. Search *reads and classifies*; it
  never writes a merge or mutates canonical identity.
* Result fields disambiguate: canonical name, type (COMPANY/PROGRAM), key identifier + kind, parent/agency,
  match basis, confidence (probabilistic only), and a canonical `link`.

## Company page (§3)

`Identity` (ref, canonical name, aliases = other observed name variants, identifiers, parent/subsidiaries,
first-seen) · `Current intelligence` (the entity's own material events, observed-fact / assessment kept
distinct, referenced by change id) · `Government activity` (programs/contracts evidenced, with agency,
role, evidence-ref count) · `Relationships` (typed edges incident to the entity, direction, link
class/join method/confidence, validity window, evidence) · `Material history` (chronological, point-in-
time states not flattened) · `Evidence` (distinct references only) · `Intelligence gaps` (explicit
unknowns).

## Program page (§4)

`Program identity` (key, agency, status=UNKNOWN unless evidenced, first-seen) · `Material changes` ·
`Companies` (evidenced incumbents/exposed, never inferred by shared sector) · `Evidence` ·
`Material history` · `Intelligence gaps`.

## Material Change → investigation (§5, core acceptance)

`OperatorConsole.material_changes` attaches an `investigation` block to each change — `company`
(subject ref + name), `program` (key), and `related_entities` (propagation-path refs) — so the customer
never copies an identifier into search. The customer-facing feed renders these as inline links; the
Material Changes screen itself is unchanged otherwise.

## Global vs customer boundary (§12, §23)

Company/program pages are **global** intelligence and carry no customer context by default. When an
authorized `customer` is supplied, a separately-keyed `customer_context` block is added: whether that
customer watches/owns the object, its relation, and which of **that** customer's own Material Changes
touch it. Authorization flows through the existing M22-C `access_check` seam (an unauthorized customer
overlay raises `PermissionError` → HTTP 403). A customer's private relevance/review state is never folded
into global truth and never leaks across customers (direct negative tests).

## Temporal truth (§7, §19)

The estate and every section are reconstructed point-in-time from `as_of`: an entity/program/relationship/
event not knowable at the cutoff does not appear; relationship validity (`valid_from`/`valid_to`) is
respected on every page and in `_edges_touching`; outcomes do not leak into earlier views.

## Real-evidence demonstration (§21)

On the tracked M22-A/B/C demo evidence (no live calls, no fabrication):

* `co_saic` → EXACT (Pyrnova entity id) → SAIC company page: PROGRAM_CONTRACTION on GSA PIID
  `47QFSA20F0057`, real `SUBCONTRACTOR_OF` edge to Torch, honest gaps (no UEI/CAGE/CIK stored).
* `KMSLVW1MZWU9` → EXACT (UEI) → DAP native-id **parent**; `YR7CLZFGCM95` → EXACT (UEI) → DAP **child**
  (`co_dap_sub`) via the `SUBSIDIARY_OF` provenance.
* `47QFSA20F0057` → EXACT (contract id) → program page listing SAIC (incumbent) + Torch (exposed).
* `DAP Construction Management` → **AMBIGUOUS**: the real child and its native-id parent carry near-
  identical names and are shown as two distinct canonical entities — "two Acmes → two Acmes".

## Non-goals (deferred — §25)

Broad natural-language search, RAG, document search, new external sources, competitor/supply-chain
intelligence, full company universe, premium data, authentication/SSO, dashboard builder, major
navigation redesign, graph visualization, full people intelligence, financial terminal, AI research
agent, autonomous actions, broad frontend polish. The future **NATURAL LANGUAGE → STRUCTURED QUERY →
DETERMINISTIC RETRIEVAL** architecture is preserved but not built here; M22-D proves the deterministic
substrate first. First-class evidence-independence lineage remains deferred (conservative single-source
presentation retained).

## Acceptance (all met)

Material Change → company and → program navigation; company/program pages expose decision-relevant
existing intelligence; exact identifiers resolve deterministically (no LLM); names/aliases resolve
without silent certainty; ambiguity surfaced; search and pages use canonical objects; customer overlays
isolated + access-checked; temporal truth intact; evidence traceable and reference-only; sparse
intelligence shown honestly; no runtime strong-model reasoning; no new intelligence domain required;
full suite **557 passed** (was 532; +25). Tests proportional to risk, not count.
