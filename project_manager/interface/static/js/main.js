/* Main application wiring */
import API from './api.js';
import Session from './session.js';
import Tree from './tree.js';
import Editor from './editor.js';
import { initAgentsPanel, updateRunTarget } from './agents.js';
import { initAgentCards, openChatWithAgent } from './agentCards.js';
import { initTopbar } from './topbar.js';

let currentFile = null;
let currentLanguage = 'plaintext';
let isDirty = false;
let currentIsFolder = false;
let currentIsReadOnly = false;

/* main.js is shared by home.html and editor.html. Only editor.html
   carries a #editor host, so every editor call is guarded. */
const hasEditor = () => Editor.hasHost();

/* The test environment is browsed from /test, so home does not list
   it. The editor does: a published test agent's agent.md is edited
   there, and /test hands its files over to the editor rather than
   editing them itself, so a tree that omitted the root would open
   the file somewhere it cannot be seen or saved.

   Adding a root to BROWSE_ROOTS therefore makes it appear on the
   editor and on /test but not on home, until this list catches up. */
const HOME_ROOTS = ['workspace', 'source_files'];

/* Paths are browser-root-qualified (workspace/..., source_files/...),
   so no scope needs to be tracked or sent. The active folder is the
   root folder selected in the tree. */

function isPathReadOnly(path) {
  const rootName = Tree.rootOf(path);
  if (rootName && Tree.roots[rootName] === false) return true;
  const node = Tree.nodeFor(path);
  if (node && node.editable === false) return true;
  return false;
}

function applyReadOnly() {
  if (hasEditor()) Editor.setReadOnly(currentIsReadOnly);
  const el = document.getElementById('readOnlyIndicator');
  if (el) el.textContent = currentIsReadOnly ? '🔒 READ-ONLY' : '';
}

function getLanguage(filePath) {
  if (!filePath) return 'plaintext';
  const ext = filePath.split('.').pop().toLowerCase();
  const map = {
    py: 'python',
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    html: 'html',
    htm: 'html',
    css: 'css',
    json: 'json',
    md: 'markdown',
    yaml: 'yaml',
    yml: 'yaml',
    sql: 'sql',
    xml: 'xml',
    sh: 'shell',
    bat: 'batch',
    ps1: 'powershell',
    env: 'shell',
    txt: 'plaintext'
  };
  return map[ext] || 'plaintext';
}

function setStatus(msg) {
  const el = document.getElementById('statusMessage');
  if (el) el.textContent = msg;
}

function updateFileDisplay() {
  const cf = document.getElementById('currentFile');
  if (cf) cf.textContent = currentFile ? currentFile : 'No file selected';
  const lang = document.getElementById('language');
  if (lang) lang.textContent = currentLanguage;
  const dirty = document.getElementById('unsavedIndicator');
  if (dirty) dirty.textContent = isDirty ? '● UNSAVED' : '';
  applyReadOnly();
}

async function openFile(filePath) {
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Open another file?');
    if (!proceed) return;
  }
  /* Home has no editor, so opening a file means handing it to
     editor.html rather than rendering it here. */
  if (!hasEditor()) {
    const root = Tree.rootOf(filePath) || Tree.activeRoot;
    window.location.href =
      `/editor?path=${encodeURIComponent(filePath)}&root=${encodeURIComponent(root)}`;
    return;
  }
  setStatus('Opening ' + filePath + '...');
  try {
    const data = await API.fileRead(filePath);
    currentFile = filePath;
    currentIsFolder = false;
    currentIsReadOnly = isPathReadOnly(filePath);
    currentLanguage = getLanguage(filePath);
    if (hasEditor()) {
      Editor.setValue(data.content || '');
      Editor.setLanguage(currentLanguage);
    }
    isDirty = false;
    updateFileDisplay();
    Tree.setSelected(filePath);
    Tree.reveal(filePath);
    setStatus(currentIsReadOnly
      ? 'Opened ' + filePath + ' (read-only)'
      : 'Opened ' + filePath);
    updateRunTarget();
  } catch (error) {
    setStatus('Error: ' + error.message);
    alert(error.message);
  }
}

