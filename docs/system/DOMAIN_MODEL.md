# Domain model

Status: descriptive semantic map  
Last reviewed: 2026-09-12

## Reading rules

Pyrnova does not have one monolithic ORM model. The implemented development path uses Python dataclasses
and dictionaries persisted to append-only JSONL. `db/schema.sql` is the intended relational mirror and
contains some schema-only concepts. A term below is called **implemented** only when a current code path
constructs/reads it; **schema-only** means no equivalent runtime repository is wired.

Three distinctions prevent most semantic errors:

- **canonical record ≠ presentation:** Material Changes and investigation pages are derived views.
- **capture ≠ verify ≠ publish:** retrieving evidence, accepting an assertion, and showing an item are
  separate decisions.
- **evidence state ≠ claim state ≠ outcome state:** a source artifact, an interpretation, and what later
  happened are not interchangeable.

## Source

- **Purpose:** declares an external observation surface and its operating/rights contract.
- **Identity:** stable string `SourceSpec.id`, for example `usaspending` or `sec_edgar`.
- **Mutability:** registry code changes through review; observed source states are not overwritten.
- **Tenancy:** global.
- **Time:** cadence, historical depth, and reliability/status are declared metadata; connectivity claims
  remain dated.
- **Evidence requirement:** rights and retention must be known or explicitly `unknown` before operation.
- **Relationships:** produces observations/evidence and advertises stable identifiers/possible links.
- **Invariants:** registry holds no secrets and performs no HTTP; `active` is not the same as live-proven.
- **Implementation:** `pyrnova/sources/registry.py`; relational mirror `source`.

## Observation

- **Purpose:** records one retrieval attempt/state and when Pyrnova saw it.
- **Identity:** runtime observation records are append-only dicts; the relational mirror uses UUID.
- **Mutability:** append-only.
- **Tenancy:** global unless a future source is explicitly customer-private.
- **Time:** `fetched_at`/`observed_at` is Pyrnova knowability, distinct from source publication/effective time.
- **Evidence requirement:** successful raw content is archived; request provenance must be sanitized.
- **Relationships:** one observation may point to content-addressed Evidence.
- **Invariants:** cache/fixture/error cannot be mislabeled as fresh ACCEPTANCE; credentials are redacted.
- **Implementation:** `pipeline.py`, source adapters/scheduler, `observations` stream; schema `observation`.

## Evidence

- **Purpose:** retained source material and provenance address.
- **Identity:** SHA-256 of exact content plus an observation-specific Evidence id.
- **Mutability:** content immutable by hash; observation sidecars append.
- **Tenancy:** currently global archive. Access to customer-private evidence is not implemented as a
  distinct archive policy.
- **Time:** `published_at` is source time; `first_seen_at` is Pyrnova observation time.
- **Evidence requirement:** source id, hash, archive URI, media type, retention tier; source ref/URL where
  available.
- **Relationships:** supports events, relationships, opportunities, threats, predictions/outcomes through
  referenced ids.
- **Invariants:** presentation stores references rather than evidence bodies; equal bytes deduplicate.
- **Implementation:** `models.Evidence`, `archive.py`; schema `evidence`, join tables.

## Entity

- **Purpose:** source-independent subject such as recipient, agency, office, or program.
- **Identity:** runtime id plus canonical name; UEI where available. Later modules also use stable `co_*`
  company refs and source-native tokens.
- **Mutability:** new evidence/profile versions append; deterministic search does not write merges.
- **Tenancy:** global.
- **Time:** base `Entity` lacks first-class validity; profiles and relationships carry availability/
  validity. Missing historical identity remains a gap.
- **Evidence requirement:** source-native identity is preferred; name-only ambiguity must survive.
- **Relationships:** subject/object of graph edges, affected subject of threat/opportunity, customer may
  reference an entity without owning global truth.
- **Invariants:** exact native id outranks name; unresolved/ambiguous entities are not silently collapsed.
- **Implementation:** `models.Entity`, `resolve.py`, grounding modules, `investigation.py`; schema `entity`.

## Relationship

- **Purpose:** evidence-backed edge between canonical records.
- **Identity:** runtime id; deterministic candidate ids in chain/relationship grounders where specified.
- **Mutability:** accepted edges append; validity can close through `valid_to`; inferred candidates may be
  deferred/rejected.
