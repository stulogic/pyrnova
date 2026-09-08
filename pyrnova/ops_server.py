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
            if parsed.path in {"/", "/index.html"}:
                return self._asset("index.html", "text/html; charset=utf-8")
            if parsed.path == "/app.js":
                return self._asset("app.js", "text/javascript; charset=utf-8")
            if parsed.path == "/styles.css":
                return self._asset("styles.css", "text/css; charset=utf-8")
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
    console = OperatorConsole(StateStore(cfg.state_dir), Path("examples/profiles"), cfg.out_dir)
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
