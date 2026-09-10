"use strict";
// Pyrnova Investigation — deterministic search + company/program pages (M22-D).
// Renders server read projections verbatim. No client-side scoring, no fabrication, no LLM.

const view = document.querySelector("#view");
const message = document.querySelector("#message");
const qInput = document.querySelector("#q");
const asof = document.querySelector("#asof");
const form = document.querySelector("#searchform");

const esc = v => String(v ?? "").replace(/[&<>'"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));
const dash = v => (v === null || v === undefined || v === "" || v === "UNKNOWN") ? "Unknown" : v;
const asofParam = () => asof.value ? `&as_of=${encodeURIComponent(asof.value)}` : "";
// The customer overlay is the AUTHENTICATED customer (fixed by the credential), never a URL parameter a
// user could edit to view another tenant's private context. In local dev (no auth) a ?customer= override
// is honored for convenience only; the server independently enforces the tenant boundary regardless.
const customerParam = () => {
  const fixed = (typeof Pyrnova !== "undefined") && Pyrnova.fixedCustomer && Pyrnova.fixedCustomer();
  const c = fixed || ((typeof Pyrnova !== "undefined" && Pyrnova.me && Pyrnova.me.require_auth)
    ? null : new URLSearchParams(location.search).get("customer"));
  return c ? `&customer=${encodeURIComponent(c)}` : "";
};

function note(text) { message.hidden = !text; message.textContent = text || ""; }

function pageLink(link) {
  if (!link) return "#";
  const a = asof.value ? `&as_of=${encodeURIComponent(asof.value)}` : "";
  if (link.company) return `/company?ref=${encodeURIComponent(link.company)}${a}`;
  if (link.program) return `/program?key=${encodeURIComponent(link.program)}${a}`;
  return "#";
}

// ---- router ----
async function route() {
  const path = location.pathname;
  const params = new URLSearchParams(location.search);
  if (params.get("as_of") && !asof.value) asof.value = params.get("as_of");
  note("");
  try {
    if (path === "/company") { qInput.value = ""; return renderCompany(params.get("ref")); }
    if (path === "/program") { qInput.value = ""; return renderProgram(params.get("key")); }
    // /search or /investigate
    const q = params.get("q") || "";
    qInput.value = q;
    if (!q) { view.innerHTML = `<div class="empty">Search the Pyrnova estate to begin an investigation.</div>`; return; }
    return renderSearch(q);
  } catch (err) { note(err.message); }
}

// ---- search results ----
async function renderSearch(q) {
  const res = await Pyrnova.authFetch(`/api/search?q=${encodeURIComponent(q)}${asofParam()}`);
  const data = await res.json();
  if (!res.ok) { note(data.error || "Search failed"); return; }
  const r = (data.resolution || "UNRESOLVED").toLowerCase();
  let html = `<div class="res-head"><h1>${esc(q)}</h1>` +
    `<span class="resolution ${r}">${esc(data.resolution)}</span>` +
    (data.match_basis ? `<span class="res-note">matched on ${esc(data.match_basis.replace(/_/g, " ").toLowerCase())}</span>` : "") +
    (data.note ? `<span class="res-note">${esc(data.note)}</span>` : "") +
    `</div>`;
  if (data.resolution === "AMBIGUOUS") {
    html += `<div class="message">More than one canonical object matches. Pyrnova does not guess — select the correct one.</div>`;
  }
  if (!(data.results || []).length) {
    html += `<div class="empty">No entity or program in the Pyrnova estate matched this query.</div>`;
    view.innerHTML = html; return;
  }
  html += `<div class="results">`;
  for (const it of data.results) {
    const meta = [];
    if (it.identifier) meta.push(`<span class="mono">${esc(it.identifier_kind || "ID")}: ${esc(it.identifier)}</span>`);
    if (it.parent_or_agency) meta.push(esc(it.parent_or_agency));
    meta.push(`matched: ${esc((it.match_basis || "").replace(/_/g, " ").toLowerCase())}`);
    html += `<a class="result" href="${pageLink(it.link)}">` +
      `<div><div class="r-name">${esc(it.canonical_name)}</div>` +
      `<div class="r-meta">${meta.join('<span class="r-type">·</span>')}</div></div>` +
      `<div class="r-right"><span class="r-type">${esc(it.type)}</span>` +
      (it.confidence !== undefined ? `<div class="badge">confidence ${esc(it.confidence)}</div>` : "") +
      `</div></a>`;
  }
  html += `</div>`;
  view.innerHTML = html;
}

// ---- shared page pieces ----
function customerCtx(cc) {
  if (!cc) return "";
  const rel = cc.watched ? `Watched — ${esc((cc.relation || "").replace(/_/g, " "))}` : "Not on this customer's watchlist";
  const ids = (cc.related_material_change_ids || []).length;
  return `<div class="customer-ctx"><div class="cc-label">Customer context · ${esc(cc.customer_id)}</div>` +
    `<div class="cc-body">${rel}. ${ids} related Material Change${ids === 1 ? "" : "s"} in this customer's feed.</div></div>`;
}

function eventCard(e) {
  const disp = (e.kind === "opportunity" ? "opportunity" : (e.kind ? "threat" : "monitoring"));
  const a = e.assessment || {}, o = e.observed || {};
  return `<div class="card ${disp}"><div class="c-top"><span class="c-title">${esc(e.title || "Material change")}</span>` +
    `<span class="c-badges"><span class="badge">Materiality ${esc(dash(a.materiality))}</span>` +
    `<span class="badge">Confidence ${esc(dash(a.confidence))}</span>` +
    (e.is_propagated ? `<span class="badge">propagated · depth ${esc(dash(e.propagation_depth))}</span>` : "") +
    `</span></div>` +
    `<div class="c-facts">` +
    `<span>Mechanism <b>${esc(dash(a.mechanism))}</b></span>` +
    `<span>Program <b class="mono">${esc(dash(o.affected_program))}</b></span>` +
    `<span>Agency <b>${esc(dash(o.agency))}</b></span>` +
    `<span>Knowable <b class="mono">${esc(dash(o.observed_at))}</b></span>` +
    `<span>Origin <b>${esc(dash(o.catalyst_class))}</b></span>` +
    `<span>Outcome <b>${esc(dash(e.outcome_state))}</b></span>` +
    `</div></div>`;
}

function section(title, inner, emptyText) {
  const body = inner || `<div class="none">${esc(emptyText || "Nothing stored.")}</div>`;
  return `<div class="section"><h2>${esc(title)}</h2>${body}</div>`;
}

function evidenceTable(rows) {
  if (!rows.length) return "";
  return `<table class="grid"><thead><tr><th>Source</th><th>Type</th><th>Reference</th></tr></thead><tbody>` +
    rows.map(r => `<tr><td>${esc(dash(r.source))}</td><td><span class="pill">${esc(r.type)}</span></td>` +
      `<td class="mono">${esc(r.evidence_id)}</td></tr>`).join("") + `</tbody></table>`;
}

function historyTable(rows) {
  if (!rows.length) return "";
  return `<div class="hist">` + rows.map(h =>
    `<div class="h-row"><span class="h-at mono">${esc(dash(h.at))}</span>` +
    `<span class="h-kind">${esc((h.kind || "").replace(/_/g, " "))}</span>` +
    `<span class="h-sum">${esc(dash(h.summary))}</span></div>`).join("") + `</div>`;
}

function gapsList(gaps) {
  return `<ul class="gaps">` + (gaps || []).map(g => `<li>${esc(g)}</li>`).join("") + `</ul>`;
}

// ---- company page ----
async function renderCompany(ref) {
  if (!ref) { note("A company ref is required."); return; }
  const res = await Pyrnova.authFetch(`/api/company?ref=${encodeURIComponent(ref)}${asofParam()}${customerParam()}`);
  const data = await res.json();
  if (!res.ok) { note(data.error || "Company not found"); view.innerHTML = `<div class="empty">${esc(data.error || "Not found")}</div>`; return; }
  const id = data.identity;
  const ids = Object.entries(id.identifiers || {});
  let html = `<div class="page-head"><div class="kicker">Company intelligence</div>` +
    `<h1>${esc(id.canonical_name)}</h1><div class="idrow">` +
    `<span class="idchip">Entity<b class="mono">${esc(id.ref)}</b></span>` +
    ids.map(([k, v]) => `<span class="idchip">${esc(k.toUpperCase())}<b class="mono">${esc(v)}</b></span>`).join("") +
    (id.parent_ref ? `<span class="idchip">Parent<b class="mono">${esc(id.parent_ref)}</b></span>` : "") +
    `</div>` +
    (id.aliases.length ? `<div class="aliases">Also observed as: ${id.aliases.map(esc).join("; ")}</div>` : "") +
    `</div>`;
  html += customerCtx(data.customer_context);

  const ci = data.current_intelligence;
  html += section("Current intelligence",
    ci.count ? ci.material_events.map(eventCard).join("") : "",
    "No current material intelligence stored for this entity.");

  html += section("Government activity",
    data.government_activity.length ? `<table class="grid"><thead><tr><th>Program / contract</th><th>Agency</th><th>Role</th><th>Evidence</th></tr></thead><tbody>` +
      data.government_activity.map(g => `<tr><td><a href="/program?key=${encodeURIComponent(g.program_key)}">${esc(g.program_key)}</a></td>` +
        `<td>${esc(dash(g.agency))}</td><td><span class="pill">${esc(g.role)}</span></td>` +
        `<td class="mono">${g.evidence_ids.length} ref(s)</td></tr>`).join("") + `</tbody></table>` : "",
    "No evidenced government program activity currently stored.");

  html += section("Relationships",
    data.relationships.length ? `<table class="grid"><thead><tr><th>Relation</th><th>Direction</th><th>Related entity</th><th>Basis</th><th>Valid</th></tr></thead><tbody>` +
      data.relationships.map(r => `<tr><td>${esc(r.relation)}</td><td><span class="pill">${esc(r.direction)}</span></td>` +
        `<td><a href="/company?ref=${encodeURIComponent(r.related_ref)}">${esc(r.related_name)}</a></td>` +
        `<td>${esc(dash(r.link_class))} · ${esc(dash(r.join_method))}${r.confidence != null ? ` · ${esc(r.confidence)}` : ""}</td>` +
        `<td class="mono">${esc(dash(r.valid_from))}${r.valid_to ? ` → ${esc(r.valid_to)}` : ""}</td></tr>`).join("") + `</tbody></table>` : "",
    "No evidenced relationships currently stored.");

  html += section("Material history", historyTable(data.material_history), "No history stored.");
  html += section("Evidence", evidenceTable(data.evidence), "No evidence references stored.");
  html += section("Intelligence gaps", gapsList(data.intelligence_gaps));
  view.innerHTML = html;
}

// ---- program page ----
async function renderProgram(key) {
  if (!key) { note("A program key is required."); return; }
  const res = await Pyrnova.authFetch(`/api/program?key=${encodeURIComponent(key)}${asofParam()}${customerParam()}`);
  const data = await res.json();
  if (!res.ok) { note(data.error || "Program not found"); view.innerHTML = `<div class="empty">${esc(data.error || "Not found")}</div>`; return; }
  const pi = data.program_identity;
  let html = `<div class="page-head"><div class="kicker">Program intelligence</div>` +
    `<h1 class="mono">${esc(pi.program_key)}</h1><div class="idrow">` +
    `<span class="idchip">Agency<b>${esc(dash(pi.agency))}</b></span>` +
    `<span class="idchip">Status<b>${esc(dash(pi.status))}</b></span>` +
    `<span class="idchip">First seen<b class="mono">${esc(dash(pi.first_seen_at))}</b></span>` +
    `</div></div>`;
  html += customerCtx(data.customer_context);

  const mc = data.material_changes;
  html += section("Material changes",
    mc.count ? mc.material_events.map(eventCard).join("") : "",
    "No material changes stored for this program.");

  html += section("Companies",
    data.companies.length ? `<table class="grid"><thead><tr><th>Company</th><th>Role</th><th>Identifier</th></tr></thead><tbody>` +
      data.companies.map(c => `<tr><td><a href="/company?ref=${encodeURIComponent(c.ref)}">${esc(c.name)}</a></td>` +
        `<td><span class="pill">${esc(c.role)}</span></td><td class="mono">${esc(dash(c.identifier))}</td></tr>`).join("") + `</tbody></table>` : "",
    "No companies evidenced on this program.");

  html += section("Evidence", evidenceTable(data.evidence), "No evidence references stored.");
  html += section("Material history", historyTable(data.material_history), "No history stored.");
  html += section("Intelligence gaps", gapsList(data.intelligence_gaps));
  view.innerHTML = html;
}

// ---- navigation ----
form.addEventListener("submit", e => {
  e.preventDefault();
  const q = qInput.value.trim();
  const a = asof.value ? `&as_of=${encodeURIComponent(asof.value)}` : "";
  history.pushState({}, "", `/search?q=${encodeURIComponent(q)}${a}`);
  route();
});
asof.addEventListener("change", route);
// Intercept in-page links so the SPA routes without a full reload.
document.addEventListener("click", e => {
  const a = e.target.closest("a");
  if (!a) return;
  const href = a.getAttribute("href") || "";
  if (/^\/(company|program|search|investigate)\b/.test(href)) {
    e.preventDefault();
    history.pushState({}, "", href);
    route();
  }
});
window.addEventListener("popstate", route);
// Establish the access session first (so the authenticated customer overlay is known), then route.
// Re-route after a successful sign-in from the access gate.
document.addEventListener("pyrnova:ready", route);
Pyrnova.init().catch(err => note(err.message));
