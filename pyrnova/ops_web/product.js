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

// --- intelligence micro-formatters (real values only; no fabrication) -------------------------------
const clamp01 = v => Math.max(0, Math.min(1, Number(v)));
function verdictClass(v) { v = String(v || "").toUpperCase();
  return v === "PURSUE" ? "good" : v === "WATCH" ? "steel" : v === "INVESTIGATE" ? "warn"
       : v === "PASS" ? "bad" : "unknown"; }
function qualClass(q) { q = String(q || "").toUpperCase();
  return q === "HIGH" ? "good" : q === "MEDIUM" ? "steel" : q === "LOW" ? "warn" : "unknown"; }
function statusClass(s) { s = String(s || "").toUpperCase();
  return (s === "EVIDENCED" || s === "DIRECT_ACCESS") ? "good"
       : (s === "" || s === "UNKNOWN") ? "unknown" : "steel"; }
function dispClass(d) { d = String(d || "").toUpperCase();
  return d === "THREAT" ? "d-threat" : d === "MONITORING" ? "d-monitoring" : "d-opportunity"; }
function dispPillClass(d) { d = String(d || "").toUpperCase();
  return d === "THREAT" ? "bad" : d === "OPPORTUNITY" ? "good" : "warn"; }
const bandFill = v => { v = clamp01(v); return v >= 0.67 ? "good" : v >= 0.4 ? "" : "warn"; };
const tail = id => String(id || "").replace(/^[a-z]+_/i, "").slice(0, 6).toUpperCase();

// A thin, honest confidence/relevance meter for a real 0..1 value. Returns "" when not a fact.
function meter(label, value) {
  if (value === null || value === undefined || isNaN(Number(value))) return "";
  const v = clamp01(value), w = Math.round(v * 100);
  return `<div class="meter"><span class="m-label">${esc(label)}</span>
    <span class="m-track"><span class="m-fill ${bandFill(v)}" style="width:${w}%"></span></span>
    <span class="m-val">${w}%</span></div>`;
}
function daysUntil(iso) { if (!iso) return null; const t = Date.parse(iso); return isNaN(t) ? null : Math.round((t - Date.now()) / 86400000); }
function windowChip(w, opp) {
  const iso = (w && w.expected_action_at) || (opp && opp.expected_action_at);
  const d = (w && typeof w.horizon_days === "number") ? w.horizon_days : daysUntil(iso);
  if (d === null && !iso) return "";
  const label = d === null ? esc(iso) : (d <= 0 ? "now" : `${d} day${d === 1 ? "" : "s"}`);
  return `<span class="chip">Window · ${label}</span>`;
}

// --- persistent Customer Lens context strip (whose lens · state · counts) ---------------------------
const lensState = { name: null, mc: null, opp: null, unc: null };
function updateLensStrip(partial) {
  Object.assign(lensState, partial || {});
  const strip = document.querySelector("#lens-strip");
  if (!strip) return;
  if (!lensState.name && lensState.mc === null && lensState.opp === null) { strip.hidden = true; return; }
  const asof = asofEl && asofEl.value;
  const asofHtml = asof
    ? `<span class="ls-asof"><span class="label">As of</span> <span class="mono">${esc(asof)}</span></span>`
    : `<span class="ls-asof ls-live">Live</span>`;
  const metric = (n, l) => (n === null || n === undefined) ? ""
    : `<span class="ls-metric"><b>${esc(n)}</b> <span>${esc(l)}</span></span>`;
  strip.innerHTML =
    `<span class="ls-lens"><span class="label accent">Lens</span> <b>${esc(lensState.name || "—")}</b></span>` +
    `<span class="ls-sep"></span>` +
    metric(lensState.opp, "opportunities") +
    metric(lensState.mc, "material changes") +
    metric(lensState.unc, "uncertain") +
    asofHtml;
  strip.hidden = false;
}

