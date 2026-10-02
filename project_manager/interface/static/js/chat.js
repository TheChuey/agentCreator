/* Chat popup module */
import API from './api.js';
import Session from './session.js';
import { assignAgentColors } from './agentColors.js';
import { initTopbar, openPopup } from './topbar.js';

const log = document.getElementById('chatLog');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const sendBtn = document.getElementById('chatSend');
const status = document.getElementById('chatStatus');
const agentSelect = document.getElementById('agentSelect');
const modelSelect = document.getElementById('modelSelect');
const agentChip = document.getElementById('activeAgentChip');
const agentName = document.getElementById('activeAgentName');
const savedChatsList = document.getElementById('savedChatsList');

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
  /* Every real message gets a copy button; the handler is the global
     copyMsg() in chat.html, shared with the saved-session rows. */
  const actions = document.createElement('span');
  actions.className = 'msg-actions';
  const copyBtn = document.createElement('button');
  copyBtn.type = 'button';
  copyBtn.className = 'btn-msg-action';
  copyBtn.title = 'Copy this message';
  copyBtn.innerHTML = '<i data-lucide="copy" style="width:13px;"></i> Copy';
  copyBtn.addEventListener('click', () => copyText(body.textContent, 'Message copied to clipboard'));
  actions.appendChild(copyBtn);
  line.appendChild(actions);
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
  if (window.lucide) window.lucide.createIcons();
}

/* Clipboard write with a textarea fallback, because the async
   clipboard API is unavailable on http:// origins. */
function copyText(text, message) {
  const area = document.createElement('textarea');
  area.value = text;
  document.body.appendChild(area);
  area.select();
  try {
    document.execCommand('copy');
    showToast(message);
  } catch (e) {
    showToast('Copy failed - select the text manually');
  } finally {
    document.body.removeChild(area);
  }
}

/* A call that executed but whose operation failed shows as a failure, not
   as its transport status: the engine records status "success" for every
   call it managed to run, and op_ok for whether the operation worked. */
function toolVerdict(t) {
  if (t.op_ok === false) return 'FAILED';
  if (t.status === 'error') return 'ERROR';
  if (t.status === 'missing') return 'MISSING';
  return 'ok';
}

function toolDetail(t) {
  const verdict = toolVerdict(t);
  const parts = [`› ${t.tool} [${verdict}]`];
  const args = t.args ? JSON.stringify(t.args) : '';
  if (args) parts.push(args.slice(0, 400));
  const why = t.op_error || t.error;
  if (why) parts.push(`\n   ${why}`);
  return parts.join(' ');
}

function appendTools(tools) {
  if (!tools || !tools.length) return;
  const detail = document.createElement('details');
  detail.className = 'msg event';
  const summary = document.createElement('summary');
  summary.className = 'msg-label';
  const failed = tools.filter(t => toolVerdict(t) !== 'ok').length;
  const names = tools.map(t => t.tool || '').filter(Boolean).join(', ');
  summary.textContent = failed
    ? `Tools used: ${names} (${failed} failed)`
    : `Tools used: ${names}`;
  detail.appendChild(summary);
  const body = document.createElement('div');
  body.className = 'msg-body';
  body.textContent = tools.map(toolDetail).join('\n');
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
    /* Each agent has its own thread and its own saved sessions, so
       swap both. */
    await loadHistory();
    await renderSavedChats();
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

/* Open the per-agent diagnostics window for the tool log. A named target
   means a second click reuses the window instead of stacking copies. The
   active agent rides in the query string so the page can filter the engine
   tool log to that agent alone. */
window.openDiagnostic = () => {
  const id = activeAgentId();
  const url = '/diagnostic' + (id ? `?agent=${encodeURIComponent(id)}` : '');
  openPopup(url, { name: 'PMDiagnostic', width: 1100, height: 820 });
};

/* The agent must be resolved before history loads, otherwise the
   first paint would show the previous agent's thread. */
initTopbar({ page: 'chat' });
populateSelectors()
  .then(() => {
    loadHistory();
    renderSavedChats();
  })
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

/* ================================================================
   SAVED CHAT SESSIONS
   ================================================================
   A session is a stored copy of one agent's thread, kept on the
   server under workspace/data/chat_sessions/<agent_id>/. Each row
   can be reopened, copied to the clipboard, downloaded to disk or
   deleted. The live thread is never modified by any of this. */

function sessionText(record) {
  const lines = [
    `# ${record.title || 'Chat session'}`,
    '',
    `Agent: ${record.agent_id}`,
    `Saved: ${record.created || ''}`,
    ''
  ];
  for (const entry of record.entries || []) {
    const who = entry.sender === 'user' ? 'You' : (entry.agent || 'Agent');
    const ts = entry.ts ? new Date(entry.ts).toLocaleString() : '';
    lines.push(`## ${who}${ts ? ' - ' + ts : ''}`, '', entry.message || '', '');
  }
  return lines.join('\n');
}

function sessionStamp(created) {
  if (!created) return '';
  const when = new Date(created);
  if (isNaN(when.getTime())) return created;
  return when.toLocaleString();
}

function rowAction(icon, title, handler) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'btn-row-action';
  btn.title = title;
  btn.setAttribute('aria-label', title);
  btn.innerHTML = `<i data-lucide="${icon}" style="width:13px;"></i>`;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    handler();
  });
  return btn;
}

