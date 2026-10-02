/* Project Manager API client module */
const API = {
  async request(method, url, body = null) {
    const options = { method };
    if (body) {
      options.headers = { 'Content-Type': 'application/json' };
      options.body = JSON.stringify(body);
    }
    const res = await fetch(url, options);
    if (!res.ok) {
      let detail = '';
      try {
        const err = await res.json();
        detail = err.detail || '';
      } catch (e) {
        detail = '';
      }
      const error = new Error(detail || `Request failed: ${res.status}`);
      /* The status rides along on the error so a caller can tell
         "not there yet" (404) from "refused" (403/500) without having
         to match on the message text. */
      error.status = res.status;
      throw error;
    }
    if (res.status === 204 || !res.headers.get('content-type')?.includes('application/json')) {
      return {};
    }
    return res.json();
  },

  health() {
    return this.request('GET', '/api/health');
  },

  /* ---- Scope handling ----
     A null scope selects the browser view, where paths may carry
     a browser-root prefix (workspace/..., source_files/...). An
     explicit 'workspace' or 'app' keeps the legacy single-root
     view. Omitting the parameter entirely is what makes the API
     return the browser tree. */

  withPath(path, scope) {
    const params = new URLSearchParams({ path });
    if (scope) params.set('scope', scope);
    return params.toString();
  },

  withScope(body, scope) {
    if (!scope) return body;
    return { ...body, scope };
  },

  /* ``roots`` is a list of browser-root names the caller wants shown.
     Omitted (the default) means all of them, so every existing caller
     keeps the full tree. */
  project(scope = null, roots = null) {
    const params = new URLSearchParams();
    if (scope) params.set('scope', scope);
    if (roots && roots.length) params.set('roots', roots.join(','));
    const query = params.toString();
    return this.request('GET', '/api/project' + (query ? `?${query}` : ''));
  },

  fileRead(path, scope = null) {
    return this.request('GET', `/api/file/read?${this.withPath(path, scope)}`);
  },

  fileWrite(path, content, scope = null) {
    return this.request('PUT', '/api/file/write', this.withScope({ path, content }, scope));
  },

  fileCreate(path, content = '', scope = null) {
    return this.request('POST', '/api/file/create', this.withScope({ path, content }, scope));
  },

  fileDelete(path, scope = null) {
    return this.request('DELETE', `/api/file/delete?${this.withPath(path, scope)}`);
  },

  directoryCreate(path, scope = null) {
    return this.request('POST', `/api/directory/create?${this.withPath(path, scope)}`);
  },

  directoryDelete(path, scope = null) {
    return this.request('DELETE', `/api/directory/delete?${this.withPath(path, scope)}`);
  },

  pathRename(oldPath, newPath, scope = null) {
    return this.request('PUT', '/api/path/rename', this.withScope({ old_path: oldPath, new_path: newPath }, scope));
  },

  chatSend(message, agent_id = null, model = null) {
    return this.request('POST', '/api/chat', { message, agent_id, model });
  },

  /* Chat history is scoped per agent. Omitting the agent returns
     the whole log, which is what headless_app expects. */
  chatHistory(limit = 100, agent = null) {
    const params = new URLSearchParams({ limit });
    if (agent) params.set('agent', agent);
    return this.request('GET', `/api/chat?${params.toString()}`);
  },

  chatClear(agent = null) {
    const query = agent ? `?agent=${encodeURIComponent(agent)}` : '';
    return this.request('DELETE', `/api/chat${query}`);
  },

  /* ---- Saved chat sessions ----
     A session is a stored copy of one agent's thread. Sessions are
     per agent, so the agent is sent with every call. */

  chatSessions(agent = null) {
    const query = agent ? `?agent=${encodeURIComponent(agent)}` : '';
    return this.request('GET', `/api/chat/sessions${query}`);
  },

  chatSessionSave(agent, title = null) {
    return this.request('POST', '/api/chat/sessions', { agent_id: agent, title });
  },

  chatSession(id, agent = null) {
    const query = agent ? `?agent=${encodeURIComponent(agent)}` : '';
    return this.request('GET', `/api/chat/sessions/${encodeURIComponent(id)}${query}`);
  },

  chatSessionDelete(id, agent = null) {
    const query = agent ? `?agent=${encodeURIComponent(agent)}` : '';
    return this.request('DELETE', `/api/chat/sessions/${encodeURIComponent(id)}${query}`);
  },

  /* Built as a URL rather than fetched: the endpoint answers with a
     Content-Disposition attachment, and a plain link hands the file
     to the browser's download handling (i.e. the user's disk). */
  chatSessionExportUrl(id, agent = null, format = 'md') {
    const params = new URLSearchParams({ format });
    if (agent) params.set('agent', agent);
    return `/api/chat/sessions/${encodeURIComponent(id)}/export?${params.toString()}`;
  },

  sessions() {
    return this.request('GET', '/api/sessions');
  },

  /* ---- Agent engine ---- */

  agents() {
    return this.request('GET', '/api/agents');
  },

  agentDefinition(id) {
    return this.request('GET', `/api/agents/${encodeURIComponent(id)}`);
  },

  agentRun(body) {
    return this.request('POST', '/api/agents/run', body);
  },

  pipelineOptions() {
    return this.request('GET', '/api/pipeline');
  },

  pipelineRun(body) {
    return this.request('POST', '/api/pipeline', body);
  },

  models() {
    return this.request('GET', '/api/models');
  },

  /* The headless engine's tool log (data/toollog/tool_usage.jsonl),
     read back through the server. This is the agent's own record of what
     it executed, so it is separate from the chat history above: clearing
     or reading one never touches the other. */

  toolLog(limit = 100, agent = null, tool = null) {
    const params = new URLSearchParams({ limit });
    if (agent) params.set('agent', agent);
    if (tool) params.set('tool', tool);
    return this.request('GET', `/api/tool-log?${params.toString()}`);
  },

  /* Wipe the tool log, or one agent's events. Never touches chat history. */
  toolLogClear(agent = null) {
    const query = agent ? `?agent=${encodeURIComponent(agent)}` : '';
    return this.request('DELETE', `/api/tool-log${query}`);
  },

  /* The tool IDs agent.json's "tools" may name. Served from the engine
     registry so a frontend never keeps its own copy of the list. */
  tools() {
    return this.request('GET', '/api/tools');
  }
};

export default API;
