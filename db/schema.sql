-- Pyrnova canonical operational schema (Postgres).
-- Scope: MVP canonical objects only. Forward-compatible with the dormant Enterprise and
-- Strategic/Data pipelines via jsonb extension columns and reserved enum values, but NO objects for
-- those pipelines are populated during the initial commercial phase (see EXECUTION_AUTHORITY_30D.md).
--
-- Deterministic core is authoritative here: identifiers, timestamps, raw-evidence pointers, rights,
-- workflow state, historical reconstruction. AI-produced content lives in `claim` as non-authoritative
-- claims until validated / human-reviewed.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- SOURCE REGISTRY + POINT-IN-TIME EVIDENCE ARCHIVE
-- ---------------------------------------------------------------------------

-- Every source we OBSERVE, with the rights/provenance metadata we must know now.
CREATE TABLE source (
    id              text PRIMARY KEY,                 -- 'usaspending', 'sam_opportunities', ...
    name            text NOT NULL,
    base_url        text NOT NULL,
    rights          text NOT NULL,                    -- 'public_domain' | 'us_gov_work' | 'licensed' ...
    retention_tier  char(1) NOT NULL CHECK (retention_tier IN ('A','B','C')),
    notes           text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- A single observed pull. This is the moat's timestamp backbone: it records WHEN Pyrnova first saw a
-- given source state, independent of the source's own publication dates.
CREATE TABLE observation (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id       text NOT NULL REFERENCES source(id),
    request_url     text NOT NULL,
    request_params  jsonb NOT NULL DEFAULT '{}'::jsonb,
    observed_at     timestamptz NOT NULL DEFAULT now(),  -- Pyrnova first-observed timestamp
    http_status     int,
    ok              boolean NOT NULL DEFAULT true
);

-- Content-addressed raw evidence. content_sha256 dedups identical bytes across observations (Tier B
-- durable content is stored once; Tier A version-sensitive content produces a new row when bytes
-- differ). archive_uri points into the object store / local archive.
CREATE TABLE evidence (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id       text NOT NULL REFERENCES source(id),
    observation_id  uuid REFERENCES observation(id),
    content_sha256  char(64) NOT NULL,
    media_type      text NOT NULL DEFAULT 'application/json',
    archive_uri     text NOT NULL,                    -- e.g. s3://bucket/... or file://var/archive/...
    source_ref      text,                             -- source-native id (award id, notice id, FR doc no)
    source_url      text,                             -- human-viewable citation link
    published_at    timestamptz,                      -- source's own publication/effective date
    first_seen_at   timestamptz NOT NULL DEFAULT now(),
    retention_tier  char(1) NOT NULL CHECK (retention_tier IN ('A','B','C')),
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX evidence_sha_idx ON evidence(content_sha256);
CREATE INDEX evidence_source_ref_idx ON evidence(source_id, source_ref);

-- ---------------------------------------------------------------------------
-- ENTITIES  (UEI-keyed where possible)
-- ---------------------------------------------------------------------------
CREATE TABLE entity (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    kind            text NOT NULL,                    -- 'recipient' | 'agency' | 'office' | 'program'
    uei             text,                             -- SAM Unique Entity ID (recipients)
    name            text NOT NULL,
    canonical_name  text,                             -- normalized for resolution
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX entity_uei_idx ON entity(uei);
CREATE INDEX entity_canonical_idx ON entity(canonical_name);

-- ---------------------------------------------------------------------------
-- CLAIM  (AI/deterministic extraction output; NOT authoritative until validated)
-- ---------------------------------------------------------------------------
CREATE TABLE claim (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    evidence_id     uuid NOT NULL REFERENCES evidence(id),
    predicate       text NOT NULL,                    -- 'incumbent_is' | 'pop_end_date' | 'notice_type' ...
    value           jsonb NOT NULL,
    evidence_span   text,                             -- quoted span / field path grounding the claim
    producer        text NOT NULL,                    -- 'deterministic' | 'ai:<model>'
    confidence      real,                             -- 0..1 (AI) or NULL (deterministic)
    validated       boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX claim_evidence_idx ON claim(evidence_id);

-- ---------------------------------------------------------------------------
-- EVENT / CATALYST  (something happened / a precursor that moves future demand)
-- ---------------------------------------------------------------------------
CREATE TABLE event (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    kind            text NOT NULL,                    -- 'award' | 'notice_posted' | 'amendment' | 'cancellation'
    stage           text CHECK (stage IN ('INTENT','AUTHORIZATION','FUNDING','PROGRAM','MARKET_ENGAGEMENT','PROCUREMENT','AWARD','OUTCOME')),
    program_key     text,                             -- explicit source/crosswalk identity; never topic-inferred
    occurred_at     timestamptz,
    agency_id       uuid REFERENCES entity(id),
    recipient_id    uuid REFERENCES entity(id),
    summary         text,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX event_program_stage_idx ON event(program_key, stage);

CREATE TABLE event_evidence (
    event_id        uuid NOT NULL REFERENCES event(id),
    evidence_id     uuid NOT NULL REFERENCES evidence(id),
    role            text NOT NULL DEFAULT 'supporting',
    PRIMARY KEY (event_id, evidence_id)
);

-- Generic evidence-backed graph edge. Sources terminate at normalized entities/events; source-native
-- fields remain in evidence/meta rather than defining this relationship model.
--
-- M5 cross-source capital-chain resolution adds the temporal/confidence columns below. join_method
-- records how the edge was established (deterministic vs conservatively inferred); first_observed_at
-- is the earliest time both endpoints were knowable, so replay can answer "when could we first have
-- known this relationship?". Topic-only, agency-name-only, and chronology-only matches are never
-- persisted here — they are rejected upstream.
CREATE TABLE relationship (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject_id      uuid NOT NULL,
    predicate       text NOT NULL,                    -- AUTHORIZES|FUNDS|IMPLEMENTS|PRECEDES|CORROBORATES|CONTRADICTS|AWARDED_TO|SUBSIDIARY_OF|LOCATED_AT|...
    object_id       uuid NOT NULL,
    join_method     text,                             -- deterministic_program_key|deterministic_native_id|inferred_strong_attribute|authoritative_entity_field
    confidence      real,                             -- per-relationship confidence 0..1
    rationale       text,                             -- why this edge exists (audit)
    first_observed_at timestamptz,                    -- earliest time both endpoints were knowable
    available_at    timestamptz,                      -- alias of first_observed_at for point-in-time queries
    valid_from      timestamptz,
    valid_to        timestamptz,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX relationship_subject_pred_idx ON relationship(subject_id, predicate);
CREATE INDEX relationship_first_observed_idx ON relationship(first_observed_at);

CREATE TABLE relationship_evidence (
    relationship_id uuid NOT NULL REFERENCES relationship(id),
    evidence_id     uuid NOT NULL REFERENCES evidence(id),
    PRIMARY KEY (relationship_id, evidence_id)
);

CREATE TABLE catalyst (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    kind            text NOT NULL,                    -- 'recompete_expiry' | 'sources_sought' | 'rfi' | 'presolicitation' | 'special_notice'
    event_id        uuid REFERENCES event(id),
    detected_by     text NOT NULL,                    -- 'recompete_engine' | 'presolicitation_engine' | 'ai'
    horizon_days    int,                              -- lead time to expected procurement action
    summary         text,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- CUSTOMER + CAPABILITY PROFILE
-- ---------------------------------------------------------------------------
CREATE TABLE customer (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            text NOT NULL,
    stage           text NOT NULL DEFAULT 'prospect', -- 'prospect' | 'sprint' | 'radar' | 'pilot'
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE capability_profile (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id     uuid NOT NULL REFERENCES customer(id),
    agencies        jsonb NOT NULL DEFAULT '[]'::jsonb,
    naics           jsonb NOT NULL DEFAULT '[]'::jsonb,
    psc             jsonb NOT NULL DEFAULT '[]'::jsonb,
    capabilities    jsonb NOT NULL DEFAULT '[]'::jsonb,   -- free-text capability tags
    geography       jsonb NOT NULL DEFAULT '[]'::jsonb,
    size_min_usd    numeric,
    size_max_usd    numeric,
    set_asides      jsonb NOT NULL DEFAULT '[]'::jsonb,
    exclusions      jsonb NOT NULL DEFAULT '[]'::jsonb,   -- explicit "cannot pursue"
    incumbencies    jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- OPPORTUNITY + STRIKE  (STRIKE is the qualified/actionable STATE of an Opportunity,
-- implemented as lifecycle over one table rather than duplicated storage.)
-- ---------------------------------------------------------------------------
CREATE TABLE opportunity (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_key    text NOT NULL UNIQUE,             -- deterministic source-native opportunity identity
    customer_id     uuid REFERENCES customer(id),
    catalyst_id     uuid REFERENCES catalyst(id),
    -- lifecycle: candidate -> reviewing -> strike (qualified) | rejected
    state           text NOT NULL DEFAULT 'candidate'
                    CHECK (state IN ('candidate','reviewing','strike','rejected')),
    title           text NOT NULL,
    agency_id       uuid REFERENCES entity(id),
    incumbent_id    uuid REFERENCES entity(id),
    naics           text,
    psc             text,
    value_usd       numeric,
    expected_action_at timestamptz,                   -- when it hits the market
    relevance_score real,                             -- capability match 0..1
    attractiveness  real,                             -- opportunity attractiveness 0..1 (kept SEPARATE)
    confidence      real,                             -- our confidence in the intelligence 0..1
    falsification   text,                             -- reasons NOT to pursue (mandatory)
    recommended_action text,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX opportunity_state_idx ON opportunity(state);
CREATE INDEX opportunity_customer_idx ON opportunity(customer_id);

-- Evidence backing an opportunity (many-to-many).
CREATE TABLE opportunity_evidence (
    opportunity_id  uuid NOT NULL REFERENCES opportunity(id),
    evidence_id     uuid NOT NULL REFERENCES evidence(id),
    role            text,                             -- 'primary' | 'incumbent' | 'context' | 'contra'
    strength        smallint CHECK (strength BETWEEN 1 AND 5),
    strength_class  text,
    polarity        text CHECK (polarity IN ('supporting','contradictory')),
    basis           text,
    PRIMARY KEY (opportunity_id, evidence_id)
);

-- M5 opportunity evolution: one evidence-caused disposition change over an opportunity/chain
-- lifecycle. Derived by replaying the active scoring policy point-in-time; it records observability
-- (prior -> new disposition, the causing evidence, and when), not a separate scoring model. No
-- promotion state is written that the evidence at that cutoff did not support.
CREATE TABLE opportunity_transition (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject_id      text NOT NULL,                    -- opportunity id, chain id, or program_key
    prior_disposition text CHECK (prior_disposition IN ('SIGNAL','WATCH','STRIKE','REJECT')),
    new_disposition text NOT NULL CHECK (new_disposition IN ('SIGNAL','WATCH','STRIKE','REJECT')),
    cause_stage     text CHECK (cause_stage IN ('INTENT','AUTHORIZATION','FUNDING','PROGRAM','MARKET_ENGAGEMENT','PROCUREMENT','AWARD','OUTCOME')),
    cause_source_id text,
    cause_source_ref text,
    occurred_at     timestamptz,                      -- cutoff at which the change became supportable
    scoring_version text NOT NULL,
    basis           text,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX opportunity_transition_subject_idx ON opportunity_transition(subject_id, occurred_at);

-- ---------------------------------------------------------------------------
-- REVIEW  (human adjudication = labeled intelligence work = benchmark corpus)
-- ---------------------------------------------------------------------------
CREATE TABLE review (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    opportunity_id  uuid NOT NULL REFERENCES opportunity(id),
    decision        text NOT NULL,                    -- legacy/system or human decision label
    reason          text,
    confidence      real,
    reviewer        text,
    human_decision  text CHECK (human_decision IN ('ACCEPT','WATCH','REJECT')),
    system_disposition text NOT NULL DEFAULT 'WATCH'
                    CHECK (system_disposition IN ('STRIKE','WATCH','REJECT')),
    score_at_review real,
    reviewed_at     timestamptz,
    customer_feedback text,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX review_opportunity_created_idx ON review(opportunity_id, created_at DESC);

-- M6 human review queue for uncertain (deferred) inferred cross-source joins. The engine scores an
-- anchored inferred candidate into the review band [0.45, 0.60); a reviewer dispositions it. The
-- pre-review confidence and prior automated recommendation are retained so this becomes durable
-- calibration/training evidence. Dev implementation is append-only JSONL; this table is the
-- production mirror. It never changes scoring_v1.
CREATE TABLE join_review (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id text NOT NULL,                    -- stable id of the candidate inferred edge
    decision        text NOT NULL CHECK (decision IN ('ACCEPT_JOIN','REJECT_JOIN','WATCH')),
    reviewer        text NOT NULL,
    reason          text,
    pre_review_confidence real,                       -- engine's computed confidence at deferral
    automated_recommendation text,                    -- prior automated disposition (e.g. 'DEFER')
    subject_id      text,
    object_id       text,
    predicate       text,
    join_method     text,
    first_observed_at timestamptz,
    reviewed_at     timestamptz,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX join_review_relationship_idx ON join_review(relationship_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- PREDICTION + OUTCOME  (forward proof; graded later)
-- ---------------------------------------------------------------------------
CREATE TABLE prediction (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    opportunity_id  uuid NOT NULL REFERENCES opportunity(id),
    statement       text NOT NULL,                    -- e.g. "recompete solicitation posts by <date>"
    predicted_at    timestamptz NOT NULL DEFAULT now(),
    resolve_by      timestamptz,
    precursor_class text,                             -- 'recompete_expiry' | 'sources_sought' | ...
    lead_time_days  int,
    meta            jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE outcome (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id   uuid NOT NULL REFERENCES prediction(id),
    observed_at     timestamptz NOT NULL DEFAULT now(),
    result          text NOT NULL,                    -- 'confirmed' | 'refuted' | 'partial' | 'pending'
    evidence_id     uuid REFERENCES evidence(id),
    notes           text
);

CREATE TABLE replay_evaluation (
    id              text PRIMARY KEY,
    case_id         text NOT NULL,
    replay_as_of    timestamptz NOT NULL,
    mechanism_family text NOT NULL,
    system_disposition text NOT NULL CHECK (system_disposition IN ('STRIKE','WATCH','REJECT')),
    score           real NOT NULL,
    scoring_version text NOT NULL,
    evidence_policy_version text NOT NULL,
    threshold_version text NOT NULL,
    mechanism_rule_version text NOT NULL,
    ground_truth_label text NOT NULL CHECK (ground_truth_label IN ('TRUE_POSITIVE','TRUE_NEGATIVE','PARTIAL','AMBIGUOUS')),
    lead_time_days  int,
    directionally_correct boolean,
    false_positive  boolean,
    false_negative  boolean,
    result          jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE scoring_policy_version (
    version         text PRIMARY KEY,
    evidence_policy_version text NOT NULL,
    threshold_version text NOT NULL,
    mechanism_rule_version text NOT NULL,
    parameters      jsonb NOT NULL,
    status          text NOT NULL CHECK (status IN ('ACTIVE','CANDIDATE','REJECTED','RETIRED')),
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE replay_case (
    case_id         text PRIMARY KEY,
    mechanism_family text NOT NULL,
    replay_as_of    timestamptz NOT NULL,
    ground_truth_label text NOT NULL CHECK (ground_truth_label IN ('TRUE_POSITIVE','TRUE_NEGATIVE','PARTIAL','AMBIGUOUS')),
    ground_truth_confidence text NOT NULL CHECK (ground_truth_confidence IN ('HIGH','MEDIUM','LOW')),
    reviewer        text NOT NULL,
    case_record     jsonb NOT NULL,
    admitted_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE replay_report (
    id              text PRIMARY KEY,
    kind            text NOT NULL,
    scoring_versions text[] NOT NULL,
    result_ids      text[] NOT NULL,
    metrics         jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Reserved for dormant pipelines (declared, never populated in initial phase):
--   FLOW, SHIFT, RISK  -> intentionally NOT created. Add only when a pipeline is activated.