// --- Customer Lens (B3.1) --------------------------------------------------------------------------
async function viewLens() {
  setNav("lens"); loading();
  try {
    const l = await api(`/api/lens?${cq()}${asofQuery()}`);
    const mc = l.material_changes || {}, opp = l.opportunities || {}, unc = l.uncertainty || {};
    const uncCount = (unc.low_confidence_opportunities || []).length;
    updateLensStrip({ name: l.customer && l.customer.name, mc: mc.count ?? 0, opp: opp.count ?? 0, unc: uncCount });
    const top = (opp.top || []).map(oppCard).join("");
    const changes = (mc.items || []).map(changeCard).join("");
    const uncertain = (unc.low_confidence_opportunities || []).map(u =>
      `<li>${esc(dash(u.title || u.id))} — confidence ${esc(dash(pct(u.confidence)))}</li>`).join("");
    main.innerHTML = `
      <h1>${esc(dash(l.customer && l.customer.name))} — Customer Lens</h1>
      <div class="stat" aria-label="Summary">
        <div class="accent"><b>${esc(opp.count ?? 0)}</b><span class="muted">Opportunities</span></div>
        <div><b>${esc(mc.count ?? 0)}</b><span class="muted">Material changes</span></div>
        <div><b>${esc(uncCount)}</b><span class="muted">Flagged uncertain</span></div>
      </div>
      <section><h2>Opportunities that matter</h2><div class="grid cols">${top || empty("No opportunities at this cutoff.")}</div></section>
      <section><h2>What materially changed</h2><div class="grid cols">${changes || empty("No material changes at this cutoff.")}</div></section>
      <section><h2>What is uncertain</h2>${uncertain ? `<ul class="unc-list">${uncertain}</ul>` : empty("No flagged uncertainty.")}</section>`;
    note(""); focusMain();
  } catch (e) { note(e.message); main.innerHTML = empty("Could not load the Lens."); }
}

// A material-change summary card for the Lens (observed entity + why it matters + strength markers).
function changeCard(c) {
  const obs = c.observed || {}, ass = c.assessment || {};
  const title = dash(obs.affected_entity || c.title || c.id);
  const why = dash(ass.consequence || obs.event_summary || ass.mechanism || c.disposition);
  return `<div class="card opp ${dispClass(c.disposition)}">
    <div class="opp-top"><h3 class="opp-title">${esc(title)}</h3>
      <span class="pill ${dispPillClass(c.disposition)}">${esc(dash(c.disposition))}</span></div>
    <p class="opp-why"><span class="label">Why it matters</span>${esc(why)}</p>
    <div class="opp-foot">
      ${ass.materiality ? `<span class="chip">Materiality · ${esc(ass.materiality)}</span>` : ""}
      ${ass.confidence ? `<span class="chip">Confidence · ${esc(ass.confidence)}</span>` : ""}
      ${rightsPill(c.source_rights)}</div></div>`;
}

// National acquisition truth (AU/CA/GB/NZ/US-as-domain). ONE country-neutral renderer driven entirely by
// the block the kernel passes through: nothing here branches on a country code, so a new national domain
// renders with no UI change. Absent block => nothing rendered and US-ontology records are untouched.
function natLabel(v) { return String(v || "").replace(/_/g, " "); }
function natMoney(v) {
  if (!v || v.amount == null) return null;
  const n = Number(v.amount);
  const compact = n >= 1e9 ? (n / 1e9).toFixed(n >= 1e10 ? 0 : 1) + "bn"
    : n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "m" : String(n);
  return `${compact} ${v.currency || ""}`.trim();
}
function nationalChips(n) {
  if (!n) return "";
  const known = v => v && v !== "UNKNOWN";
  const mech = n.mechanism || n.route;
  const val = natMoney(n.value_local);
  return `<span class="chip steel">${esc(n.domain_name || n.domain)}</span>`
    + (mech ? `<span class="chip">${esc(natLabel(mech))}</span>` : "")
    + (known(n.access_class) ? `<span class="chip">${esc(natLabel(n.access_class))}</span>` : "")
    + (known(n.timing_class) ? `<span class="chip">Timing · ${esc(natLabel(n.timing_class))}</span>` : "")
    + (n.post_award ? `<span class="chip warn">Post-award</span>` : "")
    + (val ? `<span class="chip">${esc(val)}</span>` : "");
}
function nationalSection(n) {
  if (!n) return "";
  const known = v => v && v !== "UNKNOWN";
  const row = (label, value, extra) => value
    ? `<p class="prov">${esc(label)}</p><p>${esc(value)}${extra ? ` <span class="prov">${esc(extra)}</span>` : ""}</p>` : "";
  return `
        <section class="dgroup span2">
          <h2 class="label accent">National acquisition · ${esc(n.domain_name || n.domain)}</h2>
          <div class="verdict-row">${nationalChips(n)}</div>
          ${row("Acquisition route", natLabel(n.route), n.route_meaning || "")}
          ${row("Lifecycle stage", natLabel(n.lifecycle_stage))}
          ${row("Access position", natLabel(n.access_class))}
          ${known(n.industrial_position) ? row("Industrial position", natLabel(n.industrial_position)) : ""}
          ${known(n.consequential_change_kind) ? row("Consequential change", natLabel(n.consequential_change_kind)) : ""}
          ${known(n.important_miss_kind) ? row("Important miss", natLabel(n.important_miss_kind)) : ""}
          ${known(n.timing_class) ? row("Timing basis", natLabel(n.timing_class),
            "qualified, never promoted to exact") : ""}
          ${known(n.itb_vp) ? row("ITB / Value Proposition", natLabel(n.itb_vp), "evidenced, never derived") : ""}
          ${known(n.sscr_qdc) ? row("SSCR / QDC", natLabel(n.sscr_qdc), "evidenced, never route-derived") : ""}
          ${n.post_award ? `<p class="prov">Award is not terminal — this opportunity stays monitored after award.</p>` : ""}
          ${n.dlt_calibration_ref ? `<p class="prov">Decision-lead-time calibration · <span class="mono">${esc(n.dlt_calibration_ref)}</span></p>` : ""}
        </section>`;
}

