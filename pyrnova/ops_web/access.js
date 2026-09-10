"use strict";
// Pyrnova access layer (M22-F). Establishes the authenticated organization for the customer-facing
// product and carries the credential on every API call. The customer is NEVER chosen from a dropdown or
// a URL parameter when the server can determine it from the credential — tenant identity comes from the
// authenticated actor. The credential is held in sessionStorage (cleared when the tab closes — the
// conservative choice for this controlled design-customer stage) and is never placed in a URL.

const Pyrnova = (() => {
  const KEY = "pyrnova.credential";
  let me = null;

  const getToken = () => { try { return sessionStorage.getItem(KEY) || ""; } catch { return ""; } };
  const setToken = t => { try { sessionStorage.setItem(KEY, t); } catch {} };
  const clearToken = () => { try { sessionStorage.removeItem(KEY); } catch {} };

  // fetch wrapper: attaches the bearer credential; on 401 it clears the stale credential and returns to
  // the access screen (expired/revoked credential → Authentication required).
  async function authFetch(url, opts = {}) {
    const headers = Object.assign({}, opts.headers || {});
    const token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch(url, Object.assign({}, opts, { headers }));
    if (res.status === 401) { clearToken(); showGate("Authentication required."); throw new Error("unauthenticated"); }
    return res;
  }

  function gateEl() {
    let g = document.querySelector("#access-gate");
    if (g) return g;
    g = document.createElement("div");
    g.id = "access-gate";
    g.hidden = true;
    g.innerHTML =
      '<div class="access-card">' +
      '<div class="access-brand"><span class="mark">PYRNOVA</span></div>' +
      '<h1>Access</h1>' +
      '<p class="access-msg" id="access-msg">Authentication required.</p>' +
      '<form id="access-form">' +
      '<label>Credential<input id="access-credential" type="password" autocomplete="off" spellcheck="false" required></label>' +
      '<button type="submit">Access</button>' +
      '</form></div>';
    document.body.appendChild(g);
    g.querySelector("#access-form").addEventListener("submit", async e => {
      e.preventDefault();
      const val = g.querySelector("#access-credential").value.trim();
      if (!val) return;
      setToken(val);
      const ok = await refreshMe();
      if (ok && me && me.authenticated) { hideGate(); document.dispatchEvent(new CustomEvent("pyrnova:ready", { detail: me })); }
      else { clearToken(); showGate("Access denied — check your credential."); }
    });
    return g;
  }

  function showGate(msg) {
    const g = gateEl();
    if (msg) g.querySelector("#access-msg").textContent = msg;
    g.hidden = false;
    const inp = g.querySelector("#access-credential");
    if (inp) { inp.value = ""; inp.focus(); }
  }
  function hideGate() { const g = document.querySelector("#access-gate"); if (g) g.hidden = true; }

  async function refreshMe() {
    try {
      const res = await authFetch("/api/me");
      me = await res.json();
      return true;
    } catch { return false; }
  }

  function signOut() {
    clearToken(); me = null;
    showGate("Signed out.");
  }

  // Establish the session, then hand control back via the pyrnova:ready event with the /api/me payload.
  async function init() {
    await refreshMe();
    if (me && me.require_auth && !me.authenticated) { showGate("Authentication required."); return; }
    document.dispatchEvent(new CustomEvent("pyrnova:ready", { detail: me }));
  }

  // The active customer for a tenant-scoped read. In authenticated customer mode this is fixed by the
  // credential (no switching). In local dev (no auth) or operator mode a selection may be supplied.
  function fixedCustomer() { return me && me.customer ? me.customer.id : null; }
  function switchable() { return me && Array.isArray(me.customers) ? me.customers : null; }

  return { authFetch, init, signOut, showGate, hideGate,
           get me() { return me; }, fixedCustomer, switchable, getToken };
})();