function selectFolder(path) {
  currentFile = path;
  currentIsFolder = true;
  updateFileDisplay();
  setStatus('Folder selected: ' + path);
  updateRunTarget();
}

async function saveFile() {
  if (!currentFile) {
    alert('No file is currently open.');
    return;
  }
  if (currentIsFolder) {
    alert('Select a file to save. Folders cannot be saved as files.');
    return;
  }
  if (!hasEditor()) {
    alert('Open the file in the editor to save it.');
    return;
  }
  if (currentIsReadOnly) {
    alert('This file is read-only: ' + currentFile);
    return;
  }
  setStatus('Saving...');
  try {
    await API.fileWrite(currentFile, Editor.getValue());
    isDirty = false;
    updateFileDisplay();
    setStatus('Saved ' + currentFile);
    await Tree.refresh();
  } catch (error) {
    setStatus('Save error: ' + error.message);
    alert(error.message);
  }
}

function requireWritableRoot(path) {
  const rootName = Tree.rootOf(path);
  if (rootName && Tree.roots[rootName] === false) {
    alert(rootName + ' is read-only.');
    return false;
  }
  return true;
}

function isRootFolder(path) {
  return Tree.rootOf(path) === path;
}

async function newFile() {
  if (!Tree.isWritable()) {
    alert(Tree.activeRoot + ' is read-only.');
    return;
  }
  const suggestion = (currentIsFolder ? currentFile : Tree.activeRoot) + '/';
  const fileName = prompt('Enter new file path/name:', suggestion);
  if (!fileName) return;
  if (!requireWritableRoot(fileName)) return;
  try {
    await API.fileCreate(fileName, '');
    await Tree.refresh();
    await openFile(fileName);
    setStatus('Created ' + fileName);
  } catch (error) {
    alert(error.message);
  }
}

async function newFolder() {
  if (!Tree.isWritable()) {
    alert(Tree.activeRoot + ' is read-only.');
    return;
  }
  const suggestion = (currentIsFolder ? currentFile : Tree.activeRoot) + '/';
  const folderPath = prompt('Enter new folder path:', suggestion);
  if (!folderPath) return;
  if (!requireWritableRoot(folderPath)) return;
  try {
    await API.directoryCreate(folderPath);
    await Tree.refresh();
    setStatus('Created folder ' + folderPath);
  } catch (error) {
    alert(error.message);
  }
}

async function renameSelected() {
  if (!currentFile) {
    alert('Select a file or folder first.');
    return;
  }
  if (!requireWritableRoot(currentFile)) return;
  if (isRootFolder(currentFile)) {
    alert('A root folder cannot be renamed.');
    return;
  }
  const newName = prompt('Enter the new name/path:', currentFile);
  if (!newName || newName === currentFile) return;
  if (!requireWritableRoot(newName)) return;
  try {
    await API.pathRename(currentFile, newName);
    currentFile = newName;
    await Tree.refresh();
    if (currentIsFolder) {
      Tree.setSelected(newName);
      setStatus('Renamed folder to ' + newName);
    } else {
      await openFile(newName);
    }
  } catch (error) {
    alert(error.message);
  }
}

async function deleteSelected() {
  if (!currentFile) {
    alert('Select a file or folder first.');
    return;
  }
  if (!requireWritableRoot(currentFile)) return;
  if (isRootFolder(currentFile)) {
    alert('A root folder cannot be deleted.');
    return;
  }
  const confirmed = confirm((currentIsFolder ? 'Delete folder ' : 'Delete file ') + currentFile + '?');
  if (!confirmed) return;
  try {
    if (currentIsFolder) {
      await API.directoryDelete(currentFile);
    } else {
      await API.fileDelete(currentFile);
    }
            currentFile = null;
            currentIsFolder = false;
            currentIsReadOnly = false;
            if (hasEditor()) Editor.setValue('');
            isDirty = false;
    updateFileDisplay();
    await Tree.refresh();
    setStatus('Deleted.');
    updateRunTarget();
  } catch (error) {
    alert(error.message);
  }
}

