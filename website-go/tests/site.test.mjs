// State 1 acceptance tests: intake-disabled invariants and route completeness.
// Node standard library test runner only. Run with: node --test
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderPage, routes, nav } from '../src/site.mjs';

const required = ['/', '/intelligence/', '/method/', '/trust/', '/research/', '/company/', '/evaluate/'];

test('all required public routes exist', () => {
  for (const r of required) assert.ok(routes.includes(r), `missing route ${r}`);
});

test('primary navigation matches locked authority', () => {
  assert.deepEqual(
    nav.map((n) => n.label),
    ['INTELLIGENCE', 'METHOD', 'TRUST', 'RESEARCH', 'COMPANY']
  );
});

test('every route renders complete HTML with header, main and footer', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    assert.ok(html.startsWith('<!doctype html>'), `${r} not a full document`);
    assert.ok(html.includes('<main id="main">'), `${r} missing main`);
    assert.ok(html.includes('site-footer'), `${r} missing footer`);
    assert.ok(!/lorem ipsum/i.test(html), `${r} contains placeholder copy`);
  }
});

test('home carries the locked primary message and both CTAs', () => {
  const html = renderPage('/', {});
  assert.ok(html.includes('Know what changed. Know what it changes.'));
  assert.ok(html.includes('Evaluate Pyrnova'));
  assert.ok(html.includes('See the intelligence'));
});

test('NO page contains any form, input, textarea, or submit control (intake disabled)', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    assert.ok(!/<form\b/i.test(html), `${r} contains a <form>`);
    assert.ok(!/<input\b/i.test(html), `${r} contains an <input>`);
    assert.ok(!/<textarea\b/i.test(html), `${r} contains a <textarea>`);
    assert.ok(!/<select\b/i.test(html), `${r} contains a <select>`);
    assert.ok(!/type=["']submit["']/i.test(html), `${r} contains a submit control`);
    assert.ok(!/enctype=/i.test(html), `${r} contains a form encoding`);
  }
});

test('NO page ships JavaScript or hidden collection hooks', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    assert.ok(!/<script\b/i.test(html), `${r} contains a <script> tag`);
    assert.ok(!/\bon[a-z]+=/i.test(html), `${r} contains an inline event handler`);
    assert.ok(!/fetch\(|XMLHttpRequest|navigator\.sendBeacon/i.test(html), `${r} contains a collection call`);
  }
});

test('NO page exposes a mailto, tel, or evaluation intake endpoint', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    assert.ok(!/mailto:/i.test(html), `${r} contains a mailto link`);
    assert.ok(!/tel:/i.test(html), `${r} contains a tel link`);
    assert.ok(!/\/api\//i.test(html), `${r} references an api endpoint`);
    assert.ok(!/calendly|cal\.com|savvycal|hubspot|typeform|formspree/i.test(html), `${r} references a booking/forms provider`);
  }
});

test('evaluate page states intake is not open and offers no submission', () => {
  const html = renderPage('/evaluate/', {});
  assert.ok(/not open yet/i.test(html), 'evaluate must state intake is not open');
  assert.ok(!/<form\b/i.test(html) && !/<input\b/i.test(html), 'evaluate must have no form/input');
});

test('no unsupported security or compliance certification claims', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    // These strings only ever appear negated on the Trust page ("do not claim ...").
    for (const term of ['SOC 2', 'FedRAMP', 'ISO 27001', 'CMMC']) {
      if (html.includes(term)) {
        assert.ok(
          r === '/trust/',
          `${r} mentions ${term} outside the Trust disclaimer`
        );
      }
    }
    assert.ok(!/row-level security(?!\.?<\/p>| controls)/i.test(html) || r === '/trust/', `${r} claims RLS`);
  }
});
