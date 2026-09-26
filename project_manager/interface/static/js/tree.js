/* Project tree rendering module */
import API from './api.js';

const Tree = {
  root: [],
  roots: {},
  activeRoot: null,
  selectedPath: null,
  expanded: new Set(),
  onFileSelect: null,
  onFolderSelect: null,
  onRootSelect: null,

  /* The top level of the tree is the set of browser roots, so the
     tree doubles as the folder switcher. Clicking a root folder
     makes it the folder that file operations act on. */

  rootOf(path) {
    if (!path) return null;
    const head = String(path).split('/')[0];
    return head in this.roots ? head : null;
  },

  isWritable() {
    if (this.activeRoot === null) return true;
    return this.roots[this.activeRoot] !== false;
  },

  nodeFor(path, items = this.root) {
    for (const item of items || []) {
      if (item.path === path) return item;
      if (item.children) {
        const hit = this.nodeFor(path, item.children);
        if (hit) return hit;
      }
    }
    return null;
  },

  async load() {
    const data = await API.project();
    this.root = data.filesystem || [];
    this.roots = {};
    for (const node of this.root) {
      this.roots[node.name] = node.writable !== false;
    }
    if (!(this.activeRoot in this.roots)) {
      const firstWritable = this.root.find(n => n.writable !== false);
      this.activeRoot = firstWritable ? firstWritable.name : (this.root[0]?.name ?? null);
    }
    /* Show every root folder expanded so the available folders are
       visible without having to click each one open. */
    for (const node of this.root) {
      this.expanded.add(this.key(node.path));
    }
    this.render();
  },

  key(path) {
    return path;
  },

  render(containerId = 'tree') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    this.renderItems(this.root, container);
  },

  renderItems(items, container, depth = 0) {
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'tree-item';
      if (item.type === 'directory') {
        row.classList.add('folder');
        row.dataset.path = item.path;
        const isRoot = depth === 0 && item.root;
        if (isRoot) {
          row.classList.add('root');
          if (item.name === this.activeRoot) {
            row.classList.add('active');
          }
          if (item.writable === false) {
            row.classList.add('readonly');
          }
        }
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        const isExpanded = this.expanded.has(this.key(item.path));
        const toggle = document.createElement('span');
        toggle.className = 'toggle' + (isExpanded ? ' expanded' : '');
        toggle.textContent = isExpanded ? '−' : '+';
        const label = document.createElement('span');
        label.className = 'label';
        label.textContent = (isRoot ? '🗂 ' : '📁 ') + item.name;
        row.appendChild(toggle);
        row.appendChild(label);
        if (isRoot && item.writable === false) {
          const lock = document.createElement('span');
          lock.className = 'root-lock';
          lock.textContent = '🔒';
          lock.title = 'Read-only';
          row.appendChild(lock);
        }
        const children = document.createElement('div');
        children.className = 'children' + (isExpanded ? '' : ' collapsed');
        row.onclick = () => {
          this.selectedPath = item.path;
          if (isRoot) {
            const changed = this.activeRoot !== item.name;
            this.activeRoot = item.name;
            if (changed && this.onRootSelect) this.onRootSelect(item.name);
          }
          if (this.onFolderSelect) this.onFolderSelect(item.path);
          this.render();
          this.toggle(item.path);
        };
        container.appendChild(row);
        container.appendChild(children);
        this.renderItems(item.children || [], children, depth + 1);
      } else {
        row.textContent = this.getFileIcon(item.name) + ' ' + item.name;
        if (item.editable === false) {
          row.classList.add('readonly');
          row.title = item.size > 0
            ? 'Read-only: not an editable text file, or too large'
            : 'Read-only';
        }
        if (this.selectedPath === item.path) {
          row.classList.add('selected');
        }
        row.onclick = () => {
          this.selectedPath = item.path;
          const rootName = this.rootOf(item.path);
          if (rootName && rootName !== this.activeRoot) {
            this.activeRoot = rootName;
            if (this.onRootSelect) this.onRootSelect(rootName);
          }
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
    return this.load();
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
