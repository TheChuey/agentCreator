/* Agent engine panel for the editor.
 *
 * Two jobs:
 *   1. RUN AGENT  - run the currently open agent definition
 *      (workspace/agents/<id>/agent.json + agent.md) against the engine.
 *   2. RUN PIPELINE - cascade MANY agents one after another: pick multiple,
 *      reorder the queue, send one message; each later agent receives every
 *      earlier agent's reply (feed-forward). Server-side stdout reports
 *      "Agent N (<id>) completed. Tools used: ..." for each step.
 */
import API from './api.js';

const state = {
  agents: [],       // all selectable agents (library + workspace)
  queue: [],        // ordered selected agents
  modelBox: null,
  jsonPath: null,   // run-agent target (workspace-relative)
  mdPath: null,
  ctx: null
};

const $ = (id) => document.getElementById(id);

export function initAgentsPanel(ctx) {
  state.ctx = ctx;

  // + Agent scaffold
  $('agentCreateBtn')?.addEventListener('click', scaffoldAgent);

  // Run Agent (single, current file)
  $('runAgentBtn')?.addEventListener('click', () => {
    if ($('agentPanel').classList.contains('hidden')) togglePanel();
    $('agentPrompt')?.focus();
  });
  $('runAgentBtnRun')?.addEventListener('click', runCurrentAgent);

  // Pipeline
  $('pipelineBtn')?.addEventListener('click', togglePanel);
  $('pipelineRunBtn')?.addEventListener('click', runPipeline);
  $('pipelineClearBtn')?.addEventListener('click', () => {
    state.queue = [];
    renderChecklist();
    renderQueue();
  });

  refreshEnabled();
  loadPanelData();
  updateRunTarget();
}

function togglePanel() {
  const panel = $('agentPanel');
  if (!panel) return;
  panel.classList.toggle('hidden');
  if (state.ctx && state.ctx.editorLayout) state.ctx.editorLayout();
}

function agentLabel(a) {
  return a.source === 'workspace' ? `${a.name} (ws)` : a.name;
}

/* ------------------------------------------------------------
   Panel data: agents + models
   ------------------------------------------------------------ */
async function loadPanelData() {
  try {
    const data = await API.agents();
    state.agents = data.agents || [];
    renderChecklist();
    renderQueue();
    updateRunTarget();
  } catch (e) {
    setPanel('pipelineAgents', 'Failed to load agents: ' + e.message);
  }

  try {
    const data = await API.models();
    const models = data.models || [];
    const box = $('modelBox');
    if (!box) return;
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = 'default model';
    box.appendChild(empty);
    for (const m of models) {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.name;
      box.appendChild(opt);
    }
  } catch (e) {
    // models are optional
  }
}

function activeModel() {
  return $('modelBox') ? $('modelBox').value || null : null;
}

/* ------------------------------------------------------------
   Checklist + queue
   ------------------------------------------------------------ */
function renderChecklist() {
  const host = $('pipelineAgents');
  if (!host) return;
  host.innerHTML = '';
  if (!state.agents.length) {
    host.textContent = 'No agents found.';
    return;
  }
  for (const a of state.agents) {
    const key = a.source === 'workspace' ? a.md_path : a.id;
    const row = document.createElement('label');
    row.className = 'agent-option';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = key;
    cb.checked = state.queue.some(q => q.key === key);
    cb.addEventListener('change', () => toggleAgent(a, cb.checked));
    row.appendChild(cb);
    row.append(agentLabel(a));
    host.appendChild(row);
  }
}

function toggleAgent(a, checked) {
  const key = a.source === 'workspace' ? a.md_path : a.id;
  if (checked) {
    if (!state.queue.some(q => q.key === key)) {
      state.queue.push({
        key,
        id: a.id,
        name: a.name,
        source: a.source,
        json_path: a.json_path || null,
        md_path: a.md_path || null
      });
    }
  } else {
    state.queue = state.queue.filter(q => q.key !== key);
  }
  renderQueue();
}

function moveStep(index, delta) {
  const target = index + delta;
  if (target < 0 || target >= state.queue.length) return;
  const [item] = state.queue.splice(index, 1);
  state.queue.splice(target, 0, item);
  renderQueue();
}

function renderQueue() {
  const host = $('pipelineQueue');
  if (!host) return;
  host.innerHTML = '';
  if (!state.queue.length) {
    host.textContent = 'Queue empty - tick agents above to add them.';
    return;
  }
  state.queue.forEach((q, i) => {
    const row = document.createElement('div');
    row.className = 'queue-item';

    const idx = document.createElement('span');
    idx.className = 'qidx';
    idx.textContent = (i + 1) + '.';
    row.appendChild(idx);

    const label = document.createElement('span');
    label.style.flex = '1';
    label.textContent = q.name;
    label.title = q.id;
    row.appendChild(label);

    const mk = (txt, fn) => {
      const b = document.createElement('button');
      b.textContent = txt;
      b.addEventListener('click', fn);
      row.appendChild(b);
    };
    mk('↑', () => moveStep(i, -1));
    mk('↓', () => moveStep(i, 1));
    mk('✕', () => {
      state.queue = state.queue.filter(x => x.key !== q.key);
      renderChecklist();
      renderQueue();
    });

    host.appendChild(row);
  });
}

