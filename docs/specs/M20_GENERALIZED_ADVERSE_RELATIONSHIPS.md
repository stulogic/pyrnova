# M20 — material adverse-event + relationship-type generalization

_Status: CLOSED 2026-09-09. Builds additively on M19; `scoring_v1`, `fit.py`, `replay.py`, and
`corpus_m15`…`corpus_m19` remain byte-identical._

## Contract

M20 must prove that the threat path generalizes beyond contract deobligations and subcontractors:

> real material adverse event → deterministic exposure → selective HIGH-trust direct threat → real
> non-subcontract relationship → bounded propagated consequence.

The accepted third family is `sec_corporate_adverse_event`. `parse_sec_corporate_adverse` accepts only
an explicit SEC accession, CIK, filing date, recognized adverse type, and positive known amount; generic
risk factors do not qualify. `CORPORATE_RESTRUCTURING` is a new mechanism because realized company-level
restructuring/exit costs are not honestly a program contraction, regulatory-compliance cost, or facility
geography event. A $5M family-local materiality floor rejects routine costs. Confidence comes from the
exact CIK exposure; severity comes only from the disclosed amount.

The accepted new real relationship is `COMPANY_TO_PROGRAM`. `ground_company_program_edges` requires an
exact USAspending recipient id on the award row, retains the PIID, value, source ids, archive hash, and
validity window, and emits a CONFIRMED deterministic-native-id edge. It is exercised in propagation,
not merely stored metadata.

Every relationship is both knowable at evaluation (`available_at <= as_of`) and valid when the root
catalyst occurred (`valid_from <= threat.available_at <= valid_to`). Complete join/source/validity/
provenance data survives in each propagation hop. Existing confidence degradation, depth bound, cycle
prevention, and duplicate suppression are unchanged.

## Real acceptance chain

SAIC fiscal-2026 Form 10-K, accession `0001571123-26-000029`, filed 2026-03-16, reports $35M of
restructuring, impairment and other exit costs (including severance, facility exits, impairment, and
executive-transition costs). Exact filer CIK `0001571123` → deterministic exposure →
`CORPORATE_RESTRUCTURING`, HIGH severity / HIGH confidence, status MATERIALIZED. The threat propagates
one hop to active Army program `W31P4Q21F0095` over SAIC's exact recipient-id/PIID prime relationship,
degrading to MODERATE/MEDIUM.

The retained evidence file is a compact attributable filing extract, independently identity-checked
against the existing raw SEC submissions archive. One budgeted direct full-submission request returned
HTTP 403 and was not retried; the extract is therefore not represented as a new raw filing-body archive.
This limitation does not change the source-native accession, CIK, filing date, disclosed amounts, or
official filing URL, but a future refresh should archive raw filing bytes when SEC access permits.

## Selectivity and negatives

M20 includes exact-CIK mismatch, sub-floor/immaterial cost, future filing exclusion, future relationship
evidence exclusion, not-yet-valid relationship exclusion, and name-only relationship rejection. No
relationship or supplier/customer/parent edge is inferred from names. Unresolved remains UNKNOWN and
absence never becomes false alert.

## Operations and calls

The existing selectivity/scheduler path is reused. `summarize_m20` adds relationship-type counts,
real-vs-probe types, per-type resolved/false outcomes, temporal terminations, and HIGH/CRITICAL outcome
counts. The Operations Panel adds CIK, target, amount and summary to the existing catalyst view.

Call budget/result: SEC 1 attempted / 0 successful (HTTP 403, no retry); USAspending 0; SAM 0; other
sources 0. Existing SEC/USAspending archives supplied identity and relationship evidence; all parser,
replay, selectivity, and test work was offline.

## Limitations and next work

- This closes on a real material restructuring/exit event, not a source-native contract termination.
- The direct cost is observed/materialized; the propagated program consequence is a bounded risk, not
  evidence that Army delivery failed.
- Resolved propagated outcomes remain 4 and directional; no future fact was invented for the 2026 chain.
- M21 should acquire a raw authoritative termination/cancellation or WARN closure with a named monitored
  exposure, then grow real customer/supplier/subsidiary propagation and later outcomes.
