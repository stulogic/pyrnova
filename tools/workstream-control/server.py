#!/usr/bin/env python3
"""Pyrnova Workstream Control - local, stdlib-only dispatch server.

Isolated developer tooling. Does not touch the Pyrnova product runtime,
the Phase 1 soak, or any evidence directory. Serves a static UI and a small
JSON API that assembles canonical workstream prompts and persists workstream
state separately from the canonical registry.
"""

import http.server
import json
import os
import socketserver
import subprocess
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
PROMPTS = os.path.join(ROOT, "prompts")
REGISTRY_FILE = os.path.join(ROOT, "registry.json")
STATE_FILE = os.path.join(ROOT, "state.json")
BOILERPLATE_FILE = os.path.join(PROMPTS, "_boilerplate.md")

VALID_STATUS = {"READY", "ACTIVE", "BLOCKED", "CLOSED", "DEFERRED"}
PORT = int(os.environ.get("PYRNOVA_WSC_PORT", "8787"))

_lock = threading.Lock()


def load_registry():
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {"version": 1, "states": {}}


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)


def merged_workstreams():
    """Registry definitions overlaid with persisted state (state wins)."""
    reg = load_registry()
    state = load_state().get("states", {})
    out = []
    for ws in reg["workstreams"]:
        item = dict(ws)
        st = state.get(ws["id"])
        if st and st.get("status") in VALID_STATUS:
            item["status"] = st["status"]
        out.append(item)
    return out


def find_ws(ws_id):
    for ws in merged_workstreams():
        if ws["id"] == ws_id:
            return ws
    return None


def read_boilerplate():
    try:
        with open(BOILERPLATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def read_body(ws):
    path = os.path.join(PROMPTS, ws["prompt_file"])
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "(prompt body missing: " + ws["prompt_file"] + ")"


def build_prompt(ws):
    ident = ws["id"]
    name = ws["canonical_name"]
    header = (
        "# PYRNOVA WORKSTREAM\n\n"
        "WORKSTREAM ID: " + ident + "\n\n"
        "CANONICAL NAME: " + name + "\n\n"
        "STATUS AT LAUNCH: ACTIVE\n\n"
        "This workstream ID is permanent.\n\n"
        "Do not infer this workstream's identity, authority or state from the "
        "ChatGPT sidebar conversation title. The sidebar title is "
        "non-authoritative and may change.\n\n"
        "Operate from existing Pyrnova project authority.\n\n"
        "Do not reopen decisions explicitly marked closed."
    )
    footer = (
        "# HANDOVER DELTA\n\n"
        "Close by returning the following, and only the following:\n\n"
        "WORKSTREAM ID\n"
        "FINAL STATE\n"
        "KEY FINDINGS\n"
        "DECISIONS / RECOMMENDATIONS\n"
        "ACTIONS PROMOTED INTO EXECUTION\n"
        "ITEMS DEFERRED\n"
        "UNRESOLVED QUESTIONS\n"
        "MASTER HANDOVER UPDATES\n"
        "RECOMMENDED REGISTRY STATUS"
    )
    parts = [header, read_boilerplate(), "---", read_body(ws), "---", footer]
    return "\n\n".join(p for p in parts if p).strip() + "\n"


def build_handover_header(ws):
    return (
        "# PYRNOVA WORKSTREAM HANDOVER\n\n"
        "WORKSTREAM ID: " + ws["id"] + "\n"
        "CANONICAL NAME: " + ws["canonical_name"] + "\n\n"
        "Paste the completed workstream result below this line:\n"
    )


def pbcopy(text):
    """Best-effort macOS clipboard copy; never fatal."""
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(text.encode("utf-8"))
        return p.returncode == 0
    except Exception:
        return False


def set_status(ws_id, status):
    if status not in VALID_STATUS:
        return False
    with _lock:
        state = load_state()
        state.setdefault("states", {})[ws_id] = {"status": status}
        save_state(state)
    return True


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC, **kwargs)

    def log_message(self, *args):
        pass  # quiet

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/registry":
            return self._json(200, {"workstreams": merged_workstreams()})
        if path == "/api/prompt":
            q = parse_qs(parsed.query)
            ws = find_ws(q.get("id", [""])[0])
            if not ws:
                return self._json(404, {"error": "unknown workstream"})
            return self._json(200, {"prompt": build_prompt(ws)})
        if path == "/api/handover":
            q = parse_qs(parsed.query)
            ws = find_ws(q.get("id", [""])[0])
            if not ws:
                return self._json(404, {"error": "unknown workstream"})
            return self._json(200, {"header": build_handover_header(ws)})
        if path == "/" or path == "":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        data = self._read_json_body()
        ws_id = data.get("id", "")
        ws = find_ws(ws_id)

        if path == "/api/launch":
            if not ws:
                return self._json(404, {"error": "unknown workstream"})
            prompt = build_prompt(ws)
            set_status(ws_id, "ACTIVE")
            copied = pbcopy(prompt)
            return self._json(200, {
                "prompt": prompt,
                "copied": copied,
                "status": "ACTIVE",
                "chatgpt_url": "https://chatgpt.com/",
            })

        if path == "/api/status":
            status = data.get("status", "")
            if not ws:
                return self._json(404, {"error": "unknown workstream"})
            if not set_status(ws_id, status):
                return self._json(400, {"error": "invalid status"})
            return self._json(200, {"id": ws_id, "status": status})

        if path == "/api/copy":
            # Server-side clipboard fallback for arbitrary text.
            copied = pbcopy(data.get("text", ""))
            return self._json(200, {"copied": copied})

        return self._json(404, {"error": "not found"})


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    os.chdir(ROOT)
    httpd = Server(("127.0.0.1", PORT), Handler)
    url = "http://127.0.0.1:%d/" % PORT
    print("Pyrnova Workstream Control -> " + url)
    print("(Ctrl+C to stop)")
    if os.environ.get("PYRNOVA_WSC_NO_BROWSER") != "1":
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
