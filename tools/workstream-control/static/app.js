"use strict";

var ALL_STATUSES = ["READY", "ACTIVE", "BLOCKED", "CLOSED", "DEFERRED", "SUPERSEDED"];
var ARCHIVE_STATUS = ["CLOSED", "SUPERSEDED"];
var all = [];
var view = "operational";     // operational | archive | all
var lastValidation = null;    // {results, summary} from /api/import/validate

/* ---------- helpers ---------- */
function api(path, opts) { return fetch(path, opts).then(function (r) { return r.json(); }); }
function post(path, body) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" },
                     body: JSON.stringify(body || {}) });
}
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}
function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text).catch(function () { return post("/api/copy", { text: text }); });
  }
  return post("/api/copy", { text: text });
}
function showToast() {
  var t = document.getElementById("toast");
  t.hidden = false; clearTimeout(showToast._h);
  showToast._h = setTimeout(function () { t.hidden = true; }, 4000);
}
function isArchive(s) { return ARCHIVE_STATUS.indexOf(s) !== -1; }

/* ---------- counters / filters ---------- */
function counters(list) {
  var c = { READY: 0, ACTIVE: 0, BLOCKED: 0, CLOSED: 0, SUPERSEDED: 0 };
  list.forEach(function (w) { if (c[w.status] !== undefined) c[w.status]++; });
  document.getElementById("c-ready").textContent = c.READY;
  document.getElementById("c-active").textContent = c.ACTIVE;
  document.getElementById("c-blocked").textContent = c.BLOCKED;
  document.getElementById("c-closed").textContent = c.CLOSED;
  document.getElementById("c-superseded").textContent = c.SUPERSEDED;
}
function fill(id, values) {
  var sel = document.getElementById(id), current = sel.value;
  sel.length = 1;
  values.forEach(function (v) {
    var o = document.createElement("option"); o.value = v; o.textContent = v; sel.appendChild(o);
  });
  sel.value = current;
}
function populateFilters(list) {
  var cats = {};
  list.forEach(function (w) { cats[w.category] = 1; });
  fill("f-category", Object.keys(cats).sort());
  fill("f-status", ALL_STATUSES);
  fill("f-priority", ["HIGH", "MEDIUM", "LOW"]);
}

/* ---------- view + filter ---------- */
function inView(w) {
  if (view === "operational") return !isArchive(w.status);
  if (view === "archive") return isArchive(w.status);
  return true;
}
function filtered() {
  var q = document.getElementById("f-search").value.toLowerCase().trim();
  var cat = document.getElementById("f-category").value;
  var st = document.getElementById("f-status").value;
  var pri = document.getElementById("f-priority").value;
  return all.filter(function (w) {
    if (!inView(w)) return false;
    if (cat && w.category !== cat) return false;
    if (st && w.status !== st) return false;
    if (pri && w.priority !== pri) return false;
    if (q) {
      var hay = (w.id + " " + w.canonical_name + " " + w.objective).toLowerCase();
      if (hay.indexOf(q) === -1) return false;
    }
    return true;
  });
}

/* reverse lineage: who supersedes / follows up this workstream */
function reverseLinks(id) {
  var out = [];
  all.forEach(function (w) {
    if (w.supersedes === id) out.push("superseded by " + w.id);
    else if (w.follow_up_to === id) out.push("follow-up: " + w.id);
  });
  return out;
}
function lineageHtml(w) {
  var lines = [];
  if (w.follow_up_to) lines.push("follows up " + esc(w.follow_up_to));
  if (w.supersedes) lines.push("supersedes " + esc(w.supersedes));
  if (w.related_to && w.related_to.length) lines.push("related: " + esc(w.related_to.join(", ")));
  reverseLinks(w.id).forEach(function (r) { lines.push(esc(r)); });
  if (!lines.length) return "";
  return '<div class="lineage">' + lines.map(function (l) { return "&#8627; " + l; }).join("<br>") + "</div>";
}

