"use strict";
// Pyrnova Live Intelligence — customer product SPA (Bundle 3).
// Surfaces the accepted decision intelligence: Customer Lens, Opportunities, the Opportunity Decision
// View, Evidence Inspector, As-of / temporal view, customer Disposition, brief download + delivery, and
// launch-useful Search. Deterministic reads from the /api surface; no client-side scoring or fabrication.
// UNKNOWN is rendered honestly; source-rights restrictions surface as BLOCKED (fail closed).

const main = document.querySelector("#main");
const message = document.querySelector("#message");
const asofEl = document.querySelector("#asof");
const customerSel = document.querySelector("#customer");

const esc = v => String(v ?? "").replace(/[&<>'"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));
const dash = v => (v === null || v === undefined || v === "" || v === "UNKNOWN") ? "Unknown" : v;
const money = v => (v === null || v === undefined) ? undefined : `$${Math.round(v).toLocaleString("en-US")}`;
const pct = v => (v === null || v === undefined) ? undefined : `${Math.round(v * 100)}%`;

function note(text) { message.hidden = !text; message.textContent = text || ""; }
function currentCustomer() { return Pyrnova.fixedCustomer() || (customerSel && customerSel.value) || null; }
function asofQuery() { return asofEl && asofEl.value ? `&as_of=${encodeURIComponent(asofEl.value)}` : ""; }
function cq() { const c = currentCustomer(); return c ? `customer=${encodeURIComponent(c)}` : "customer="; }

async function api(path) {
  const res = await Pyrnova.authFetch(path);
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try { const j = await res.json(); if (j.error) msg = j.error; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

function rightsPill(sr) {
  const d = (sr && sr.display) || "ALLOWED";
  const cls = d === "ALLOWED" ? "good" : (d === "BLOCKED" ? "bad" : "warn");
  return `<span class="pill ${cls}" title="Source-rights display">${esc(d)}</span>`;
}
function loading() { main.innerHTML = `<p class="spin" role="status">Loading…</p>`; }
function empty(msg) { return `<div class="empty">${esc(msg)}</div>`; }
function setNav(name) {
  document.querySelectorAll("[data-nav]").forEach(a =>
    a.setAttribute("aria-current", a.getAttribute("data-nav") === name ? "page" : "false"));
}
function focusMain() { main.focus(); }

// --- Customer Lens (B3.1) --------------------------------------------------------------------------
async function viewLens() {
  setNav("lens"); loading();
  try {
    const l = await api(`/api/lens?${cq()}${asofQuery()}`);
    const mc = l.material_changes || {}, opp = l.opportunities || {}, unc = l.uncertainty || {};
    const top = (opp.top || []).map(oppCard).join("");
    const changes = (mc.items || []).map(c => `
      <div class="card"><h3>${esc(dash((c.observed||{}).affected_entity || c.title || c.id))}</h3>
        <p class="muted">${esc(dash((c.assessment||{}).summary || (c.observed||{}).summary || c.disposition))}</p>
        ${rightsPill(c.source_rights)}</div>`).join("");
    const uncertain = (unc.low_confidence_opportunities || []).map(u =>
      `<li>${esc(dash(u.title || u.id))} — confidence ${esc(dash(pct(u.confidence)))}</li>`).join("");
    main.innerHTML = `
      <h1>${esc(dash(l.customer && l.customer.name))} — Customer Lens</h1>
      <div class="stat panel" aria-label="Summary">
        <div><b>${esc(mc.count ?? 0)}</b><span class="muted">Material changes</span></div>
        <div><b>${esc(opp.count ?? 0)}</b><span class="muted">Opportunities</span></div>
        <div><b>${esc((unc.low_confidence_opportunities||[]).length)}</b><span class="muted">Uncertain</span></div>
      </div>
      <section><h2>What materially changed</h2><div class="grid cols">${changes || empty("No material changes at this cutoff.")}</div></section>
      <section><h2>Opportunities that matter</h2><div class="grid cols">${top || empty("No opportunities at this cutoff.")}</div></section>
      <section><h2>What is uncertain</h2>${uncertain ? `<ul>${uncertain}</ul>` : empty("No flagged uncertainty.")}</section>`;
    note(""); focusMain();
  } catch (e) { note(e.message); main.innerHTML = empty("Could not load the Lens."); }
}

function oppCard(o) {
  if ((o.source_rights || {}).display === "BLOCKED")
    return `<div class="card"><h3>Restricted</h3>${rightsPill(o.source_rights)}
      <p class="muted">Source rights restrict customer display of this item.</p></div>`;
  const w = o.why_now || {}, s = o.signal || {}, disp = o.customer_disposition;
  return `<a class="card" href="#/opp/${encodeURIComponent(o.id)}">
    <h3>${esc(dash(o.title))}</h3>
    <dl class="kv">
      <dt>Why now</dt><dd>${esc(dash(w.kind))} — ${esc(dash(w.summary))}</dd>
      <dt>Incumbent</dt><dd>${esc(dash(o.incumbent))}</dd>
      <dt>Value</dt><dd>${esc(dash(money(o.value_usd)))}</dd>
      <dt>Expected action</dt><dd>${esc(dash(o.expected_action_at))}</dd>
      <dt>Signals</dt><dd>attractiveness ${esc(dash(pct(s.attractiveness)))} · confidence ${esc(dash(pct(s.confidence)))}</dd>
      ${disp ? `<dt>Your view</dt><dd>${esc(dash(disp.pursuit))} / ${esc(dash(disp.relevance))}</dd>` : ""}
    </dl>
    <p class="prov">Pyrnova-derived · next: ${esc(dash(o.recommended_action))}</p>
    ${rightsPill(o.source_rights)}</a>`;
}

// --- Opportunities list (B3.3) ---------------------------------------------------------------------
async function viewOpportunities() {
  setNav("opportunities"); loading();
  try {
    const data = await api(`/api/opportunities?${cq()}${asofQuery()}`);
    const cards = (data.opportunities || []).map(oppCard).join("");
    main.innerHTML = `<h1>Opportunities <span class="muted">(${esc(data.count ?? 0)})</span> ${rightsPill(data.source_rights)}</h1>
      <div class="grid cols">${cards || empty("No opportunities at this cutoff.")}</div>`;
    note(""); focusMain();
  } catch (e) { note(e.message); main.innerHTML = empty("Could not load opportunities."); }
}

// --- Opportunity Decision View (B3.4) + Evidence (B3.6) + As-of (B3.7) + Disposition (B3.8) ---------
async function viewOpportunity(id) {
  setNav("opportunities"); loading();
  try {
    const d = await api(`/api/opportunities/${encodeURIComponent(id)}/decision?${cq()}${asofQuery()}`);
    const dc = d.decision_chain || {};
    if ((dc.source_rights || {}).display === "BLOCKED") {
      main.innerHTML = `<h1>Restricted opportunity</h1><div class="panel">${rightsPill(dc.source_rights)}
        <p class="muted">Source rights restrict customer display of this opportunity's basis.</p></div>`;
      return focusMain();
    }
    const opp = dc.opportunity || {}, w = dc.why_now || {}, ic = dc.incumbent_competitive || {},
      fit = dc.customer_fit || {}, p = dc.pursuit || {}, unc = dc.uncertainty || {}, t = dc.temporal || {};
    const verdictPill = `<span class="pill unknown">${esc(dash(p.verdict))}</span>`;
    const mc = (dc.material_changes || []).map(c =>
      `<li>${esc(dash((c.observed||{}).affected_entity || c.title || c.id))} ${rightsPill(c.source_rights)}</li>`).join("");
    const ev = (dc.evidence || []).map(e => evidenceBlock(id, e)).join("");
    main.innerHTML = `
      <p><a href="#/opportunities">← Opportunities</a></p>
      <h1>${esc(dash(opp.title))} ${rightsPill(d.source_rights)}</h1>
      <p class="muted">${esc(dash(opp.lifecycle_state))} · ${esc(dash(opp.agency))} · ${esc(dash(money(opp.value_usd)))}
        · <span class="prov">as of ${esc(t.as_of || "current")}</span></p>
      <div class="chain">
        <section><h2>Why now</h2><p>${esc(dash(w.kind))}: ${esc(dash(w.summary))} — expected action by ${esc(dash(w.expected_action_at))}</p></section>
        <section><h2>Buyer</h2><p>${esc(dash(dc.buyer && dc.buyer.agency))} <span class="pill unknown">${esc(dash(dc.buyer && dc.buyer.status))}</span></p></section>
        <section><h2>Incumbent / competitive</h2><p>${esc(dash(ic.incumbent))}</p></section>
        <section><h2>Access</h2><p><span class="pill unknown">${esc(dash(dc.access && dc.access.status))}</span></p></section>
        <section><h2>Customer fit</h2><p>relevance ${esc(dash(fit.relevance_score))} <span class="pill unknown">${esc(dash(fit.status))}</span></p></section>
        <section><h2>Pursuit ${verdictPill}</h2>
          <p><strong>Recommended:</strong> ${esc(dash(p.recommended_action))}</p>
          <p class="prov">Native signal: attractiveness ${esc(dash(pct((p.native_signal||{}).attractiveness)))}
             · confidence ${esc(dash(pct((p.native_signal||{}).confidence)))}. Verdict UNKNOWN when Bundle-2 pursuit inputs are not persisted (no fabricated score).</p>
          ${(p.reversal_conditions||[]).filter(Boolean).length ? `<p><strong>Reversal:</strong> ${esc(dash((p.reversal_conditions||[]).filter(Boolean).join("; ")))}</p>` : ""}
        </section>
        <section><h2>Material changes</h2>${mc ? `<ul>${mc}</ul>` : `<p class="muted">None affecting this opportunity.</p>`}</section>
        <section><h2>Next action</h2><p>${esc(dash(dc.next_action))}</p></section>
        <section><h2>Uncertainty</h2><p>${esc(dash(unc.falsification))}</p></section>
        <section><h2>Evidence (${(dc.evidence||[]).length})</h2>${ev || `<p class="muted">No evidence attached.</p>`}</section>
        <section><h2>Temporal / as-of history</h2>
          <p class="muted">Known then vs now is controlled by the As-of date in the header. Evidence first seen:
            ${esc(dash((t.evidence_first_seen||[]).join(", ")))}</p></section>
      </div>
      ${dispositionForm(id, dc.customer_disposition)}
      <div class="actions">
        <a class="act" href="/api/opportunities/${encodeURIComponent(id)}/brief?${cq()}${asofQuery()}&download=1"
           rel="noopener">Download brief</a>
        <button class="act" id="deliver-btn" type="button">Deliver brief…</button>
      </div>
      <div id="deliver-out" aria-live="polite"></div>`;
    wireOpportunity(id);
    note(""); focusMain();
  } catch (e) { note(e.message); main.innerHTML = empty("Could not load the decision view."); }
}

function evidenceBlock(oppId, e) {
  const doc = e.doctrine || {};
  const blocked = (e.source_rights || {}).display === "BLOCKED";
  return `<details class="ev" data-ev="${esc(e.id)}">
    <summary>${esc(dash(e.source_id))} — ${esc(dash(e.source_ref || e.id))} ${rightsPill(e.source_rights)}</summary>
    ${blocked ? `<p class="muted">Rights-restricted: raw source is not shown; provenance only.</p>` : ""}
    <dl class="kv">
      <dt class="prov">Source fact</dt><dd>${esc(dash(e.source_id))}</dd>
      <dt class="prov">Observed</dt><dd>${esc(dash(e.first_seen_at || e.published_at))}</dd>
      <dt class="prov">Provenance</dt><dd><code>${esc(dash(e.content_sha256))}</code></dd>
      ${e.source_url ? `<dt class="prov">Source URL</dt><dd><a href="${esc(e.source_url)}" rel="noopener">official record</a></dd>` : ""}
    </dl></details>`;
}

function dispositionForm(id, current) {
  const cur = current || {};
  const opts = (name, values) => values.map(v =>
    `<option value="${v}"${cur[name] === v ? " selected" : ""}>${v}</option>`).join("");
  return `<section class="panel"><h2>Your decision (recorded to Decision Memory)</h2>
    <p class="prov">Customer judgment — kept distinct from Pyrnova's assessment.</p>
    <form class="disp" id="disp-form">
      <label>Relevance<select name="relevance">${opts("relevance", ["UNKNOWN","RELEVANT","NOT_RELEVANT","PARTIAL"])}</select></label>
      <label>Pursuit<select name="pursuit">${opts("pursuit", ["UNKNOWN","PURSUE","WATCH","INVESTIGATE","PASS"])}</select></label>
      <label>Note<textarea name="note" rows="2" maxlength="500">${esc(cur.note || "")}</textarea></label>
      <div class="actions"><button class="act primary" type="submit">Save my decision</button></div>
    </form></section>`;
}

function wireOpportunity(id) {
  const form = document.querySelector("#disp-form");
  if (form) form.addEventListener("submit", async e => {
    e.preventDefault();
    const body = { customer: currentCustomer(), relevance: form.relevance.value,
                   pursuit: form.pursuit.value, note: form.note.value.trim() || null };
    try {
      const res = await Pyrnova.authFetch(`/api/opportunities/${encodeURIComponent(id)}/disposition`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!res.ok) throw new Error((await res.json()).error || "save failed");
      note("Your decision was recorded.");
    } catch (err) { note(err.message); }
  });
  const btn = document.querySelector("#deliver-btn");
  const out = document.querySelector("#deliver-out");
  // Inline, validated recipient entry — not a raw browser prompt(). The form discloses on demand,
  // validates the email client-side, disables while sending, and reports a deterministic delivery
  // status (including an explicit FAILED state when no verified transport is configured).
  async function submitDelivery(to, statusEl, submitEl) {
    submitEl.disabled = true;
    statusEl.textContent = "Sending…";
    try {
      const res = await Pyrnova.authFetch(`/api/opportunities/${encodeURIComponent(id)}/deliver`,
        { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ customer: currentCustomer(), recipients: [to] }) });
      const j = await res.json();
      if (!res.ok) throw new Error(j.error || "delivery failed");
      out.innerHTML = `<p class="muted">Delivery <code>${esc(j.delivery_id)}</code> — status
        <strong>${esc(j.status)}</strong>${j.status === "FAILED" ? " (no verified transport configured — real external delivery pending)" : ""}.</p>`;
    } catch (err) {
      statusEl.textContent = err.message;
      submitEl.disabled = false;
    }
  }
  if (btn) btn.addEventListener("click", () => {
    if (document.querySelector("#deliver-form")) { document.querySelector("#deliver-to").focus(); return; }
    out.innerHTML =
      `<form id="deliver-form" class="deliver-form" novalidate>
        <label for="deliver-to">Deliver this brief to an authorized recipient</label>
        <div class="deliver-row">
          <input id="deliver-to" type="email" inputmode="email" autocomplete="off" spellcheck="false"
                 placeholder="name@organization.gov" required>
          <button class="act primary" type="submit">Send</button>
          <button class="act" type="button" id="deliver-cancel">Cancel</button>
        </div>
        <p class="deliver-status muted" id="deliver-status" aria-live="polite"></p>
      </form>`;
    const form = document.querySelector("#deliver-form");
    const input = document.querySelector("#deliver-to");
    const statusEl = document.querySelector("#deliver-status");
    input.focus();
    document.querySelector("#deliver-cancel").addEventListener("click", () => { out.innerHTML = ""; });
    form.addEventListener("submit", e => {
      e.preventDefault();
      const to = input.value.trim();
      if (!to || !input.checkValidity()) { statusEl.textContent = "Enter a valid recipient email."; input.focus(); return; }
      submitDelivery(to, statusEl, form.querySelector('button[type="submit"]'));
    });
  });
}

// --- Search (B3.9) ---------------------------------------------------------------------------------
async function viewSearch() {
  setNav("search");
  main.innerHTML = `<h1>Search</h1>
    <form id="search-form" role="search"><label>Query
      <input id="q" type="search" placeholder="opportunity, buyer, entity, program…" autocomplete="off"></label>
      <button class="act" type="submit">Search</button></form>
    <div id="results" aria-live="polite"></div>`;
  const form = document.querySelector("#search-form");
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const q = document.querySelector("#q").value.trim();
    const out = document.querySelector("#results");
    if (!q) { out.innerHTML = ""; return; }
    out.innerHTML = `<p class="spin">Searching…</p>`;
    try {
      const r = await api(`/api/search?q=${encodeURIComponent(q)}${asofQuery()}`);
      const rows = (r.results || []).map(x =>
        `<li><strong>${esc(dash(x.type))}</strong> — ${esc(dash(x.canonical_name || x.key || x.identifier))}
          ${x.parent_or_agency ? `<span class="muted">· ${esc(x.parent_or_agency)}</span>` : ""}
          ${x.match_basis ? `<span class="muted">(${esc(x.match_basis)})</span>` : ""}</li>`).join("");
      out.innerHTML = rows ? `<ul>${rows}</ul>` : empty("No matches.");
    } catch (err) { out.innerHTML = empty(err.message); }
  });
  document.querySelector("#q").focus();
}

