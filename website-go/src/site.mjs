// Pyrnova public website content - Revision B.
// WEBSITE GO / OUTREACH INTAKE DISABLED (State 1).
//
// Doctrine followed:
//  - Corporate posture & brand (D-054): discretion + intelligence + competence + control;
//    dark, architectural, expensive without ostentation; canonical cyan as signal only.
//  - Product Language Authority (D-041): functional, precise, operational copy; no slogans,
//    no rhetorical headings, no generic startup prose. ZERO em dash characters in public copy.
//  - Reuses the canonical product grammar from pyrnova/ops_web (Material Change objects:
//    disposition / materiality / confidence / observed fact / Pyrnova assessment / why it
//    matters / evidence / uncertainty / AS OF / provenance). The website is a controlled
//    static window into the product; all specimens are clearly labelled synthetic.
//  - Canonical mark/wordmark only (docs/brand/notion). No invented logo.

const MARK = '<img class="brandmark" src="/pyrnova-mark.svg" alt="" width="26" height="26">';

export const nav = [
  { label: 'INTELLIGENCE', path: '/intelligence/' },
  { label: 'METHOD', path: '/method/' },
  { label: 'TRUST', path: '/trust/' },
  { label: 'RESEARCH', path: '/research/' },
  { label: 'COMPANY', path: '/company/' },
];
const evaluatePath = '/evaluate/';

function masthead(path, module) {
  const links = nav
    .map((n) => `<a href="${n.path}"${path === n.path ? ' aria-current="page"' : ''}>${n.label}</a>`)
    .join('');
  const evalCurrent = path === evaluatePath ? ' aria-current="page"' : '';
  return `<header class="masthead"><a class="brand" href="/" aria-label="Pyrnova home">${MARK}<span class="mark">PYRNOVA</span><span class="module">${module}</span></a><div class="nav-wrap"><nav class="primary" aria-label="Sections">${links}</nav><a class="nav-cta" href="${evaluatePath}"${evalCurrent}><span class="dot" aria-hidden="true"></span>Evaluate</a></div></header>`;
}

function footer() {
  const links = [...nav, { label: 'EVALUATE', path: evaluatePath }]
    .map((n) => `<a href="${n.path}">${n.label}</a>`)
    .join('');
  return `<footer class="site-footer"><div class="footer-inner"><div class="f-brand">${MARK.replace('width="26" height="26"', 'width="24" height="24"')}<span class="mark">PYRNOVA</span></div><nav aria-label="Footer navigation">${links}</nav></div><p class="f-note">Company-specific consequence intelligence for federal contractors. This informational website does not collect personal data and does not accept evaluation submissions. Specimens shown are synthetic and illustrate product structure; they are not live production output and represent no customer or source event. Nightglass is Pyrnova's internal research and demonstration corpus.</p></footer>`;
}

// ---- Material Change specimen (canonical .change grammar) ----
function facts(rows) {
  return `<dl class="facts">${rows
    .map(([dt, dd, mono]) => `<dt>${dt}</dt><dd${mono ? ' class="mono"' : ''}>${dd}</dd>`)
    .join('')}</dl>`;
}
function spec(d) {
  const caption = d.caption || 'MATERIAL CHANGE';
  const badges = `<div class="badges"><span class="badge" title="Severity of the economic consequence if the assessment holds">Materiality<b>${d.materiality}</b></span><span class="badge" title="How strongly retained evidence supports the assessment">Confidence<b>${d.confidence}</b></span></div>`;
  const evidence = `<div class="evidence"><span class="label">Evidence</span>${d.evidence
    .map((e) => `<span class="chip${e.cls ? ' ' + e.cls : ''}">${e.text}</span>`)
    .join('')}</div>`;
  const uncertainty = d.falsifiers
    ? `<div class="uncertainty"><span class="u-label">Would weaken or falsify</span><ul>${d.falsifiers
        .map((f) => `<li>${f}</li>`)
        .join('')}</ul></div>`
    : '';
  return `<article class="spec ${d.disposition}"><div class="spec-caption"><span>${caption}</span><span class="synthetic">SYNTHETIC SPECIMEN / NIGHTGLASS</span></div><div class="spec-body"><div class="spec-top"><span class="disposition ${d.disposition}">${d.dispoLabel}</span>${badges}</div><h3 class="headline">${d.headline}</h3><div class="why"><span class="why-label">Why it matters</span><span class="why-detail">${d.why}</span><span class="relevance-basis">${d.relevance}</span></div><div class="split"><div class="pane observed"><span class="pane-label">Observed fact</span>${facts(d.observed)}</div><div class="pane assessed"><span class="pane-label">Pyrnova assessment</span>${facts(d.assessed)}</div></div>${evidence}${uncertainty}<div class="spec-foot"><span>Point in time <b class="asof">AS OF ${d.asof}</b></span><span class="prov">${d.provenance}</span></div></div></article>`;
}

