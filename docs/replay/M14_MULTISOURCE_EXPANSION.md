# M14 — Multi-source expansion + cross-source chains (evidence report)

_Reproducible from `tests/test_m14_cross_source.py` and `tests/test_m14_ops_panel.py`. Spec:
`docs/specs/M14_MULTI_SOURCE_EXPANSION.md`. Manifest: `docs/specs/SOURCE_MANIFEST.md`._

## Source breadth

Nine registered families across distinct economic domains (procurement spend, procurement
opportunities, procurement forecast, appropriations/budget, regulation/policy, funding/assistance,
corporate intelligence, sanctions/trade, federal R&D). M14 added two materially new keyless,
archive-first families: **`sbir`** (federal R&D — earliest capability/commercialization precursor) and
**`sanctions_ofac`** (sanctions/trade exposure). Reliability/status per source is in `SOURCE_MANIFEST.md`.

Operational on real bytes (five distinct domains): `usaspending` (live-proven, M13), `sam_opportunities`
(live-proven, M2), `sec_edgar` (archive-operational on real SAIC submissions), `sanctions_ofac` and
`federal_register` (archive-operational — see below). Adapter-ready offline: `grants_gov`,
`appropriations`, `acquisition_forecast`. Blocked: `sbir` (provider returned HTTP 403).

## Live-call discipline

Exactly **three** bounded connectivity probes were made in M14 (one per newly-touched source, no
retries), with all adapter/parser/chain development done against fixtures and existing real archives:

- **`sanctions_ofac` — 1 call, HTTP 200, 5.68 MB, 19,365 real designations.** A single bulk download of
  `www.treasury.gov/ofac/downloads/sdn.csv` confirmed the host and validated `parse_ofac_csv` on real
  production data (7,519 individuals, 1,540 vessels, 342 aircraft, remainder entities). Raw bytes were
  archived offline (git-ignored `var/m14_archive/`, sha256 `1c878982988268de…`) — **archive-once,
  replay-many**; no further OFAC calls were made. Records-per-call: 19,365.
- **`federal_register` — 1 call, HTTP 200.** A filtered `documents.json` probe confirmed the adapter's
  params/schema on real documents; bytes archived offline. Archive-operational.
- **`sbir` — 1 call, HTTP 403 Forbidden.** `api.www.sbir.gov/public/api/awards` refused the probe
  (consistent with the provider-maintenance notice, 2026-09). Documented blocker; the adapter is
  validated offline and connectivity should be retried when the provider is available.

The SDN.CSV fixed-field schema and SBIR JSON schema are stable and confirmed from official
documentation.

## Cross-source chains (Workstream 5)

Both chains reuse the frozen M5/M6 engine (`chains.resolve_chain`) and M10 grounding
(`multisource.build_multisource_profile`) — no new join semantics were introduced.

### Chain A — R&D precursor → procurement (`sbir` + `usaspending`)

SBIR/STTR awards (PROGRAM stage) for Torch Technologies + the firm's real USAspending prime award
(AWARD stage), joined by the engine on Torch's **authoritative recipient UEI** (`YA63J5PVEZE6`, read
from the real USAspending recipient endpoint — not hardcoded) plus awarding agency.

| Metric | Value |
|---|---|
| Contributing families | `sbir`, `usaspending` |
| Accepted joins (total / cross-family) | 3 / 2 |
| Cross-family join method | `inferred_strong_attribute` (UEI + agency anchor) |
| Rejected weak joins | 3 (all `agency_name_only` — different firm/UEI, no shared identifier) |
| Deferred joins | 0 |
| Entity relationships | 1 (`AWARDED_TO` → `entity:uei:YA63J5PVEZE6`) |
| Chain confidence | 0.60 |
| Independent sources | 2 |
| Temporally consistent | yes |
| Observed lead time | 2498 days (~6.8 years, 2014 SBIR → 2021 prime award) |

This demonstrates measurable R&D→procurement lead time. Deterministic identity (UEI) is preferred; the
inferred join is auditable (every factor/penalty retained). A different firm's SBIR award is **rejected**
on agency/topic alone — never silently collapsed onto Torch.

### Chain B — corporate + procurement entity linkage (`sec_edgar` + `usaspending`)

Real SAIC evidence: SEC EDGAR submissions + USAspending prime awards + USAspending recipient, merged
deterministically by `multisource` (recipient / UEI / CIK authority order), point-in-time at
`2024-12-31`.

| Metric | Value |
|---|---|
| Contributing families | `sec_edgar`, `usaspending_prime`, `usaspending_recipient` (3) |
| Join method | `deterministic_entity_merge` |
| Merged authoritative UEI | `MMLKPW9JLX64` |
| Source facts merged | 8 |

## Invariants preserved

Point-in-time truth holds (an early cutoff excludes future procurement, so no cross-family join forms —
`test_point_in_time_excludes_future_procurement`). Raw provenance and request identity are retained by
the existing archive/state layers. `scoring_v1`, `fit.py`, and the frozen historical corpora are
byte-for-byte unchanged (M14 is additive). No STRIKE explosion (M14 creates no candidates/STRIKEs). No
secret leakage (adapters archive sanitized provenance only; no credentials in retained state).

## Known weaknesses / next steps

- `sanctions_ofac` is now `archive_operational` on real bytes; a per-snapshot content-hash cadence run
  would exercise change-detection over time. `sbir` remains `blocked` (HTTP 403) pending provider
  availability — retry one connectivity call to upgrade it to `archive_operational`.
- Chain A's SBIR award *content* is representative; the entity anchor (UEI) and the USAspending award
  are real. A live SBIR acquisition for Torch would upgrade the award content to real bytes.
- OFAC exposure matching is deliberately name-only/weak (non-authoritative); authoritative
  identifier-based sanctions linkage is a roadmap item (`STRATEGIC_CAPABILITY_ROADMAP.md` areas 1, 12).
- Deferred families (Congress, EIA, BLS/BEA, USPTO, WARN, state/local) remain recorded in the roadmap
  with documented rationale.
