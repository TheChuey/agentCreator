/* Per-agent tool diagnostics.

   Reads the headless engine's tool log through GET /api/tool-log?agent=...
   and shows one row per tool call. The tool-stage events (stage="tool") carry
   the operation verdict (ok), timing and a summary, so this page answers
   "did the tool actually work?" rather than just "was it called?".

   Opened from /chat's Diagnostics button, which passes the active agent id in
   the query string. Without one, it shows every agent's calls. */

import API from './api.js';

const params = new URLSearchParams(window.location.search);
const agentId = params.get('agent');

const listEl = document.getElementById('diagList');
const nameEl = document.getElementById('agentName');
const totalEl = document.getElementById('statTotal');
const okEl = document.getElementById('statOk');
const badEl = document.getElementById('statBad');
const updatedEl = document.getElementById('updatedAt');
const refreshBtn = document.getElementById('refreshBtn');
const clearBtn = document.getElementById('clearBtn');
const autoBox = document.getElementById('autoRefresh');

let timer = null;

function isOk(event) {
  const ok = event.ok !== undefined ? event.ok : event.op_ok;
  if (ok !== undefined) return ok === true;
  return event.status !== 'error' && event.status !== 'missing';
}

function verdictOf(event) {
  if (isOk(event)) return 'OK';
  return event.status === 'missing' ? 'MISSING' : 'FAILED';
}

function stamp(event) {
  if (event.ts) {
    const parsed = new Date(event.ts);
    if (!Number.isNaN(parsed.getTime())) return parsed.toLocaleTimeString();
  }
  return event.time || '';
}

function makeRow(event) {
  const ok = isOk(event);
  const row = document.createElement('div');
  row.className = 'diag-row' + (ok ? '' : ' bad');

  const head = document.createElement('div');
  head.className = 'diag-head';

  const tool = document.createElement('span');
  tool.className = 'diag-tool';
  tool.textContent = event.tool || '(unknown tool)';
  head.appendChild(tool);

  const verdict = document.createElement('span');
  verdict.className = 'diag-verdict';
  verdict.textContent = verdictOf(event);
  head.appendChild(verdict);

  const time = document.createElement('span');
  time.className = 'diag-time';
  time.textContent = stamp(event);
  head.appendChild(time);

  if (event.elapsed_ms !== undefined && event.elapsed_ms !== null) {
    const ms = document.createElement('span');
    ms.className = 'diag-ms';
    ms.textContent = `${event.elapsed_ms}ms`;
    head.appendChild(ms);
  }

  if (event.model) {
    const model = document.createElement('span');
    model.className = 'diag-model';
    model.textContent = event.model;
    head.appendChild(model);
  }

  row.appendChild(head);

  if (event.summary) {
    const summary = document.createElement('div');
    summary.className = 'diag-summary';
    summary.textContent = event.summary;
    row.appendChild(summary);
  }

  if (event.args && Object.keys(event.args).length) {
    const args = document.createElement('div');
    args.className = 'diag-args';
    args.textContent = JSON.stringify(event.args);
    row.appendChild(args);
  }

  const why = event.error || event.op_error;
  if (why) {
    const error = document.createElement('div');
    error.className = 'diag-error';
    error.textContent = why;
    row.appendChild(error);
  }

  if (event.result_preview) {
    const details = document.createElement('details');
    details.className = 'raw';
    const summary = document.createElement('summary');
    summary.textContent = 'result preview';
    details.appendChild(summary);
    const preview = document.createElement('div');
    preview.className = 'diag-preview';
    preview.textContent = event.result_preview;
    details.appendChild(preview);
    row.appendChild(details);
  }

  return row;
}

function empty(message) {
  const div = document.createElement('div');
  div.className = 'diag-empty';
  div.textContent = message;
  return div;
}

async function resolveAgentName() {
  if (!agentId) {
    nameEl.textContent = 'All agents';
    return;
  }
  nameEl.textContent = agentId;
  try {
    const data = await API.agents();
    const match = (data.agents || []).find(a => a.id === agentId);
    if (match && match.name) nameEl.textContent = match.name;
  } catch (e) {
    /* Keep the raw id if the agent list cannot be read. */
  }
}

async function render() {
  listEl.innerHTML = '';
  listEl.appendChild(empty('Loading…'));
  try {
    const payload = await API.toolLog(500, agentId);
    const events = payload.events || [];

    /* Tool-execution events carry stage="tool". If the log predates that
       field, fall back to any event that names a tool. */
    let rows = events.filter(e => e.stage === 'tool' && e.tool);
    if (!rows.length) rows = events.filter(e => !e.stage && e.tool);

    const failed = rows.filter(e => !isOk(e)).length;
    totalEl.textContent = `${rows.length} call${rows.length === 1 ? '' : 's'}`;
    okEl.textContent = `${rows.length - failed} OK`;
    badEl.textContent = `${failed} failed`;

    listEl.innerHTML = '';
    if (!rows.length) {
      listEl.appendChild(empty(payload.log_exists
        ? 'No tool executions recorded for this agent yet.'
        : 'No tool log yet — it appears once an agent runs a tool.'));
    } else {
      rows.slice().reverse().forEach(e => listEl.appendChild(makeRow(e)));
    }
    updatedEl.textContent = 'Updated ' + new Date().toLocaleTimeString();
  } catch (error) {
    listEl.innerHTML = '';
    listEl.appendChild(empty('Could not load the tool log: ' + error.message));
  }
}

function setAuto(on) {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  if (on) timer = setInterval(render, 3000);
}

async function clearLog() {
  const scope = agentId
    ? `this agent (${nameEl.textContent})`
    : 'EVERY agent';
  if (!window.confirm(`Clear the tool log for ${scope}? This cannot be undone.`)) return;
  refreshBtn.disabled = true;
  clearBtn.disabled = true;
  try {
    const result = await API.toolLogClear(agentId);
    updatedEl.textContent = `Cleared ${result.cleared} event(s).`;
    await render();
  } catch (error) {
    listEl.innerHTML = '';
    listEl.appendChild(empty('Could not clear the tool log: ' + error.message));
  } finally {
    refreshBtn.disabled = false;
    clearBtn.disabled = false;
  }
}

refreshBtn.addEventListener('click', render);
clearBtn.addEventListener('click', clearLog);
autoBox.addEventListener('change', () => setAuto(autoBox.checked));

resolveAgentName().then(render);
