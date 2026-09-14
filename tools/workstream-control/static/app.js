"use strict";

var STATUSES = ["READY", "ACTIVE", "BLOCKED", "CLOSED", "DEFERRED"];
var all = [];

function api(path, opts) {
  return fetch(path, opts).then(function (r) { return r.json(); });
}

function copyText(text) {
  // Prefer the browser clipboard (localhost is a secure context); the server
  // also copies via pbcopy on launch, so this is belt-and-braces.
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text).catch(function () {
      return serverCopy(text);
    });
  }
  return serverCopy(text);
}

function serverCopy(text) {
  return api("/api/copy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text }),
  });
}

function showToast() {
  var t = document.getElementById("toast");
  t.hidden = false;
  clearTimeout(showToast._h);
  showToast._h = setTimeout(function () { t.hidden = true; }, 4000);
}

function counters(list) {
  var c = { READY: 0, ACTIVE: 0, BLOCKED: 0, CLOSED: 0 };
  list.forEach(function (w) { if (c[w.status] !== undefined) c[w.status]++; });
  document.getElementById("c-ready").textContent = c.READY;
  document.getElementById("c-active").textContent = c.ACTIVE;
  document.getElementById("c-blocked").textContent = c.BLOCKED;
  document.getElementById("c-closed").textContent = c.CLOSED;
}

function populateFilters(list) {
  var cats = {}, pris = {};
  list.forEach(function (w) { cats[w.category] = 1; pris[w.priority] = 1; });
  fill("f-category", Object.keys(cats).sort());
  fill("f-status", STATUSES);
  fill("f-priority", Object.keys(pris).sort());
}

function fill(id, values) {
  var sel = document.getElementById(id);
  var current = sel.value;
  // keep first (All) option
  sel.length = 1;
  values.forEach(function (v) {
    var o = document.createElement("option");
    o.value = v; o.textContent = v; sel.appendChild(o);
  });
  sel.value = current;
}

function filtered() {
  var q = document.getElementById("f-search").value.toLowerCase().trim();
  var cat = document.getElementById("f-category").value;
  var st = document.getElementById("f-status").value;
  var pri = document.getElementById("f-priority").value;
  return all.filter(function (w) {
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

function statusButtons(w) {
  var defs = [
    ["MARK READY", "READY"],
    ["MARK ACTIVE", "ACTIVE"],
    ["MARK BLOCKED", "BLOCKED"],
    ["MARK CLOSED", "CLOSED"],
  ];
  return defs.map(function (d) {
    return '<button data-act="status" data-status="' + d[1] + '" data-id="' + w.id + '">' + d[0] + "</button>";
  }).join("");
}

function render() {
  var list = filtered();
  var host = document.getElementById("cards");
  if (!list.length) { host.innerHTML = '<div class="empty">No workstreams match.</div>'; return; }
  host.innerHTML = list.map(function (w) {
    return '' +
      '<div class="card">' +
        '<div class="card-top">' +
          '<span class="card-id">' + w.id + '</span>' +
          '<span class="badge status-' + w.status + '">' + w.status + '</span>' +
        '</div>' +
        '<div class="card-name">' + esc(w.canonical_name) + '</div>' +
        '<div class="card-meta"><span class="tag">' + w.category + '</span><span class="tag">' + w.priority + '</span></div>' +
        '<div class="card-obj">' + esc(w.objective) + '</div>' +
        '<button class="launch" data-act="launch" data-id="' + w.id + '">LAUNCH</button>' +
        '<div class="secondary">' +
          '<button data-act="copy-prompt" data-id="' + w.id + '">COPY PROMPT</button>' +
          '<button data-act="copy-handover" data-id="' + w.id + '">COPY HANDOVER HEADER</button>' +
          statusButtons(w) +
        '</div>' +
      '</div>';
  }).join("");
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}

function refresh() {
  return api("/api/registry").then(function (d) {
    all = d.workstreams || [];
    counters(all);
    populateFilters(all);
    render();
  });
}

function onClick(e) {
  var btn = e.target.closest("button[data-act]");
  if (!btn) return;
  var act = btn.getAttribute("data-act");
  var id = btn.getAttribute("data-id");

  if (act === "launch") {
    api("/api/launch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: id }),
    }).then(function (d) {
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
    var status = btn.getAttribute("data-status");
    api("/api/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: id, status: status }),
    }).then(refresh);
  }
}

document.addEventListener("click", onClick);
["f-search", "f-category", "f-status", "f-priority"].forEach(function (id) {
  document.getElementById(id).addEventListener("input", render);
});
refresh();