- **Tenancy:** global evidence graph. Customer watch/relevance is not a global relationship.
- **Time:** `first_observed_at`/`available_at` control knowability; `valid_from`/`valid_to` control truth at
  event time.
- **Evidence requirement:** evidence ids, join method, confidence, and rationale; weak/topic-only joins are
  rejected or reviewed.
- **Relationships:** connects entities/events and supplies exposure/propagation paths.
- **Invariants:** conflicting edges can coexist as evidence-backed records; readers decide point-in-time
  validity rather than rewriting history.
- **Implementation:** `models.Relationship`, `chains.py`, `relationships.py`; schema `relationship`.

## Event

- **Purpose:** source-independent occurrence such as award, notice, regulatory precursor, program signal,
  modification, or termination.
- **Identity:** runtime id; source id/ref remains the native anchor.
- **Mutability:** append-oriented; revisions are separate evidence/events unless a module models lineage.
- **Tenancy:** global.
- **Time:** `occurred_at` is event/effective time; evidence availability governs when it may be used.
- **Evidence requirement:** source identity/ref and evidence ids for authoritative use.
- **Relationships:** may sit in staged program chains and generate catalysts/opportunities/threats.
- **Invariants:** occurrence time does not imply knowability time; source-independent representation must
  retain source provenance.
- **Implementation:** `models.Event`, normalizers/adverse-event modules; schema `event`/`event_evidence`.

## Claim / assertion

- **Purpose:** non-authoritative interpretation extracted from evidence.
- **Identity/mutability:** schema UUID and validation flag.
- **Tenancy:** not explicitly tenant-scoped in the current schema.
- **Time:** schema `created_at`; no complete implemented claim lifecycle.
- **Evidence requirement:** evidence id, predicate/value, evidence span, producer, optional confidence.
- **Relationships:** may inform review but must not overwrite deterministic facts.
- **Invariants:** AI output is a claim/recommendation, not authoritative fact.
- **Implementation:** `claim` exists in `db/schema.sql`; runtime has `ai.Reasoner`/`NullReasoner` and
  optional `opp.meta['ai']`, but no first-class Python Claim repository. Treat this as partial/schema-only.

## Opportunity

- **Purpose:** actionable or monitorable commercial possibility generated from a catalyst.
- **Identity:** pipeline uses a UUIDv5 from a source-native opportunity key; the M22-E tracked demo uses
  `opp_<hash(award_id, catalyst kind, subject ref)>` for rebuild stability.
- **Mutability:** lifecycle changes from candidate/reviewing to strike/rejected; append-only state records
  preserve history in the development path.
- **Tenancy:** global intelligence can carry customer/profile context; customer delivery is materialized
  separately per tenant.
- **Time:** expected action and evidence knowability are distinct; expired candidates are not active.
- **Evidence requirement:** catalyst plus evidence and mandatory falsification; enrichment alone cannot
  manufacture STRIKE.
- **Relationships:** reviewed into disposition, frozen into Prediction, later resolved by Outcome, projected
  as Material Change.
- **Invariants:** relevance, attractiveness, and confidence are separate values; system STRIKE is not the
  same as human ACCEPT.
- **Implementation:** `models.Opportunity`, engines/pipeline/review; schema `opportunity`.

## Capital catalyst and Commercial Consequence

- **Purpose:** a catalyst is an evidence-backed change likely to alter economic behavior; a consequence
  states a specific mechanism, participant, capability, timing/value posture, assumptions, and falsifiers.
- **Identity:** deterministic ids derived from program/evidence/mechanism anchors.
- **Mutability:** append-only records; status can be active/contradicted/superseded in schema.
- **Tenancy:** global until evaluated for a customer/company through fit/relevance.
- **Time:** `first_observed_at`/`available_at` and `first_supportable_at` gate historical use; effective date
  and activation/timing remain separate.
- **Evidence requirement:** triggering evidence and supporting relationships; zero consequences is valid.
- **Relationships:** consequence belongs to catalyst; fit evaluates company posture; opportunity remains a
  distinct object.
