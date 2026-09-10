"use strict";
// Pyrnova Material Changes — customer-facing read view (M22-A).
// Deterministic read model rendered from /api/material-changes. No fabrication, no client-side scoring.

const customerSel = document.querySelector("#customer");
const customerField = document.querySelector("#customer-field");
const orgEl = document.querySelector("#org");
const asof = document.querySelector("#asof");
const filters = document.querySelector("#filters");
const feed = document.querySelector("#feed");
const message = document.querySelector("#message");
const template = document.querySelector("#change");

const DISPOSITIONS = ["ALL", "THREAT", "OPPORTUNITY", "MONITORING"];
let active = "ALL";
let payload = null;

const esc = v => String(v ?? "").replace(/[&<>'"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));
const dash = v => (v === null || v === undefined || v === "" || v === "UNKNOWN") ? "Unknown" : v;
// Whole-dollar formatting for a known contract value; undefined (not a fact) is skipped by facts().
const money = v => (v === null || v === undefined) ? undefined : `$${Math.round(v).toLocaleString("en-US")}`;

function note(text) {
  message.hidden = !text;
  message.textContent = text || "";
}

// The active tenant. In authenticated customer mode it is fixed by the credential (Pyrnova.fixedCustomer);
// a dev/operator selector is only present when the server offered a switchable list. The customer is
// never taken from a user-editable field when the credential determines it.
function currentCustomer() {
  return Pyrnova.fixedCustomer() || (customerSel && customerSel.value) || null;
}

// Configure the masthead from the authenticated identity (§36): show the fixed organization, or a
// dev/operator selector, plus Sign Out when a credential is in use.
function applyIdentity(me) {
  const fixed = Pyrnova.fixedCustomer();
  const switchable = Pyrnova.switchable();
  const signout = document.querySelector("#signout");
  const consoleLink = document.querySelector("#console-link");
  if (fixed && me.customer) {
    orgEl.querySelector(".org-name").textContent = me.customer.name || me.customer.id;
    orgEl.hidden = false;
    customerField.hidden = true;
  } else if (switchable) {
    customerSel.innerHTML = switchable
      .map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join("");
    customerField.hidden = switchable.length === 0;
    orgEl.hidden = true;
    if (consoleLink) consoleLink.hidden = false;  // operator / local dev may reach the operator console
  }
  if (signout) { signout.hidden = !Pyrnova.getToken(); signout.onclick = () => Pyrnova.signOut(); }
}

async function load() {
  const customer = currentCustomer();
  if (!customer) { feed.innerHTML = '<div class="empty">No customer intelligence contexts are configured.</div>'; return; }
  const params = new URLSearchParams({ customer });
  if (asof.value) params.set("as_of", asof.value);
  const res = await Pyrnova.authFetch(`/api/material-changes?${params.toString()}`);
  payload = await res.json();
  if (!res.ok) { note(payload.error || "Request failed"); return; }
  note("");
  renderFilters();
  renderFeed();
}

function renderFilters() {
  const counts = payload.by_disposition || {};
  const total = payload.count || 0;
  filters.innerHTML = DISPOSITIONS.map(d => {
    const n = d === "ALL" ? total : (counts[d] || 0);
    return `<button data-d="${d}" aria-pressed="${active === d}">${d}<span class="n">${n}</span></button>`;
  }).join("");
  filters.querySelectorAll("button").forEach(b =>
    b.addEventListener("click", () => { active = b.dataset.d; renderFilters(); renderFeed(); }));
}

function facts(pairs) {
  return pairs.filter(([, v]) => v !== undefined)
    .map(([k, v, mono]) => `<dt>${esc(k)}</dt><dd class="${mono ? "mono" : ""}">${esc(dash(v))}</dd>`).join("");
}

function renderFeed() {
  const items = (payload.material_changes || [])
    .filter(m => active === "ALL" || m.disposition === active);
  feed.innerHTML = "";
  if (!items.length) {
    feed.innerHTML = `<div class="empty">No material changes for ${esc(payload.customer.name)}${active !== "ALL" ? ` under ${esc(active)}` : ""}${asof.value ? ` as of ${esc(asof.value)}` : ""}.</div>`;
    return;
  }
  items.forEach(renderChange);
}

function renderChange(m) {
  const node = template.content.cloneNode(true);
  const art = node.querySelector(".change");
  const disp = m.disposition.toLowerCase();
  art.classList.add(disp);

  const d = node.querySelector(".disposition");
  d.textContent = m.disposition;
  d.classList.add(disp);

  node.querySelector(".materiality").innerHTML = `Materiality<b>${esc(m.assessment.materiality)}</b>`;
  node.querySelector(".confidence").innerHTML = `Confidence<b>${esc(m.assessment.confidence)}</b>`;
  node.querySelector(".headline").textContent = m.title;

  node.querySelector(".why-detail").textContent = m.relevance.detail;
  node.querySelector(".relevance-basis").textContent = `[${m.relevance.basis.replace(/_/g, " ")}]`;

  // Observed fact vs Pyrnova assessment — kept structurally distinct (never flattened).
  const o = m.observed;
  node.querySelector(".pane.observed .facts").innerHTML = facts([
    ["Event", o.event_type],
    ["Affected", o.affected_entity],
    ["Program", o.affected_program, true],
    ["Agency", o.agency],
    // Opportunity-only distinctions (known contract value + expected-action deadline); undefined on
    // threats/monitoring, so facts() omits the rows there rather than showing "Unknown".
    ["Contract value", o.value_usd == null ? undefined : money(o.value_usd)],
    ["Expected action", o.expected_action_at == null ? undefined : o.expected_action_at, true],
    // For an opportunity the "event" is the future expected action shown above — don't repeat it here.
    ["Event time", o.expected_action_at == null ? o.event_time : undefined, true],
    ["Knowable at", o.observed_at, true],
    ["Origin", o.catalyst_class],
  ]);
  const a = m.assessment;
  node.querySelector(".pane.assessed .facts").innerHTML = facts([
    ["Mechanism", a.mechanism],
    ["Consequence", a.consequence],
    ["Affected value", a.affected_value_category],
    ["Materiality", a.materiality],
    ["Confidence", a.confidence],
    ["Engine", a.assessment_engine],
  ]);

  // M22-D §5: investigation navigation — reach the affected company/program without copying an id.
  const investigate = node.querySelector(".investigate");
  if (investigate && m.investigation) {
    const links = [];
    const co = m.investigation.company;
    if (co && co.ref) links.push(`<a href="/company?ref=${encodeURIComponent(co.ref)}">Investigate ${esc(co.name || co.ref)}</a>`);
    const pr = m.investigation.program;
    if (pr && pr.key) links.push(`<a href="/program?key=${encodeURIComponent(pr.key)}">Program ${esc(pr.key)}</a>`);
    (m.investigation.related_entities || []).forEach(r => {
      if (r.ref && (!co || r.ref !== co.ref)) links.push(`<a href="/company?ref=${encodeURIComponent(r.ref)}">${esc(r.ref)}</a>`);
    });
    if (links.length) {
      investigate.innerHTML = `<span class="why-label">Investigate</span>` + links.join("");
      investigate.hidden = false;
    }
  }

  const prop = node.querySelector(".propagation");
  if (m.propagation && m.propagation.is_propagated && (m.propagation.path || []).length) {
    const hops = m.propagation.path.map(h => `${esc(h.from_ref)} —${esc(h.relation || "REL")}→ ${esc(h.to_ref)}`).join("  ·  ");
    prop.innerHTML = `<span class="why-label">Propagated exposure</span> <span class="flow">${hops}</span> · depth ${esc(m.propagation.depth)} · ${esc(m.propagation.exposure_join_class || "join unknown")}`;
    prop.hidden = false;
  }

  const ev = m.evidence;
  const chips = [`${ev.evidence_count} evidence record(s)`,
                 `${ev.independent_source_count} authoritative source(s)`];
  let html = chips.map(c => `<span class="chip">${esc(c)}</span>`).join("");
  if (ev.raw_authoritative_bytes) html += `<span class="chip raw">raw archived bytes</span>`;
  if (ev.single_source) html += `<span class="chip single">single-source · not independently corroborated</span>`;
  if (ev.catalyst_class) html += `<span class="chip">catalyst ${esc(ev.catalyst_class)}</span>`;
  node.querySelector(".evidence").innerHTML = html;

  const unc = node.querySelector(".uncertainty");
  if ((m.uncertainty || []).length) {
    unc.innerHTML = `<span class="u-label">Uncertainty / falsifiers</span><ul>` +
      m.uncertainty.map(u => `<li>${esc(u.detail)}</li>`).join("") + `</ul>`;
    unc.hidden = false;
  }

  node.querySelector(".status").innerHTML =
    `Lifecycle <b>${esc(m.lifecycle_state)}</b> · Outcome <b>${esc(dash(m.outcome_state))}</b>`;

  // M22-C: per-customer first-seen provenance — three DISTINCT times, never collapsed.
  // Absent when the server has no customer-scoped store (backward compatible: render nothing).
  const fs = m.first_seen;
  const firstSeen = node.querySelector(".first-seen");
  const history = node.querySelector(".history");
  if (fs && fs.status === "MATERIALIZED") {
    let line =
      `Knowable <b>${esc(dash(fs.intelligence_observed_at))}</b>` +
      ` · Relevant to you <b>${esc(dash(fs.first_relevant_at))}</b>` +
      ` · Delivered <b>${esc(dash(fs.delivered_at))}</b>` +
      ` · v${esc(dash(fs.content_version))}`;
    if (fs.content_version > 1) line += ` <span class="fs-updated">updated (${esc(dash(fs.change_kind))})</span>`;
    firstSeen.innerHTML = line;
    firstSeen.hidden = false;
    history.hidden = false;
    history.addEventListener("click", () => toggleVersions(m.id, node));
  } else if (fs && fs.status === "PENDING_FANOUT") {
    firstSeen.innerHTML = `<span class="fs-pending">Not yet materialized</span>`;
    firstSeen.hidden = false;
  }

  // M22-B: customer review/lifecycle state — kept visually distinct from the SYSTEM lifecycle above.
  const review = m.review || { state: "NEW" };
  const stateEl = node.querySelector(".review-state");
  stateEl.textContent = review.state;
  stateEl.className = "review-state " + review.state.toLowerCase();
  const actionsEl = node.querySelector(".review-actions");
  actionsEl.innerHTML = REVIEW_ACTIONS.map(([label, action]) =>
    `<button type="button" data-action="${action}" data-id="${esc(m.id)}">${label}</button>`).join("");
  actionsEl.querySelectorAll("button").forEach(b =>
    b.addEventListener("click", () => recordReview(b.dataset.id, b.dataset.action)));

  const refs = node.querySelector(".refs");
  refs.textContent = JSON.stringify({ id: m.id, refs: m.refs, provenance: m.provenance }, null, 2);
  node.querySelector(".inspect").addEventListener("click", () => { refs.hidden = !refs.hidden; });

  feed.append(node);
}

// Minimal lifecycle actions behind the M22-A view (function before polish). Persist server-side.
const REVIEW_ACTIONS = [
  ["Mark reviewed", "MARK_REVIEWED"],
  ["Monitor", "MONITOR"],
  ["Record investigation", "RECORD_INVESTIGATION"],
  ["Dismiss", "DISMISS"],
  ["Resolve", "RESOLVE"],
  ["Reopen", "REOPEN"],
];

async function recordReview(changeId, action) {
  const customer = currentCustomer();
  if (!customer) return;
  // The audit actor is the authenticated actor (set server-side); never trusted from the client.
  const res = await Pyrnova.authFetch(`/api/material-changes/${encodeURIComponent(changeId)}/review`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ customer, action_type: action }),
  });
  const data = await res.json();
  if (!res.ok) { note(data.error || "Review action failed"); return; }
  note("");
  await load();  // reload so the persisted state (and counts) reflect the change across refresh/restart
}

