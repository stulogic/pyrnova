"""Local HTTP transport for Pyrnova Operator Console v0.1."""

from __future__ import annotations

import json
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .operator import OperatorService

STATIC = Path(__file__).with_name("console_static")


class ConsoleApplication:
    def __init__(self, service: OperatorService):
        self.service = service

    def start_run(self, options: dict) -> str:
        run_id = uuid.uuid4().hex
        thread = threading.Thread(
            target=self.service.create_run,
            kwargs={"options": options, "run_id": run_id},
            daemon=True,
            name=f"pyrnova-run-{run_id[:8]}",
        )
        thread.start()
        return run_id


def make_handler(app: ConsoleApplication):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def _json(self, value, status=HTTPStatus.OK):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _error(self, exc, status=HTTPStatus.BAD_REQUEST):
            self._json({"error": str(exc)}, status)

        def _body(self):
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self):
            path = urlparse(self.path).path
            try:
                if path == "/api/profiles":
                    return self._json(app.service.profiles.list())
                if path == "/api/runs":
                    return self._json(app.service.runs.list())
                if path.startswith("/api/runs/"):
                    return self._json(app.service.get_run(path.rsplit("/", 1)[-1]))
                asset = "index.html" if path == "/" else path.removeprefix("/")
                if asset not in {"index.html", "app.js", "styles.css"}:
                    return self._error("not found", HTTPStatus.NOT_FOUND)
                file = STATIC / asset
                body = file.read_bytes()
                media = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[file.suffix]
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", f"{media}; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except KeyError as exc:
                self._error(exc, HTTPStatus.NOT_FOUND)
            except Exception as exc:
                self._error(exc)

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                payload = self._body()
                if path == "/api/runs":
                    run_id = app.start_run(payload)
                    return self._json({"id": run_id, "status": "running"}, HTTPStatus.ACCEPTED)
                if path.startswith("/api/runs/") and path.endswith("/reviews"):
                    run_id = path.split("/")[3]
                    return self._json(app.service.save_review(run_id, payload), HTTPStatus.CREATED)
                if path.startswith("/api/runs/") and path.endswith("/briefs"):
                    run_id = path.split("/")[3]
                    return self._json(
                        app.service.generate_brief(run_id, payload.get("candidate_ids", [])),
                        HTTPStatus.CREATED,
                    )
                self._error("not found", HTTPStatus.NOT_FOUND)
            except KeyError as exc:
                self._error(exc, HTTPStatus.NOT_FOUND)
            except Exception as exc:
                self._error(exc)

    return Handler


def serve(*, host="127.0.0.1", port=8765):
    repo_root = Path(__file__).resolve().parent.parent
    app = ConsoleApplication(OperatorService.default(repo_root))
    server = ThreadingHTTPServer((host, port), make_handler(app))
    print(f"Pyrnova Operator Console: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