/* ------------------------------------------------------------
   Run Agent (current file)
   ------------------------------------------------------------ */
function updateRunTarget() {
  const cf = state.ctx ? state.ctx.getCurrentFile() : null;
  const hint = $('runAgentHint');
  const btn = $('runAgentBtnRun'); // panel button text
  if (!cf) {
    state.jsonPath = state.mdPath = null;
    if (hint) hint.textContent = 'Open an agents/<id>/agent.json or agent.md to run it.';
    if (btn) btn.disabled = true;
    return;
  }
  const m = /^agents\/([^/]+)\/(agent\.json|agent\.md)$/.exec(cf);
  if (m) {
    state.jsonPath = `agents/${m[1]}/agent.json`;
    state.mdPath = `agents/${m[1]}/agent.md`;
    if (hint) hint.textContent = `Will run: ${m[1]} (${state.jsonPath})`;
    if (btn) btn.disabled = false;
  } else {
    state.jsonPath = state.mdPath = null;
    if (hint) hint.textContent = 'Open an agents/<id>/agent.json or agent.md to run it.';
    if (btn) btn.disabled = true;
  }
}

async function runCurrentAgent() {
  if (!state.jsonPath) {
    alert('Open an agents/<id>/agent.json or agent.md first.');
    return;
  }
  const message = $('agentPrompt').value.trim();
  if (!message) {
    alert('Enter an instruction for the agent.');
    return;
  }
  // Save the open file first so the run uses the latest edits.
  if (state.ctx && state.ctx.isDirty()) await state.ctx.saveFile();

  setPanel('agentResult', 'Running agent…');
  try {
    const res = await API.agentRun({
      json_path: state.jsonPath,
      md_path: state.mdPath,
      message,
      model: activeModel()
    });
    const tools = (res.tool_events || []).map(t => t.tool).filter(Boolean).join(', ') || 'none';
    renderResult('agentResult', [
      { head: `${res.name || res.agent_id} (${res.model || res.agent_id})`, text: res.reply || '(empty reply)' },
      { head: `Tools used: ${tools}`, text: '' }
    ]);
  } catch (e) {
    setPanel('agentResult', 'Error: ' + e.message);
  }
}

/* ------------------------------------------------------------
   Run Pipeline (cascade)
   ------------------------------------------------------------ */
async function runPipeline() {
  if (!state.queue.length) {
    alert('Tick at least one agent in the pipeline list.');
    return;
  }
  const message = $('pipelinePrompt').value.trim();
  if (!message) {
    alert('Enter the idea/message to cascade through the agents.');
    return;
  }
  if (state.ctx && state.ctx.isDirty()) await state.ctx.saveFile();

  const steps = state.queue.map(q => q.json_path
    ? { json_path: q.json_path, md_path: q.md_path }
    : q.id);

  setPanel('pipelineResult', 'Cascading ' + steps.length + ' agent(s)…');
  try {
    const res = await API.pipelineRun({ steps, message, model: activeModel() });
    const outputs = res.outputs || [];
    const parts = [];
    outputs.forEach((o, i) => {
      const tools = (o.tools_used || []).join(', ') || 'none';
      parts.push({ head: `✓ Agent ${i + 1} (${o.agent_name}) completed - tools: ${tools}`, text: o.output });
    });
    parts.push({ head: 'Final reply', text: res.reply });
    renderResult('pipelineResult', parts);
  } catch (e) {
    setPanel('pipelineResult', 'Error: ' + e.message);
  }
}

/* ------------------------------------------------------------
   Scaffold a new workspace agent
   ------------------------------------------------------------ */
async function scaffoldAgent() {
  const name = prompt('Agent id / folder name (e.g. "doc_writer"):');
  if (!name) return;
  if (!/^[A-Za-z0-9_\-]+$/.test(name)) {
    alert('Use only letters, numbers, underscore or dash.');
    return;
  }
  const rel = `agents/${name}`;
  const json = JSON.stringify({
    id: name,
    name: name.replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    description: 'A custom agent scaffolded from the editor.',
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
    state.queue = state.queue.filter(q => q.json_path !== `${rel}/agent.json`);
    loadPanelData();
    if (state.ctx) {
      await state.ctx.refreshTree();
      await state.ctx.openFile(`${rel}/agent.json`);
    }
    setPanel('agentResult', `Created ${rel}/agent.json + agent.md`);
  } catch (e) {
    alert('Failed to scaffold agent: ' + e.message);
  }
}

/* ------------------------------------------------------------
   Small rendering helpers
   ------------------------------------------------------------ */
function setPanel(id, text) {
  const el = $(id);
  if (el) {
    el.innerHTML = '';
    el.textContent = text;
  }
}

function renderResult(hostId, items) {
  const host = $(hostId);
  if (!host) return;
  host.innerHTML = '';
  items.forEach(it => {
    const card = document.createElement('div');
    card.className = 'result-box';
    const head = document.createElement('div');
    head.className = 'step-card-ok';
    head.textContent = it.head;
    card.appendChild(head);
    if (it.text) {
      const body = document.createElement('div');
      body.className = 'result-text';
      body.textContent = it.text;
      card.appendChild(body);
    }
    host.appendChild(card);
  });
}

function refreshEnabled() {
  // re-evaluated in updateRunTarget
}

export { updateRunTarget };