"use strict";
// Rendered-proof harness: executes the REAL pyrnova/ops_web/product.js render functions against the
// REAL captured API JSON, through a minimal DOM shim, and writes self-contained HTML snapshots
// (real markup + real CSS inlined). No fabricated data — every payload is a live server capture.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const WEB = "/Users/stu/Documents/Pyrnova-intl/pyrnova/ops_web";
const SC = __dirname;
const OUT = "/Users/stu/Documents/Pyrnova-intl/docs/frontend/render";
fs.mkdirSync(OUT, { recursive: true });

const lens = JSON.parse(fs.readFileSync(path.join(SC, "lens.json")));
const opps = JSON.parse(fs.readFileSync(path.join(SC, "opps.json")));
const decision = JSON.parse(fs.readFileSync(path.join(SC, "decision.json")));
const oid = fs.readFileSync(path.join(SC, "oid.txt"), "utf8").trim();

// --- minimal DOM shim (only what the pure render functions touch) ---
const cache = new Map();
function mkEl() {
  return {
    innerHTML: "", textContent: "", hidden: false, value: "",
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    style: {}, dataset: {},
    focus() {}, blur() {}, addEventListener() {}, removeEventListener() {},
    setAttribute() {}, getAttribute() { return null; },
    querySelector() { return mkEl(); }, querySelectorAll() { return []; },
    appendChild() {}, append() {}, cloneNode() { return mkEl(); },
  };
}
function q(sel) { if (!cache.has(sel)) cache.set(sel, mkEl()); return cache.get(sel); }

const routeJson = url => url.includes("/decision") ? decision
  : url.includes("/api/opportunities") ? opps
  : url.includes("/api/lens") ? lens : {};

const sandbox = {
  console,
  location: { hash: "#/lens" },
  document: {
    querySelector: q, querySelectorAll: () => [], addEventListener() {},
    createElement: mkEl, body: mkEl(),
  },
  window: { addEventListener() {} },
  CustomEvent: class { constructor(t, o) { this.type = t; this.detail = o && o.detail; } },
  Pyrnova: {
    authFetch: async (url) => ({ ok: true, status: 200, json: async () => routeJson(url) }),
    init: async () => {}, signOut() {}, fixedCustomer: () => null,
    switchable: () => (lens.customer ? [lens.customer] : null), getToken: () => "",
  },
};
sandbox.global = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(WEB, "product.js"), "utf8"), sandbox, { filename: "product.js" });

const css = ["system.css", "access.css", "product.css"]
  .map(f => `/* ${f} */\n` + fs.readFileSync(path.join(WEB, f), "utf8")).join("\n\n");

const masthead = `
  <header class="masthead" role="banner">
    <div class="brand"><span class="mark">PYRNOVA</span> <span class="tag">Live Intelligence</span></div>
    <nav class="topnav" aria-label="Primary">
      <a href="#/lens" aria-current="page">Lens</a><a href="#/opportunities">Opportunities</a>
      <a href="#/search">Search</a><a href="#">Material Changes</a>
    </nav>
    <div class="ident"><span class="org">Torch Technologies</span>
      <label class="asof-field">As&nbsp;of <input type="date"></label></div>
  </header>`;

function page(title, mainHtml, lensStripHtml) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title>
<style>${css}</style></head><body>
${masthead}
<div class="lens-strip" role="region" aria-label="Customer Lens context"${lensStripHtml ? "" : " hidden"}>${lensStripHtml || ""}</div>
<main id="main" tabindex="-1" role="main">${mainHtml}</main>
<footer class="foot">Pyrnova composes source facts, Pyrnova-derived intelligence, and customer decisions — each labelled. UNKNOWN is a legitimate state; source-rights restrictions fail closed.</footer>
</body></html>`;
}

(async () => {
  const captures = [
    ["lens", "Customer Lens", sandbox.viewLens],
    ["opportunities", "Opportunities", sandbox.viewOpportunities],
    ["decision", "Decision View", () => sandbox.viewOpportunity(oid)],
  ];
  for (const [name, title, fn] of captures) {
    q("#main").innerHTML = "";
    await fn();
    const mainHtml = q("#main").innerHTML;
    const strip = q("#lens-strip");
    const stripHtml = strip.hidden ? "" : strip.innerHTML;
    fs.writeFileSync(path.join(OUT, name + ".html"), page("Pyrnova — " + title, mainHtml, stripHtml));
    console.log(`wrote ${name}.html  (main ${mainHtml.length}b, lens-strip ${stripHtml.length}b)`);
  }
})();