function sessionRow(session) {
  const agentId = activeAgentId();
  const item = document.createElement('div');
  item.className = 'saved-chat-item';
  item.title = 'Open this saved session';

  const info = document.createElement('div');
  info.className = 'saved-chat-info';
  const title = document.createElement('div');
  title.className = 'saved-chat-title';
  title.textContent = session.title || session.id;
  const meta = document.createElement('div');
  meta.className = 'saved-chat-date';
  const count = session.entry_count === 1 ? '1 message' : `${session.entry_count} messages`;
  meta.textContent = `${count} · ${sessionStamp(session.created)}`;
  info.appendChild(title);
  info.appendChild(meta);

  const actions = document.createElement('div');
  actions.className = 'saved-chat-actions';

  actions.appendChild(rowAction('message-square', 'Open in chat', () => {
    openSavedSession(session.id, agentId);
  }));

  actions.appendChild(rowAction('copy', 'Copy transcript', () => {
    copySavedSession(session.id, agentId);
  }));

  /* An anchor, not a button: the endpoint answers with a
     Content-Disposition attachment, so a plain link hands the file
     to the browser's own download handling and can also be
     right-clicked into "Save as". */
  const download = document.createElement('a');
  download.className = 'btn-row-action';
  download.href = API.chatSessionExportUrl(session.id, agentId, 'md');
  download.download = '';
  download.title = 'Download to disk (.md)';
  download.setAttribute('aria-label', 'Download to disk');
  download.innerHTML = '<i data-lucide="download" style="width:13px;"></i>';
  download.addEventListener('click', (e) => e.stopPropagation());
  actions.appendChild(download);

  const jsonDownload = document.createElement('a');
  jsonDownload.className = 'btn-row-action';
  jsonDownload.href = API.chatSessionExportUrl(session.id, agentId, 'json');
  jsonDownload.download = '';
  jsonDownload.title = 'Download raw data (.json)';
  jsonDownload.setAttribute('aria-label', 'Download raw data');
  jsonDownload.innerHTML = '<i data-lucide="braces" style="width:13px;"></i>';
  jsonDownload.addEventListener('click', (e) => e.stopPropagation());
  actions.appendChild(jsonDownload);

  actions.appendChild(rowAction('trash-2', 'Delete this saved session', () => {
    deleteSavedSession(session, agentId);
  }));

  item.appendChild(info);
  item.appendChild(actions);
  item.addEventListener('click', () => openSavedSession(session.id, agentId));
  return item;
}

function emptySessionRow(text) {
  const item = document.createElement('div');
  item.className = 'saved-chat-empty';
  item.textContent = text;
  return item;
}

async function renderSavedChats() {
  if (!savedChatsList) return;
  const agentId = activeAgentId();
  savedChatsList.innerHTML = '';
  if (!agentId) {
    savedChatsList.appendChild(emptySessionRow('Select an agent to see its saved sessions.'));
    return;
  }
  try {
    const data = await API.chatSessions(agentId);
    const sessions = data.sessions || [];
    if (!sessions.length) {
      savedChatsList.appendChild(
        emptySessionRow(`No saved sessions for ${agentLabel(agentId)} yet. Use Save Session to keep a copy of this thread.`)
      );
      return;
    }
    for (const session of sessions) {
      savedChatsList.appendChild(sessionRow(session));
    }
    if (window.lucide) window.lucide.createIcons();
  } catch (e) {
    savedChatsList.appendChild(emptySessionRow('Could not load saved sessions: ' + e.message));
  }
}

async function saveCurrentChat() {
  const agentId = activeAgentId();
  if (!agentId) {
    showToast('Select an agent first');
    return;
  }
  const suggested = (log.textContent || '').trim().split('\n').pop();
  const title = prompt(
    `Save the current ${agentLabel(agentId)} thread as a named session:`,
    suggested ? suggested.slice(0, 60) : ''
  );
  if (title === null) return;
  try {
    const res = await API.chatSessionSave(agentId, title.trim() || null);
    await renderSavedChats();
    const saved = res.session || {};
    showToast(`Saved "${saved.title || saved.id}" (${saved.entry_count || 0} messages)`);
  } catch (e) {
    alert('Failed to save the session: ' + e.message);
  }
}

function showSession(record) {
  log.innerHTML = '';
  const entries = record.entries || [];
  if (!entries.length) {
    appendLine('system', 'This saved session has no messages.');
    return;
  }
  for (const entry of entries) {
    const ts = entry.ts ? new Date(entry.ts).toLocaleTimeString() : '';
    const who = entry.agent ? agentLabel(entry.agent) : null;
    appendLine(entry.sender === 'user' ? 'user' : 'system', entry.message, ts, who);
  }
  setStatus(`Loaded saved session: ${record.title || record.id}`);
}

async function openSavedSession(sessionId, agentId) {
  try {
    const record = await API.chatSession(sessionId, agentId);
    showSession(record);
    showToast(`Loaded "${record.title || sessionId}"`);
  } catch (e) {
    alert('Failed to open the session: ' + e.message);
  }
}

async function copySavedSession(sessionId, agentId) {
  try {
    const record = await API.chatSession(sessionId, agentId);
    copyText(sessionText(record), 'Session copied to clipboard');
  } catch (e) {
    alert('Failed to copy the session: ' + e.message);
  }
}

async function deleteSavedSession(session, agentId) {
  const label = session.title || session.id;
  if (!confirm(`Delete the saved session "${label}"? The live chat history is not affected.`)) return;
  try {
    await API.chatSessionDelete(session.id, agentId);
    await renderSavedChats();
    showToast('Saved session deleted');
  } catch (e) {
    alert('Failed to delete the session: ' + e.message);
  }
}

window.scaffoldNewAgent = scaffoldNewAgent;
window.wipeChat = wipeChat;
window.saveCurrentChat = saveCurrentChat;
