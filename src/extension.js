const vscode = require('vscode');
const http = require('http');
const https = require('https');
const { URL } = require('url');

let started = false;

function activate(context) {
  console.log('My AI Refactor Extension activated');

  // Command: start event sending
  let startCmd = vscode.commands.registerCommand('extension.start', () => {
    started = true;
    vscode.window.showInformationMessage('🚀 My AI Refactor Extension started (sending events).');
    console.log('Extension start command executed — events will be sent.');
  });
  context.subscriptions.push(startCmd);

  // Command: manually request suggestions
  let suggestCmd = vscode.commands.registerCommand('extension.suggest', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage("No active editor!");
      return;
    }

    const code = editor.document.getText();
    const file = editor.document.uri.fsPath; // ✅ send full file path

    const payload = { file, text: code };

    try {
      const url = "http://127.0.0.1:8000/suggest";
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();

      if (!data.suggestions || data.suggestions.length === 0) {
        vscode.window.showInformationMessage("✅ No issues found.");
      } else {
        data.suggestions.forEach(s =>
          vscode.window.showInformationMessage(`💡 ${s.reason}\n👉 ${s.patch}`)
        );
      }
    } catch (err) {
      vscode.window.showErrorMessage(`Error fetching suggestions: ${err.message}`);
    }
  });
  context.subscriptions.push(suggestCmd);

  // Auto-send on text changes
  const changeDisposable = vscode.workspace.onDidChangeTextDocument((event) => {
    if (!started) return;
    const payload = {
      type: 'edit',
      uri: event.document.uri.toString(),
      text: event.document.getText(),
      timestamp: new Date().toISOString()
    };
    sendEvent(payload);
  });
  context.subscriptions.push(changeDisposable);

  // Auto-send on cursor/selection changes
  const selDisposable = vscode.window.onDidChangeTextEditorSelection((event) => {
    if (!started) return;
    const payload = {
      type: 'cursor',
      uri: event.textEditor.document.uri.toString(),
      selections: event.selections.map(s => ({
        start: s.start,
        end: s.end
      })),
      timestamp: new Date().toISOString()
    };
    sendEvent(payload);
  });
  context.subscriptions.push(selDisposable);
}

function sendEvent(payload) {
  try {
    const url = new URL('http://127.0.0.1:8000/event');
    const data = JSON.stringify(payload);
    const opts = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)
      },
      timeout: 3000
    };
    const lib = url.protocol === 'https:' ? https : http;
    const req = lib.request(opts, (res) => {
      res.on('data', () => {}); // ignore response body
      res.on('end', () => {
        console.log('Event sent, status:', res.statusCode);
      });
    });
    req.on('error', (err) => {
      console.error('Failed to send event:', err.message || err);
    });
    req.on('timeout', () => {
      console.error('Request timed out sending event');
      req.destroy();
    });
    req.write(data);
    req.end();
  } catch (err) {
    console.error('sendEvent exception:', err);
  }
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
