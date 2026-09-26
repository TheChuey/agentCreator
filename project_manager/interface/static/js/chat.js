/* Chat popup module */
import API from './api.js';
import Session from './session.js';
import { assignAgentColors } from './agentColors.js';
import { initTopbar } from './topbar.js';

const log = document.getElementById('chatLog');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const sendBtn = document.getElementById('chatSend');
const status = document.getElementById('chatStatus');
const agentSelect = document.getElementById('agentSelect');
const modelSelect = document.getElementById('modelSelect');
const agentChip = document.getElementById('activeAgentChip');
const agentName = document.getElementById('activeAgentName');

/* Agent id requested by the home page card, e.g. /chat?agent=rag_assistant */
const requestedAgent = new URLSearchParams(window.location.search).get('agent');

let agentColorById = new Map();

function appendLine(role, text, meta = '', labelText = null) {
  const line = document.createElement('div');
  line.className = 'msg ' + role;
  const label = document.createElement('span');
  label.className = 'msg-label';
  label.textContent = labelText
    || (role === 'user' ? 'You' : role === 'event' ? 'Event' : 'System');
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

function activeAgentId() {
  return agentSelect && agentSelect.value ? agentSelect.value : null;
}

function agentLabel(id) {
  if (!id) return 'No agent selected';
  const opt = agentSelect ? agentSelect.querySelector(`option[value="${CSS.escape(id)}"]`) : null;
  return opt ? opt.textContent : id;
}

function paintAgentChip() {
  const id = activeAgentId();
  if (!agentChip || !agentName) return;
  if (!id) {
    agentChip.hidden = true;
    return;
  }
  const color = agentColorById.get(id) || '#4fc3f7';
  agentChip.style.setProperty('--agent-color', color);
  agentName.textContent = agentLabel(id);
  agentChip.hidden = false;
  if (input) {
    input.placeholder = `Message ${agentLabel(id)}...`;
  }
}

async function populateAgents() {
  try {
    const data = await API.agents();
    const agents = data.agents || [];
    agentColorById = assignAgentColors(agents);
    const savedAgent = localStorage.getItem('pmAgent');
    agentSelect.innerHTML = '';
    for (const a of agents) {
      const opt = document.createElement('option');
      opt.value = a.id;
      opt.textContent = a.source === 'workspace' ? `${a.name} (ws)` : a.name;
      if (a.id === savedAgent) opt.selected = true;
      agentSelect.appendChild(opt);
    }
    /* An explicit ?agent= from a home card outranks the saved choice. */
    const preferred = agents.some(a => a.id === requestedAgent) ? requestedAgent : savedAgent;
    if (preferred) agentSelect.value = preferred;
    if (!agentSelect.value && agents.length) agentSelect.value = agents[0].id;
    if (agentSelect.value) localStorage.setItem('pmAgent', agentSelect.value);
    paintAgentChip();
  } catch (e) {
    console.warn('Failed to load agents', e);
  }
}

async function populateModels() {
  try {
    const data = await API.models();
    const models = data.models || [];
    const savedModel = localStorage.getItem('pmModel') || '';
    modelSelect.innerHTML = '';
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
}

async function populateSelectors() {
  await populateAgents();
  await populateModels();

  agentSelect.addEventListener('change', async () => {
    localStorage.setItem('pmAgent', agentSelect.value);
    paintAgentChip();
    /* Each agent has its own thread, so swap the transcript. */
    await loadHistory();
  });

  modelSelect.addEventListener('change', () => {
    localStorage.setItem('pmModel', modelSelect.value);
  });
}

async function refreshAgents() {
  await populateAgents();
}

async function loadHistory() {
  try {
    const data = await API.chatHistory(100, activeAgentId());
    const entries = data.entries || [];
    log.innerHTML = '';
    if (!entries.length) {
      const who = agentLabel(activeAgentId());
      appendLine('system', `No messages yet with ${who}. Say hello!`);
      return;
    }
    for (const entry of entries) {
      const ts = entry.ts ? new Date(entry.ts).toLocaleTimeString() : '';
      const who = entry.agent ? agentLabel(entry.agent) : null;
      appendLine(entry.sender === 'user' ? 'user' : 'system', entry.message, ts, who);
    }
  } catch (error) {
    setStatus('Failed to load history: ' + error.message);
  }
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;
  const agentId = activeAgentId();
  input.value = '';
  appendLine('user', message, new Date().toLocaleTimeString());
  setStatus('Running agent…');
  sendBtn.disabled = true;
  try {
    const result = await API.chatSend(
      message,
      agentId,
      modelSelect ? modelSelect.value || null : null
    );
    const who = agentLabel(result.agent_id || agentId);
    appendLine('system', result.reply || '(empty reply)', new Date().toLocaleTimeString(), who);
    appendTools(result.tool_events || []);
    setStatus(`${who} · ${result.model || 'model'} replied.`);
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

/* The agent must be resolved before history loads, otherwise the
   first paint would show the previous agent's thread. */
initTopbar({ page: 'chat' });
populateSelectors()
  .then(loadHistory)
  .catch((e) => setStatus('Failed to start: ' + e.message));
Session.connect();

// ---- New agent scaffold + wipe chat (exposed for inline handlers) ----

async function scaffoldNewAgent() {
  const name = prompt('New agent id / folder name (e.g. "doc_writer"):');
  if (!name) return;
  if (!/^[A-Za-z0-9_\-]+$/.test(name)) {
    alert('Use only letters, numbers, underscore or dash.');
    return;
  }
  const rel = `workspace/agents/${name}`;
  const json = JSON.stringify({
    id: name,
    name: name.replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    description: 'A custom agent scaffolded from the AI Agent Creator.',
    mode: 'agent',
    model: '',
    tools: ['map_files', 'read_file', 'write_text_file']
  }, null, 2);
  const md =
    `# ${name}\n` +
    `\n## role\n` +
    `\nYou are ${name}, a helpful Project Manager agent.\n` +
    `\n## purpose\n` +
    `\nDescribe what this agent accomplishes and when it is used.\n` +
    `\n## boundaries\n` +
    `\nState what this agent will not do.\n` +
    `\n## output format\n` +
    `\nDescribe the shape of the reply the agent must produce.\n`;
  try {
    await API.fileCreate(`${rel}/agent.json`, json);
    await API.fileCreate(`${rel}/agent.md`, md);
    localStorage.setItem('pmAgent', name);
    await refreshAgents();
    window.open(`/editor?path=${encodeURIComponent(`${rel}/agent.json`)}&root=workspace`, '_blank');
    setStatus(`Created ${rel}/agent.json + agent.md`);
    showToast(`Agent '${name}' created`);
  } catch (e) {
    alert('Failed to scaffold agent: ' + e.message);
  }
}

async function wipeChat() {
  const who = agentLabel(activeAgentId());
  if (!confirm(`Wipe the chat history with ${who}? This cannot be undone.`)) return;
  try {
    const res = await API.chatClear(activeAgentId());
    log.innerHTML = '';
    appendLine('system', `Chat history with ${who} wiped${res.cleared ? ` (${res.cleared} entries removed)` : ''}.`);
    setStatus('Chat history cleared');
    showToast('Chat history cleared');
  } catch (e) {
    setStatus('Wipe failed: ' + e.message);
    alert('Failed to clear chat: ' + e.message);
  }
}

window.scaffoldNewAgent = scaffoldNewAgent;
window.wipeChat = wipeChat;
