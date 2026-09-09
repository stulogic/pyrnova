# M21 replay evidence — raw termination + economic relationship diversity

_Reproducible from `~/Documents/Pyrnova` on `main`. All replay is offline over archived raw bytes and the
committed OFAC fixture; no live calls are needed to reproduce._

## Reproduce

```
.venv/bin/python -m pytest tests/test_m21_sec_hardening.py \
    tests/test_m21_raw_termination_relationship.py tests/test_m21_corpus.py -q
```

## Flagship raw chain (offline, hash-verified)

| Stage | Evidence | Value |
|---|---|---|
| Raw adverse event | `usaspending_award_termination_dap.transactions.json` (raw bytes) | Terminate for convenience, PIID `36C25726N0240`, mod `P00002`, action_type `F`, 2026-08-31, −$3,908,263.25 |
| Archive hash | `.transactions.provenance.json` `sha256` | matches `sha256(raw bytes)` (immutable evidence) |
| Deterministic exposure | recipient UEI `YR7CLZFGCM95` on the terminated award | `deterministic_native_id`, CONFIRMED |
| Direct threat | `PROGRAM_CANCELLATION_OR_DELAY` | severity LOW (frozen $ bands), confidence **HIGH**, OBSERVED, exposure_join_class deterministic |
| New relationship | `SUBSIDIARY_OF` child `YR7CLZFGCM95` → parent `KMSLVW1MZWU9` | `deterministic_native_id`, CONFIRMED (native UEIs; self-parent filtered) |
| Propagated threat | parent inherits | confidence **MEDIUM** (degraded one hop, never increases), severity not distance-inflated |
| Outcome | — | honestly **UNRESOLVED** (event days old; no defensible later evidence within budget) |

## Corpus metrics (`summarize_m21`, OFAC-designations harness)

- **80 cases, 80 passing** (74 frozen M20 lineage + 6 M21). Frozen `corpus_m15`…`corpus_m20` byte-identical.
- Direct threats **55**, propagated threats **19**; max propagation depth **2**; propagation explosion
  **False**; confidence never increases **True**; temporal leakage violations **0**.
- Real relationship types: `COMPANY_TO_PROGRAM`, `SUBCONTRACTOR_OF`, **`SUBSIDIARY_OF`** (new, outside the
  government-program graph); unique entity pairs **16**.
- Raw adverse event: `contract_modification` / `CONTRACT_TERMINATION`, `raw_authoritative_bytes` True;
  termination direct threats **4**, termination propagated threats **2**.
- Deterministic direct threats **47**; resolved deterministic direct outcomes precision **0.9412** (N=17);
  negatives **20**; adverse-event families exercised **3** (contract_modification, regulatory_adverse_event,
  sec_corporate_adverse_event).
- Relationship temporal terminations **2**.

## Selectivity / negatives (M21 cases)

| Case | Demonstrates | Result |
|---|---|---|
| `m21-real-termination-subsidiary` | flagship raw termination → SUBSIDIARY_OF propagation | 1 direct HIGH, 1 propagated MEDIUM |
| `m21-termination-unrelated-same-sector-no-exposure` | shared NAICS 236220 / geography is not a dependency | 0 threats, NO_EXPOSURE |
| `m21-subsidiary-edge-not-yet-valid` | relationship invalid at event time | direct fires, 0 propagated, 1 temporal termination |
| `m21-weak-subsidiary-name-only-terminates` | weak/inferred edge insufficient for propagation | direct fires, 0 propagated |
| `m21-lapsed-incumbency-exposure-ended` | deterministic identity is not itself a threat | 0 threats, EXPOSURE_ENDED |
| `m21-duplicate-subsidiary-edge-suppressed` | duplicate evidence ≠ duplicate intelligence | 1 propagated (1 suppressed) |

## SEC ingestion hardening (offline, fault-injected)

`tests/test_m21_sec_hardening.py`: declared identity composes from config and is never fabricated (empty +
clean failure when unconfigured); `SEC_ACCESS_ORDER` + discovery/body separation; `full_submission_url`
raw artifact; `accession_dedupe` skips archived accessions and preserves amendments as new artifacts; a
403 is terminal (one call, no retry loop, spend recorded) and a 429 installs a cooldown.

## Calls

USAspending (keyless, public domain, one-time acquisition, archived for replay): ~16 total — discovery to
locate a material termination with a distinct parent, then 3 archival retrievals
(transactions/award/recipient). SEC 0, SAM 0, other 0. From this canonical local tree USAspending
returned HTTP 200; the M20 SEC 403 observation (cloud egress) is unchanged and untested here.
