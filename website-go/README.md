# Pyrnova public website. WEBSITE-GO-001 (Revision B)

**Target state: WEBSITE GO / OUTREACH INTAKE DISABLED (State 1).**
Safe to publish as an informational site. **Not** a public evaluation-intake destination.

Branch `website-go-001`, isolated from the Live Ops soak (built on pinned base
`e7cb2c98c3594166cbcb4d5691c0f370d4c5eb57`). This project imports no product code,
shares no runtime, state, secrets or configuration with `pyrnova/`, `ops/`, `var/`,
and never touches the running soak.

## What this is (Revision B)

A static, dependency-free informational website that reads as a controlled window into
the product. Node's standard library renders fixed content into `dist/` as one static
HTML file per route. There is **no** server logic in the published output, **no**
JavaScript, **no** forms, **no** analytics, and **no** data-collection endpoint of any
kind. Motion is CSS only and respects `prefers-reduced-motion`.

It reuses the canonical product grammar from `pyrnova/ops_web` (Material Change objects:
disposition, materiality, confidence, observed fact vs Pyrnova assessment, evidence
chips, uncertainty and falsifier, AS OF, provenance) and the canonical brand mark from
`docs/brand/notion` (`assets/pyrnova-mark.svg`, cropped from the canonical header; no
invented logo). Canonical brand cyan `#25cfe8` is used as signal only. All specimens are
synthetic and clearly labelled; none is presented as live production output. Copy follows
the Product Language Authority (D-041) and contains zero em dash characters (test-enforced).

## Build, test, preview

```
npm test      # State 1 invariants + route completeness (node --test, no deps)
npm run build # render static site to dist/
npm run serve # build + local read-only preview on 127.0.0.1:4318
```

No package installation is required (standard library only).

## Routes (locked authority)

`/` (HOME), `/intelligence/`, `/method/`, `/trust/`, `/research/`, `/company/`,
`/evaluate/`. Primary nav: INTELLIGENCE · METHOD · TRUST · RESEARCH · COMPANY ·
EVALUATE. Primary message: "Know what changed. Know what it changes."

## Intake-disabled guarantee (State 1)

EVALUATE is a complete informational page that **omits the intake form entirely**.
Across the whole site there are no personal-data fields, no submit control, no hidden
collection path, no JavaScript collection, no mailto/tel founder workaround, no
booking/calendar flow and no file upload. The EVALUATE page states plainly that public
evaluation intake is not open and that the site does not collect visitor details.
These invariants are enforced by `tests/site.test.mjs`.

## Claims discipline

Product semantics (evidence provenance, source attribution, uncertainty, AS-OF /
point-in-time, customer-specific consequence, source-rights controls) are described as
implemented/tested. Production deployment and control posture are explicitly **not**
claimed. No SOC 2 / FedRAMP / ISO / CMMC, no database RLS, no production MFA/SSO/DR/
monitoring claims. Application-layer isolation is never described as database RLS.

## State 2 is out of scope

No privacy/controller identity, intake fields, receiving destination or dormant intake
endpoints are built or stored "for later". Activating public intake is a separate,
separately-authorized workstream.
