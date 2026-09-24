/* Project tree rendering module */
import API from './api.js';

/* Curated "important app scripts" shown as quick links in Dev view. */
const DEV_LINKS = [
  { name: 'server.py', icon: '🐍', path: 'server.py' },
  { name: 'README.md', icon: '📝', path: 'README.md' },
  { name: 'requirements.txt', icon: '📄', path: 'requirements.txt' },
  { name: 'parameters/filesystem.py', icon: '⚙️', path: 'parameters/filesystem.py' },
  { name: 'interface/core/operations.py', icon: '🧩', path: 'interface/core/operations.py' },
  { name: 'interface/core/defaults.py', icon: '🧩', path: 'interface/core/defaults.py' },
  { name: 'interface/routers/files.py', icon: '🌐', path: 'interface/routers/files.py' },
  { name: 'interface/routers/chat.py', icon: '🌐', path: 'interface/routers/chat.py' },
  { name: 'interface/clients/editor_client.py', icon: '🔗', path: 'interface/clients/editor_client.py' },
  { name: 'scripts/run.sh', icon: '⌨️', path: 'scripts/run.sh' },
  { name: 'scripts/run.bat', icon: '⌨️', path: 'scripts/run.bat' }
];

const Tree = {
  root: [],
  selectedPath: null,
  scope: 'workspace',
  expanded: new Set(),
  onFileSelect: null,
  onFolderSelect: null,
  onDevLink: null,

  async load(scope = 'workspace') {
    this.scope = scope;
    const data = await API.project(scope);
    this.root = data.filesystem || [];
    this.render();
  },

  key(path) {
    return this.scope + ':' + path;
  },

  render(containerId = 'tree') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    this.renderItems(this.root, container);
  },

  renderItems(items, container) {
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'tree-item';
      if (item.type === 'directory') {
        row.classList.add('folder');
        row.dataset.path = item.path;
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        const isExpanded = this.expanded.has(this.key(item.path));
        const toggle = document.createElement('span');
        toggle.className = 'toggle' + (isExpanded ? ' expanded' : '');
        toggle.textContent = isExpanded ? '−' : '+';
        const label = document.createElement('span');
        label.className = 'label';
        label.textContent = '📁 ' + item.name;
        row.appendChild(toggle);
        row.appendChild(label);
        const children = document.createElement('div');
        children.className = 'children' + (isExpanded ? '' : ' collapsed');
        row.onclick = () => {
          this.selectedPath = item.path;
          if (this.onFolderSelect) this.onFolderSelect(item.path);
          this.render();
          this.toggle(item.path);
        };
        container.appendChild(row);
        container.appendChild(children);
        this.renderItems(item.children || [], children);
      } else {
        row.textContent = this.getFileIcon(item.name) + ' ' + item.name;
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        row.onclick = () => {
          this.selectedPath = item.path;
          if (this.onFileSelect) this.onFileSelect(item.path);
          this.render();
        };
        container.appendChild(row);
      }
    }
  },

  toggle(path) {
    const key = this.key(path);
    if (this.expanded.has(key)) {
      this.expanded.delete(key);
    } else {
      this.expanded.add(key);
    }
    const container = document.getElementById('tree');
    if (!container) return;
    const row = container.querySelector('.tree-item.folder[data-path="' + path.replace(/"/g, '\\"') + '"]');
    if (!row) return;
    const toggle = row.querySelector('.toggle');
    toggle.classList.toggle('expanded');
    toggle.textContent = toggle.classList.contains('expanded') ? '−' : '+';
    const children = row.nextElementSibling;
    if (children && children.classList.contains('children')) {
      children.classList.toggle('collapsed');
    }
  },

  reveal(path) {
    const parts = path.split('/');
    for (let i = 1; i < parts.length; i++) {
      this.expanded.add(this.key(parts.slice(0, i).join('/')));
    }
    this.render();
  },

  setSelected(path) {
    this.selectedPath = path;
    this.render();
  },

  refresh() {
    return this.load(this.scope);
  },

  renderDevLinks(containerId = 'devLinks') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    for (const link of DEV_LINKS) {
      const row = document.createElement('button');
      row.className = 'dev-link';
      row.type = 'button';
      row.textContent = link.icon + ' ' + link.name;
      row.title = link.path;
      row.onclick = () => {
        if (this.onDevLink) this.onDevLink(link);
      };
      container.appendChild(row);
    }
  },

  getFileIcon(name) {
    const ext = name.split('.').pop().toLowerCase();
    const icons = {
      py: '🐍',
      html: '🌐', htm: '🌐',
      css: '🎨',
      js: '🟨', mjs: '🟨', jsx: '🟨',
      ts: '🔷', tsx: '🔷',
      json: '📋',
      md: '📝',
      sql: '🗄️',
      xml: '🧾',
      sh: '⌨️', bat: '⌨️', ps1: '⌨️',
      yaml: '⚙️', yml: '⚙️', toml: '⚙️', ini: '⚙️', cfg: '⚙️', env: '⚙️',
      txt: '📄', csv: '📄'
    };
    return icons[ext] || '📄';
  }
};

export default Tree;
