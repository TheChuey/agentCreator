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
      throw new Error(detail || `Request failed: ${res.status}`);
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

  project(scope = null) {
    const params = new URLSearchParams();
    if (scope) params.set('scope', scope);
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
  }
};

export default API;
