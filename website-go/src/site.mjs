// Pyrnova public website — State 1 content.
// WEBSITE GO / OUTREACH INTAKE DISABLED.
// Static informational site. No forms, no personal-data collection, no intake endpoints.
// Content is server-rendered once at build time into static HTML.

const arrow = '<span aria-hidden="true">↗</span>';
const label = (text) => `<p class="eyebrow">${text}</p>`;
const intro = (n, title, text) =>
  `<div class="section-intro">${label(n)}<h2>${title}</h2>${text ? `<p>${text}</p>` : ''}</div>`;
const button = (text, href, secondary = false) =>
  `<a class="button${secondary ? ' secondary' : ''}" href="${href}">${text} ${arrow}</a>`;

// Primary navigation is locked authority.
export const nav = [
  { label: 'INTELLIGENCE', path: '/intelligence/' },
  { label: 'METHOD', path: '/method/' },
  { label: 'TRUST', path: '/trust/' },
  { label: 'RESEARCH', path: '/research/' },
  { label: 'COMPANY', path: '/company/' },
];
const evaluatePath = '/evaluate/';

// Reusable closing call-to-action. Points to the informational EVALUATE page only.
const closing = `<section class="closing"><div>${label('Evaluate Pyrnova')}<h2>Test Pyrnova against a real external change affecting your organization.</h2><p>See the consequence, the evidence behind it, the uncertainty and the point in time it was knowable.</p></div>${button('Evaluate Pyrnova', evaluatePath)}</section>`;

// Illustrative evidence panel shared on the home and intelligence pages.
const evidencePanel = `<aside class="evidence-panel" aria-label="Illustrative consequence intelligence structure"><div class="panel-top"><span>INTELLIGENCE STRUCTURE</span><span>ILLUSTRATIVE</span></div><div class="panel-body"><p class="eyebrow">01 / External change</p><h2>A program changes its acquisition approach.</h2><div class="connector" aria-hidden="true"></div><p class="eyebrow accent">02 / Company-specific consequence</p><p class="panel-consequence">An engineering supplier's route to market may shift from a direct award to a teaming position.</p><div class="evidence-row"><span>Evidence</span><strong>Source-linked reasoning</strong></div><div class="evidence-row"><span>Uncertainty</span><strong>Vehicle &amp; scope unresolved</strong></div><div class="evidence-row"><span>Falsifier</span><strong>Direct award path retained</strong></div><p class="panel-note">Hypothetical example. No customer, source event or product result is represented.</p></div><div class="panel-bottom"><span>FACT ≠ ASSESSMENT</span><span>PRIOR STATE PRESERVED</span></div></aside>`;

