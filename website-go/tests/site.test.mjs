// State 1 acceptance tests + Revision B doctrine invariants.
// Node standard library test runner only. Run with: node --test
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { renderPage, routes, nav } from '../src/site.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const assetsDir = join(here, '..', 'assets');
const required = ['/', '/intelligence/', '/method/', '/trust/', '/research/', '/company/', '/evaluate/'];
const allHtml = routes.map((r) => renderPage(r, {})).join('\n');

test('all required public routes exist', () => {
  for (const r of required) assert.ok(routes.includes(r), `missing route ${r}`);
});

test('primary navigation matches locked authority', () => {
  assert.deepEqual(nav.map((n) => n.label), ['INTELLIGENCE', 'METHOD', 'TRUST', 'RESEARCH', 'COMPANY']);
});

test('every route renders a complete document with masthead, main and footer', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    assert.ok(html.startsWith('<!doctype html>'), `${r} not a full document`);
    assert.ok(html.includes('<main id="main">'), `${r} missing main`);
    assert.ok(html.includes('site-footer'), `${r} missing footer`);
    assert.ok(html.includes('class="masthead"'), `${r} missing masthead`);
    assert.ok(!/lorem ipsum/i.test(html), `${r} contains placeholder copy`);
  }
});

test('home carries the locked message, both CTAs and a Material Change specimen in first view', () => {
  const html = renderPage('/', {});
  assert.ok(html.includes('Know what changed.') && html.includes('Know what it changes.'));
  assert.ok(html.includes('Evaluate Pyrnova'));
  assert.ok(html.includes('See the intelligence'));
  // Product specimen present before any section boundary (first viewport).
  const heroEnd = html.indexOf('class="section"');
  const hero = html.slice(0, heroEnd);
  assert.ok(/class="spec /.test(hero), 'home hero missing Material Change specimen');
  assert.ok(/disposition/.test(hero) && /pane observed/.test(hero) && /Pyrnova assessment/.test(hero),
    'home specimen missing product grammar');
});

test('canonical mark is referenced (no invented logo file)', () => {
  for (const r of routes) {
    assert.ok(renderPage(r, {}).includes('/pyrnova-mark.svg'), `${r} does not use the canonical mark`);
  }
  const mark = readFileSync(join(assetsDir, 'pyrnova-mark.svg'), 'utf8');
  // Canonical cyan signal from docs/brand/notion, and no fabricated single-letter mark.
  assert.ok(mark.includes('25cfe8') || mark.toLowerCase().includes('25cfe8'), 'mark missing canonical cyan');
});

test('ZERO em dash characters in public website source and rendered output', () => {
  const EMDASH = String.fromCharCode(0x2014); // U+2014, built to keep this file em-dash free
  const files = [
    join(here, '..', 'src', 'site.mjs'),
    join(assetsDir, 'site.css'),
    ...readdirSync(assetsDir).filter((f) => f.endsWith('.svg')).map((f) => join(assetsDir, f)),
  ];
  let count = 0;
  const offenders = [];
  for (const f of files) {
    const c = readFileSync(f, 'utf8').split(EMDASH).length - 1;
    if (c) offenders.push(`${f}:${c}`);
    count += c;
  }
  const rendered = allHtml.split(EMDASH).length - 1;
  count += rendered;
  if (rendered) offenders.push(`rendered:${rendered}`);
  assert.equal(count, 0, `em dash count must be 0; offenders: ${offenders.join(', ')}`);
});

test('NO page contains any form, input, textarea, select or submit control (intake disabled)', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    assert.ok(!/<form\b/i.test(html), `${r} contains a <form>`);
    assert.ok(!/<input\b/i.test(html), `${r} contains an <input>`);
    assert.ok(!/<textarea\b/i.test(html), `${r} contains a <textarea>`);
    assert.ok(!/<select\b/i.test(html), `${r} contains a <select>`);
    assert.ok(!/type=["']submit["']/i.test(html), `${r} contains a submit control`);
  }
});

test('NO page ships JavaScript or hidden collection hooks', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    assert.ok(!/<script\b/i.test(html), `${r} contains a <script> tag`);
    assert.ok(!/\son[a-z]+=/i.test(html), `${r} contains an inline event handler`);
    assert.ok(!/fetch\(|XMLHttpRequest|sendBeacon/i.test(html), `${r} contains a collection call`);
  }
});

test('NO page exposes mailto, tel, api endpoint or booking/forms provider', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    assert.ok(!/mailto:/i.test(html), `${r} contains a mailto link`);
    assert.ok(!/tel:/i.test(html), `${r} contains a tel link`);
    assert.ok(!/\/api\//i.test(html), `${r} references an api endpoint`);
    assert.ok(!/calendly|cal\.com|savvycal|hubspot|typeform|formspree/i.test(html), `${r} references a booking/forms provider`);
  }
});

test('evaluate page states intake is not open, shows output specimen, offers no submission', () => {
  const html = renderPage('/evaluate/', {});
  assert.ok(/not open/i.test(html), 'evaluate must state intake is not open');
  assert.ok(/class="spec /.test(html), 'evaluate must show an output specimen');
  assert.ok(!/<form\b/i.test(html) && !/<input\b/i.test(html), 'evaluate must have no form/input');
});

test('specimens are labelled synthetic and never claimed as live production', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    if (/class="spec /.test(html)) {
      assert.ok(/SYNTHETIC SPECIMEN/i.test(html), `${r} has an unlabelled specimen`);
    }
  }
});

test('no unsupported security or compliance certification claims', () => {
  for (const r of routes) {
    const html = renderPage(r, {});
    for (const term of ['SOC 2', 'FedRAMP', 'ISO 27001', 'CMMC']) {
      if (html.includes(term)) assert.ok(r === '/trust/', `${r} mentions ${term} outside the Trust disclaimer`);
    }
  }
});