function oppCard(o) {
  if ((o.source_rights || {}).display === "BLOCKED")
    return `<div class="card opp"><div class="opp-top"><h3 class="opp-title">Restricted</h3>${rightsPill(o.source_rights)}</div>
      <p class="opp-restricted">Source rights restrict customer display of this item.</p></div>`;
  const w = o.why_now || {}, s = o.signal || {}, disp = o.customer_disposition, pur = o.pursuit || {};
  const verdict = pur.verdict
    ? `<span class="pill ${verdictClass(pur.verdict)}">${esc(pur.verdict)}${pur.confidence ? ` · ${esc(pur.confidence)}` : ""}</span>`
    : "";
  return `<a class="card opp d-opportunity" href="#/opp/${encodeURIComponent(o.id)}">
    <div class="opp-top">
      <div><span class="opp-code mono">OPP·${esc(tail(o.id))}</span><h3 class="opp-title">${esc(dash(o.title))}</h3></div>
      ${verdict}
    </div>
    <p class="opp-why"><span class="label">Why now</span>${esc(dash(w.summary || w.kind))}</p>
    <div class="opp-meters">${meter("Attractiveness", s.attractiveness)}${meter("Confidence", s.confidence)}</div>
    <div class="opp-foot">
      ${windowChip(w, o)}
      ${o.value_usd != null ? `<span class="chip">${esc(money(o.value_usd))}</span>` : ""}
      ${nationalChips(o.national)}
      ${o.evidence_count != null ? `<span class="chip source">Evidence · ${esc(o.evidence_count)}</span>` : ""}
      ${disp ? `<span class="chip signal">Your view · ${esc(dash(disp.pursuit))}</span>` : ""}
      ${rightsPill(o.source_rights)}
    </div></a>`;
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
      fit = dc.customer_fit || {}, p = dc.pursuit || {}, unc = dc.uncertainty || {}, t = dc.temporal || {},
      acc = dc.access || {}, buyer = dc.buyer || {}, ns = p.native_signal || {}, fr = fit.fit_reasoning || {};
    // A record carrying national acquisition truth is governed by THAT truth: the US-ontology access /
    // incumbent panels are structurally UNKNOWN for it by design (see opportunity_recompute), so showing
    // them would present "Unknown" where the authoritative national position exists. One shared rule, no
    // per-country branch; US-ontology records keep the existing layout exactly.
    const nat = dc.national_acquisition || null;
    const listOf = arr => (arr || []).filter(Boolean);
    const reasonsFor = listOf(p.why), reasonsNot = listOf(p.why_not), reversals = listOf(p.reversal_conditions);
    const wiso = w.expected_action_at || opp.expected_action_at || t.expected_action_at;
    const wdays = (typeof w.horizon_days === "number") ? w.horizon_days : daysUntil(wiso);
    const wcls = wdays === null ? "" : (wdays <= 14 ? "imminent" : wdays <= 45 ? "soon" : "");
    const wbig = wdays === null ? esc(dash(wiso)) : (wdays <= 0 ? "now" : String(wdays));
    const wunit = (wdays === null || wdays <= 0) ? "" : `<span class="muted">day${wdays === 1 ? "" : "s"} to expected action</span>`;
    const mcItems = (dc.material_changes || []).map(c =>
      `<li>${esc(dash((c.observed||{}).affected_entity || c.title || c.id))} ${rightsPill(c.source_rights)}</li>`).join("");
    const firstSeen = listOf(t.evidence_first_seen);
    const ev = (dc.evidence || []).map(e => evidenceBlock(id, e)).join("");

    main.innerHTML = `
      <p><a class="backlink" href="#/opportunities">← Opportunities</a></p>
      <div class="decision-head">
        <span class="opp-code mono">OPP·${esc(tail(id))}</span>
        <h1>${esc(dash(opp.title))} ${rightsPill(d.source_rights)}</h1>
        <div class="decision-meta">
          <span>${esc(dash(opp.lifecycle_state))}</span><span>·</span>
          <span>${esc(dash(opp.agency))}</span><span>·</span>
          <span class="mono">${esc(dash(money(opp.value_usd)))}</span><span>·</span>
          <span class="prov">as of ${esc(t.as_of || "current — live")}</span>
        </div>
      </div>

      <div class="decision">
        <section class="dgroup verdict span2">
          <h2 class="label signal">Why it matters · Pyrnova disposition</h2>
          <div class="verdict-row">
            <span class="pill ${verdictClass(p.verdict)}">${esc(dash(p.verdict))}</span>
            ${p.confidence ? `<span class="pill ${qualClass(p.confidence)}">Confidence · ${esc(p.confidence)}</span>` : ""}
            <span class="prov">Pyrnova-derived — kept distinct from your decision</span>
          </div>
          <p class="strong">${esc(dash(p.recommended_action))}</p>
          <div class="opp-meters">${meter("Attractiveness", ns.attractiveness)}${meter("Signal confidence", ns.confidence)}</div>
          ${(reasonsFor.length || reasonsNot.length) ? `<div class="reasons">
            ${reasonsFor.length ? `<div class="r-col for"><span class="label">Supports</span><ul>${reasonsFor.map(r => `<li>${esc(r)}</li>`).join("")}</ul></div>` : ""}
            ${reasonsNot.length ? `<div class="r-col against"><span class="label">Against</span><ul>${reasonsNot.map(r => `<li>${esc(r)}</li>`).join("")}</ul></div>` : ""}
          </div>` : ""}
          ${reversals.length ? `<p class="prov" style="margin-top:10px">Reversal conditions</p><ul class="rev">${reversals.map(r => `<li>${esc(r)}</li>`).join("")}</ul>` : ""}
        </section>

        <section class="dgroup">
          <h2 class="label accent">What changed · why now</h2>
          <p class="strong">${esc(dash(w.kind))}</p>
          <p>${esc(dash(w.summary))}</p>
          ${wiso ? `<p class="prov">Expected action by <span class="mono">${esc(wiso)}</span></p>` : ""}
        </section>

        <section class="dgroup">
          <h2 class="label accent">Decision window</h2>
          <div class="window-line"><span class="big ${wcls}">${wbig}</span> ${wunit}</div>
          ${nat ? "" : `<p class="prov" style="margin-top:8px">Buyer <span class="pill ${statusClass(buyer.status)}">${esc(dash(buyer.status))}</span></p>`}
        </section>

        ${nat ? nationalSection(nat) : `
        <section class="dgroup">
          <h2 class="label accent">Access · route</h2>
          <p><span class="pill ${statusClass(acc.verdict)}">${esc(dash(acc.verdict))}</span>${acc.teaming_required ? ` <span class="pill warn">Teaming required</span>` : ""}</p>
          ${acc.summary ? `<p>${esc(acc.summary)}</p>` : ""}
          ${acc.required_vehicle ? `<p class="prov">Required vehicle <span class="mono">${esc(acc.required_vehicle)}</span></p>` : ""}
        </section>`}

        <section class="dgroup">
          <h2 class="label accent">Customer consequence · fit</h2>
          <p><span class="pill ${statusClass(fit.status)}">${esc(dash(fit.status))}</span>${fr.posture ? ` <span class="pill steel">Posture · ${esc(fr.posture)}</span>` : ""}</p>
          ${fr.explanation ? `<p>${esc(fr.explanation)}</p>` : ""}
          ${meter("Fit confidence", fr.fit_confidence)}
          ${fr.decisive_factor ? `<p class="prov">Decisive factor · ${esc(String(fr.decisive_factor).replace(/_/g, " "))}</p>` : ""}
        </section>

        ${nat ? (dc.next_action ? `
        <section class="dgroup">
          <h2 class="label accent">Next action</h2>
          <p>${esc(dc.next_action)}</p>
        </section>` : "") : `
        <section class="dgroup">
          <h2 class="label accent">Incumbent · competitive</h2>
          <p>${esc(dash(ic.incumbent))}</p>
          ${dc.next_action ? `<p class="prov">Next action</p><p>${esc(dash(dc.next_action))}</p>` : ""}
        </section>`}

        <section class="dgroup span2">
          <h2 class="label accent">Uncertainty · what would make this wrong</h2>
          <p class="falsify">${esc(dash(unc.falsification))}</p>
          ${meter("Assessment confidence", unc.confidence)}
        </section>

        <section class="dgroup evidence-group">
          <h2 class="label">Evidence · audit trail (${(dc.evidence || []).length})</h2>
          <div class="ev-list">${ev || `<p class="muted">No evidence attached.</p>`}</div>
        </section>

        <section class="dgroup memory">
          <h2 class="label">Decision memory · temporal</h2>
          <p class="prov">Material changes affecting this opportunity</p>
          ${mcItems ? `<ul>${mcItems}</ul>` : `<p class="muted">None affecting this opportunity.</p>`}
          ${firstSeen.length ? `<p class="prov" style="margin-top:10px">Evidence first entered the record</p>
            <div class="timeline">${firstSeen.map(f => `<div class="t-row"><span class="t-when mono">${esc(f)}</span><span class="t-what">first retained</span></div>`).join("")}</div>` : ""}
          <p class="prov" style="margin-top:10px">Known-then vs now is controlled by the As-of date in the header.</p>
        </section>
      </div>

      ${dispositionForm(id, dc.customer_disposition)}
      <div class="actions">
        <a class="act primary" href="/api/opportunities/${encodeURIComponent(id)}/brief?${cq()}${asofQuery()}&download=1" rel="noopener">Download brief</a>
        <button class="act" id="deliver-btn" type="button">Deliver brief…</button>
      </div>
      <div id="deliver-out" aria-live="polite"></div>`;
    wireOpportunity(id);
    note(""); focusMain();
  } catch (e) { note(e.message); main.innerHTML = empty("Could not load the decision view."); }
}