// Reusable specimens (synthetic; federal-contracting domain; mirror real product structure).
const specRecompete = {
  disposition: 'threat',
  dispoLabel: 'THREAT',
  materiality: 'High',
  confidence: 'Moderate',
  headline: 'A sustainment requirement is consolidated into a multiple-award services vehicle.',
  why: 'Direct-award pursuit basis weakens for a subject supplier that lacks access to the vehicle.',
  relevance: 'WATCHED PROGRAM',
  observed: [
    ['Source event', 'Acquisition strategy notice'],
    ['Program', 'Program of record sustainment', true],
    ['Vehicle', 'Multiple-award IDIQ', true],
    ['Published', '2026-09-08', true],
  ],
  assessed: [
    ['Exposure path', 'Vehicle access gap'],
    ['Consequence', 'Route to market shift'],
    ['Prior thesis', 'Direct pursuit'],
    ['Materiality band', 'High', true],
  ],
  evidence: [
    { text: 'notice:SAM 3 refs', cls: 'raw' },
    { text: 'corroboration: single source', cls: 'single' },
    { text: 'program crosswalk', cls: '' },
  ],
  falsifiers: [
    'A separate direct-award path is retained for the requirement.',
    'The engineering scope leaves the consolidated vehicle.',
  ],
  asof: '2026-09-11',
  provenance: 'ev:9f2a · src:acq-notice',
};
const specTeaming = {
  disposition: 'opportunity',
  dispoLabel: 'OPPORTUNITY',
  materiality: 'Moderate',
  confidence: 'Moderate',
  headline: 'A prime adds a task order aligned to a subject supplier capability.',
  why: 'A teaming position becomes commercially significant where direct access is limited.',
  relevance: 'CAPABILITY MATCH',
  observed: [
    ['Source event', 'Award modification'],
    ['Prime', 'Incumbent integrator'],
    ['Scope added', 'Modeling and simulation'],
    ['Observed', '2026-09-09', true],
  ],
  assessed: [
    ['Exposure path', 'Subcontract relationship'],
    ['Consequence', 'Pursuit reprioritization'],
    ['Confidence basis', 'One authoritative source'],
    ['Materiality band', 'Moderate', true],
  ],
  evidence: [
    { text: 'award:USASpending', cls: 'raw' },
    { text: 'corroboration: single source', cls: 'single' },
  ],
  falsifiers: ['The added scope is self-performed by the prime.'],
  asof: '2026-09-11',
  provenance: 'ev:41c7 · src:award-mod',
};
const specBudget = {
  disposition: 'monitoring',
  dispoLabel: 'MONITORING',
  materiality: 'Moderate',
  confidence: 'Low',
  headline: 'A budget line supporting a watched program is marked for restructuring.',
  why: 'Timing and scope of the watched program may move; no commercial consequence is established yet.',
  relevance: 'WATCHED PROGRAM',
  observed: [
    ['Source event', 'Budget justification change'],
    ['Instrument', 'Program element', true],
    ['Direction', 'Restructure, amount unresolved'],
    ['Observed', '2026-09-10', true],
  ],
  assessed: [
    ['Exposure path', 'Timing uncertainty'],
    ['Consequence', 'Unresolved'],
    ['State', 'Monitoring'],
    ['Materiality band', 'Moderate', true],
  ],
  evidence: [{ text: 'doc:budget-just', cls: 'raw' }, { text: 'corroboration: single source', cls: 'single' }],
  falsifiers: ['Later evidence restores the original program timing and amount.'],
  asof: '2026-09-11',
  provenance: 'ev:7b10 · src:budget-doc',
};