/* ---------- cards ---------- */
function statusButtons(w) {
  var defs = [["READY", "MARK READY"], ["ACTIVE", "MARK ACTIVE"],
              ["BLOCKED", "MARK BLOCKED"], ["CLOSED", "MARK CLOSED"]];
  return defs.map(function (d) {
    return '<button data-act="status" data-status="' + d[0] + '" data-id="' + w.id + '">' + d[1] + "</button>";
  }).join("");
}
function archiveControls(w) {
  return '<button data-act="reopen" data-id="' + w.id + '">REOPEN</button>' +
         '<button data-act="followup" data-id="' + w.id + '">CREATE FOLLOW-UP</button>';
}
function render() {
  var list = filtered();
  var host = document.getElementById("cards");
  if (!list.length) { host.innerHTML = '<div class="empty">No workstreams in this view.</div>'; return; }
  host.innerHTML = list.map(function (w) {
    var archived = isArchive(w.status);
    return '' +
      '<div class="card' + (archived ? " archived" : "") + '">' +
        '<div class="card-top">' +
          '<span class="card-id">' + esc(w.id) + '</span>' +
          '<span class="badge status-' + w.status + '">' + w.status + '</span>' +
        '</div>' +
        '<div class="card-name">' + esc(w.canonical_name) + '</div>' +
        '<div class="card-meta"><span class="tag">' + esc(w.category) + '</span><span class="tag">' + esc(w.priority) + '</span></div>' +
        '<div class="card-obj">' + esc(w.objective) + '</div>' +
        lineageHtml(w) +
        '<button class="launch" data-act="launch" data-id="' + w.id + '">LAUNCH</button>' +
        '<div class="secondary">' +
          '<button data-act="copy-prompt" data-id="' + w.id + '">COPY PROMPT</button>' +
          '<button data-act="copy-handover" data-id="' + w.id + '">COPY HANDOVER HEADER</button>' +
          (archived ? archiveControls(w) : statusButtons(w) +
             '<button data-act="followup" data-id="' + w.id + '">CREATE FOLLOW-UP</button>') +
        '</div>' +
      '</div>';
  }).join("");
}

/* ---------- data ---------- */
function refresh() {
  return api("/api/registry").then(function (d) {
    all = d.workstreams || [];
    counters(all);
    populateFilters(all);
    render();
  });
}

/* ---------- import ---------- */
function parseImport() {
  var raw = document.getElementById("import-json").value.trim();
  if (!raw) return null;
  var v;
  try { v = JSON.parse(raw); } catch (e) { return { error: e.message }; }
  return { items: Array.isArray(v) ? v : [v] };
}
function renderImportResults(results, summary) {
  var el = document.getElementById("import-results");
  var chip = function (label, n, cls) { return '<span class="chip ' + cls + '">' + n + " " + label + "</span>"; };
  document.getElementById("import-summary").innerHTML =
    chip("NEW", summary.new, "ok") + chip("POSSIBLE DUPLICATES", summary.possible_duplicates, "warn") +
    chip("ID CONFLICTS", summary.id_conflicts, "bad") + chip("INVALID", summary.invalid, "bad");
  el.innerHTML = results.map(function (r) {
    var body = "";
    if (r.state === "ID_CONFLICT") {
      body = '<div class="r-detail bad">REJECT — ' + esc(r.detail) +
        (r.existing ? ' (existing: ' + esc(r.existing.id) + " " + esc(r.existing.canonical_name || "") + ")" : "") + "</div>";
    } else if (r.state === "INVALID") {
      body = '<div class="r-detail bad">' + esc(r.detail) + "</div>";
    } else if (r.state === "POSSIBLE_DUPLICATE") {
      var m = (r.matches || []).map(function (x) {
        return esc(x.id) + " (" + esc(x.canonical_name) + ") — " + esc(x.reasons.join("; ")); }).join("<br>");
      body = '<div class="r-detail warn">POSSIBLE DUPLICATE of:<br>' + m + "</div>" +
        '<div class="r-choice">' +
          '<label><input type="radio" name="res-' + esc(r.id) + '" value="CANCEL" checked> CANCEL</label>' +
          '<label><input type="radio" name="res-' + esc(r.id) + '" value="IMPORT_ANYWAY"> IMPORT ANYWAY</label>' +
        "</div>";
    } else {
      body = '<div class="r-detail ok">NEW</div>';
    }
    return '<div class="r-item state-' + r.state + '"><div class="r-id">' + esc(r.id || "(no id)") +
      " <em>" + esc(r.canonical_name || "") + "</em></div>" + body + "</div>";
  }).join("");
}
function doValidate() {
  var p = parseImport();
  if (!p) { alert("Paste JSON first."); return; }
  if (p.error) { alert("Invalid JSON: " + p.error); return; }
  post("/api/import/validate", { workstreams: p.items }).then(function (d) {
    lastValidation = { items: p.items, results: d.results, summary: d.summary };
    renderImportResults(d.results, d.summary);
    var blockable = d.summary.id_conflicts === 0 && d.summary.invalid === 0;
    document.getElementById("btn-commit").disabled = !blockable || d.summary.total === 0;
  });
}
function collectResolutions() {
  var res = {};
  (lastValidation.results || []).forEach(function (r) {
    if (r.state === "POSSIBLE_DUPLICATE") {
      var sel = document.querySelector('input[name="res-' + r.id + '"]:checked');
      res[r.id] = sel ? sel.value : "CANCEL";
    }
  });
  return res;
}
function doCommit() {
  if (!lastValidation) return;
  post("/api/import/commit", { workstreams: lastValidation.items,
                               resolutions: collectResolutions() }).then(function (d) {
    alert(d.message + (d.committed ? "" : "\n(Nothing was written.)"));
    if (d.committed) {
      document.getElementById("import-json").value = "";
      document.getElementById("import-results").innerHTML = "";
      document.getElementById("import-summary").innerHTML = "";
      document.getElementById("btn-commit").disabled = true;
      lastValidation = null;
      refresh();
    } else {
      renderImportResults(d.results, d.summary);
    }
  });
}