// --- routing ---------------------------------------------------------------------------------------
function route() {
  const h = location.hash.replace(/^#/, "") || "/lens";
  const parts = h.split("/").filter(Boolean);
  if (parts[0] === "opp" && parts[1]) return viewOpportunity(decodeURIComponent(parts[1]));
  if (parts[0] === "opportunities") return viewOpportunities();
  if (parts[0] === "search") return viewSearch();
  return viewLens();
}

function applyIdentity(me) {
  const org = document.querySelector("#org");
  const field = document.querySelector("#customer-field");
  const signout = document.querySelector("#signout");
  const fixed = Pyrnova.fixedCustomer();
  const switchable = Pyrnova.switchable();
  if (fixed && me && me.customer) { org.textContent = me.customer.name || me.customer.id; field.hidden = true; }
  else if (switchable) {
    field.hidden = false;
    customerSel.innerHTML = switchable.map(c => `<option value="${esc(c.id)}">${esc(c.name || c.id)}</option>`).join("");
    org.textContent = "";
  }
  if (me && me.authenticated) { signout.hidden = false; signout.onclick = () => Pyrnova.signOut(); }
}

document.addEventListener("pyrnova:ready", e => {
  applyIdentity(e.detail);
  if (!location.hash) location.hash = "#/lens";
  route();
});
window.addEventListener("hashchange", route);
[asofEl, customerSel].forEach(el => el && el.addEventListener("change", route));
Pyrnova.init();