function evidenceBlock(oppId, e) {
  const blocked = (e.source_rights || {}).display === "BLOCKED";
  const isJson = /json/i.test(e.media_type || "");
  return `<details class="ev" data-ev="${esc(e.id)}">
    <summary>
      <span class="ev-src">${esc(dash(e.source_id))}</span>
      <span class="ev-ref">${esc(dash(e.source_ref || e.id))}</span>
      ${rightsPill(e.source_rights)}
    </summary>
    <div class="ev-body">
      ${blocked ? `<p class="ev-restricted">Rights-restricted — raw source withheld; provenance retained for audit.</p>` : ""}
      <div class="ev-chain">
        <span class="step">Source</span><span class="arr">→</span>
        <span class="step">Retrieved</span><span class="arr">→</span>
        <span class="step">Retained</span><span class="arr">→</span>
        <span class="step">Assessed</span>
      </div>
      <dl class="ev-prov-grid">
        <dt>Source</dt><dd>${esc(dash(e.source_id))}${e.media_type ? ` · <span class="mono">${esc(e.media_type)}</span> <span class="chip ${isJson ? "source" : "derived"}">${isJson ? "structured record" : "document"}</span>` : ""}</dd>
        <dt>Reference</dt><dd class="mono">${esc(dash(e.source_ref || e.id))}</dd>
        <dt>Published</dt><dd class="mono">${esc(dash(e.published_at))}</dd>
        <dt>Retrieved</dt><dd class="mono">${esc(dash(e.retrieved_at))}</dd>
        <dt>First seen</dt><dd class="mono">${esc(dash(e.first_seen_at))}</dd>
        <dt>Retention</dt><dd>${esc(dash(e.retention_tier))}</dd>
        <dt>Integrity</dt><dd><code>${esc(dash(e.content_sha256))}</code></dd>
        ${e.source_url ? `<dt>Official record</dt><dd><a href="${esc(e.source_url)}" rel="noopener">${esc(e.source_url)}</a></dd>` : ""}
      </dl>
    </div></details>`;
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
  if (fixed && me && me.customer) {
    org.textContent = me.customer.name || me.customer.id; field.hidden = true;
    updateLensStrip({ name: me.customer.name || me.customer.id });
  }
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
