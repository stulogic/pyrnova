"use strict";
// Pyrnova Material Changes — customer-facing read view (M22-A).
// Deterministic read model rendered from /api/material-changes. No fabrication, no client-side scoring.

const customerSel = document.querySelector("#customer");
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

function note(text) {
  message.hidden = !text;
  message.textContent = text || "";
}

async function loadCustomers() {
  const res = await fetch("/api/customers");
  const data = await res.json();
  customerSel.innerHTML = (data.customers || [])
    .map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join("");
}

async function load() {
  const customer = customerSel.value;
  if (!customer) { feed.innerHTML = '<div class="empty">No customer intelligence contexts are configured.</div>'; return; }
  const params = new URLSearchParams({ customer });
  if (asof.value) params.set("as_of", asof.value);
  const res = await fetch(`/api/material-changes?${params.toString()}`);
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
    ["Event time", o.event_time, true],
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
  const customer = customerSel.value;
  if (!customer) return;
  const res = await fetch(`/api/material-changes/${encodeURIComponent(changeId)}/review`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ customer, action_type: action, actor: "operator" }),
  });
  const data = await res.json();
  if (!res.ok) { note(data.error || "Review action failed"); return; }
  note("");
  await load();  // reload so the persisted state (and counts) reflect the change across refresh/restart
}

customerSel.addEventListener("change", load);
asof.addEventListener("change", load);

loadCustomers()
  .then(load)
  .catch(err => note(err.message));
