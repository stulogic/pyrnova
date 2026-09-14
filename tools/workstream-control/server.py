#!/usr/bin/env python3
"""Pyrnova Workstream Control - local, stdlib-only dispatch server.

Isolated developer tooling. Does not touch the Pyrnova product runtime,
the Phase 1 soak, or any evidence directory. Serves a static UI and a small
JSON API that assembles canonical workstream prompts and persists workstream
state separately from the canonical registry.

Design principle: CLOSED means DONE AND REMEMBERED, not DELETED. Completed
work is preserved as historical project memory so new work is not accidentally
duplicated. Permanent IDs are never silently reused. All fuzzy matching is
deterministic (difflib) with no external dependencies.
"""

import datetime
import difflib
import http.server
import json
import os
import re
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
HISTORY_FILE = os.path.join(ROOT, "history.json")  # permanent ID ledger
BOILERPLATE_FILE = os.path.join(PROMPTS, "_boilerplate.md")

VALID_STATUS = {"READY", "ACTIVE", "BLOCKED", "CLOSED", "DEFERRED", "SUPERSEDED"}
ARCHIVE_STATUS = {"CLOSED", "SUPERSEDED"}
REGISTRY_FIELDS = [
    "id", "canonical_name", "category", "priority", "status", "objective",
    "prompt_file", "dependencies", "notes",
    "related_to", "supersedes", "follow_up_to",
]
REQUIRED_IMPORT_FIELDS = ["id", "canonical_name", "category", "objective"]
PORT = int(os.environ.get("PYRNOVA_WSC_PORT", "8787"))

_lock = threading.RLock()

STOPWORDS = set((
    "a an the and or of to for in on with without into that this its their our "
    "your my his her at by from as is are be been being new current original vs "
    "versus over under between across within about against system roadmap study"
).split())


def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------

def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return default


def _save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def load_registry():
    return _load_json(REGISTRY_FILE, {"version": 1, "workstreams": []})


def save_registry(reg):
    _save_json(REGISTRY_FILE, reg)


def load_state():
    return _load_json(STATE_FILE, {"version": 1, "states": {}})


def save_state(state):
    _save_json(STATE_FILE, state)


def load_history():
    return _load_json(HISTORY_FILE, {"version": 1, "ids": {}})


def save_history(hist):
    _save_json(HISTORY_FILE, hist)


def ensure_ledger():
    """Every registry ID must be recorded in the permanent ID ledger."""
    with _lock:
        reg = load_registry()
        hist = load_history()
        ids = hist.setdefault("ids", {})
        changed = False
        for ws in reg.get("workstreams", []):
            if ws["id"] not in ids:
                ids[ws["id"]] = {
                    "canonical_name": ws.get("canonical_name", ""),
                    "category": ws.get("category", ""),
                    "first_seen": now_iso(),
                }
                changed = True
        if changed:
            save_history(hist)


def known_ids():
    """Every ID that has EVER existed: registry + permanent ledger."""
    reg = load_registry()
    hist = load_history()
    ids = set(hist.get("ids", {}).keys())
    for ws in reg.get("workstreams", []):
        ids.add(ws["id"])
    return ids


def merged_workstreams():
    """Registry definitions overlaid with persisted state (state wins)."""
    reg = load_registry()
    state = load_state().get("states", {})
    out = []
    for ws in reg.get("workstreams", []):
        item = dict(ws)
        st = state.get(ws["id"])
        if st and st.get("status") in VALID_STATUS:
            item["status"] = st["status"]
        item["history"] = (st or {}).get("history", [])
        out.append(item)
    return out


def find_ws(ws_id):
    for ws in merged_workstreams():
        if ws["id"] == ws_id:
            return ws
    return None


def set_status(ws_id, status, reason=None):
    if status not in VALID_STATUS:
        return False
    with _lock:
        state = load_state()
        states = state.setdefault("states", {})
        entry = states.setdefault(ws_id, {})
        entry["status"] = status
        hist = entry.setdefault("history", [])
        hist.append({"status": status, "at": now_iso(),
                     "reason": reason or "manual"})
        save_state(state)
    return True