async function refreshTree() {
  await Tree.refresh();
  setStatus('Refreshed.');
}

function selectRoot(rootName) {
  setStatus('Working in ' + rootName
    + (Tree.roots[rootName] === false ? ' (read-only)' : ''));
}

function openChatPopup(agentId) {
  openChatWithAgent(agentId);
}

function init() {
  Editor.init()
    .then(async () => {
      initTopbar({ page: hasEditor() ? 'editor' : 'home' });

      if (hasEditor()) {
        Editor.onChange(() => {
          if (currentFile) {
            isDirty = true;
            updateFileDisplay();
          }
        });
      }

      Tree.onFileSelect = openFile;
      Tree.onFolderSelect = selectFolder;
      Tree.onRootSelect = selectRoot;

      // ---- Project name ----
      if (document.getElementById('projectName')) {
        try {
          const info = await API.health();
          const name = info.project?.name;
          if (name) document.getElementById('projectName').textContent = name;
        } catch (e) {
          // ignore
        }
      }

      // ---- Top bar actions ----
      /* Page navigation lives in the shared topbar; only this page's
         own tools are wired here. */
      document.getElementById('saveBtn')?.addEventListener('click', saveFile);
      document.getElementById('newFileBtn')?.addEventListener('click', newFile);
      document.getElementById('newFolderBtn')?.addEventListener('click', newFolder);
      document.getElementById('renameBtn')?.addEventListener('click', renameSelected);
      document.getElementById('deleteBtn')?.addEventListener('click', deleteSelected);
      document.getElementById('refreshBtn')?.addEventListener('click', refreshTree);

      document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
          event.preventDefault();
          saveFile();
        }
      });

      const sidebar = document.getElementById('sidebar');
      const resizeHandle = document.getElementById('resizeHandle');
      if (resizeHandle && sidebar) {
        let resizing = false;
        resizeHandle.addEventListener('mousedown', () => { resizing = true; document.body.style.cursor = 'col-resize'; });
        document.addEventListener('mousemove', (e) => {
          if (!resizing) return;
          const width = e.clientX;
          if (width >= 180 && width <= 500) {
            sidebar.style.width = width + 'px';
            Editor.layout();
          }
        });
        document.addEventListener('mouseup', () => { resizing = false; document.body.style.cursor = ''; });
      }

      window.addEventListener('beforeunload', (event) => {
        if (!isDirty) return;
        event.preventDefault();
        event.returnValue = '';
      });

      setStatus('Ready');
      await Tree.load(hasEditor() ? null : HOME_ROOTS);

      /* Home page: agent cards replace the editor. */
      if (document.getElementById('agentCards')) {
        try {
          await initAgentCards({ onOpen: openChatPopup });
        } catch (e) {
          const host = document.getElementById('agentCards');
          host.textContent = 'Failed to load agents: ' + e.message;
        }
        return;
      }

      initAgentsPanel({
        getCurrentFile: () => currentFile,
        isDirty: () => isDirty,
        saveFile,
        refreshTree,
        openFile,
        editorLayout: () => Editor.layout()
      });
      const urlParams = new URLSearchParams(window.location.search);
      const initialPath = urlParams.get('path');
      const initialRoot = urlParams.get('root');
      if (initialRoot && initialRoot in Tree.roots) {
        Tree.activeRoot = initialRoot;
      }
      if (initialPath) {
        await openFile(initialPath);
      }
    })
    .catch((e) => {
      setStatus('Error: ' + e.message);
    });

  Session.connect();
}

document.addEventListener('DOMContentLoaded', init);

export { openFile, saveFile, newFile, newFolder, renameSelected, deleteSelected, refreshTree, openChatPopup, currentFile, isDirty };
