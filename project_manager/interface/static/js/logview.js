/* Unified log viewer.

   Reads GET /api/logs, which merges the engine's chat, tool and pipeline
   logs with the header-test report into one row shape:

       {id, ts, source, agent, level, message, detail, pinned}

   Filtering is done client-side over the fetched batch, so switching a
   filter is instant (the API also filters for other callers). Pinning is
   server-side, so a saved row survives a reload.

   The × hides a row from this view only. It deliberately does not rewrite
   an append-only log line, which would desync the chat memory the engine
   replays; deleting a whole source is the Clear logs button. */

import API from './api.js';
import { initTopbar } from './topbar.js';

initTopbar({ page: 'logs' });

const ROW_LIMIT = 500;
const FONT_KEY = 'pm.logs.fontSize';
const FONT_MIN = 12;
const FONT_MAX = 24;
const FONT_DEFAULT = 16;
const LEVEL_CLASS = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  DEBUG: 'debug'
};

const listEl = document.getElementById('logList');
const logCountEl = document.getElementById('logCount');
const savedCountEl = document.getElementById('savedCount');
const updatedEl = document.getElementById('updatedAt');
const refreshBtn = document.getElementById('refreshBtn');
const clearBtn = document.getElementById('clearBtn');
const autoBox = document.getElementById('autoRefresh');
const sourceFilter = document.getElementById('sourceFilter');
const levelFilter = document.getElementById('levelFilter');
const agentFilter = document.getElementById('agentFilter');
const fontSizeEl = document.getElementById('fontSize');

let rows = [];
const hidden = new Set();
let timer = null;

function levelClass(level) {
  return LEVEL_CLASS[String(level || '').toUpperCase()] || 'info';
}

function clampFontSize(value) {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed)) return FONT_DEFAULT;
  return Math.min(FONT_MAX, Math.max(FONT_MIN, parsed));
}

function applyFontSize(value) {
  const size = clampFontSize(value);
  document.documentElement.style.setProperty('--log-font-size', size + 'px');
  fontSizeEl.value = String(size);
  return size;
}

function initFontSize() {
  for (let size = FONT_MIN; size <= FONT_MAX; size += 1) {
    const opt = document.createElement('option');
    opt.value = String(size);
    opt.textContent = size + 'px';
    fontSizeEl.appendChild(opt);
  }

  let stored = FONT_DEFAULT;
  try {
    stored = clampFontSize(window.localStorage.getItem(FONT_KEY));
  } catch (error) {
    stored = FONT_DEFAULT;
  }
  applyFontSize(stored);

  fontSizeEl.addEventListener('change', () => {
    const size = applyFontSize(fontSizeEl.value);
    try {
      window.localStorage.setItem(FONT_KEY, String(size));
    } catch (error) {
      /* storage unavailable (private mode): keep the in-memory size */
    }
  });
}

function formatTime(ts) {
  if (!ts) return '';
  const when = new Date(ts);
  if (Number.isNaN(when.getTime())) return ts;
  return when.toLocaleTimeString();
}

function fullTime(ts) {
  if (!ts) return '';
  const when = new Date(ts);
  return Number.isNaN(when.getTime()) ? ts : when.toLocaleString();
}

function matches(row) {
  if (sourceFilter.value && row.source !== sourceFilter.value) return false;
  if (levelFilter.value && row.level !== levelFilter.value) return false;
  if (agentFilter.value && row.agent !== agentFilter.value) return false;
  return true;
}

function updateCounts(visible) {
  logCountEl.textContent = `${visible.length} log${visible.length === 1 ? '' : 's'}`;
  const saved = visible.filter(row => row.pinned).length;
  savedCountEl.textContent = `${saved} saved log${saved === 1 ? '' : 's'}`;
}

