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
    const cfg = vscode.workspace.getConfiguration('myAiRefactor');
    const host = cfg.get('backend.host') || '127.0.0.1';
    const portPrimary = cfg.get('backend.port') || 8000;
    const portFallback = (portPrimary === 8000) ? 8001 : 8000;
    const domain = cfg.get('domain') || 'gaming';
    const complianceTargets = cfg.get('complianceTargets') || [];

    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage("No active editor!");
      return;
    }

    const code = editor.document.getText();
    const file = editor.document.uri.fsPath; // ✅ send full file path

    const payload = { file, text: code, domain, complianceTargets };

    try {
      let res;
      const primaryUrl = `http://${host}:${portPrimary}/suggest`;
      const fallbackUrl = `http://${host}:${portFallback}/suggest`;
      try {
        res = await fetch(primaryUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      } catch (e) {
        res = await fetch(fallbackUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      }
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

  // Command: Workspace-wide analysis orchestration
  let wsCmd = vscode.commands.registerCommand('extension.workspaceAnalyze', async () => {
    const cfg = vscode.workspace.getConfiguration('myAiRefactor');
    const host = cfg.get('backend.host') || '127.0.0.1';
    const portPrimary = cfg.get('backend.port') || 8000;
    const portFallback = (portPrimary === 8000) ? 8001 : 8000;
    const domain = cfg.get('domain') || 'gaming';
    const workspaceFolders = vscode.workspace.workspaceFolders;
    const wsPath = workspaceFolders && workspaceFolders.length ? workspaceFolders[0].uri.fsPath : '';
    const payload = { path: wsPath, domain, benchmarkDomain: domain };
    try {
      const url1 = `http://${host}:${portPrimary}/workspace_analysis`;
      const url2 = `http://${host}:${portFallback}/workspace_analysis`;
      let res;
      try {
        res = await fetch(url1, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      } catch (e) {
        res = await fetch(url2, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      }
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      vscode.window.showInformationMessage('Workspace analysis complete. Report written on backend.');
      console.log('Workspace report:', data.report ? Object.keys(data.report) : data);
    } catch (err) {
      vscode.window.showErrorMessage(`Workspace analysis failed: ${err.message}`);
    }
  });
  context.subscriptions.push(wsCmd);

  // Command: Apply Patch (AI)
  let applyCmd = vscode.commands.registerCommand('extension.applyPatch', async () => {
    const cfg = vscode.workspace.getConfiguration('myAiRefactor');
    const host = cfg.get('backend.host') || '127.0.0.1';
    const portPrimary = cfg.get('backend.port') || 8000;
    const portFallback = (portPrimary === 8000) ? 8001 : 8000;
    const domain = cfg.get('domain') || 'gaming';
    const complianceTargets = cfg.get('complianceTargets') || [];
    const editor = vscode.window.activeTextEditor;
    if (!editor) { vscode.window.showErrorMessage('No active editor'); return; }
    const file = editor.document.uri.fsPath;
    const newText = await vscode.window.showInputBox({ prompt: 'Paste new file text to apply (MVP)', ignoreFocusOut: true });
    if (newText === undefined) return;
    const wsFolders = vscode.workspace.workspaceFolders;
    const projectPath = wsFolders && wsFolders.length ? wsFolders[0].uri.fsPath : '';
    const payload = { file, newText, patch: 'User-applied via extension', domain, projectPath, complianceTargets };
    try {
      const url1 = `http://${host}:${portPrimary}/apply_patch`;
      const url2 = `http://${host}:${portFallback}/apply_patch`;
      let res;
      try { res = await fetch(url1, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});} 
      catch { res = await fetch(url2, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});}    
      if (!res.ok) throw new Error(`Server ${res.status}`);
      const data = await res.json();
      vscode.window.showInformationMessage('Patch applied and timeline event recorded.');
      console.log('Apply result:', data);
    } catch (err) {
      vscode.window.showErrorMessage(`Apply failed: ${err.message}`);
    }
  });
  context.subscriptions.push(applyCmd);

  // Command: Run Validation Pack (shows simple results webview)
  let runValCmd = vscode.commands.registerCommand('extension.runValidationPack', async () => {
    try {
      const cfg = vscode.workspace.getConfiguration('myAiRefactor');
      const host = cfg.get('backend.host') || '127.0.0.1';
      const portPrimary = cfg.get('backend.port') || 8000;
      const portFallback = (portPrimary === 8000) ? 8001 : 8000;
      const domain = await vscode.window.showQuickPick(['gaming','robotics','hpc','medical','satellite','sustainability','speech_therapy'], { placeHolder: 'Select domain' });
      if (!domain) return;
      const seriesId = await vscode.window.showInputBox({ prompt: 'Series ID (letters, numbers, dashes)', value: `series-${Date.now()}` });
      if (!seriesId) return;
      const wsFolders = vscode.workspace.workspaceFolders;
      const projectPath = wsFolders && wsFolders.length ? wsFolders[0].uri.fsPath : '';
      const payload = { domain, path: projectPath, seriesId };
      let res;
      try {
        res = await fetch(`http://${host}:${portPrimary}/validate_pack`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      } catch {
        res = await fetch(`http://${host}:${portFallback}/validate_pack`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      }
      if (!res.ok) throw new Error(`Server ${res.status}`);
      const data = await res.json();
      const panel = vscode.window.createWebviewPanel('validationPack', `Validation Pack: ${seriesId}`, vscode.ViewColumn.Active, { enableScripts: false });
      const artifacts = (data && data.index && data.index.artifacts) ? data.index.artifacts : [];
      const summary = (data && data.index && data.index.summary) ? data.index.summary : {};
      panel.webview.html = `<!doctype html><html><head><meta charset="utf-8"><style>body{font-family: sans-serif;padding:16px} pre{background:#f5f5f5;padding:8px;border-radius:4px}</style></head><body>
        <h2>Validation Pack</h2>
        <p><b>Domain:</b> ${domain}</p>
        <p><b>Series:</b> ${seriesId}</p>
        <h3>Summary</h3>
        <pre>${JSON.stringify(summary,null,2)}</pre>
        <h3>Artifacts</h3>
        <ul>${artifacts.map(a=>`<li>${a}</li>`).join('')}</ul>
        <p>Artifacts are saved on disk (see listed paths). Open them in your OS or the VS Code Explorer.</p>
      </body></html>`;
    } catch (e) {
      vscode.window.showErrorMessage(`Validation pack error: ${e}`);
    }
  });
  context.subscriptions.push(runValCmd);

  // Command: Show Timeline (with refresh after Flag/Revert)
  let timelineCmd = vscode.commands.registerCommand('extension.showTimeline', async () => {
    const cfg = vscode.workspace.getConfiguration('myAiRefactor');
    const host = cfg.get('backend.host') || '127.0.0.1';
    const portPrimary = cfg.get('backend.port') || 8000;
    const portFallback = (portPrimary === 8000) ? 8001 : 8000;
    const wsFolders = vscode.workspace.workspaceFolders;
    const projectPath = wsFolders && wsFolders.length ? wsFolders[0].uri.fsPath : '';
    const panel = vscode.window.createWebviewPanel('aiTimeline', 'AI Timeline', vscode.ViewColumn.Beside, { enableScripts: true });

    async function fetchTimeline() {
      const url1 = `http://${host}:${portPrimary}/timeline?project_path=${encodeURIComponent(projectPath)}`;
      const url2 = `http://${host}:${portFallback}/timeline?project_path=${encodeURIComponent(projectPath)}`;
      let res;
      try { res = await fetch(url1); } catch { res = await fetch(url2); }
      if (!res.ok) throw new Error(`Server ${res.status}`);
      return await res.json();
    }

    async function render() {
      try {
        const data = await fetchTimeline();
        const events = data.events || [];
        const rows = events.map((e, idx) => {
          const cues = (e && e.cues && e.cues.arch && e.cues.arch.ok === false) ? 'arch: violation' : 'arch: ok';
          const bench = (e && e.result && e.result.benchmark && e.result.benchmark.result) ? (e.result.benchmark.result.value || '') : '';
          const hash = e && e.chain_hash ? e.chain_hash.slice(0,8) : '';
          const actions = (e && e.backup && e.file)
            ? `<button onclick="revert(${idx})">Revert</button>`
            : '';
          return '<tr>'+
            `<td>${idx+1}</td>`+
            `<td>${e.type||''}</td>`+
            `<td>${e.file||''}</td>`+
            `<td>${e.domain||''}</td>`+
            `<td>${e.message||''}</td>`+
            `<td><code>${cues}</code></td>`+
            `<td>${bench}</td>`+
            `<td>${hash}</td>`+
            `<td><button onclick="flag(${idx})">Flag</button>${actions}</td>`+
          '</tr>';
        }).join('');
        const escProject = projectPath.replace(/\\/g, "\\\\");
        const eventsJson = JSON.stringify(events).replace(/</g, "&lt;");
        panel.webview.html = '<!doctype html><html><head><meta charset="utf-8" />'+
          '<style>body{font-family:sans-serif}table{width:100%;border-collapse:collapse}th,td{border:1px solid #ccc;padding:6px;font-size:12px}th{background:#f6f6f6}button{font-size:12px}</style>'+
          '</head><body>'+`
          <h3>AI Timeline — ${projectPath}</h3>
          <table><thead><tr><th>#</th><th>Type</th><th>File</th><th>Domain</th><th>Message</th><th>Cues</th><th>Metric</th><th>Hash</th><th>Actions</th></tr></thead>`+
          `<tbody>${rows||''}</tbody></table>`+
          '<script>\n'+
          'const vscode = acquireVsCodeApi();\n'+
          'const host="'+host+'";\n'+
          'const portPrimary='+portPrimary+';\n'+
          'const portFallback='+portFallback+';\n'+
          'const projectPath="'+escProject+'";\n'+
          'const events='+eventsJson+';\n'+
          'async function post(path, body){\n'+
          '  const url1 = "http://"+host+":"+portPrimary+path;\n'+
          '  try { return await fetch(url1,{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify(body)});}\n'+
          '  catch (e) { const url2 = "http://"+host+":"+portFallback+path; return await fetch(url2,{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify(body)});}\n'+
          '}\n'+
          'async function flag(i){\n'+
          '  const e=events[i];\n'+
          '  const reason=prompt("Flag reason?");\n'+
          '  if(!reason) return;\n'+
          '  const res=await post("/flag_step",{projectPath,file:e.file,reason});\n'+
          '  if(res.ok){ vscode.postMessage({type:"refresh"}); } else { const t=await res.text(); alert("Flag failed: "+res.status+" "+t); }\n'+
          '}\n'+
          'async function revert(i){\n'+
          '  const e=events[i];\n'+
          '  if(!confirm("Revert this step?")) return;\n'+
          '  const res=await post("/revert_step",{projectPath,file:e.file,backupPath:e.backup});\n'+
          '  if(res.ok){ vscode.postMessage({type:"refresh"}); } else { const t=await res.text(); alert("Revert failed: "+res.status+" "+t); }\n'+
          '}\n'+
          '</script></body></html>';
      } catch (err) {
        vscode.window.showErrorMessage(`Timeline failed: ${err.message}`);
      }
    }

    panel.webview.onDidReceiveMessage(async (msg) => {
      if (msg && msg.type === 'refresh') {
        await render();
      }
    });

    await render();
  });
  context.subscriptions.push(timelineCmd);

  // Tuning commands
  let toggleTuningCmd = vscode.commands.registerCommand('extension.toggleTuning', async () => {
    const cfg = vscode.workspace.getConfiguration('myAiRefactor');
    const host = cfg.get('backend.host') || '127.0.0.1';
    const portPrimary = cfg.get('backend.port') || 8000;
    const portFallback = (portPrimary === 8000) ? 8001 : 8000;
    const wsFolders = vscode.workspace.workspaceFolders;
    const projectPath = wsFolders && wsFolders.length ? wsFolders[0].uri.fsPath : '';
    const enabled = await vscode.window.showQuickPick(['enable','disable'], { placeHolder:'AI Tuning' });
    if (!enabled) return;
    const payload = { projectPath, enabled: enabled === 'enable' };
    try {
      const u1 = `http://${host}:${portPrimary}/tuning_toggle`;
      const u2 = `http://${host}:${portFallback}/tuning_toggle`;
      let res; try { res = await fetch(u1, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});} catch { res = await fetch(u2, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});}    
      if (!res.ok) throw new Error(`Server ${res.status}`);
      vscode.window.showInformationMessage('Tuning state updated.');
    } catch (err) { vscode.window.showErrorMessage(`Toggle failed: ${err.message}`); }
  });
  context.subscriptions.push(toggleTuningCmd);

  let resetTuningCmd = vscode.commands.registerCommand('extension.resetTuning', async () => {
    const cfg = vscode.workspace.getConfiguration('myAiRefactor');
    const host = cfg.get('backend.host') || '127.0.0.1';
    const portPrimary = cfg.get('backend.port') || 8000;
    const portFallback = (portPrimary === 8000) ? 8001 : 8000;
    const wsFolders = vscode.workspace.workspaceFolders;
    const projectPath = wsFolders && wsFolders.length ? wsFolders[0].uri.fsPath : '';
    const payload = { projectPath };
    try {
      const u1 = `http://${host}:${portPrimary}/tuning_reset`;
      const u2 = `http://${host}:${portFallback}/tuning_reset`;
      let res; try { res = await fetch(u1, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});} catch { res = await fetch(u2, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});}    
      if (!res.ok) throw new Error(`Server ${res.status}`);
      vscode.window.showInformationMessage('Tuning reset.');
    } catch (err) { vscode.window.showErrorMessage(`Reset failed: ${err.message}`); }
  });
  context.subscriptions.push(resetTuningCmd);
}

function sendEvent(payload) {
  try {
    const cfg = vscode.workspace.getConfiguration('myAiRefactor');
    const host = cfg.get('backend.host') || '127.0.0.1';
    const portPrimary = cfg.get('backend.port') || 8000;
    const portFallback = (portPrimary === 8000) ? 8001 : 8000;
    const data = JSON.stringify(payload);
    const trySend = (port) => new Promise((resolve, reject) => {
      const opts = {
        hostname: host,
        port,
        path: '/event',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(data)
        },
        timeout: 3000
      };
      const req = http.request(opts, (res) => {
        res.on('data', () => {});
        res.on('end', () => resolve(res.statusCode));
      });
      req.on('error', reject);
      req.on('timeout', () => { req.destroy(new Error('timeout')); });
      req.write(data);
      req.end();
    });

    trySend(portPrimary).catch(() => trySend(portFallback)).catch((err) => {
      console.error('Failed to send event:', err && err.message ? err.message : err);
    });
  } catch (err) {
    console.error('sendEvent exception:', err);
  }
}

function deactivate() {}

module.exports = {
  activate,
  deactivate
};