// ---- deterministic environmental graphics ----
function heroField() {
  const nodes = [
    [128, 300, 2.2],
    [232, 96, 1.8],
    [360, 356, 2],
    [470, 150, 2.4],
    [96, 168, 1.6],
  ];
  const dots = nodes
    .map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" fill="#333c47"/>`)
    .join('');
  return `<div class="hero-field" aria-hidden="true"><svg viewBox="0 0 600 460" preserveAspectRatio="xMidYMid slice" fill="none">
<g stroke="#1a2129" stroke-width="1">
${Array.from({ length: 7 }, (_, i) => `<line x1="${i * 100}" y1="0" x2="${i * 100}" y2="460"/>`).join('')}
${Array.from({ length: 5 }, (_, i) => `<line x1="0" y1="${i * 100 + 30}" x2="600" y2="${i * 100 + 30}"/>`).join('')}
</g>
<g stroke="#2b3a45" stroke-width="1" fill="none">
<circle cx="452" cy="232" r="150"/>
<circle cx="452" cy="232" r="96"/>
<ellipse cx="300" cy="240" rx="288" ry="130" transform="rotate(-14 300 240)"/>
</g>
<path class="trace-path" d="M452 232 L300 240 L232 96" stroke="#25cfe8" stroke-width="1.4" fill="none" pathLength="1"/>
${dots}
<circle class="sig-node" cx="452" cy="232" r="4" fill="#25cfe8"/>
<circle cx="452" cy="232" r="9" stroke="#25cfe8" stroke-width="1" fill="none" opacity="0.5"/>
<line x1="452" y1="208" x2="452" y2="220" stroke="#25cfe8" stroke-width="1.4"/>
<line x1="452" y1="244" x2="452" y2="256" stroke="#25cfe8" stroke-width="1.4"/>
</svg></div>`;
}

function signalTrace() {
  const stages = ['SIGNAL', 'MATERIAL CHANGE', 'EXPOSURE', 'CONSEQUENCE', 'EVIDENCE', 'UNCERTAINTY', 'AS OF', 'DECISION'];
  const n = stages.length;
  const pad = 70;
  const w = 1120;
  const step = (w - pad * 2) / (n - 1);
  const y = 30;
  const circles = stages
    .map((s, i) => {
      const x = pad + i * step;
      const isSig = i === 0;
      return `<circle cx="${x}" cy="${y}" r="${isSig ? 5 : 3.5}" fill="${isSig ? '#25cfe8' : '#8fa9c9'}"${isSig ? ' class="sig-node"' : ''}/><text x="${x}" y="60" text-anchor="middle" font-family="ui-monospace, Menlo, monospace" font-size="10" letter-spacing="1" fill="#97a2b0">${s}</text>`;
    })
    .join('');
  return `<div class="signal-trace" aria-hidden="true"><svg viewBox="0 0 ${w} 72" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto">
<line x1="${pad}" y1="${y}" x2="${w - pad}" y2="${y}" stroke="#262d36" stroke-width="1"/>
<path class="trace-path" d="M${pad} ${y} L${w - pad} ${y}" stroke="#25cfe8" stroke-width="1.6" fill="none" pathLength="1"/>
${circles}
</svg></div>`;
}

function temporalAxis() {
  return `<div class="temporal"><svg viewBox="0 0 760 190" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Point-in-time availability: evidence available before an AS OF cutoff is eligible for the earlier view; later evidence is excluded.">
<line x1="40" y1="120" x2="720" y2="120" stroke="#333c47" stroke-width="1"/>
<g font-family="ui-monospace, Menlo, monospace" font-size="11" fill="#97a2b0">
<text x="40" y="150">t0</text><text x="560" y="150" text-anchor="middle">AS OF cutoff</text><text x="720" y="150" text-anchor="end">now</text>
</g>
<line x1="380" y1="70" x2="380" y2="140" stroke="#25cfe8" stroke-width="1.4"/>
<text x="380" y="58" text-anchor="middle" font-family="ui-monospace, Menlo, monospace" font-size="10" letter-spacing="1" fill="#25cfe8">AS OF</text>
<g fill="#7fa8c9"><circle cx="120" cy="120" r="4"/><circle cx="210" cy="120" r="4"/><circle cx="300" cy="120" r="4"/></g>
<text x="120" y="102" font-family="ui-monospace, Menlo, monospace" font-size="9" fill="#6a7481">eligible</text>
<g fill="#6a7481" opacity="0.6"><circle cx="470" cy="120" r="4"/><circle cx="560" cy="120" r="4"/><circle cx="650" cy="120" r="4"/></g>
<text x="560" y="102" text-anchor="middle" font-family="ui-monospace, Menlo, monospace" font-size="9" fill="#6a7481">excluded from earlier view</text>
</svg></div>`;
}

