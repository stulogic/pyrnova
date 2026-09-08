const target = document.querySelector('#target');
const queue = document.querySelector('#queue');
const message = document.querySelector('#message');
const template = document.querySelector('#candidate');
let snapshot;

const pct = value => `${Math.round((Number(value) || 0) * 100)}%`;
const money = value => value == null ? 'Value unknown' : `$${Number(value).toLocaleString()}`;
const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
const safeUrl = value => { try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : null; } catch { return null; } };
const post = async (url, body) => {
  const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
};

function smallRow(label, value, status = '') {
  return `<div class="small-row"><span>${label}</span><strong class="${status}">${value}</strong></div>`;
}

async function load(preserveTargets = true) {
  const query = target.value ? `?target=${encodeURIComponent(target.value)}` : '';
  const response = await fetch(`/api/snapshot${query}`);
  snapshot = await response.json();
  if (!preserveTargets || !target.options.length) {
    target.innerHTML = snapshot.targets.map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join('');
    const populatedTarget = snapshot.queue.find(item => item.target)?.target;
    if (populatedTarget && [...target.options].some(option => option.value === populatedTarget)) target.value = populatedTarget;
    if (target.value) return load(true);
  }
  render();
}

function render() {
  document.querySelector('#runs').innerHTML = snapshot.runs.length
    ? snapshot.runs.map(run => smallRow(escapeHtml(run.id.slice(0, 9)), `${run.candidates} candidates`)).join('')
    : '<p class="muted">No persisted runs for this target.</p>';
  document.querySelector('#sources').innerHTML = snapshot.source_health.map(source =>
    smallRow(escapeHtml(source.id.replaceAll('_', ' ')), escapeHtml(source.status.replace('_', ' ')), source.status)
  ).join('');
  const metrics = snapshot.scoreboard;
  document.querySelector('#metrics').innerHTML = [
    ['Briefs', metrics.signal_briefs_produced || 0], ['Accepts', metrics.review_accepts || 0],
    ['Watches', metrics.review_watches || 0], ['Rejects', metrics.review_rejects || 0]
  ].map(([a,b]) => smallRow(a,b)).join('');
  queue.innerHTML = '';
  if (!snapshot.queue.length) queue.innerHTML = '<div class="empty">No candidates are persisted for this target. Run Capture Radar first.</div>';
  snapshot.queue.forEach(renderCandidate);
}

function renderCandidate(item) {
  const node = template.content.cloneNode(true);
  const article = node.querySelector('.candidate');
  article.dataset.id = item.id;
  node.querySelector('h3').textContent = item.title;
  const provenance = item.source_status ? ` · ${item.source_status}${item.source_as_of ? ` ${item.source_as_of}` : ''}` : '';
  node.querySelector('.agency').textContent = `${item.agency || 'Agency unknown'} · ${money(item.value_usd)}${provenance}`;
  const disposition = node.querySelector('.disposition');
  disposition.textContent = item.human_decision || item.system_disposition;
  disposition.classList.add((item.human_decision || item.system_disposition).toLowerCase());
  const score = value => item.score_status === 'unavailable' ? 'Unavailable' : pct(value);
  node.querySelector('.scores').innerHTML = `<span>Relevance <b>${score(item.relevance)}</b></span><span>Confidence <b>${score(item.confidence)}</b></span><span>Attractiveness <b>${score(item.attractiveness)}</b></span><span>Posture <b>${item.posture}</b></span>`;
  const consequence = node.querySelector('.consequence');
  if (item.m7_consequence) consequence.textContent = `M7 consequence · ${item.m7_consequence.directness || 'unknown directness'} · ${item.m7_consequence.mechanism || 'mechanism unknown'} · confidence ${pct(item.m7_consequence.confidence)}`;
  else consequence.remove();
  node.querySelector('.evidence').innerHTML = item.evidence.length ? '<span>Evidence</span> ' + item.evidence.map(ev => {
    const url = safeUrl(ev.url);
    const label = `${escapeHtml(ev.source)}: ${escapeHtml(ev.ref || 'record')}`;
    return url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${label}</a>` : `<em>${label}</em>`;
  }).join(' · ') : '<span>Evidence</span> none linked';
  const form = node.querySelector('form');
  form.elements.posture.value = item.posture;
  form.elements.notes.value = item.notes || '';
  form.elements.falsification.value = item.falsification || '';
  form.elements.outcome.value = item.outcome?.status || 'UNKNOWN';
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    delete data.outcome;
    await act(() => post(`/api/opportunities/${encodeURIComponent(item.id)}/review`, data), 'Adjudication saved.');
  });
  node.querySelector('.save-outcome').addEventListener('click', () => act(
    () => post(`/api/opportunities/${encodeURIComponent(item.id)}/outcome`, {status: form.elements.outcome.value, notes: form.elements.notes.value}),
    'Outcome saved.'
  ));
  queue.append(node);
}

async function act(fn, success) {
  try { await fn(); message.textContent = success; await load(true); }
  catch (error) { message.textContent = error.message; }
}

target.addEventListener('change', () => load(true));
document.querySelector('#export').addEventListener('click', async () => {
  try { const result = await post('/api/briefs', {target: target.value}); message.textContent = `Signal Brief exported to ${result.path}`; await load(true); }
  catch (error) { message.textContent = error.message; }
});
load(false).catch(error => { message.textContent = error.message; });