- **Invariants:** mechanism confidence is not opportunity score; headline value may remain UNKNOWN;
  negative/fatal falsifiers can suppress output.
- **Implementation:** `models.CapitalCatalyst`, `models.CommercialConsequence`, `catalysts.py`, `value.py`;
  relational mirrors of the same names.

## Threat and Exposure

- **Purpose:** Exposure is an explicit subject-to-target dependency; Threat combines exposure, catalyst,
  mechanism, economic effect, severity, confidence, horizon, evidence, falsifiers, and mitigation.
- **Identity:** deterministic helper functions in `threat.py`.
- **Mutability:** append-oriented; status/review/outcome are separate. Propagated threats retain root/path.
- **Tenancy:** global; customer relevance is applied later.
- **Time:** availability and validity are enforced; lapsed exposure can reject a threat.
- **Evidence requirement:** accepted exposure plus catalyst evidence; weak joins produce explicit rejection.
- **Relationships:** threats may have dual opportunity references and may propagate over accepted economic
  relationships.
- **Invariants:** severity and confidence are separate; propagation does not raise confidence; an identity
  match alone is insufficient without materiality/validity.
- **Implementation:** `models.Exposure`/`Threat`/`ThreatRejection`, `threat.py`, `propagation.py`.

## Prediction

- **Purpose:** freezes a falsifiable prospective statement for later grading.
- **Identity:** runtime id linked to one opportunity; schema UUID.
- **Mutability:** immutable snapshot by doctrine; never edited by later outcomes.
- **Tenancy:** linked to the originating opportunity/customer context; current JSONL lacks a universal
  explicit tenant wrapper.
- **Time:** `predicted_at`, optional `resolve_by`, lead time.
- **Evidence requirement:** inherits the opportunity/catalyst state available at creation.
- **Relationships:** later OutcomeObservation references opportunity and optional prediction id.
- **Invariants:** no retrospective forecast backfill; later facts grade rather than rewrite the call.
- **Implementation:** `models.Prediction`, `review.make_prediction`; schema `prediction`.

## Outcome

- **Purpose:** authoritative, dated observation of what later happened.
- **Identity:** stable hash across opportunity, label, observation time, and source ref.
- **Mutability:** append-only; resolution selects a point-in-time winner without altering observations.
- **Tenancy:** global opportunity outcome; customer lifecycle may link an `outcome_ref` without rewriting it.
- **Time:** `observed_at` is the cutoff gate; future outcomes are excluded.
- **Evidence requirement:** source id/ref and strength. Negative/terminal/capture outcomes require explicit
  evidence strength of at least 3.
- **Relationships:** grades a prediction/opportunity or threat; informs later calibration.
- **Invariants:** absence never means loss; if nothing authoritative is visible, outcome is `UNKNOWN`.
- **Implementation:** `outcomes.OutcomeObservation`, threat outcome helpers; schema `outcome` is older and
  not a one-to-one mirror of the runtime label vocabulary.

## Customer and Customer Relevance

- **Purpose:** CustomerProfile states who the tenant is and structured relevance inputs; CustomerContext is
  the derived matching view.
- **Identity:** stable operator-chosen `customer_id`/`customer_key` slug.
- **Mutability:** profile versions append; latest effective version wins. Watch retirement appends a closure.
- **Tenancy:** customer-private.
- **Time:** profile `effective_from`, watch `valid_from`/`valid_to`; context reconstructs as of cutoff.
- **Evidence requirement:** operator provenance; entity/watch resolution state remains explicit.
- **Relationships:** relevance matches direct subject, watched entity/program, capability, or agency.
- **Invariants:** a customer-private fact never promotes itself into global intelligence; the authenticated
  actor cannot choose a different tenant.
- **Implementation:** `customers.py`, `material_changes.CustomerContext`; schema `customer`,
  `customer_watchlist`.

## Material Change

- **Purpose:** customer-facing projection answering what changed and why it matters to that customer.
- **Identity:** source intelligence id is the stable `material_change_id`; durable version identity is
  `(customer_id, material_change_id, content_version)`.
- **Mutability:** projection is recomputed; customer-scoped records append a version only when the material
  content hash changes.