# ---------------------------------------------------------------------------
# prompt assembly
# ---------------------------------------------------------------------------

def read_boilerplate():
    return _read_text(BOILERPLATE_FILE, "")


def _read_text(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return fallback


def read_body(ws):
    path = os.path.join(PROMPTS, ws.get("prompt_file", ""))
    return _read_text(path, "(prompt body missing: " + str(ws.get("prompt_file")) + ")")


def build_prompt(ws):
    header = (
        "# PYRNOVA WORKSTREAM\n\n"
        "WORKSTREAM ID: " + ws["id"] + "\n\n"
        "CANONICAL NAME: " + ws["canonical_name"] + "\n\n"
        "STATUS AT LAUNCH: ACTIVE\n\n"
        "This workstream ID is permanent.\n\n"
        "Do not infer this workstream's identity, authority or state from the "
        "ChatGPT sidebar conversation title. The sidebar title is "
        "non-authoritative and may change.\n\n"
        "Operate from existing Pyrnova project authority.\n\n"
        "Do not reopen decisions explicitly marked closed."
    )
    lineage = _lineage_block(ws)
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
    parts = [header, lineage, read_boilerplate(), "---", read_body(ws),
             "---", footer]
    return "\n\n".join(p for p in parts if p).strip() + "\n"


def _lineage_block(ws):
    lines = []
    if ws.get("follow_up_to"):
        lines.append("FOLLOW-UP TO: " + str(ws["follow_up_to"]))
    if ws.get("supersedes"):
        lines.append("SUPERSEDES: " + str(ws["supersedes"]))
    if ws.get("related_to"):
        rel = ws["related_to"]
        rel = ", ".join(rel) if isinstance(rel, list) else str(rel)
        if rel:
            lines.append("RELATED TO: " + rel)
    if not lines:
        return ""
    return ("LINEAGE (historical chain — build on prior work, do not repeat it):"
            "\n" + "\n".join(lines))


def build_handover_header(ws):
    return (
        "# PYRNOVA WORKSTREAM HANDOVER\n\n"
        "WORKSTREAM ID: " + ws["id"] + "\n"
        "CANONICAL NAME: " + ws["canonical_name"] + "\n\n"
        "Paste the completed workstream result below this line:\n"
    )


def pbcopy(text):
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(text.encode("utf-8"))
        return p.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# deterministic duplicate detection
# ---------------------------------------------------------------------------

def normalize_name(s):
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def tokens(s):
    return set(t for t in normalize_name(s).split() if len(t) > 2 and t not in STOPWORDS)


def jaccard(a, b):
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def ratio(a, b):
    return difflib.SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def dup_score(cand, existing):
    """Deterministic similarity between two workstream dicts -> (score, reasons)."""
    name_r = ratio(cand.get("canonical_name", ""), existing.get("canonical_name", ""))
    name_j = jaccard(tokens(cand.get("canonical_name", "")),
                     tokens(existing.get("canonical_name", "")))
    obj_j = jaccard(tokens(cand.get("objective", "")),
                    tokens(existing.get("objective", "")))
    cat_match = (cand.get("category", "") or "").upper() == \
                (existing.get("category", "") or "").upper()
    reasons = []
    if name_r >= 0.75:
        reasons.append("name %d%% similar" % round(name_r * 100))
    if name_j >= 0.5:
        reasons.append("shared name keywords")
    if obj_j >= 0.4:
        reasons.append("objective overlap %d%%" % round(obj_j * 100))
    if cat_match and (name_j >= 0.34 or obj_j >= 0.3):
        reasons.append("same category + overlap")
    score = max(name_r, name_j, obj_j, (0.55 if cat_match and obj_j >= 0.3 else 0.0))
    return score, reasons


DUP_THRESHOLD = 0.6


def find_duplicates(cand, pool):
    matches = []
    for ex in pool:
        if ex.get("id") == cand.get("id"):
            continue
        score, reasons = dup_score(cand, ex)
        if reasons and score >= DUP_THRESHOLD:
            matches.append({
                "id": ex["id"],
                "canonical_name": ex.get("canonical_name", ""),
                "status": ex.get("status", ""),
                "score": round(score, 3),
                "reasons": reasons,
            })
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches


# ---------------------------------------------------------------------------
# import (bulk-safe, atomic)
# ---------------------------------------------------------------------------

def _clean_entry(item):
    entry = {}
    for f in REGISTRY_FIELDS:
        if f in item and item[f] is not None:
            entry[f] = item[f]
    entry.setdefault("priority", "MEDIUM")
    entry.setdefault("status", "READY")
    entry.setdefault("dependencies", [])
    entry.setdefault("notes", "")
    return entry


def classify_import(items):
    """Classify each item without mutating anything. Returns (results, summary)."""
    kids = known_ids()
    pool = merged_workstreams()  # ACTIVE + CLOSED + SUPERSEDED + all
    batch_ids = set()
    batch_pool = []
    results = []
    for idx, item in enumerate(items):
        iid = item.get("id")
        missing = [f for f in REQUIRED_IMPORT_FIELDS if not item.get(f)]
        if missing:
            results.append({"index": idx, "id": iid, "state": "INVALID",
                            "detail": "missing fields: " + ", ".join(missing)})
            continue
        if iid in kids:
            ex = _lookup(iid, pool)
            results.append({"index": idx, "id": iid, "state": "ID_CONFLICT",
                            "detail": "ID already exists",
                            "existing": _brief(ex) if ex else {"id": iid,
                            "note": "in permanent ID ledger"}})
            continue
        if iid in batch_ids:
            results.append({"index": idx, "id": iid, "state": "ID_CONFLICT",
                            "detail": "duplicate ID within this batch"})
            continue
        dupes = find_duplicates(item, pool + batch_pool)
        state = "POSSIBLE_DUPLICATE" if dupes else "NEW"
        results.append({"index": idx, "id": iid, "state": state,
                        "canonical_name": item.get("canonical_name"),
                        "matches": dupes})
        batch_ids.add(iid)
        batch_pool.append(item)
    summary = {
        "new": sum(1 for r in results if r["state"] == "NEW"),
        "possible_duplicates": sum(1 for r in results if r["state"] == "POSSIBLE_DUPLICATE"),
        "id_conflicts": sum(1 for r in results if r["state"] == "ID_CONFLICT"),
        "invalid": sum(1 for r in results if r["state"] == "INVALID"),
        "total": len(results),
    }
    return results, summary


def _lookup(iid, pool):
    for ws in pool:
        if ws["id"] == iid:
            return ws
    return None


def _brief(ws):
    if not ws:
        return {}
    return {"id": ws["id"], "canonical_name": ws.get("canonical_name", ""),
            "status": ws.get("status", ""), "category": ws.get("category", "")}


def commit_import(items, resolutions):
    """Atomic. Imports nothing unless all hard conflicts are clear and every
    POSSIBLE_DUPLICATE has an explicit resolution."""
    resolutions = resolutions or {}
    with _lock:
        results, summary = classify_import(items)
        blocking = [r for r in results if r["state"] in ("INVALID", "ID_CONFLICT")]
        if blocking:
            return {"committed": False, "imported": 0, "summary": summary,
                    "results": results,
                    "message": "Hard conflicts present. 0 IMPORTED UNTIL RESOLVED."}
        # Every possible duplicate must be explicitly resolved.
        unresolved = [r for r in results if r["state"] == "POSSIBLE_DUPLICATE"
                      and resolutions.get(r["id"]) not in ("IMPORT_ANYWAY", "CANCEL")]
        if unresolved:
            return {"committed": False, "imported": 0, "summary": summary,
                    "results": results,
                    "message": "Unresolved possible duplicates. Choose CANCEL or "
                               "IMPORT ANYWAY for each. 0 IMPORTED UNTIL RESOLVED."}
        # Build the set to import.
        to_import = []
        for r in results:
            if r["state"] == "NEW":
                to_import.append(items[r["index"]])
            elif r["state"] == "POSSIBLE_DUPLICATE" and \
                    resolutions.get(r["id"]) == "IMPORT_ANYWAY":
                to_import.append(items[r["index"]])
        # Prepare entries + prompt files in memory before touching registry.
        reg = load_registry()
        hist = load_history()
        prepared = []
        for item in to_import:
            entry = _clean_entry(item)
            prompt_file = _ensure_prompt_file(entry, item)
            entry["prompt_file"] = prompt_file
            prepared.append(entry)
        # Commit registry + ledger in one shot.
        for entry in prepared:
            reg["workstreams"].append(entry)
            hist.setdefault("ids", {})[entry["id"]] = {
                "canonical_name": entry.get("canonical_name", ""),
                "category": entry.get("category", ""),
                "first_seen": now_iso(),
            }
        save_registry(reg)
        save_history(hist)
        return {"committed": True, "imported": len(prepared), "summary": summary,
                "results": results,
                "message": "%d IMPORTED" % len(prepared)}


def _ensure_prompt_file(entry, item):
    """Create prompts/<id>.md if the caller supplied a body or none exists."""
    given = item.get("prompt_file")
    if given and os.path.exists(os.path.join(PROMPTS, given)):
        return given
    fname = re.sub(r"[^A-Za-z0-9._-]", "_", entry["id"]) + ".md"
    path = os.path.join(PROMPTS, fname)
    body = item.get("prompt_body")
    if not body:
        body = ("## Task: " + entry["canonical_name"] + "\n\n" +
                entry.get("objective", "") + "\n\n"
                "Use current web research where contemporary facts matter and "
                "cite sources. Deliver a decision-ready result, not a survey.")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body.strip() + "\n")
    return fname


