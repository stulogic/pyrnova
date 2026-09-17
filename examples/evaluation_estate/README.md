# Pyrnova Internal Evaluation — multinational evaluation estate

One **internal** evaluation Lens populated from accepted historical/replay evidence already in this
repository, so the real customer product can be inspected under realistic data load.

It is **not a real customer**, asserts **no commercial relationship**, and contains **no live production
intelligence**. Every record is lawful replay/fixture-derived evidence and says so in its own provenance:
the Evidence Inspector shows the real fixture source, and live-source status stays whatever each national
domain honestly reports.

## Launch

```sh
cd /Users/stu/Documents/Pyrnova-intl
source .venv/bin/activate

python -m pyrnova.cli domains provision-eval --replay-dir examples/evaluation_estate   # once; idempotent
python -m pyrnova.ops_server                                                            # 127.0.0.1:8765
```

Then open:

```
http://127.0.0.1:8765/?customer=eval-multinational&as_of=2026-09-01
```

The Lens is selected by the ordinary `?customer=` tenant parameter — no bypass, no weakened
authentication. On a local bind with no credentials provisioned the server runs in its existing
permissive local-dev posture; any non-local bind still forces authentication, and the demo/evaluation
seeding paths are skipped entirely when auth is enforced.

`as_of=2026-09-01` is the estate's cutoff: it is after every selected case became knowable. An earlier
`as_of` correctly shows fewer records — that is AS-OF integrity working, not missing data.

## What the estate contains

31 opportunities across all five national domains (CA 9, GB 8, US 6, NZ 5, AU 3), chosen for semantic
breadth rather than volume:

- **States** — live candidates, flagged-for-review, and downgraded/monitoring (cancelled) records.
- **Mechanisms** — Canada's five families (competitive/open, directed/OEM, FMS/GtG, strategic-source,
  digital/ICT), UK consequential-change archetypes, AU/NZ open/limited/panel/direct-source routes, US
  full-and-open and GWAC/schedule.
- **Lifecycle** — cancellation, reissue (a *fresh* opportunity, never a silent continuation), post-award
  risk, prime-position change, access change, route change, re-scope, capability insertion.
- **Timing** — exact, bounded, contaminated and unknown timing classes; no numeric DLT threshold is
  invented for a domain that has none.
- **Evidence** — depth 1 to 3, varying honestly. Evidence is never duplicated to inflate a count.
- **Language** — French-original Canadian evidence keeps original-language authority; a translation stays
  PYRNOVA-DERIVED and never becomes the evidentiary authority.
- **Decision Memory** — 13 recorded internal-review dispositions, marked `CUSTOMER_FEEDBACK` with a note
  saying the reviewer is Pyrnova's own evaluation, not a customer.

## Honesty rules

- **Rights fail closed.** Two accepted cases (`au-fms-case-movement`, `nz-treasury-civil-blocked`) are
  backed by `DECLARED => DENY` sources and are **blocked**, reported, and never materialized. Two US
  evidence records come from sources that are not declared US national sources and are **withheld**, and
  reported. Nothing is laundered in.
- **Nothing is invented.** Titles are quotations of the accepted corpora's own notes. Values, dates,
  agencies and source references come from the fixtures. A field the fixture does not support stays
  `UNKNOWN` — an assignment never invents a favourable position, a value, or a date.
- **Real companies are not projected.** Entity-specific accepted cases (the `m9-*` Torch / MTSI fit cases)
  are deliberately excluded: re-attributing a real company's position to an internal evaluation lens would
  assert a relationship that does not exist.
- **One projection path.** Each country's own accepted `build_customer_proof.py` is reused verbatim with
  this Lens's identity. There is no second national implementation, no country-specific UI, no demo-only
  product logic, and no mock API.

`us_replay/build_customer_proof.py` documents the one place judgement is applied: the accepted US corpora
record evidence and adjudication but not the national route/access vocabulary, so each US case's `route`
and `access_class` are an explicit, per-case **reading** of that case's own adjudicated text (stated in its
`basis` field) — an evaluation-estate assignment, not a source fact.

## Tenancy

The estate is one tenant. `tests/test_evaluation_estate.py` guards that it never leaks into another
tenant, that provisioning is deterministic and idempotent, and that the population floor, national
coverage, state/mechanism breadth, evidence-depth variation and rights honesty all hold.
