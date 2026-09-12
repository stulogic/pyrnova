# Data and provenance

Status: descriptive  
Last reviewed: 2026-09-12

## Provenance chain

```text
SourceSpec
→ sanitized request + deterministic request fingerprint
→ retrieval attempt / cache or fixture decision
→ exact raw bytes
→ SHA-256 content address + observation metadata
→ source-faithful normalized record
→ event/entity/relationship/exposure
→ assessment, opportunity, consequence, or threat
→ customer relevance + Material Change reference
→ review/prediction/outcome
```

Each transition should remain inspectable. A presentation must be able to point back to evidence; it must
not become the only retained copy of a fact.

## Source identity and status

`pyrnova/sources/registry.py` is the machine-readable source inventory. Each `SourceSpec` declares a
stable source id, source family, base URL, access/auth method, identifiers, possible links, historical
depth, cadence, request-budget posture, reliability, implementation status, priority, and rights note.
The rendered inventory is [`../specs/SOURCE_MANIFEST.md`](../specs/SOURCE_MANIFEST.md).

Important distinctions:

- `active=True` means eligible under the current product boundary; it does not prove current reachability.
- `status=operational`, `adapter_ready`, or `blocked` is an implementation/operation label.
- `reliability=live_proven`, `archive_operational`, `fixture_only`, or `unverified` describes the evidence
  used to validate the adapter. These values and notes can age.
- source rights/status are engineering metadata, not legal advice or an unrestricted-redistribution claim.

## Retrieval modes

| Mode | Network | Cache/archive | Intended use |
|---|---|---|---|
| OFFLINE | Forbidden by source control | Fixture or previously archived bytes | Default development, tests, replay |
| LIVE_SAFE | Explicit and budgeted | Reuse allowed/preferred | Controlled delta operation |
| ACCEPTANCE | Explicit fresh call | Cache is not allowed to masquerade as success | Dated connectivity/freshness proof |

`SourceControl` authorizes the request immediately before transport. A failed live request still consumes
the reserved budget. Retry timing is metadata; no hidden infinite retry loop or sleep is embedded.
`SourceScheduler` persists budget/breaker/checkpoint state across restarts and gates poll cadence. Cache
hits and offline replay do not consume live-call cadence/budget.

## Request provenance and secrets

`sanitized_request` lowercases/sorts headers, canonicalizes URLs, removes fragments, sorts query
parameters, and recursively redacts credential-like keys. `request_fingerprint` hashes the canonical JSON
representation with SHA-256. Credential values therefore do not enter the retained fingerprint.

Adapters must never persist API keys, bearer tokens, cookies, passwords, private keys, or secret-bearing
exceptions/URLs. `.env` and local runtime directories remain outside Git. SEC live access requires a
configured descriptive identity; code returns an empty identity rather than inventing contact data.

## Archival and hashes

`EvidenceArchive.put` accepts bytes and returns an `Evidence` record. The local backend stores bytes at:

```text
<archive root>/<source id>/<first two hash characters>/<sha256>
```

It writes the body only if absent, then appends an `.observations.jsonl` sidecar for every observation.
The optional S3-compatible backend uses the equivalent content key and one observation object per Evidence
id. Hash identity refers to retained bytes, not semantic equivalence.

The archive does not itself verify that a publisher’s semantic content is truthful; it proves which bytes
Pyrnova retained and when Pyrnova recorded the observation.

## Retention tiers

- **Tier A:** version-sensitive/mutable sources. Retain materially distinct states and observation history.
- **Tier B:** durable publication/artifact content. Equal bytes can share one content object while separate
  observations remain recorded.
- **Tier C:** declared ephemeral tier; no current foundation document claims a production lifecycle for it.

The registry controls the tier supplied by pipeline archival. A new adapter must justify its tier and
rights posture before production activation.

## Source-native identifiers

Preserve the strongest native identifiers before normalization: award/notice id, solicitation number,
UEI, CIK/accession, OFAC `ent_num`, SBIR tracking number, document number, TAS/federal account, or a
source-specific forecast id. Deterministic identities should hash or namespace these stable values, not
titles or generated prose.

Name normalization is a search aid, not proof of identity. M22-D search deliberately returns AMBIGUOUS or
UNRESOLVED rather than forcing a merge. Relationship grounding records join method and rationale.