# ---------------------------------------------------------------------------
# follow-up / reopen
# ---------------------------------------------------------------------------

def next_id(parent_id, kids):
    m = re.search(r"^(.*?)(\d+)$", parent_id)
    if not m:
        return parent_id + "-002"
    prefix, num = m.group(1), m.group(2)
    width = len(num)
    maxn = int(num)
    pat = re.compile(re.escape(prefix) + r"(\d+)$")
    for kid in kids:
        km = pat.match(kid)
        if km:
            maxn = max(maxn, int(km.group(1)))
    return prefix + str(maxn + 1).zfill(width)


def create_follow_up(parent_id, supersede=False, new_id=None):
    with _lock:
        parent = find_ws(parent_id)
        if not parent:
            return {"ok": False, "error": "unknown parent workstream"}
        kids = known_ids()
        nid = new_id or next_id(parent_id, kids)
        if nid in kids:
            ex = _lookup(nid, merged_workstreams())
            return {"ok": False, "error": "ID already exists: " + nid,
                    "existing": _brief(ex)}
        entry = {
            "id": nid,
            "canonical_name": parent["canonical_name"] + " (Follow-up)",
            "category": parent.get("category", ""),
            "priority": parent.get("priority", "MEDIUM"),
            "status": "READY",
            "objective": parent.get("objective", ""),
            "dependencies": [],
            "notes": "Follow-up to " + parent_id,
            "follow_up_to": parent_id,
            "related_to": [parent_id],
        }
        if supersede:
            entry["supersedes"] = parent_id
        # Prompt body references and includes the parent's work.
        parent_body = read_body(parent)
        fu_body = (
            "## Task: " + entry["canonical_name"] + "\n\n"
            "This is a FOLLOW-UP to " + parent_id + " (" +
            parent["canonical_name"] + "). Build on that completed workstream; "
            "do not repeat it. Extend, update, or act on its conclusions. Use "
            "current web research where facts may have moved on.\n\n"
            "### Prior workstream task (for continuity)\n\n" + parent_body
        )
        fname = re.sub(r"[^A-Za-z0-9._-]", "_", nid) + ".md"
        with open(os.path.join(PROMPTS, fname), "w", encoding="utf-8") as f:
            f.write(fu_body.strip() + "\n")
        entry["prompt_file"] = fname
        reg = load_registry()
        reg["workstreams"].append(entry)
        save_registry(reg)
        hist = load_history()
        hist.setdefault("ids", {})[nid] = {
            "canonical_name": entry["canonical_name"],
            "category": entry["category"], "first_seen": now_iso()}
        save_history(hist)
        if supersede:
            set_status(parent_id, "SUPERSEDED", reason="superseded by " + nid)
        return {"ok": True, "id": nid, "entry": entry, "superseded_parent": supersede}