const pages = {
  '/': {
    title: 'Pyrnova — Know what changed. Know what it changes.',
    description:
      'Pyrnova detects consequential external change, traces its effect on your organization, and shows the evidence behind each conclusion.',
    body: `<section class="hero"><div class="hero-copy">${label('External change · Commercial consequence')}<h1>Know what changed. Know what it changes.</h1><p class="lead">Pyrnova detects consequential external change, traces its effect on your organization, and shows the evidence behind each conclusion.</p><div class="cta-row">${button('Evaluate Pyrnova', evaluatePath)}${button('See the intelligence', '/intelligence/', true)}</div></div>${evidencePanel}</section>
    <section class="section">${intro('01 / The question', 'External information is abundant. Company-specific meaning is harder.', '')}<div class="section-content"><p>Opportunity databases, market research, alerts, analysts and internal capture knowledge each serve a purpose.</p><p class="large">The hard question is what an external change actually means to <em>this</em> particular organization.</p><p>Pyrnova connects the change to an organization's exposure, capabilities and commercial context, with a reasoning path that can be inspected.</p></div></section>
    <section class="section" id="how-it-works">${intro('02 / How Pyrnova thinks', 'From change to consequence. From outcome to learning.', 'A conclusion is useful when you can inspect its basis and revisit it as evidence changes.')}<div class="section-content"><ol class="reasoning-loop">${['External change', 'Customer relevance', 'Commercial consequence', 'Evidence', 'Investigation', 'Decision', 'Action', 'Outcome', 'Learning'].map((s, i) => `<li><span>${String(i + 1).padStart(2, '0')}</span>${s}</li>`).join('')}</ol><p class="muted">The loop describes the intelligence workflow. Decisions and actions remain with your organization; outcomes require sourced observation. ${button('See the method', '/method/', true)}</p></div></section>
    <section class="section">${intro('03 / Material change', 'One event. Different commercial consequences.', 'Relevance depends on the organization, not just the headline.')}<div class="section-content example"><p class="example-label">HYPOTHETICAL EXAMPLE — NOT A CUSTOMER RESULT</p><div class="source-block">${label('Source event')}<h3>An agency moves a planned engineering requirement into a broader services vehicle.</h3><p>No actual agency notice is represented in this illustration.</p></div><div class="consequence-grid"><div>${label('Company context')}<p>A specialist supplier has the relevant engineering capability but lacks access to the proposed vehicle.</p></div><div>${label('Pyrnova-derived consequence')}<p>The direct pursuit thesis weakens. A prime relationship may become commercially significant.</p></div></div><div class="example-foot"><div><strong>Investigate</strong><p>Confirm vehicle access, scope and the supplier's potential role.</p></div><div><strong>Could invalidate the thesis</strong><p>The agency retains a separate direct award path, or the engineering scope leaves the requirement.</p></div></div></div></section>
    <section class="section">${intro('04 / Evidence', 'Know which part is fact. Know which part is judgment.', 'A source citation is a starting point. The distinction between evidence and conclusion matters.')}<div class="section-content"><p>Every conclusion carries the source identity, evidence references, observation times and uncertainty behind it. Fact and assessment are labelled separately, so a reader can inspect the basis rather than trust a claim.</p>${button('How evidence is structured', '/intelligence/', true)}</div></section>
    <section class="section">${intro('05 / Trust', 'Evidence before assertion.', '')}<div class="section-content"><p>Provenance. Inspectable reasoning. Explicit uncertainty. Customer isolation. Point-in-time integrity.</p><p>We distinguish implemented and tested product behaviour from production controls that have not yet been verified — and we say plainly which is which.</p>${button('Read the Trust page', '/trust/', true)}</div></section>${closing}`,
  },

  '/intelligence/': {
    title: 'Intelligence — Pyrnova',
    description:
      'What a Pyrnova conclusion contains: a company-specific consequence, the evidence behind it, explicit uncertainty and the point in time it was knowable.',
    body: `<header class="page-heading">${label('Intelligence')}<h1>A consequence you can inspect, not just an alert you receive.</h1><p class="lead">Pyrnova produces a company-specific commercial consequence from an external change — and shows the evidence, uncertainty and historical state behind it.</p></header>
    <section class="hero anatomy"><div class="hero-copy">${label('Anatomy of a conclusion')}<p>An alert tells you something happened. Pyrnova tells you what it may mean for a specific organization, and lets you check the reasoning.</p><p>Each conclusion separates the observed source fact from the Pyrnova-derived assessment, keeps the uncertainty visible, and records a falsifier — the evidence that would change the call.</p><p class="muted">The panel shown here is the shape of a single conclusion. It is illustrative and represents no customer or source event.</p></div>${evidencePanel}</section>
    <section class="section">${intro('01 / Attribution', 'Every statement carries its origin.', 'Provenance is not a footnote. It is part of the conclusion.')}<div class="section-content"><div class="semantic-rows"><div><span class="tag">SOURCE FACT</span><p>Information supported by a retained source record, with source identity and provenance.</p></div><div><span class="tag">PYRNOVA DERIVED</span><p>A calculated or inferred conclusion produced from evidence and company context.</p></div><div><span class="tag">MODEL EXPLANATION</span><p>Model-assisted explanation, attributed separately from authoritative source facts.</p></div><div><span class="tag">HUMAN ASSESSMENT</span><p>An explicitly recorded human judgement, where present. Human review is not implied for every output.</p></div></div><p class="muted">Source identifiers, links, observation times and evidence references make the reasoning inspectable. Missing information remains unknown rather than assumed.</p></div></section>
    <section class="section">${intro('02 / Uncertainty', 'A confident tone is not evidence.', '')}<div class="section-content"><p>Pyrnova keeps the unresolved parts of a conclusion visible: what is still ambiguous, what would confirm it and what would contradict it.</p><p class="large">Absence of evidence is not treated as a win, a loss or a completed outcome.</p><p>A thesis can be strengthened, weakened, contradicted or falsified as new evidence arrives — without erasing the earlier call.</p><div class="states"><span>Strengthened</span><span>Weakened</span><span>Contradicted</span><span>Falsified</span></div></div></section>
    <section class="section">${intro('03 / AS-OF', 'What was actually knowable at the time?', 'Historical views should respect when information became available.')}<div class="section-content"><div class="timeline" aria-label="Illustrative point-in-time availability"><div><span>Before cutoff</span><strong>Available evidence</strong><p>Eligible for the historical view.</p></div><div class="cutoff"><span>AS-OF</span><strong>Explicit cutoff</strong><p>A boundary on knowledge.</p></div><div><span>After cutoff</span><strong>Later evidence</strong><p>Excluded from that earlier view.</p></div></div><p>A publication date, Pyrnova's observation time and the time a change became relevant to your organization may differ. A point-in-time reconstruction excludes future information and preserves the earlier assessment state.</p><p class="muted">Historical reconstruction is not a claim of infallible prediction.</p></div></section>${closing}`,
  },

  '/method/': {
    title: 'Method — Pyrnova',
    description:
      'How Pyrnova works: a reasoning loop from external change to company-specific consequence, evidence, investigation, outcome and learning.',
    body: `<header class="page-heading">${label('Method')}<h1>From an external change to a decision you can defend.</h1><p class="lead">Pyrnova follows a repeatable reasoning loop. Each step is recorded so a conclusion can be inspected and revisited as evidence changes.</p></header>
    <section class="section">${intro('The loop', 'Change in. Consequence, evidence and learning out.', '')}<div class="section-content"><ol class="reasoning-loop">${['External change', 'Customer relevance', 'Commercial consequence', 'Evidence', 'Investigation', 'Decision', 'Action', 'Outcome', 'Learning'].map((s, i) => `<li><span>${String(i + 1).padStart(2, '0')}</span>${s}</li>`).join('')}</ol><p class="muted">Decisions and actions remain with your organization. Pyrnova structures the reasoning and preserves its evidence.</p></div></section>
    <section class="section">${intro('01 / Detect', 'Consequential change, not every headline.', '')}<div class="section-content"><p>Pyrnova watches for external change — in programs, policy, budgets, technology, acquisition and institutional behaviour — that could carry commercial consequence, and retains the source record behind what it observes.</p></div></section>
    <section class="section">${intro('02 / Trace', 'Connect the change to a specific organization.', '')}<div class="section-content"><p>Relevance depends on an organization's exposure, capabilities and commercial context. Pyrnova traces how a change reaches a particular company and where it lands, rather than broadcasting the same signal to everyone.</p></div></section>
    <section class="section">${intro('03 / Evidence', 'Separate the fact from the assessment.', '')}<div class="section-content"><p>The observed source fact and the Pyrnova-derived consequence are recorded distinctly, with links, observation times and references. Uncertainty is kept explicit and a falsifier is stated: the evidence that would change the conclusion.</p>${button('See how evidence is structured', '/intelligence/', true)}</div></section>
    <section class="section">${intro('04 / Point-in-time integrity', 'Respect what was knowable then.', '')}<div class="section-content"><p>AS-OF reconstruction rebuilds an earlier view using only the evidence available at that time, excluding later information. Prior assessments and review state are preserved rather than overwritten, so a conclusion can be revisited honestly.</p></div></section>
    <section class="section">${intro('05 / Learn', 'A thesis can change without losing its history.', '')}<div class="section-content"><p>As sourced outcomes arrive, a conclusion may be strengthened, weakened, contradicted or falsified. Pyrnova retains the earlier call alongside the later evidence. Outcome resolution stays unknown when evidence does not establish a result.</p></div></section>${closing}`,
  },

  '/trust/': {
    title: 'Trust — Pyrnova',
    description:
      'Implemented and tested product behaviour, and an honest account of what has not yet been verified in production.',
    body: `<header class="page-heading">${label('Trust')}<h1>Make the basis of a conclusion inspectable — including our own claims.</h1><p class="lead">Trust begins with a clear account of what the system does, what has been tested and what has not been verified in production.</p><p class="review-date">Capability review: 12 September 2026</p></header>
    <section class="section">${intro('Implemented / tested', 'Product behaviour with repository evidence.', '')}<div class="section-content prose"><h3>Identity and customer isolation</h3><p>Credential-based authentication is implemented. Fail-closed application-layer tenant isolation is implemented and covered by offline tests. Customer identity is bound to the credential; cross-customer requests are rejected. This is application-layer isolation, not database row-level security.</p><h3>Evidence and attribution</h3><p>Source identity, evidence references, retained content hashes and observation metadata support provenance. SOURCE FACT, PYRNOVA DERIVED, MODEL EXPLANATION and HUMAN ASSESSMENT distinguish the origin of a statement where applicable. A model explanation does not become a source fact, and human assessment is only represented when recorded.</p><h3>Point-in-time integrity</h3><p>AS-OF views and historical replay apply availability cutoffs. Later evidence is excluded from earlier views; prior predictions, assessments and customer review state are preserved. Replay and future-exclusion behaviour are covered by offline tests.</p><h3>Source rights</h3><p>Source material carries rights and usage constraints. Pyrnova retains source identity and links and applies source-rights controls to how retained material may be used, rather than treating every retrieved item as freely redistributable.</p><h3>Operational behaviour</h3><p>Source health and freshness states, bounded retries, durable checkpoints, restart and recovery handling, duplicate suppression and downstream idempotency are implemented and tested. These capabilities do not by themselves establish uninterrupted service, complete coverage or production resilience.</p></div></section>
    <section class="section">${intro('Not yet verified', 'Production deployment and control posture.', '')}<div class="section-content prose"><p>Offline application tests are not a production security assessment. Production deployment controls require separate verification before customer operation.</p><p>We do <strong>not</strong> claim verified production backups, disaster recovery, encryption at rest, production TLS architecture or 24/7 monitoring. The HTTPS edge that serves this website does not verify the intelligence product's production controls.</p><p>We do <strong>not</strong> claim database row-level security, production MFA or SSO, penetration testing, SOC 2, ISO 27001, FedRAMP or CMMC certification. No authorization to process classified information, FCI or CUI is represented.</p></div></section>
    <section class="section">${intro('Data boundary', 'A bounded early environment.', '')}<div class="section-content"><div class="notice"><p><strong>Please do not submit restricted information to Pyrnova.</strong></p><p>Pyrnova does not intentionally accept FCI, CUI, classified information or export-controlled technical data in the current environment. This is an operating boundary, not a technical data-loss-prevention claim.</p></div><p class="muted">Capability evidence and unresolved deployment requirements can be discussed in a founder-led evaluation.</p></div></section>${closing}`,
  },

  '/research/': {
    title: 'Research — Pyrnova',
    description:
      'Pyrnova’s evidence-led research approach: point-in-time reconstruction, historical replay and falsification discipline.',
    body: `<header class="page-heading">${label('Research')}<h1>An evidence-led approach, tested against the past.</h1><p class="lead">Pyrnova's methods are examined the same way its conclusions are: with explicit evidence, point-in-time discipline and a willingness to be wrong.</p></header>
    <section class="section">${intro('Approach', 'Reconstruct the past honestly.', 'Point-in-time reconstruction is the discipline underneath everything else.')}<div class="section-content"><p>To ask whether a consequence would have been knowable, you have to rebuild the past without leaking the present into it. Pyrnova's AS-OF reconstruction excludes later information and preserves the assessment state that existed at a chosen moment.</p><p class="large">A method that quietly uses future information cannot be trusted about the past.</p></div></section>
    <section class="section">${intro('Practices', 'How the work is examined.', '')}<div class="section-content"><div class="card-grid"><div class="card">${label('Historical replay')}<h3>Replay against recorded events</h3><p>Reasoning is exercised over retained historical events, so behaviour can be inspected rather than asserted.</p></div><div class="card">${label('Future exclusion')}<h3>No hindsight leakage</h3><p>An AS-OF view is reconstructed using only evidence available before its cutoff. Later evidence is excluded from earlier views.</p></div><div class="card">${label('Falsification')}<h3>State what would be wrong</h3><p>Each conclusion records a falsifier — the evidence that would contradict it — so it can be challenged directly.</p></div><div class="card">${label('Provenance')}<h3>Keep the source record</h3><p>Source identity, links and observation times are retained, so a claim can be traced to what it rests on.</p></div></div></div></section>
    <section class="section">${intro('Honesty', 'Where this stands.', '')}<div class="section-content"><div class="notice"><p>Pyrnova is early. This page describes the research approach and the disciplines applied to it — <strong>not</strong> a claim of predictive accuracy or a published benchmark result.</p></div><p class="muted">Specific evidence relevant to a use case can be reviewed in a founder-led evaluation.</p></div></section>${closing}`,
  },

  '/company/': {
    title: 'Company — Pyrnova',
    description:
      'Pyrnova is a founder-led intelligence company focused on what external change means commercially to a specific organization.',
    body: `<header class="page-heading">${label('Company')}<h1>External intelligence, grounded in a company's reality.</h1><p class="lead">Pyrnova is a founder-led intelligence company focused on what external change means commercially to a specific organization.</p></header>
    <section class="section">${intro('Purpose', 'Consequence, with an inspectable basis.', '')}<div class="section-content"><p>Information becomes commercially meaningful when it connects to an organization's capabilities, exposure and situation. Pyrnova is built around that connection.</p><p>We preserve the distinction between source evidence and analytical judgement, make uncertainty explicit and retain what was knowable at a given time.</p></div></section>
    <section class="section">${intro('Initial application', 'Upstream of capture.', '')}<div class="section-content"><p class="large">Pyrnova is initially being evaluated with mid-market U.S. federal contractors and their growth and capture teams.</p><p>It turns changes in programs, policy, budgets, technology, acquisition and institutional behaviour into customer-specific commercial consequences before they become just another opportunity record.</p><p>Pyrnova augments mature capture and growth systems with earlier, customer-specific consequence intelligence. This initial application does not define the limits of the category.</p></div></section>
    <section class="section">${intro('Founder-led', 'Built and run with direct accountability.', '')}<div class="section-content"><p>Pyrnova is founder-led. Evaluations and early conversations are handled directly, focused on your organization's commercial context, an external change worth investigating and the evidence needed to judge the conclusion.</p>${button('Evaluate Pyrnova', evaluatePath, true)}</div></section>${closing}`,
  },

  '/evaluate/': {
    title: 'Evaluate — Pyrnova',
    description:
      'What a Pyrnova evaluation involves. Evaluations are arranged directly with the founder; there is no public submission form at this time.',
    body: `<header class="page-heading">${label('Evaluate Pyrnova')}<h1>Test Pyrnova against a change that matters to your company.</h1><p class="lead">An evaluation puts Pyrnova against a real external change affecting a specific organization — so you can judge the consequence, the evidence and the uncertainty for yourself.</p></header>
    <section class="section">${intro('What an evaluation is', 'A conclusion you can inspect, on your own context.', '')}<div class="section-content"><p>Rather than a generic demo, an evaluation works from an external change relevant to your organization. You see the company-specific consequence Pyrnova derives, the source evidence behind it, the uncertainty it keeps visible and the point in time the conclusion was knowable.</p><p>The aim is a judgement you can defend: is the reasoning sound, is the evidence real, and does the conclusion hold up when you push on it?</p></div></section>
    <section class="section">${intro('How it works today', 'Arranged directly, in a limited early program.', '')}<div class="section-content"><div class="notice"><p><strong>Public evaluation intake is not open yet.</strong></p><p>Evaluations are currently arranged directly with the founder as part of a limited early program. This page explains what to expect — there is no submission form or account sign-up here, and this site does not collect your details.</p></div><ol class="step-list"><li><span class="step-num">01</span><div><h3>A specific change</h3><p>An evaluation starts from an external change relevant to your organization — not a canned scenario.</p></div></li><li><span class="step-num">02</span><div><h3>The consequence and its evidence</h3><p>Pyrnova derives the company-specific consequence and shows the source facts, uncertainty and falsifier behind it.</p></div></li><li><span class="step-num">03</span><div><h3>Your judgement</h3><p>You inspect the reasoning and decide whether it holds. Decisions and actions remain with your organization.</p></div></li></ol></div></section>
    <section class="section">${intro('Before an evaluation', 'One boundary to keep in mind.', '')}<div class="section-content"><div class="notice"><p><strong>Please plan to share public or ordinary business information only.</strong></p><p>Pyrnova does not intentionally accept FCI, CUI, classified information or export-controlled technical data in the current environment. Keep restricted categories out of any evaluation.</p></div><p class="muted">Want the detail behind these claims first? ${button('Read the Trust page', '/trust/', true)}</p></div></section>`,
  },
};