## Evidence spans and claims

The PostgreSQL schema can store `claim.evidence_span`, producer, confidence, and validation status. The
runtime does not yet implement a first-class Claim repository. Current AI support is a bounded optional
`Reasoner` that may add non-authoritative metadata/recommendations and must not overwrite deterministic
ids, dates, evidence, or calculations.

For current runtime records, evidence roles/assessments, source refs, URLs, hashes, and archive URIs provide
the implemented grounding. Do not claim the schema-only validation lifecycle is operational.

## Deduplication and idempotency

Different layers use different identities:

- request dedupe: sanitized request SHA-256 in `SourceStateStore`;
- raw content: exact-byte SHA-256 in `EvidenceArchive`;
- pipeline opportunity: source-native identity key, then UUIDv5;
- relationships/threats/consequences: deterministic ids over documented anchors;
- customer Material Change: `(customer_id, source intelligence id)`;
- customer Material Change version: deterministic version number plus material content hash;
- outcomes/review actions/watches: stable hashes over their semantic identity fields.

Equal content or equal request does not prove equal event. Conversely, two publisher artifacts may describe
one underlying event and require an explicit lineage model; first-class multi-source event clustering and
evidence independence remain limited.

## Revisions, amendments, and conflicts

Mutable source states should produce new retained observations. Amendments must not be silently dropped;
source-native version/accession identifiers and content hashes are the basis for distinguishing them.
Current adapters handle several source-specific cases, such as SEC accession dedupe that preserves
amendments and Tier-A snapshot changes. There is no universal amendment/supersession engine.

Append-only storage permits contradictory evidence or assessments to survive. Readers and replay choose
what was visible and valid at a cutoff. They do not rewrite older bytes or frozen predictions.

## Temporal availability

- `published_at`: date/time asserted by the source for publication.
- `occurred_at` or effective date: when the described event happened.
- `first_seen_at`/`fetched_at`/`observed_at`: when Pyrnova observed the source state.
- `available_at`: when a record/relationship could legitimately enter reasoning.
- `valid_from`/`valid_to`: interval in which an entity relationship or customer watch is considered valid.
- `delivered_at`: when a customer-scoped Material Change was first materialized.

These may differ. If availability is absent, replay code excludes the record rather than assuming it was
known. The repository currently mixes some naive and timezone-aware ISO timestamps; normalization is
recorded technical debt.

## Source health and checkpointing

`SourceStateStore` persists checkpoint, request index, budget epoch/calls, breaker state, metrics, and
operator/schedule fields per source. Scheduler health reports source mode, pause state, budget, breaker,
next poll, call/cache metrics, last success/change, checkpoint, and indexed-request count.

Health means what the persisted telemetry establishes. Missing quota remains unknown. A stored observation
is not proof the source is reachable now; a successful fixture parse is not a live connectivity result.

## Implemented examples

- **USAspending:** award ids/recipient identifiers retained; exact bytes archived; deterministic recompete,
  deobligation, termination, recipient hierarchy, and subaward relationship paths are covered by tests and
  replay artifacts.
- **SAM.gov:** notice/solicitation identity, API-key redaction, raw archival, and pre-solicitation detection;
  live use requires `SAM_API_KEY`.
- **SEC EDGAR:** CIK/accession identity, configured User-Agent, accession dedupe, submissions/companyfacts
  parsing, safe 403 behavior, and archived examples.
- **Federal Register/OFAC:** archived real examples and source-specific parsers feed adverse-event/exposure
  paths; OFAC use is intelligence evidence, not authoritative sanctions-screening compliance.
- **SBIR, Grants.gov, appropriations, procurement forecasts:** adapters/fixtures with explicit registry
  reliability; do not upgrade them to live-proven without dated acceptance evidence.

## Replay requirements

A replay-grade case needs stable case and source identities, source role, strength, an availability time,
cutoff, candidate/expected disposition, ground truth, reviewer, and explicit future exclusion. Stronger
canonical cases also record URLs, human adjudication, outcome, and ambiguity/negative controls. See
[`REPLAY_AND_TEMPORAL_TRUTH.md`](REPLAY_AND_TEMPORAL_TRUTH.md).