def reopen(ws_id):
    ws = find_ws(ws_id)
    if not ws:
        return {"ok": False, "error": "unknown workstream"}
    if ws["status"] not in ARCHIVE_STATUS:
        return {"ok": False, "error": "only CLOSED or SUPERSEDED workstreams "
                                      "can be reopened (deliberate action)"}
    set_status(ws_id, "ACTIVE", reason="explicit REOPEN")
    return {"ok": True, "id": ws_id, "status": "ACTIVE"}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC, **kwargs)

    def log_message(self, *args):
        pass

    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path, q = parsed.path, parse_qs(parsed.query)
        if path == "/api/registry":
            return self._json(200, {"workstreams": merged_workstreams(),
                                    "archive_status": sorted(ARCHIVE_STATUS),
                                    "statuses": sorted(VALID_STATUS)})
        if path == "/api/prompt":
            ws = find_ws(q.get("id", [""])[0])
            return self._json(200, {"prompt": build_prompt(ws)}) if ws \
                else self._json(404, {"error": "unknown workstream"})
        if path == "/api/handover":
            ws = find_ws(q.get("id", [""])[0])
            return self._json(200, {"header": build_handover_header(ws)}) if ws \
                else self._json(404, {"error": "unknown workstream"})
        if path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._body()

        if path == "/api/launch":
            ws = find_ws(data.get("id", ""))
            if not ws:
                return self._json(404, {"error": "unknown workstream"})
            prompt = build_prompt(ws)
            set_status(ws["id"], "ACTIVE", reason="launch")
            return self._json(200, {"prompt": prompt, "copied": pbcopy(prompt),
                                    "status": "ACTIVE",
                                    "chatgpt_url": "https://chatgpt.com/"})

        if path == "/api/status":
            ws = find_ws(data.get("id", ""))
            if not ws:
                return self._json(404, {"error": "unknown workstream"})
            if not set_status(ws["id"], data.get("status", ""),
                              reason="manual set"):
                return self._json(400, {"error": "invalid status"})
            return self._json(200, {"id": ws["id"], "status": data["status"]})

        if path == "/api/copy":
            return self._json(200, {"copied": pbcopy(data.get("text", ""))})

        if path == "/api/import/validate":
            results, summary = classify_import(data.get("workstreams", []))
            return self._json(200, {"results": results, "summary": summary})

        if path == "/api/import/commit":
            return self._json(200, commit_import(data.get("workstreams", []),
                                                 data.get("resolutions", {})))

        if path == "/api/followup":
            res = create_follow_up(data.get("parent_id", ""),
                                   bool(data.get("supersede", False)),
                                   data.get("new_id") or None)
            return self._json(200 if res.get("ok") else 409, res)

        if path == "/api/reopen":
            res = reopen(data.get("id", ""))
            return self._json(200 if res.get("ok") else 400, res)

        return self._json(404, {"error": "not found"})


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    os.chdir(ROOT)
    ensure_ledger()
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