const closing = `<section class="closing"><div><h2>Evaluate Pyrnova against a real external change affecting your organization.</h2><p>See the company-specific consequence, the evidence behind it, the uncertainty it keeps visible and the point in time it was knowable.</p></div><a class="button" href="${evaluatePath}">Evaluate Pyrnova</a></section>`;

// ---------------- pages ----------------
const pages = {
  '/': {
    module: 'Public Overview',
    title: 'Pyrnova - Company-specific consequence intelligence',
    description:
      'Pyrnova detects consequential external change, traces its effect on a specific organization, and shows the evidence, uncertainty and point-in-time basis behind each conclusion.',
    body: `<section class="hero">${heroField()}<div class="hero-copy"><span class="status-line"><span class="live" aria-hidden="true"></span>Phase 1 · Material Changes · Illustrative specimen</span><h1>Know what changed.<br><span class="l2">Know what it changes.</span></h1><p class="lead">Pyrnova detects consequential external change, traces its effect on a specific organization, and shows the evidence, uncertainty and point-in-time basis behind each conclusion.</p><div class="cta-row"><a class="button" href="${evaluatePath}">Evaluate Pyrnova</a><a class="button secondary" href="/intelligence/">See the intelligence</a></div></div><div class="hero-spec">${spec(specRecompete)}</div></section>
    <section class="section"><div class="sec-head"><h2>Signal to consequence</h2><span class="sec-meta">The path behind every Material Change</span></div><p class="sec-intro">A change in the outside world becomes commercially meaningful only when it is connected to a specific organization. Pyrnova traces that path and keeps the basis inspectable at each step.</p>${signalTrace()}<div class="chain" style="margin-top:18px">${[
      ['01', 'Signal', 'A consequential external change is observed and its source record retained.'],
      ['02', 'Material change', 'The change is structured as an object, separating observed fact from assessment.'],
      ['03', 'Exposure', 'The change is connected to a specific organization by a deterministic relevance basis.'],
      ['04', 'Consequence', 'The company-specific commercial consequence is derived, with materiality and confidence kept orthogonal.'],
    ]
      .map((c) => `<div class="node"><span class="n-step">${c[0]}</span><h3>${c[1]}</h3><p>${c[2]}</p></div>`)
      .join('')}</div></section>
    <section class="section"><div class="sec-head"><h2>What the record contains</h2></div><div class="grid-3">${[
      ['Observed vs assessed', 'The source fact and the Pyrnova assessment are kept in separate structured blocks and never flattened together.'],
      ['Materiality and confidence', 'Severity of consequence and strength of evidence are reported as orthogonal bands, not a single score.'],
      ['Point-in-time truth', 'Each conclusion carries an AS OF. Later evidence is excluded from an earlier view; prior state is preserved.'],
      ['Evidence by reference', 'Statements cite retained evidence by identifier, with conservative treatment of single-source corroboration.'],
      ['Customer relevance', 'Relevance is established by an explicit basis such as watched program or capability match, not topical similarity.'],
      ['Uncertainty and falsifiers', 'What is unresolved is stated, along with the evidence that would weaken or falsify the conclusion.'],
    ]
      .map((c) => `<div class="obj"><span class="obj-label">${c[0]}</span><p>${c[1]}</p></div>`)
      .join('')}</div></section>${closing}`,
  },

  '/intelligence/': {
    module: 'Intelligence',
    title: 'Intelligence - Pyrnova',
    description:
      'A controlled static view of the Pyrnova intelligence surface: Material Changes, company exposure, resolution and evidence, using synthetic specimens.',
    body: `<header class="page-head"><span class="label accent">Intelligence</span><h1>The closest public view of using Pyrnova.</h1><p class="lead">The surfaces below use the product's own structure with synthetic specimens. They are not live production output and represent no customer or source event.</p></header>
    <section class="section"><div class="sec-head"><h2>Material Changes</h2><span class="sec-meta">What materially changed, and why it matters to this organization</span></div><div class="grid-2">${spec(specRecompete)}${spec(specTeaming)}</div><div style="margin-top:18px">${spec(specBudget)}</div></section>
    <section class="section"><div class="sec-head"><h2>Company exposure</h2><span class="sec-meta">Deterministic relevance basis</span></div><p class="sec-intro">Relevance is established by an explicit, inspectable basis. The same external event carries different consequences for different organizations.</p><div class="idrow"><span class="idchip">Watched programs<b>2</b></span><span class="idchip">Watched entities<b>1</b></span><span class="idchip">Capability matches<b>4</b></span><span class="idchip">Agency interest<b>Army, MDA, Space Force</b></span></div><div class="result"><div><div class="r-name">Program of record sustainment</div><div class="r-meta"><span class="r-type">Watched program</span><span>relevance basis: WATCHED_PROGRAM</span></div></div><div class="r-right">exposure: vehicle access gap</div></div><div class="result"><div><div class="r-name">Modeling and simulation</div><div class="r-meta"><span class="r-type">Capability</span><span>relevance basis: CAPABILITY_MATCH</span></div></div><div class="r-right">exposure: teaming position</div></div></section>
    <section class="section"><div class="sec-head"><h2>Resolution and evidence</h2><span class="sec-meta">Entity resolution over the estate</span></div><p class="sec-intro">Companies, programs and identifiers are resolved to canonical entities before analysis, so evidence attaches to the right subject.</p><div class="idrow"><span class="idchip">UEI<b>resolved</b></span><span class="idchip">CAGE<b>resolved</b></span><span class="idchip">PIID<b>crosswalk</b></span><span class="idchip">CIK<b>resolved</b></span></div><div class="result"><div><div class="r-name">Subject supplier</div><div class="r-meta"><span class="r-type">Company</span><span>match: exact</span></div></div><div class="r-right">refs: 3</div></div></section>${closing}`,
  },

  '/method/': {
    module: 'Method',
    title: 'Method - Pyrnova',
    description:
      'How Pyrnova works: the reasoning chain from signal to decision implication, with observed fact and assessment kept distinct and point-in-time truth enforced.',
    body: `<header class="page-head"><span class="label accent">Method</span><h1>From signal to decision implication.</h1><p class="lead">Pyrnova follows a repeatable reasoning chain. Each stage is recorded so a conclusion can be inspected and revisited as evidence changes.</p></header>
    <section class="section"><div class="sec-head"><h2>The intelligence chain</h2></div>${signalTrace()}<div class="chain" style="margin-top:18px">${[
      ['01', 'Signal', 'A consequential external change is observed and its source record retained.'],
      ['02', 'Material change', 'The change becomes a structured object; observed fact and assessment stay separate.'],
      ['03', 'Customer exposure', 'A deterministic relevance basis connects the change to a specific organization.'],
      ['04', 'Commercial consequence', 'The company-specific consequence is derived; materiality and confidence stay orthogonal.'],
      ['05', 'Evidence', 'Statements cite retained evidence by identifier, with conservative corroboration.'],
      ['06', 'Uncertainty', 'What is unresolved is stated, along with a falsifier.'],
      ['07', 'AS OF', 'The conclusion is bound to a point in time; later evidence is excluded from earlier views.'],
      ['08', 'Decision implication', 'The implication is presented for the organization to act on. Decisions remain with the customer.'],
    ]
      .map((c) => `<div class="node"><span class="n-step">${c[0]}</span><h3>${c[1]}</h3><p>${c[2]}</p></div>`)
      .join('')}</div></section>
    <section class="section"><div class="sec-head"><h2>Observed fact and assessment</h2><span class="sec-meta">Never flattened</span></div><p class="sec-intro">The two are kept in separate structured blocks. A model explanation does not become a source fact, and a human judgement is recorded only when it exists.</p><div class="split">${facts([['Source event', 'Acquisition strategy notice'], ['Instrument', 'Multiple-award IDIQ', true], ['Published', '2026-09-08', true]]).replace('class="facts"', 'class="facts"')}${''}</div><div class="grid-2" style="margin-top:16px"><div class="pane observed"><span class="pane-label">Observed fact</span>${facts([['Source event', 'Acquisition strategy notice'], ['Instrument', 'Multiple-award IDIQ', true], ['Published', '2026-09-08', true], ['Corroboration', 'Single source']])}</div><div class="pane assessed"><span class="pane-label">Pyrnova assessment</span>${facts([['Consequence', 'Route to market shift'], ['Exposure path', 'Vehicle access gap'], ['Materiality', 'High', true], ['Confidence', 'Moderate', true]])}</div></div></section>
    <section class="section"><div class="sec-head"><h2>Point-in-time truth</h2><span class="sec-meta">AS OF</span></div><p class="sec-intro">A publication date, Pyrnova's observation time and the time a change becomes relevant may all differ. An AS OF view is reconstructed using only evidence available before its cutoff.</p>${temporalAxis()}</section>${closing}`,
  },

  '/trust/': {
    module: 'Trust',
    title: 'Trust - Pyrnova',
    description:
      'Fact versus assessment, source provenance, uncertainty, source rights and point-in-time integrity as product objects, with an honest account of what is not yet verified in production.',
    body: `<header class="page-head"><span class="label accent">Trust</span><h1>The basis of a conclusion is inspectable, including our own claims.</h1><p class="lead">What the system does, what has been tested, and what has not been verified in production. Stated plainly.</p><p class="review-date">Capability review: 2026-09-12</p></header>
    <section class="section"><div class="sec-head"><h2>Fact and assessment</h2><span class="sec-meta">Separated by construction</span></div><div class="grid-2"><div class="pane observed"><span class="pane-label">Observed fact</span>${facts([['Attribution', 'Retained source record'], ['Identity', 'Source id and provenance'], ['Content', 'Point-in-time hash', true]])}</div><div class="pane assessed"><span class="pane-label">Pyrnova assessment</span>${facts([['Attribution', 'Derived from evidence'], ['Type', 'Calculated or inferred'], ['Model role', 'Explanation, attributed']])}</div></div></section>
    <section class="section"><div class="sec-head"><h2>Provenance and evidence</h2></div><p class="sec-intro">Statements cite retained evidence by identifier. A single authoritative source is treated as not corroborated.</p><div class="evidence"><span class="label">Evidence</span><span class="chip raw">notice:SAM 3 refs</span><span class="chip single">corroboration: single source</span><span class="chip">program crosswalk</span></div></section>
    <section class="section"><div class="sec-head"><h2>Uncertainty and falsification</h2></div><div class="obj hold"><span class="obj-label">Unresolved</span><div class="uncertainty" style="margin-top:8px"><span class="u-label">Would weaken or falsify</span><ul><li>A separate direct-award path is retained for the requirement.</li><li>The engineering scope leaves the consolidated vehicle.</li></ul></div><p style="margin-top:8px">Absence of evidence is not treated as a win, a loss or a completed outcome. A conclusion can be strengthened, weakened, contradicted or falsified without erasing the earlier call.</p></div></section>
    <section class="section"><div class="sec-head"><h2>Point-in-time integrity</h2><span class="sec-meta">AS OF and replay</span></div>${temporalAxis()}</section>
    <section class="section"><div class="sec-head"><h2>Current posture</h2><span class="sec-meta">Implemented and tested, and what is not</span></div><div class="grid-2"><div class="obj ok"><span class="obj-label">Implemented / tested</span><h3>Product behaviour with repository evidence</h3><p>Credential-based authentication. Fail-closed application-layer tenant isolation covered by offline tests; customer identity bound to the credential and cross-customer requests rejected. This is application-layer isolation, not database row-level security.</p><p>Evidence provenance, source attribution, the observed-versus-assessed distinction, materiality and confidence, AS OF views and historical replay, source-rights controls, bounded retries, durable checkpoints, restart and recovery, and duplicate suppression are implemented and covered by offline tests.</p></div><div class="obj hold"><span class="obj-label">Not yet verified</span><h3>Production deployment and control posture</h3><p>Offline application tests are not a production security assessment. We do not claim verified production backups, disaster recovery, encryption at rest, production TLS architecture or 24/7 monitoring.</p><p>We do not claim database row-level security, production MFA or SSO, penetration testing, SOC 2, ISO 27001, FedRAMP or CMMC certification. No authority to process FCI, CUI or classified information is represented.</p></div></div><div class="notice" style="margin-top:18px"><span class="n-label">Data boundary</span><p><strong>Please do not submit restricted information to Pyrnova.</strong> Pyrnova does not intentionally accept FCI, CUI, classified information or export-controlled technical data in the current environment. This is an operating boundary, not a technical data-loss-prevention claim.</p></div></section>${closing}`,
  },

  '/research/': {
    module: 'Research',
    title: 'Research - Pyrnova',
    description:
      'Point-in-time reconstruction, historical replay, future-exclusion and falsification discipline shown as product objects. No benchmark results are claimed.',
    body: `<header class="page-head"><span class="label accent">Research</span><h1>An evidence-led approach, tested against the past.</h1><p class="lead">Methods are examined the way conclusions are: with explicit evidence, point-in-time discipline and a stated way to be wrong.</p></header>
    <section class="section"><div class="sec-head"><h2>Point-in-time reconstruction</h2><span class="sec-meta">Knowable then vs known now</span></div><p class="sec-intro">To ask whether a consequence would have been knowable, the past has to be rebuilt without leaking the present into it. An AS OF view excludes later evidence and preserves the assessment state that existed at that moment.</p>${temporalAxis()}</section>
    <section class="section"><div class="sec-head"><h2>Historical replay</h2><span class="sec-meta">Illustrative thesis lifecycle</span></div><div class="obj"><div class="hist">${[
      ['2026-08-24', 'OBSERVED', 'Acquisition strategy notice retained as source record.'],
      ['2026-08-24', 'ASSESSED', 'Route to market shift derived; materiality High, confidence Moderate.'],
      ['2026-09-02', 'STRENGTHENED', 'Second reference aligns with the consolidation direction.'],
      ['2026-09-11', 'MONITORING', 'Vehicle access unresolved; prior assessment state preserved.'],
    ]
      .map((r) => `<div class="h-row"><span class="h-at">${r[0]}</span><span class="h-kind">${r[1]}</span><span class="h-sum">${r[2]}</span></div>`)
      .join('')}</div></div></section>
    <section class="section"><div class="sec-head"><h2>Validation discipline</h2></div><div class="grid-2">${[
      ['Historical replay', 'Reasoning is exercised over retained historical events, so behaviour can be inspected rather than asserted.'],
      ['Future exclusion', 'An AS OF view is reconstructed using only evidence available before its cutoff. Later evidence is excluded.'],
      ['Falsification', 'Each conclusion records a falsifier, the evidence that would contradict it, so it can be challenged directly.'],
      ['Provenance', 'Source identity, references and observation times are retained, so a claim can be traced to what it rests on.'],
    ]
      .map((c) => `<div class="obj"><span class="obj-label">${c[0]}</span><p>${c[1]}</p></div>`)
      .join('')}</div><div class="notice" style="margin-top:18px"><span class="n-label">On results</span><p>Pyrnova is early. This page describes the research approach and the disciplines applied to it. It does <strong>not</strong> claim predictive accuracy or a published benchmark result.</p></div></section>${closing}`,
  },

  '/company/': {
    module: 'Company',
    title: 'Company - Pyrnova',
    description:
      'A founder-led intelligence company focused on what external change means commercially to a specific organization.',
    body: `<header class="page-head"><span class="label accent">Company</span><h1>External intelligence, grounded in a company's reality.</h1><p class="lead">Pyrnova is a founder-led intelligence company. Its work is what external change means commercially to a specific organization, with the basis kept inspectable.</p></header>
    <section class="section"><div class="sec-head"><h2>Position</h2></div><dl class="meta-rows"><div><dt>Focus</dt><dd>Company-specific commercial consequence of external change, with evidence, uncertainty and point-in-time integrity.</dd></div><div><dt>Initial application</dt><dd>Evaluated with mid-market <b>U.S. federal contractors</b> and their growth and capture teams. This does not define the limits of the category.</dd></div><div><dt>Posture</dt><dd>Discreet, precise, evidence-led. <b>Discretion, intelligence, competence, control.</b></dd></div><div><dt>Structure</dt><dd><b>Founder-led</b>, with direct accountability for evaluations and early conversations.</dd></div><div><dt>Disclosure</dt><dd>Need-to-know by default. Capability evidence is discussed where there is a commercial reason.</dd></div></dl></section>
    <section class="section"><div class="sec-head"><h2>Where Pyrnova sits</h2></div><p class="sec-intro">Pyrnova augments mature capture and growth systems with earlier, customer-specific consequence intelligence. It turns changes in programs, policy, budgets, technology, acquisition and institutional behaviour into commercial consequences before they become just another opportunity record.</p></section>${closing}`,
  },

  '/evaluate/': {
    module: 'Evaluate',
    title: 'Evaluate - Pyrnova',
    description:
      'What a Pyrnova evaluation produces. Evaluations are arranged directly with the founder; there is no public submission form at this time and this site collects no personal data.',
    body: `<header class="page-head"><span class="label accent">Evaluate Pyrnova</span><h1>Test Pyrnova against a change that matters to your company.</h1><p class="lead">An evaluation puts Pyrnova against a real external change affecting a specific organization, so you can judge the consequence, the evidence and the uncertainty directly.</p></header>
    <section class="section"><div class="sec-head"><h2>What an evaluation produces</h2><span class="sec-meta">Synthetic specimen of the output</span></div><p class="sec-intro">An evaluation returns the same structured record the product produces: a company-specific consequence with its observed fact, assessment, evidence, uncertainty and AS OF. The specimen below illustrates that output.</p>${spec(specRecompete)}</section>
    <section class="section"><div class="sec-head"><h2>How it works today</h2></div><div class="notice"><span class="n-label">Intake status</span><p><strong>Public evaluation intake is not open.</strong> Evaluations are currently arranged directly with the founder as part of a limited early program. This page explains what to expect. There is no submission form or account sign-up here, and this site does not collect your details.</p></div><div class="grid-3" style="margin-top:18px">${[
      ['01', 'A specific change', 'An evaluation starts from an external change relevant to your organization, not a canned scenario.'],
      ['02', 'The consequence and its evidence', 'Pyrnova derives the company-specific consequence and shows the source facts, uncertainty and falsifier behind it.'],
      ['03', 'Your judgement', 'You inspect the reasoning and decide whether it holds. Decisions and actions remain with your organization.'],
    ]
      .map((c) => `<div class="obj"><span class="obj-label">Step ${c[0]}</span><h3>${c[1]}</h3><p>${c[2]}</p></div>`)
      .join('')}</div></section>
    <section class="section"><div class="sec-head"><h2>Before an evaluation</h2></div><div class="notice"><span class="n-label">Data boundary</span><p><strong>Please plan to share public or ordinary business information only.</strong> Pyrnova does not intentionally accept FCI, CUI, classified information or export-controlled technical data in the current environment. Keep restricted categories out of any evaluation.</p></div></section>`,
  },
};

export const routes = Object.keys(pages);

export function renderPage(path, { origin = 'https://pyrnova.com' } = {}) {
  const page = pages[path];
  if (!page) return null;
  const canonical = `${origin}${path}`;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>${page.title}</title><meta name="description" content="${page.description}"><meta name="robots" content="index, follow"><link rel="canonical" href="${canonical}"><meta name="theme-color" content="#0b0d10"><meta property="og:type" content="website"><meta property="og:site_name" content="Pyrnova"><meta property="og:title" content="${page.title}"><meta property="og:description" content="${page.description}"><meta property="og:url" content="${canonical}"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/site.css"></head><body><a class="skip-link" href="#main">Skip to content</a>${masthead(path, page.module)}<main id="main">${page.body}</main>${footer()}</body></html>`;
}

export function robotsTxt(origin) {
  return `User-agent: *\nAllow: /\nSitemap: ${origin}/sitemap.xml\n`;
}
export function sitemapXml(origin) {
  return `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${routes
    .map((p) => `<url><loc>${origin}${p}</loc></url>`)
    .join('')}</urlset>`;
}