export const routes = Object.keys(pages);

function headerHtml(path) {
  const links = nav
    .map(
      (item) =>
        `<a href="${item.path}"${path === item.path ? ' aria-current="page"' : ''}>${item.label}</a>`
    )
    .join('');
  const evalCurrent = path === evaluatePath ? ' aria-current="page"' : '';
  return `<header class="site-header"><a class="wordmark" href="/" aria-label="Pyrnova home"><span class="brand-mark" aria-hidden="true">P</span>PYRNOVA</a><div class="header-nav"><nav class="primary" aria-label="Main navigation">${links}</nav><a class="nav-cta" href="${evaluatePath}"${evalCurrent}>EVALUATE ${arrow}</a></div></header>`;
}

function footerHtml() {
  const links = [...nav, { label: 'Evaluate', path: evaluatePath }]
    .map((item) => `<a href="${item.path}">${item.label.charAt(0) + item.label.slice(1).toLowerCase()}</a>`)
    .join('');
  return `<footer class="site-footer"><div><a class="wordmark" href="/">PYRNOVA</a><p>Company-specific consequence intelligence. Know what changed. Know what it changes.</p></div><nav aria-label="Footer navigation">${links}</nav><p class="copyright">© 2026 Pyrnova. This informational website does not currently collect personal data or accept evaluation submissions.</p></footer>`;
}

export function renderPage(path, { origin = 'https://pyrnova.com' } = {}) {
  const page = pages[path];
  if (!page) return null;
  const canonical = `${origin}${path}`;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${page.title}</title><meta name="description" content="${page.description}"><meta name="robots" content="index, follow"><link rel="canonical" href="${canonical}"><meta property="og:type" content="website"><meta property="og:site_name" content="Pyrnova"><meta property="og:title" content="${page.title}"><meta property="og:description" content="${page.description}"><meta property="og:url" content="${canonical}"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/site.css"></head><body><a class="skip-link" href="#main">Skip to content</a>${headerHtml(path)}<main id="main">${page.body}</main>${footerHtml()}</body></html>`;
}

export function robotsTxt(origin) {
  return `User-agent: *\nAllow: /\nSitemap: ${origin}/sitemap.xml\n`;
}

export function sitemapXml(origin) {
  return `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${routes
    .map((p) => `<url><loc>${origin}${p}</loc></url>`)
    .join('')}</urlset>`;
}