function makeEntry(row) {
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  entry.dataset.id = row.id;

  const el = document.createElement('div');
  el.className = 'log-row'
    + (row.pinned ? ' saved' : '')
    + (row.level === 'ERROR' ? ' bad' : '');

  const check = document.createElement('input');
  check.type = 'checkbox';
  check.className = 'save-check';
  check.checked = !!row.pinned;
  check.title = 'Save this entry';
  check.addEventListener('change', () => togglePin(row, check));
  el.appendChild(check);

  const time = document.createElement('span');
  time.className = 'log-time';
  time.textContent = formatTime(row.ts);
  time.title = fullTime(row.ts);
  el.appendChild(time);

  const source = document.createElement('span');
  source.className = 'log-source';
  source.dataset.source = row.source;
  source.textContent = row.source || '?';
  el.appendChild(source);

  const agent = document.createElement('span');
  agent.className = 'log-agent';
  agent.textContent = row.agent || '\u2014';
  agent.title = row.agent || '';
  el.appendChild(agent);

  const level = document.createElement('span');
  level.className = 'log-level ' + levelClass(row.level);
  level.textContent = String(row.level || 'INFO').toUpperCase();
  el.appendChild(level);

  const message = document.createElement('span');
  message.className = 'log-message';
  message.textContent = row.message || '';
  message.title = 'Click for details';
  el.appendChild(message);

  const del = document.createElement('button');
  del.type = 'button';
  del.className = 'delete-btn';
  del.title = 'Hide this row (does not delete the log)';
  del.textContent = '\u00d7';
  del.addEventListener('click', () => hideRow(row.id));
  el.appendChild(del);

  const detail = document.createElement('div');
  detail.className = 'log-detail';
  detail.hidden = true;
  detail.textContent = JSON.stringify(row.detail === undefined ? {} : row.detail, null, 2);

  message.addEventListener('click', () => { detail.hidden = !detail.hidden; });

  entry.appendChild(el);
  entry.appendChild(detail);
  return entry;
}

function render() {
  const visible = rows.filter(row => !hidden.has(row.id) && matches(row));
  listEl.innerHTML = '';

  if (!visible.length) {
    const empty = document.createElement('div');
    empty.className = 'log-empty';
    empty.textContent = rows.length
      ? 'No rows match the current filters.'
      : 'No logs yet \u2014 they appear once an agent runs.';
    listEl.appendChild(empty);
  } else {
    visible.forEach(row => listEl.appendChild(makeEntry(row)));
  }

  updateCounts(visible);
}

async function togglePin(row, checkbox) {
  const pinned = checkbox.checked;
  try {
    await API.logPin(row.id, pinned);
    row.pinned = pinned;
    checkbox.closest('.log-row').classList.toggle('saved', pinned);
    updateCounts(rows.filter(r => !hidden.has(r.id) && matches(r)));
  } catch (error) {
    checkbox.checked = !pinned;
    updatedEl.textContent = 'Could not save: ' + error.message;
  }
}

function hideRow(id) {
  hidden.add(id);
  render();
}

function fillAgents() {
  const current = agentFilter.value;
  const agents = Array.from(new Set(rows.map(r => r.agent).filter(Boolean))).sort();

  agentFilter.innerHTML = '';
  const all = document.createElement('option');
  all.value = '';
  all.textContent = 'All';
  agentFilter.appendChild(all);

  agents.forEach(agent => {
    const opt = document.createElement('option');
    opt.value = agent;
    opt.textContent = agent;
    agentFilter.appendChild(opt);
  });

  agentFilter.value = agents.includes(current) ? current : '';
}

async function refresh() {
  refreshBtn.disabled = true;
  try {
    const payload = await API.logRows(ROW_LIMIT);
    rows = payload.rows || [];
    fillAgents();
    render();
    updatedEl.textContent = 'Updated ' + new Date().toLocaleTimeString();
  } catch (error) {
    listEl.innerHTML = '';
    const empty = document.createElement('div');
    empty.className = 'log-empty';
    empty.textContent = 'Could not load logs: ' + error.message;
    listEl.appendChild(empty);
  } finally {
    refreshBtn.disabled = false;
  }
}

async function clearLogs() {
  const scope = sourceFilter.value || 'EVERY source';
  if (!window.confirm(`Clear ${scope} logs? This cannot be undone.`)) return;
  clearBtn.disabled = true;
  refreshBtn.disabled = true;
  try {
    await API.logClear(sourceFilter.value || null);
    hidden.clear();
    await refresh();
  } catch (error) {
    updatedEl.textContent = 'Could not clear: ' + error.message;
  } finally {
    clearBtn.disabled = false;
    refreshBtn.disabled = false;
  }
}

function setAuto(on) {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  if (on) timer = setInterval(refresh, 5000);
}

refreshBtn.addEventListener('click', refresh);
clearBtn.addEventListener('click', clearLogs);
autoBox.addEventListener('change', () => setAuto(autoBox.checked));
sourceFilter.addEventListener('change', render);
levelFilter.addEventListener('change', render);
agentFilter.addEventListener('change', render);

initFontSize();
refresh();
