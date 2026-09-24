/* Monaco editor module */
let editor = null;

const Editor = {
  init() {
    return new Promise((resolve, reject) => {
      if (typeof require === 'undefined') {
        reject(new Error('Monaco loader not found'));
        return;
      }
      require.config({
        paths: {
          vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs'
        }
      });
      require(['vs/editor/editor.main'], () => {
        editor = monaco.editor.create(document.getElementById('editor'), {
          value: '// Select a file from the sidebar to start editing\n',
          language: 'plaintext',
          theme: 'vs-dark',
          automaticLayout: true,
          minimap: { enabled: true },
          wordWrap: 'on',
          fontSize: 14,
          tabSize: 4,
          insertSpaces: true,
          autoIndent: 'full',
          formatOnType: true,
          formatOnPaste: true
        });
        resolve(editor);
      });
    });
  },

  getEditor() {
    return editor;
  },

  setValue(content) {
    if (editor) editor.setValue(content);
  },

  getValue() {
    return editor ? editor.getValue() : '';
  },

  setLanguage(lang) {
    if (editor && monaco && editor.getModel()) {
      monaco.editor.setModelLanguage(editor.getModel(), lang);
    }
  },

  onChange(callback) {
    if (editor) {
      editor.onDidChangeModelContent(callback);
    }
  },

  layout() {
    if (editor) editor.layout();
  }
};

export default Editor;
