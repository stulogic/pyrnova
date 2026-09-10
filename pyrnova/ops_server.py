"""Local-only HTTP host for the Pyrnova Operator Console."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .config import load_config
from .ops import OperatorConsole
from .state import StateStore

WEB_ROOT = Path(__file__).with_name("ops_web")


def _seed_demo_customers(demo_dir: Path, store: StateStore) -> None:
    """Seed demo customers into persisted state via the example seeder (loaded by file path).

    The demo identities live in ``examples/`` — never hard-coded into the ``pyrnova`` runtime package —
    so this loads the example module by path only at startup wiring time (M22-B doctrine, D-056)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "pyrnova_demo_seed_customers", demo_dir / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed(store)


def make_handler(console: OperatorConsole):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ValueError("request too large")
            return json.loads(self.rfile.read(length) or b"{}")

        def _asset(self, name: str, content_type: str):
            path = WEB_ROOT / name
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/snapshot":
                target = parse_qs(parsed.query).get("target", [None])[0]
                return self._json(200, console.snapshot(target))
            if parsed.path == "/api/customers":
                return self._json(200, {"customers": console.customers()})
            # M22-B: one customer's persisted profile + watchlist, or just its watchlist.
            if parsed.path.startswith("/api/customers/"):
                parts = parsed.path.split("/")  # ['', 'api', 'customers', '<id>', ...]
                cid = unquote(parts[3]) if len(parts) > 3 else ""
                query = parse_qs(parsed.query)
                as_of = query.get("as_of", [None])[0]
                try:
                    if len(parts) == 5 and parts[4] == "watchlist":
                        return self._json(200, {"customer_id": cid,
                                                "watchlist": console.list_customer_watches(cid, as_of=as_of)})
                    if len(parts) == 4:
                        return self._json(200, console.get_customer_profile(cid, as_of=as_of))
                except ValueError as exc:
                    return self._json(404, {"error": str(exc)})
                return self._json(404, {"error": "not found"})
            # M22-D: deterministic search over the Pyrnova estate (no runtime LLM).
            if parsed.path == "/api/search":
                query = parse_qs(parsed.query)
                return self._json(200, console.search(
                    query.get("q", [""])[0], as_of=query.get("as_of", [None])[0]))
            # M22-D: company investigation page (global; optional authorized customer overlay).
            if parsed.path == "/api/company":
                query = parse_qs(parsed.query)
                ref = query.get("ref", [None])[0]
                if not ref:
                    return self._json(400, {"error": "ref is required"})
                try:
                    return self._json(200, console.company_intelligence(
                        ref, as_of=query.get("as_of", [None])[0],
                        customer=query.get("customer", [None])[0]))
                except PermissionError as exc:
                    return self._json(403, {"error": str(exc)})
                except ValueError as exc:
                    return self._json(404, {"error": str(exc)})
            # M22-D: program investigation page (global; optional authorized customer overlay).
            if parsed.path == "/api/program":
                query = parse_qs(parsed.query)
                key = query.get("key", [None])[0]
                if not key:
                    return self._json(400, {"error": "key is required"})
                try:
                    return self._json(200, console.program_intelligence(
                        key, as_of=query.get("as_of", [None])[0],
                        customer=query.get("customer", [None])[0]))
                except PermissionError as exc:
                    return self._json(403, {"error": str(exc)})
                except ValueError as exc:
                    return self._json(404, {"error": str(exc)})
            if parsed.path == "/api/material-changes":
                query = parse_qs(parsed.query)
                customer = query.get("customer", [None])[0]
                if not customer:
                    return self._json(400, {"error": "customer is required"})
                try:
                    return self._json(200, console.material_changes(
                        customer,
                        as_of=query.get("as_of", [None])[0],
                        disposition=query.get("disposition", [None])[0]))
                except PermissionError as exc:
                    return self._json(403, {"error": str(exc)})
                except ValueError as exc:
                    return self._json(404, {"error": str(exc)})
            # M22-B: per-customer review history for one Material Change.
            if parsed.path.startswith("/api/material-changes/") and parsed.path.endswith("/review-history"):
                change_id = unquote(parsed.path.split("/")[3])
                query = parse_qs(parsed.query)
                customer = query.get("customer", [None])[0]
                if not customer:
                    return self._json(400, {"error": "customer is required"})
                try:
                    return self._json(200, console.customer_review_history(
                        customer, change_id, as_of=query.get("as_of", [None])[0]))
                except ValueError as exc:
                    return self._json(404, {"error": str(exc)})
            # M22-C: stored version history for one customer Material Change (original assessment → outcome).
            if parsed.path.startswith("/api/material-changes/") and parsed.path.endswith("/versions"):
                change_id = unquote(parsed.path.split("/")[3])
                query = parse_qs(parsed.query)
                customer = query.get("customer", [None])[0]
                if not customer:
                    return self._json(400, {"error": "customer is required"})
                try:
                    return self._json(200, console.customer_material_change_versions(customer, change_id))
                except (ValueError, PermissionError) as exc:
                    return self._json(403 if isinstance(exc, PermissionError) else 404,
                                      {"error": str(exc)})
            # M22-A: the customer-facing Material Changes product is the front door ("/"); the internal
            # Operator Console moves to "/console". Both are served from the same asset directory.
            assets = {
                "/": ("material.html", "text/html; charset=utf-8"),
                "/material.html": ("material.html", "text/html; charset=utf-8"),
                "/material.js": ("material.js", "text/javascript; charset=utf-8"),
                "/material.css": ("material.css", "text/css; charset=utf-8"),
                # M22-D: investigation surfaces (search + company/program). One asset trio routed by JS.
                "/investigate": ("investigation.html", "text/html; charset=utf-8"),
                "/search": ("investigation.html", "text/html; charset=utf-8"),
                "/company": ("investigation.html", "text/html; charset=utf-8"),
                "/program": ("investigation.html", "text/html; charset=utf-8"),
                "/investigation.html": ("investigation.html", "text/html; charset=utf-8"),
                "/investigation.js": ("investigation.js", "text/javascript; charset=utf-8"),
                "/investigation.css": ("investigation.css", "text/css; charset=utf-8"),
                "/console": ("index.html", "text/html; charset=utf-8"),
                "/index.html": ("index.html", "text/html; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            }
            if parsed.path in assets:
                name, content_type = assets[parsed.path]
                return self._asset(name, content_type)
            self._json(404, {"error": "not found"})

        def do_POST(self):
            parsed = urlparse(self.path)
            try:
                payload = self._body()
                if parsed.path.startswith("/api/opportunities/") and parsed.path.endswith("/review"):
                    opportunity_id = unquote(parsed.path.split("/")[3])
                    return self._json(200, console.adjudicate(opportunity_id, **payload))
                if parsed.path.startswith("/api/opportunities/") and parsed.path.endswith("/outcome"):
                    opportunity_id = unquote(parsed.path.split("/")[3])
                    return self._json(200, console.record_outcome(opportunity_id, **payload))
                if parsed.path == "/api/briefs":
                    return self._json(200, console.export_signal_brief(payload.get("target", "")))
                # M22-C: run the customer Material Change fan-out (continuous-operations path). Optional
                # ``customers`` (subset) and ``as_of``; returns the structured observability report.
                if parsed.path == "/api/fanout":
                    return self._json(200, console.fan_out(
                        customer_ids=payload.get("customers"), as_of=payload.get("as_of")))
                # M22-B: create a persisted customer.
                if parsed.path == "/api/customers":
                    return self._json(200, console.create_customer(**payload))
                # M22-B: add / retire a watchlist entry.
                if parsed.path.startswith("/api/customers/"):
                    parts = parsed.path.split("/")  # ['', 'api', 'customers', '<id>', 'watchlist', ...]
                    cid = unquote(parts[3]) if len(parts) > 3 else ""
                    if len(parts) == 5 and parts[4] == "watchlist":
                        return self._json(200, console.add_customer_watch(cid, **payload))
                    if len(parts) == 7 and parts[4] == "watchlist" and parts[6] == "retire":
                        return self._json(200, console.retire_customer_watch(cid, unquote(parts[5])))
                    return self._json(404, {"error": "not found"})
                # M22-B: record a customer review/lifecycle action on one Material Change.
                if parsed.path.startswith("/api/material-changes/") and parsed.path.endswith("/review"):
                    change_id = unquote(parsed.path.split("/")[3])
                    customer = payload.pop("customer", None)
                    if not customer:
                        return self._json(400, {"error": "customer is required"})
                    return self._json(200, console.record_customer_review(customer, change_id, **payload))
                self._json(404, {"error": "not found"})
            except PermissionError as exc:
                self._json(403, {"error": str(exc)})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._json(400, {"error": str(exc)})

        def log_message(self, format, *args):
            return

    return Handler


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pyrnova local Operator Console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("the operator console is local-only; host must be 127.0.0.1 or localhost")
    cfg = load_config()
    # M22-A: serve Material Changes from persisted threat streams when present; otherwise fall back to
    # the tracked, replay-safe demonstration fixture so the product view is populated on a fresh checkout.
    demo_dir = Path("examples/material_changes_demo")
    state_store = StateStore(cfg.state_dir)
    mc_store = state_store
    if not (Path(cfg.state_dir) / "threats.jsonl").exists() and (demo_dir / "state" / "threats.jsonl").exists():
        mc_store = StateStore(demo_dir / "state")
    # M22-B: the running product operates from PERSISTED customer state. On a fresh checkout with no
    # persisted customers, seed the demo customers into the persisted structures (deterministic, from
    # examples/ — not hard-coded runtime behavior) so the product path — not a demo JSON — is exercised.
    from . import customers as _cust
    if not _cust.list_customers(state_store) and (demo_dir / "seed_customers.py").exists():
        _seed_demo_customers(demo_dir, state_store)
    # M22-C: the running product operates against the customer-scoped persisted Material Change store.
    # Fan-out is the ordinary continuous-operations path — NOT a demo script — so we materialize current
    # customer-scoped state at startup (idempotent, content-hash deduped) and the read path serves it.
    cmc_store = state_store
    console = OperatorConsole(
        state_store, Path("examples/profiles"), cfg.out_dir,
        mc_store=mc_store, contexts_dir=demo_dir, customer_store=state_store, cmc_store=cmc_store)
    try:
        report = console.fan_out()
        print(f"Material Change fan-out: {report['inserted']} inserted, {report['updated']} updated, "
              f"{report['duplicates_suppressed']} unchanged across {report['customers']} customer(s)")
    except ValueError:
        pass
    server = ThreadingHTTPServer((args.host, args.port), make_handler(console))
    print(f"Pyrnova Operator Console: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
