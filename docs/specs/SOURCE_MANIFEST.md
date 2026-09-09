# Pyrnova source manifest

_Status: active manifest · authority: `01-PROJECT-AUTHORITY.md` · machine-readable source of truth:
`pyrnova/sources/registry.py`_

`pyrnova/sources/registry.py` is the durable, machine-readable manifest. This document renders and
annotates it; when the two differ, the registry wins. Unknown facts are recorded as `unknown` and must
never be fabricated. Only `active` sources are fetched in the current commercial phase; declared-but-
inactive sources exist for forward compatibility (anti-accumulation rule, `01-PROJECT-AUTHORITY.md`).

## Families and sources

Nine registered families across distinct economic domains (procurement, budget/appropriations, policy/
regulation, funding/assistance, corporate, sanctions/trade, and federal R&D):

| Source id | Family | Access | Auth | Reliability | Status | Priority | Precursor |
|---|---|---|---|---|---|---|---|
| `appropriations` | appropriations_budget | bulk_download | none | fixture_only | adapter_ready | high | AUTHORIZATION |
| `sec_edgar` | corporate_intelligence | rest_api | none | archive_operational | operational | high | — |
| `grants_gov` | funding_assistance | rest_api | none | fixture_only | adapter_ready | medium | FUNDING |
| `acquisition_forecast` | procurement_forecast | bulk_download | none | fixture_only | adapter_ready | medium | MARKET_ENGAGEMENT |
| `sam_opportunities` | procurement_opportunities | rest_api | api_key | live_proven | operational | high | PROCUREMENT |
| `usaspending` | procurement_spend | rest_api | none | live_proven | operational | high | AWARD |
| `federal_register` | regulation_policy | rest_api | none | archive_operational | operational | medium | AUTHORIZATION |
| `sanctions_ofac` | sanctions_trade | bulk_download | none | archive_operational | operational | high | — |
| `sbir` | science_rd | rest_api | none | unverified | blocked | high | PROGRAM |

Connectivity verified 2026-09-09 with three bounded probes total (one per newly-touched source, no
retries): `sanctions_ofac` → HTTP 200, 5.68 MB SDN bulk file, **19,365 real designations** parsed (one
call, 19,365 useful records); `federal_register` → HTTP 200, real documents, adapter params/schema
confirmed; both archived offline (git-ignored `var/`). `sbir` → HTTP 403 (provider maintenance /
bot-block); adapter validated offline, retry connectivity when the provider is available. Five families
are now operational on real bytes across five distinct economic domains (procurement spend, procurement
opportunities, corporate, sanctions, regulation).

## Field meanings

Every registry entry additionally records: `signals` (signal types), `incremental` (checkpoint/cursor/
window mechanism), `identifiers` (stable IDs for entity linking), `links_to` (sources it can join to),
`historical_depth`, `native_cadence`, `recommended_poll`, `call_budget`, and `rights_note`. Reliability
and status are defined as:

- **reliability** — `live_proven` (a real live retrieval has been archived and validated),
  `archive_operational` (real archived bytes are ingested and parsed offline), `fixture_only` (adapter
  validated on representative fixtures), `unverified` (adapter ready; no live/real bytes yet).
- **status** — `operational`, `adapter_ready` (code + tests, offline), `declared`, or `blocked`.

## Precursor lifecycle coverage

M14 broadens observation across the capital lifecycle: **INTENT/AUTHORIZATION** (`appropriations`,
`federal_register`) → **FUNDING** (`grants_gov`) → **PROGRAM / R&D precursor** (`sbir`) →
**MARKET_ENGAGEMENT** (`acquisition_forecast`) → **PROCUREMENT** (`sam_opportunities`) → **AWARD**
(`usaspending`), with `sec_edgar` (corporate) and `sanctions_ofac` (exposure/threat) as cross-cutting
entity-context families. `sbir` is the earliest capability/commercialization precursor added in M14.

## Rights / licensing

All registered sources are US government works (public domain data). API access is governed by each
provider's terms: SAM.gov (authenticated, quota-limited — never rotate keys), SEC EDGAR (fair-access,
descriptive User-Agent required), SBIR.gov + Federal Register + Grants.gov (keyless public APIs), and
OFAC (public bulk downloads; used only as intelligence evidence, not as an authoritative compliance
screening tool). Exact current OFAC download host and SBIR.gov availability are marked `unverified`
pending a single connectivity check; the SDN.CSV fixed-field schema and SBIR JSON schema are stable.

## Governance

New sources must pass the coverage/selectivity/provenance/replay/API-efficiency test in
`M4_SOURCE_EXPANSION.md` and honor `SOURCE_INGESTION.md`. Source expansion beyond this manifest is
tracked in `docs/strategy/STRATEGIC_CAPABILITY_ROADMAP.md` (area 12); items there are promoted,
deferred, superseded, or rejected explicitly — never dropped silently.