- **Tenancy:** per customer for relevance, first-seen/delivery, version, and review overlay; referenced
  global intelligence stays global.
- **Time:** intelligence observed, first relevant, delivered, reviewed, and outcome times remain distinct.
- **Evidence requirement:** references to global source/evidence, never copied evidence bodies.
- **Relationships:** projects threat, propagated threat, or opportunity; links investigation pages and
  customer lifecycle.
- **Invariants:** observed and assessed blocks remain separate; unrelated customer rows are suppressed;
  rebuild is idempotent and does not erase review history.
- **Implementation:** `material_changes.py`, `customer_material_changes.py`, `ops.py`; schema
  `customer_material_change`.

## Investigation

- **Purpose:** point-in-time deterministic search and company/program read projections beneath a Material
  Change.
- **Identity:** reuses canonical company refs, native identifiers, and program keys.
- **Mutability:** read-only projection; search never writes a merge.
- **Tenancy:** global by default; optional customer-private overlay is access-checked.
- **Time:** estate, edges, sections, and outcomes filter at `as_of` and relationship validity.
- **Evidence requirement:** identifiers come from structured provenance; ambiguity remains visible.
- **Relationships:** navigates entities, programs, events, relationships, threats, opportunities, outcomes.
- **Invariants:** exact identifier → exact name/alias → scored partial; no runtime LLM resolution.
- **Implementation:** `investigation.py`, service/API/frontend in ops modules.

## Watchlist and review lifecycle

- **Purpose:** watchlists state customer attention; ReviewAction records what a customer did about a
  Material Change.
- **Identity:** watch id hashes customer/type/ref/valid-from; review action hashes customer/change/action/
  time/actor.
- **Mutability:** append-only additions, closures, and actions.
- **Tenancy:** strictly customer-private.
- **Time:** watches have validity; actions have `at`; lifecycle as-of is reconstructed.
- **Evidence requirement:** explicit operator/customer action; unresolved watch references stay unresolved.
- **Relationships:** watch feeds relevance; review overlays NEW/REVIEWED/MONITORING/INVESTIGATING/
  DISMISSED/RESOLVED onto the system assessment.
- **Invariants:** customer dismissal does not mutate global threat/opportunity; cross-customer action fails.
- **Implementation:** `customers.py`; schema `customer_watchlist`, `customer_review_action`.

## Replay

- **Purpose:** reconstructs what could have been known and what the policy would have decided at a cutoff.
- **Identity:** case ids, policy/version ids, and deterministic result/report hashes.
- **Mutability:** corpora are frozen inputs; results append or are regenerated deterministically.
- **Tenancy:** evaluation/global; customer-specific historical context must use its effective configuration.
- **Time:** `available_at <= replay_as_of`; later evidence/outcomes remain excluded until visible.
- **Evidence requirement:** source ids/refs, record kind, strength, timing; stronger canonical cases include
  role, URL, human adjudication, later outcome, and explicit future evidence.
- **Relationships:** exercises scoring, chains, consequences, fit, threats, selectivity, and outcomes.
- **Invariants:** prospective calls are frozen; later evidence may resolve history but not rewrite the
  earlier state.
- **Implementation:** `replay.py`, `examples/replay/`, `docs/replay/`, milestone corpus tests.

## Invariant status summary

| Statement | Status in this baseline |
|---|---|
| Canonical record ≠ presentation | Implemented in Material Changes/investigation projections |
| Capture ≠ verify ≠ publish | Implemented as distinct archive, system disposition, review, and delivery steps; not every source has a first-class verification state |
| Evidence state ≠ claim state ≠ outcome state | Architectural rule; evidence/outcome implemented, Claim only partial/schema-only |
| Unknown never becomes zero | Implemented in outcomes/value/fit paths where documented; do not assume universal validation over arbitrary new code |
| Conflicting claims may survive | Supported by append-only evidence/relationships; no complete first-class runtime Claim lifecycle |
| Prospective calls are frozen | Implemented for replay/prediction corpora and append-only outcome learning |
| No retrospective forecast backfill | Implemented by preserved predictions and future-outcome exclusion |
| Later evidence resolves but does not rewrite prior knowledge | Implemented in replay, outcome resolution, customer Material Change versions, and append-only histories |
