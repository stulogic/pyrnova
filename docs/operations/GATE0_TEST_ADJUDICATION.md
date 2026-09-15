# Gate 0 — adjudication of the 12 known integration failures

PRELAUNCH-CONVERGENCE-001, Gate 0 (G0.2). Baseline: `phase1-integration-001` @ `7c119dd`
(12 failed, 705 passed, 2 skipped). The identical failing set existed at the `operator-alerts-001`
control tip; integration introduced zero new failures. All 12 live in the five files that
`SOURCE-RIGHTS-001` (a bounded delta that deliberately did not re-run the full suite) left unmigrated.

Governing authority: `docs/strategy/SOURCE_RIGHTS_AUTHORITY.md` and the accepted, passing
`tests/test_source_rights.py`.

## Classification

Each failing expectation was classified A (stale test), B (real defect), or C (authority ambiguity).

### A — STALE TESTS (9), corrected to accepted semantics

**A.1 — D&B/DUNS fixture contamination (7 tests).** `tests/fixtures/sbir_awards.json` embedded a
legacy `duns` field on every record. Accepted authority denies D&B fields ("HTML, workspace, sensitive
or non-public entity data, FOUO/CUI, and D&B fields are denied"); `parse_sbir_awards` and the M14 chain
screen the payload and fail closed. The fixtures' endorsed anchor is UEI (authority: "carries firm UEI");
no test asserts on `duns`. Fix: remove the `duns` fields from the fixture. No production change; source
rights not weakened.
- `test_sbir::test_parse_sbir_awards_returns_chain_ready_records`
- `test_sbir::test_parse_sbir_awards_normalizes_date_edge_cases`
- `test_sbir::test_parse_sbir_awards_company_name_filter_is_case_insensitive_substring`
- `test_sbir::test_parse_sbir_awards_is_idempotent`
- `test_m14_cross_source::test_sbir_to_procurement_accepted_on_real_uei_anchor`
- `test_m14_cross_source::test_different_firm_sbir_is_a_rejected_weak_join`
- `test_m14_cross_source::test_point_in_time_excludes_future_procurement`

**A.2 — SBIR live ingest disabled (2 tests).** Authority retains SBIR "for offline replay; live ingest
remains disabled pending provider review" (`state=INGEST_DISABLED`). `SbirClient.search_awards`
correctly fails closed at `authorize_request` before transport. The old tests expected a successful
live fetch / an `HTTP 503` transport error. Fix: migrated to assert the accepted ingest-disabled denial
takes precedence over transport (offline replay remains covered by the `parse_sbir_awards` tests). No
production change.
- `test_sbir::test_client_search_awards_...` → `test_client_live_search_is_denied_while_ingest_disabled`
- `test_sbir::test_client_raises_on_non_200` → `test_client_ingest_gate_precedes_transport_error_handling`

### B — REAL DEFECTS (0)

Current production enforcement is consistent with accepted authority; no production correction was
required to reach the truthful baseline below.

### C — AUTHORITY AMBIGUITY (3), recorded blocker; production left unchanged

The `SOURCE-RIGHTS-001` registry simultaneously (a) attached `_AGENCY_ARTIFACT_POLICY`
(identity `agency_artifacts`, host `www.acquisition.gov`, `NORMALIZED_ONLY`, `state=INGEST_DISABLED`)
to the `appropriations` and `acquisition_forecast` specs, signalling intent to profile them, and
(b) added the guard `spec.policy.identity != spec.id`, which denies any source whose policy identity
does not match its id. No source has id `agency_artifacts`, so both sources fail closed as UNPROFILED.
The authority doc lists "agency artifacts" as approved substrate, yet the accepted registry leaves the
profile ingest-disabled and mis-identified, and points `appropriations` (which fetches
`www.usaspending.gov` budget artifacts, an endpoint outside every reviewed scope) at the
acquisition.gov profile.

The three tests below assert pre-rights raw-archive success for these sources. Making them green would
require an owner rights-posture decision — enable ingest for agency artifacts / appropriations, correct
the profiled identity and scope, and (for the offline pipeline) supply NORMALIZED_ONLY representations —
or a non-trivial rework of `pyrnova/source_expansion.py` (which archives `sec_edgar` raw, violating the
accepted NORMALIZED_ONLY policy). Neither is a "smallest correction," and the intended launch posture
cannot be safely determined from repository authority. Per the work order's Category-C rule, production
is left unchanged, tests are neither blanket-skipped nor deleted, and these remain as documented,
non-permanent failures pending an owner decision.

- `test_appropriations::test_archive_observation_stores_exact_bytes_with_sanitized_fingerprint`
  — `appropriations` UNPROFILED (acquisition.gov profile vs usaspending.gov endpoint).
- `test_m4_integration::test_program_signal_requires_explicit_join_and_only_enriches`
  — archives raw `acquisition_forecast`; UNPROFILED, and NORMALIZED_ONLY would forbid the raw bytes.
- `test_source_expansion::test_offline_source_expansion_archives_normalizes_resolves_and_chains`
  — offline pipeline archives `sec_edgar` raw (NORMALIZED_ONLY violation) and a disabled forecast.

**Recorded blocker for the owner:** _AGENCY-ARTIFACT / APPROPRIATIONS INGEST POSTURE._ Decide whether
agency-artifact and appropriations budget ingest are approved for Customer #1; if so, correct the
profiled identity/scope and NORMALIZED_ONLY representations and re-green the three tests; if not,
confirm the fail-closed posture so the stale tests can be retired to assert denial.

## Result

Truthful relevant baseline after Gate 0 corrections: **3 failed (all documented Category-C blockers),
714 passed, 2 skipped.** No source-rights enforcement was weakened; no blanket xfail/skip; no test
deleted to force green.
