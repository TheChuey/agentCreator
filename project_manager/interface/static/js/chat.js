/* Chat popup module */
import API from './api.js';
import Session from './session.js';

const log = document.getElementById('chatLog');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const sendBtn = document.getElementById('chatSend');
const status = document.getElementById('chatStatus');
const agentSelect = document.getElementById('agentSelect');
const modelSelect = document.getElementById('modelSelect');

function appendLine(role, text, meta = '') {
  const line = document.createElement('div');
  line.className = 'msg ' + role;
  const label = document.createElement('span');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'You' : role === 'event' ? 'Event' : 'System';
  const body = document.createElement('span');
  body.className = 'msg-body';
  body.textContent = text;
  line.appendChild(label);
  line.appendChild(body);
  if (meta) {
    const ts = document.createElement('span');
    ts.className = 'msg-meta';
    ts.textContent = meta;
    line.appendChild(ts);
  }
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function appendTools(tools) {
  if (!tools || !tools.length) return;
  const detail = document.createElement('details');
  detail.className = 'msg event';
  const summary = document.createElement('summary');
  summary.className = 'msg-label';
  summary.textContent = 'Tools used: ' + tools.map(t => t.tool || '').filter(Boolean).join(', ');
  detail.appendChild(summary);
  const body = document.createElement('div');
  body.className = 'msg-body';
  body.textContent = tools.map(t => {
    const args = t.args ? JSON.stringify(t.args).slice(0, 400) : '';
    const ok = t.op_ok ? 'ok' : (t.status || '?');
    return `› ${t.tool} (${ok}) ${args}`;
  }).join('\n');
  detail.appendChild(body);
  log.appendChild(detail);
  log.scrollTop = log.scrollHeight;
}

function setStatus(text) {
  if (status) status.textContent = text;
}

// ---- Agent / model selector population ----

async function populateSelectors() {
  try {
    const data = await API.agents();
    const agents = data.agents || [];
    const savedAgent = localStorage.getItem('pmAgent');
    for (const a of agents) {
      const opt = document.createElement('option');
      opt.value = a.id;
      opt.textContent = a.source === 'workspace' ? `${a.name} (ws)` : a.name;
      if (a.id === savedAgent) opt.selected = true;
      agentSelect.appendChild(opt);
    }
    if (!savedAgent && agents.length) agentSelect.value = agents[0].id;
    if (savedAgent) agentSelect.value = savedAgent;
  } catch (e) {
    console.warn('Failed to load agents', e);
  }

  agentSelect.addEventListener('change', () => {
    localStorage.setItem('pmAgent', agentSelect.value);
  });

  try {
    const data = await API.models();
    const models = data.models || [];
    const savedModel = localStorage.getItem('pmModel') || '';
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = 'default model';
    modelSelect.appendChild(empty);
    for (const m of models) {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.name;
      modelSelect.appendChild(opt);
    }
    if (savedModel) modelSelect.value = savedModel;
  } catch (e) {
    console.warn('Failed to load models', e);
  }

  modelSelect.addEventListener('change', () => {
    localStorage.setItem('pmModel', modelSelect.value);
  });
}

async function loadHistory() {
  try {
    const data = await API.chatHistory();
    const entries = data.entries || [];
    if (!entries.length) {
      appendLine('system', 'No messages yet. Say hello!');
      return;
    }
    for (const entry of entries) {
      const ts = entry.ts ? new Date(entry.ts).toLocaleTimeString() : '';
      appendLine(entry.sender === 'user' ? 'user' : 'system', entry.message, ts);
    }
  } catch (error) {
    setStatus('Failed to load history: ' + error.message);
  }
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  appendLine('user', message, new Date().toLocaleTimeString());
  setStatus('Running agent…');
  sendBtn.disabled = true;
  try {
    const result = await API.chatSend(
      message,
      agentSelect ? agentSelect.value || null : null,
      modelSelect ? modelSelect.value || null : null
    );
    const label = result.agent_id || 'agent';
    appendLine('system', result.reply || '(empty reply)', new Date().toLocaleTimeString());
    appendTools(result.tool_events || []);
    setStatus(`${label} · ${result.model || 'model'} replied.`);
  } catch (error) {
    setStatus('Send failed: ' + error.message);
  } finally {
    sendBtn.disabled = false;
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  sendMessage();
});

sendBtn.addEventListener('click', sendMessage);

Session.onEvent = (msg) => {
  if (msg.type === 'event' && msg.event) {
    const ev = msg.event;
    const what = ev.type || 'event';
    const path = ev.path || '';
    appendLine('event', what + (path ? ': ' + path : ''));
  }
};

loadHistory();
populateSelectors();
Session.connect();