// M22-C: version history for a materialized change. Fetched on demand, hidden until clicked
// (mirrors the .inspect/.refs reveal). Renders server-supplied rows verbatim — no client scoring.
async function toggleVersions(changeId, node) {
  const box = node.querySelector(".versions");
  if (!box.hidden) { box.hidden = true; return; }
  const customer = currentCustomer();
  if (!customer) return;
  const params = new URLSearchParams({ customer });
  const res = await Pyrnova.authFetch(`/api/material-changes/${encodeURIComponent(changeId)}/versions?${params.toString()}`);
  const data = await res.json();
  if (!res.ok) { note(data.error || "Version history unavailable"); return; }
  note("");
  const rows = data.versions || [];
  if (!rows.length) {
    box.innerHTML = `<div class="version-empty">No version history recorded.</div>`;
  } else {
    box.innerHTML = rows.map(v => {
      const snap = v.assessment_snapshot || {};
      return `<div class="version-row">` +
        `<span class="v-num">v${esc(dash(v.content_version))}</span>` +
        `<span class="v-kind">${esc(dash(v.change_kind))}</span>` +
        `<span class="v-assess">Materiality ${esc(dash(snap.materiality))} · Confidence ${esc(dash(snap.confidence))}</span>` +
        `<span class="v-outcome">Outcome ${esc(dash(v.outcome_state))}</span>` +
        `<span class="v-time mono">${esc(dash(v.delivered_at))}${v.last_updated_at ? ` · updated ${esc(v.last_updated_at)}` : ""}</span>` +
        `</div>`;
    }).join("");
  }
  box.hidden = false;
}

customerSel.addEventListener("change", load);
asof.addEventListener("change", load);

// Driven by the access layer: once the session is established (or dev mode confirmed), configure the
// identity and load the feed. Re-fires after a successful sign-in from the access gate.
document.addEventListener("pyrnova:ready", ev => {
  try { applyIdentity(ev.detail || {}); } catch (e) { /* identity is best-effort chrome */ }
  load().catch(err => note(err.message));
});
Pyrnova.init().catch(err => note(err.message));
