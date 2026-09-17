# Rendered proof — Customer product (FRONTEND-R2 / R3)

These `*.html` files are **self-contained rendered snapshots** of the redesigned customer
product. They are not mockups: each was produced by executing the **real**
`pyrnova/ops_web/product.js` render functions against **real** captured server JSON, with
the **real** `system.css` + `access.css` + `product.css` inlined. Open any file in a
browser to see the genuine production markup + styling with live demo-tenant data (`torch`).

| File | Surface | Real data shown |
|---|---|---|
| `lens.html` | Customer Lens | stat tiles (6 opps / 8 material changes / 1 uncertain), opportunity queue, material-change cards, Lens context strip |
| `opportunities.html` | Opportunity queue | ranked items with pursuit verdict, attractiveness/confidence meters, decision-window chips |
| `decision.html` | Decision View | grouped disposition / why-now / window / **access (DIRECT_ACCESS)** / fit / uncertainty / audit-grade evidence |

## Provenance / regeneration

- `lens.json`, `opps.json`, `decision.json` — verbatim captures from a live
  `python -m pyrnova.ops_server` (tenant `torch`), the same payloads the browser receives.
- `render.js` — the harness (real `product.js` executed via Node `vm` + a minimal DOM shim).

Regenerate:

```sh
python -m pyrnova.ops_server &                       # 127.0.0.1:8765
curl -s "http://127.0.0.1:8765/api/lens?customer=torch" > lens.json
curl -s "http://127.0.0.1:8765/api/opportunities?customer=torch" > opps.json
OID=$(python3 -c "import json;print(json.load(open('opps.json'))['opportunities'][0]['id'])")
curl -s "http://127.0.0.1:8765/api/opportunities/$OID/decision?customer=torch" > decision.json
echo "$OID" > oid.txt
node render.js
```

No fabricated customers, sources, confidence or status appears here — where a field is
genuinely absent the UI renders `Unknown` / an empty state, never an invented value.
Pixel screenshots require a browser/headless tool, which was not available offline in the
authoring session; these saved pages are the rendered substitute.
