/* Main application wiring */
import API from './api.js';
import Session from './session.js';
import Tree from './tree.js';
import Editor from './editor.js';
import { initAgentsPanel, updateRunTarget } from './agents.js';

let currentFile = null;
let currentLanguage = 'plaintext';
let isDirty = false;
let currentIsFolder = false;
let scope = 'workspace';

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
}

async function openFile(filePath) {
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Open another file?');
    if (!proceed) return;
  }
  setStatus('Opening ' + filePath + '...');
  try {
    const data = await API.fileRead(filePath, scope);
    currentFile = filePath;
    currentIsFolder = false;
    currentLanguage = getLanguage(filePath);
    Editor.setValue(data.content || '');
    Editor.setLanguage(currentLanguage);
    isDirty = false;
    updateFileDisplay();
    Tree.setSelected(filePath);
    Tree.reveal(filePath);
    setStatus('Opened ' + filePath);
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
  setStatus('Saving...');
  try {
    await API.fileWrite(currentFile, Editor.getValue(), scope);
    isDirty = false;
    updateFileDisplay();
    setStatus('Saved ' + currentFile);
    await Tree.refresh();
  } catch (error) {
    setStatus('Save error: ' + error.message);
    alert(error.message);
  }
}

async function newFile() {
  const fileName = prompt('Enter new file path/name:');
  if (!fileName) return;
  try {
    await API.fileCreate(fileName, '', scope);
    await Tree.refresh();
    await openFile(fileName);
    setStatus('Created ' + fileName);
  } catch (error) {
    alert(error.message);
  }
}

async function newFolder() {
  const folderPath = prompt('Enter new folder path:');
  if (!folderPath) return;
  try {
    await API.directoryCreate(folderPath, scope);
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
  const newName = prompt('Enter the new name/path:', currentFile);
  if (!newName || newName === currentFile) return;
  try {
    await API.pathRename(currentFile, newName, scope);
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
  const confirmed = confirm((currentIsFolder ? 'Delete folder ' : 'Delete file ') + currentFile + '?');
  if (!confirmed) return;
  try {
    if (currentIsFolder) {
      await API.directoryDelete(currentFile, scope);
    } else {
      await API.fileDelete(currentFile, scope);
    }
    currentFile = null;
    currentIsFolder = false;
    Editor.setValue('');
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

function updateScopeButtons() {
  const wsBtn = document.getElementById('scopeWs');
  const appBtn = document.getElementById('scopeApp');
  if (wsBtn) wsBtn.classList.toggle('active', scope === 'workspace');
  if (appBtn) appBtn.classList.toggle('active', scope === 'app');
}

async function setScope(nextScope) {
  if (scope === nextScope) return;
  if (isDirty) {
    const proceed = confirm('You have unsaved changes. Switch scope?');
    if (!proceed) return;
  }
  scope = nextScope;
  currentFile = null;
  currentIsFolder = false;
  Editor.setValue('');
  isDirty = false;
  updateFileDisplay();
  updateScopeButtons();
  setStatus(scope === 'app' ? 'Dev mode: application files' : 'Workspace mode: project files');
  try {
    await Tree.load(scope);
  } catch (error) {
    setStatus('Error: ' + error.message);
  }
}

async function openDevLink(link) {
  if (scope !== 'app') {
    scope = 'app';
    updateScopeButtons();
  }
  setStatus('Opening ' + link.path + '...');
  try {
    await Tree.load(scope);
    await openFile(link.path);
  } catch (error) {
    setStatus('Error: ' + error.message);
  }
}

function openChatPopup() {
  const width = 420; const height = 600;
  const left = (window.screen.width - width) / 2;
  const top = (window.screen.height - height) / 2;
  window.open('/chat', 'ProjectManagerChat', `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no`);
}

function goHome() {
  window.location.href = '/';
}

function goEditor() {
  window.location.href = '/editor';
}

function init() {
  Editor.init()
    .then(async () => {
      Editor.onChange(() => {
        if (currentFile) {
          isDirty = true;
          updateFileDisplay();
        }
      });

      Tree.onFileSelect = openFile;
      Tree.onFolderSelect = selectFolder;
      Tree.onDevLink = openDevLink;

      // ---- Dev-script quick links ----
      if (document.getElementById('devLinks')) {
        Tree.renderDevLinks('devLinks');
      }

      const devLinksToggle = document.getElementById('devLinksToggle');
      const devLinksBox = document.getElementById('devLinks');
      if (devLinksToggle && devLinksBox) {
        devLinksToggle.addEventListener('click', () => {
          const hidden = devLinksBox.style.display === 'none';
          devLinksBox.style.display = hidden ? '' : 'none';
          devLinksToggle.textContent = hidden ? '−' : '+';
        });
      }

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

      // ---- Scope toggle ----
      document.getElementById('scopeWs')?.addEventListener('click', () => setScope('workspace'));
      document.getElementById('scopeApp')?.addEventListener('click', () => setScope('app'));
      updateScopeButtons();

      // ---- Top bar actions ----
      document.getElementById('saveBtn')?.addEventListener('click', saveFile);
      document.getElementById('newFileBtn')?.addEventListener('click', newFile);
      document.getElementById('newFolderBtn')?.addEventListener('click', newFolder);
      document.getElementById('renameBtn')?.addEventListener('click', renameSelected);
      document.getElementById('deleteBtn')?.addEventListener('click', deleteSelected);
      document.getElementById('refreshBtn')?.addEventListener('click', refreshTree);
      document.getElementById('chatBtn')?.addEventListener('click', openChatPopup);
      document.getElementById('editorBtn')?.addEventListener('click', goEditor);
      document.getElementById('homeBtn')?.addEventListener('click', goHome);

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
      await Tree.load(scope);
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
      const initialScope = urlParams.get('scope');
      if (initialScope === 'app' || initialScope === 'workspace') {
        scope = initialScope;
        updateScopeButtons();
      }
      if (initialPath) {
        if (initialScope === 'app') await Tree.load('app');
        await openFile(initialPath);
      }
    })
    .catch((e) => {
      setStatus('Error: ' + e.message);
    });

  Session.connect();
}

document.addEventListener('DOMContentLoaded', init);

export { openFile, saveFile, newFile, newFolder, renameSelected, deleteSelected, refreshTree, setScope, openDevLink, goHome, goEditor, currentFile, isDirty };
