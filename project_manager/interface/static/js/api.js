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

  project(scope = 'workspace') {
    return this.request('GET', `/api/project?scope=${encodeURIComponent(scope)}`);
  },

  fileRead(path, scope = 'workspace') {
    return this.request('GET', `/api/file/read?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  fileWrite(path, content, scope = 'workspace') {
    return this.request('PUT', '/api/file/write', { path, content, scope });
  },

  fileCreate(path, content = '', scope = 'workspace') {
    return this.request('POST', '/api/file/create', { path, content, scope });
  },

  fileDelete(path, scope = 'workspace') {
    return this.request('DELETE', `/api/file/delete?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  directoryCreate(path, scope = 'workspace') {
    return this.request('POST', `/api/directory/create?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  directoryDelete(path, scope = 'workspace') {
    return this.request('DELETE', `/api/directory/delete?path=${encodeURIComponent(path)}&scope=${encodeURIComponent(scope)}`);
  },

  pathRename(oldPath, newPath, scope = 'workspace') {
    return this.request('PUT', '/api/path/rename', { old_path: oldPath, new_path: newPath, scope });
  },

  chatSend(message, agent_id = null, model = null) {
    return this.request('POST', '/api/chat', { message, agent_id, model });
  },

  chatHistory(limit = 100) {
    return this.request('GET', `/api/chat?limit=${limit}`);
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
