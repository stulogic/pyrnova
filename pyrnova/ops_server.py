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
                except ValueError as exc:
                    return self._json(404, {"error": str(exc)})
            # M22-A: the customer-facing Material Changes product is the front door ("/"); the internal
            # Operator Console moves to "/console". Both are served from the same asset directory.
            assets = {
                "/": ("material.html", "text/html; charset=utf-8"),
                "/material.html": ("material.html", "text/html; charset=utf-8"),
                "/material.js": ("material.js", "text/javascript; charset=utf-8"),
                "/material.css": ("material.css", "text/css; charset=utf-8"),
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
                self._json(404, {"error": "not found"})
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
    console = OperatorConsole(
        state_store, Path("examples/profiles"), cfg.out_dir,
        mc_store=mc_store, contexts_dir=demo_dir)
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