/* ---------- actions ---------- */
function onClick(e) {
  var seg = e.target.closest("#viewseg button[data-view]");
  if (seg) {
    view = seg.getAttribute("data-view");
    document.querySelectorAll("#viewseg button").forEach(function (b) { b.classList.remove("active"); });
    seg.classList.add("active");
    render();
    return;
  }
  if (e.target.id === "btn-import") { toggleImport(true); return; }
  if (e.target.id === "btn-import-close") { toggleImport(false); return; }
  if (e.target.id === "btn-validate") { doValidate(); return; }
  if (e.target.id === "btn-commit") { doCommit(); return; }

  var btn = e.target.closest("button[data-act]");
  if (!btn) return;
  var act = btn.getAttribute("data-act"), id = btn.getAttribute("data-id");

  if (act === "launch") {
    post("/api/launch", { id: id }).then(function (d) {
      if (d.prompt) copyText(d.prompt);
      showToast();
      window.open(d.chatgpt_url || "https://chatgpt.com/", "_blank");
      refresh();
    });
  } else if (act === "copy-prompt") {
    api("/api/prompt?id=" + encodeURIComponent(id)).then(function (d) {
      if (d.prompt) { copyText(d.prompt); showToast(); }
    });
  } else if (act === "copy-handover") {
    api("/api/handover?id=" + encodeURIComponent(id)).then(function (d) {
      if (d.header) { copyText(d.header); showToast(); }
    });
  } else if (act === "status") {
    post("/api/status", { id: id, status: btn.getAttribute("data-status") }).then(refresh);
  } else if (act === "reopen") {
    if (!confirm("REOPEN " + id + "?\nThis is a deliberate action for work closed by mistake.")) return;
    post("/api/reopen", { id: id }).then(function (d) {
      if (!d.ok) alert(d.error); else refresh();
    });
  } else if (act === "followup") {
    var sup = confirm("Create follow-up to " + id + " with a new permanent ID.\n\n" +
      "OK = also mark " + id + " as SUPERSEDED.\nCancel = keep " + id + " as-is (just create the follow-up).");
    post("/api/followup", { parent_id: id, supersede: sup }).then(function (d) {
      if (!d.ok) { alert("Could not create follow-up: " + d.error); return; }
      alert("Created " + d.id + (d.superseded_parent ? "\n" + id + " marked SUPERSEDED." : ""));
      refresh();
    });
  }
}
function toggleImport(show) {
  document.getElementById("import-panel").hidden = !show;
  if (show) document.getElementById("import-json").focus();
}

document.addEventListener("click", onClick);
["f-search", "f-category", "f-status", "f-priority"].forEach(function (id) {
  document.getElementById(id).addEventListener("input", render);
});
refresh();
