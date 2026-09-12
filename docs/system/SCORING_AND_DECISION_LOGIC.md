# Scoring and decision logic

Status: descriptive  
Last reviewed: 2026-09-12

## Do not collapse these values

Pyrnova uses several decision quantities for different questions:

| Quantity | Question | Primary implementation |
|---|---|---|
| evidence strength | How authoritative/direct is the supporting record? | Evidence assessments/replay records, 1–5 |
| relevance score | Does this opportunity match a capability profile? | `match.py`, 0–1 |
| opportunity attractiveness | How commercially attractive is it? | `Opportunity.attractiveness`, separate field |
| intelligence confidence | How strongly is the assessment supported? | Opportunity/consequence/threat fields |
| materiality/severity | How large or consequential is the change? | Threat/material-change assessment |
| fit confidence | How credible is the company posture for a consequence? | `fit.py` |
| relationship confidence | How well is an edge grounded? | `chains.py`/`relationships.py` |
| human decision | What did a reviewer decide? | `review.py`, review queues, customer actions |

Evidence strength is not confidence. Confidence is not materiality. Fit is not the opportunity score.
Customer lifecycle state is not the system verdict.

## Generic intelligence principles

- deterministic facts, ids, dates, calculations, and state are authoritative;
- optional AI output is non-authoritative and cannot overwrite deterministic fields;
- unknown remains unknown;
- direct/source-native identity outranks inferred similarity;
- evidence, assumptions, falsifiers, and contradictions remain inspectable;
- zero consequences, no fit, WATCH, or REJECT are valid results;
- temporal availability and validity gate every historical judgment;
- later outcomes grade prior calls rather than rewriting them;
- policy changes are versioned and corpus-evaluated.

These principles do not define a universal cross-sector scorer.

## Phase 1 / federal-contractor policies

### Active replay scoring

`replay.ACTIVE_SCORING_VERSION` is `scoring_v1`:

| Policy | Status | Strike threshold | Watch threshold | Notes |
|---|---|---:|---:|---|
| `scoring_v1` | active | 0.30 | 0.15 | `evidence_v1`, `thresholds_v1`, `mechanisms_v1` |
| `scoring_v1_stricter_candidate` | evaluation only | 0.40 | 0.15 | challenger, not production |
| `scoring_v2_candidate` | evaluation only | 0.80 | 0.15 | challenger, not production |

Replay score is derived from visible evidence strengths, contradiction/failure conditions, and candidate
policy inputs in `replay.py`. The corpus fixes expected dispositions and ground truth. Do not modify
`scoring_v1` to make a single case or metric look better.

### Capture Radar recommendation

`match.py` computes deterministic relevance from structured capability-profile fields. In `review.py`:

- recompete expiry is WATCH at relevance ≥ 0.15 because expiry alone needs corroborating procurement
  evidence before STRIKE;
- a direct opportunity clears STRIKE at the configured relevance threshold (default 0.30);
- relevance ≥ 0.15 becomes WATCH;
- lower relevance becomes REJECT.

The automated reviewer label is `auto-recommend/v2`. Passing a legacy reviewer name to the pipeline does
not itself prove human acceptance. Explicit adjudication requires ACCEPT/WATCH/REJECT, a non-empty reviewer,
and a reason; `apply_review` then maps the human/system disposition to opportunity lifecycle.

### Cross-source joins

M5/M6 chain resolution accepts deterministic program/native-id joins. Anchored inferred joins are scored
against a frozen acceptance threshold; a lower review band is queued for human adjudication. Topic-only,
agency-name-only, and chronology-only paths are rejected upstream. Review retains pre-review confidence and
automated recommendation for calibration.

### Consequence and fit

Commercial consequences use named mechanisms and directness (`DIRECT`, `DOWNSTREAM`, `SECOND_ORDER`),
with mechanism confidence, assumptions, falsifiers, and an explicit screened disposition. Value may be
unknown. `fit.py` evaluates structured dimensions into PRIME/SUPPORT/TEAM/DEFEND/NO_FIT and
POSITIVE/NEGATIVE/UNKNOWN. Fatal blockers suppress fit. This logic does not override `scoring_v1`.

### Threats and Material Changes

Threat `severity` and `confidence` are categorical, orthogonal values. Exposure join class, materiality,
temporal validity, evidence, and mechanism all matter. Propagation over accepted edges cannot increase
confidence. Material Changes then map source intelligence to OPPORTUNITY/THREAT/MONITORING and apply
deterministic customer relevance in this priority order:

1. DIRECT_SUBJECT;
2. WATCHED_ENTITY;
3. WATCHED_PROGRAM;
4. CAPABILITY_MATCH;
5. AGENCY_INTEREST (monitoring-grade).

The projection reports the basis and all reasons. It uses no runtime LLM.

## Review and adjudication boundaries

| State | Authority |
|---|---|
| system disposition | Named deterministic policy/code revision |
| opportunity human adjudication | Named reviewer record |
| inferred join/fit review | Named reviewer record retaining automated state |
| customer Material Change lifecycle | Customer/operator action overlay only |
| outcome | Dated, sourced observation; never absence |

A customer dismissal does not refute or delete the underlying global intelligence. A reviewer decision is
valuable labeled evidence, but it does not silently modify policy weights.

## Fallbacks and failure behavior

- Missing/invalid availability: exclude from historical reasoning.
- Missing authoritative outcome: UNKNOWN.
- Unresolved entity: surface UNRESOLVED/AMBIGUOUS, do not guess.
- No credible consequence/fit: return none/UNKNOWN/REJECT rather than inventing one.
- Source/adaptor failure: report failure/degraded state; do not present stale data as fresh.
- AI unavailable: `NullReasoner`, deterministic path unchanged.

## Known limitations

- Threshold/corpus sizes are small and milestone-specific; dated precision results are not universal
  performance claims.
- Some mechanism families exist but have limited or no reviewed cases.
- Evidence independence is conservative source counting, not first-class lineage.
- Materiality bands and Phase 1 relevance are federal-procurement oriented.
- `industrial_v1` is research terminology on a separate branch, not a current production policy.
- There is no probabilistic calibration service, model registry, or automated policy promotion.

Policy changes require explicit authority, a new version identifier, full applicable corpus comparison,
negative-control review, regression explanation, and separate production/owner acceptance evidence.
