# My AI Refactor Extension & Backend
 
 A full-stack, profiler-driven, explainable AI refactoring system with domain-aware reasoning, benchmarking, compliance/architecture guardrails, tamper-evident timelines, and adaptive tuning.
 
 ## Highlights (Unique Features)
 - **Profiler-driven suggestions**: `backend/analysis/suggestion.py` runs an AST micro-profiler (`microprofiler.py`) to project expected runtime/memory impact per function (`audit.expected_impact`).
 - **Domain-tailored reasoning**: Explanations adjusted per domain (`gaming`, `robotics`, `hpc`, `medical`).
 - **Architecture guardrails**: Rule-based invariants (`arch_guard.py`) detect cross-boundary risks and disable automerge.
 - **Compliance checks**: `compliance.py` yields domain notes/risks, auto-disables automerge on warnings.
 - **Benchmarks + Validation Packs**: `/benchmark` for domain metrics; `/validate_pack` generates simulated time-series + plots (PNG) and JSON artifacts.
 - **Workspace analysis**: `/workspace_analysis` orchestrates analysis→profile→compliance→benchmark and writes full report to disk.
 - **Tamper-evident timeline**: `/apply_patch` records APPLIED events with prev-hash chaining (`timeline.py`). UI timeline allows Flag/Revert.
 - **Adaptive tuning**: Per-project weights (`tuning.py`) bias suggestion ordering; toggle/reset via endpoints.
 - **VS Code integration**: Commands to suggest, apply, view timeline, analyze workspace, and manage tuning. Settings for domain, optimization profile, backend, compliance targets, and audit prefs.
 - **Containerized backend**: `backend/Dockerfile` for uvicorn service.
 
 ## Architecture (High-level)
 ```mermaid
 flowchart TD
   A[VS Code Extension] -- /suggest --> B[FastAPI Backend]
   subgraph Backend
     B -- AST & Microprofiler --> C[suggestion.py]
     C -- Domain Reasoning --> C
     C -- Arch Guard --> D[arch_guard.py]
     C -- Compliance --> E[compliance.py]
     C -- Tuning Weights --> F[tuning.py]
     B -- Benchmarks --> G[benchmark.py]
     B -- Validation Packs --> H[validation_packs/*]
     B -- Timeline --> I[timeline.py]
     B -- Analyze --> J[analyzer.py]
   end
   I -- JSONL Chain --> K[(backend/data/...)]
   H -- Artifacts(JSON,PNG) --> K
 ```
 
 ## Backend Layout
 - `backend/app.py` FastAPI app with endpoints:
   - `POST /suggest` -> domain-aware, profiler-driven suggestions. Body: `{file,text,domain?,path?,targets?}`. Returns `suggestions[]`, `patch`, `reason`.
   - `POST /apply_patch` -> applies file text, runs benchmark/compliance, appends timeline.
   - `GET /timeline?project_path=...` -> events and summary with hash chain.
   - `POST /flag_step`, `POST /revert_step` -> annotate or revert steps.
   - `POST /benchmark` -> domain metrics + JSONL record.
   - `POST /validate_pack` -> simulated time-series + plots per domain run.
   - `POST /compliance` -> domain compliance notes.
   - `POST /workspace_analysis` -> orchestrated analysis; returns summary; writes full report.
   - `GET /tuning_state`, `POST /tuning_toggle`, `POST /tuning_reset` -> adaptive tuning state.
   - `POST /ci/analyze` -> CI-friendly end-to-end analysis producing a report file.
 - `backend/analysis/` modules:
   - `suggestion.py`, `microprofiler.py`, `arch_guard.py`, `compliance.py`, `benchmark.py`, `validation_packs/`, `analyzer.py`, `profiler.py`, `timeline.py`, `tuning.py`.
 - **Gemini integration**: `backend/analysis/openai_integration.py` loads `GEMINI_API_KEY` from `backend/.env` and calls `google-generativeai` where complexity warrants. Turn on by setting the key and having `google-generativeai` installed (already in `requirements.txt`).
 
 ## Quick Start (venv)
 ```bash
 # 1) Backend
 cd backend
 python -m venv .venv
 source .venv/bin/activate   # macOS/Linux
 pip install -r requirements.txt
 # Optional: echo GEMINI_API_KEY=xxxx > .env
 uvicorn app:app --reload --host 127.0.0.1 --port 8001
 
 # 2) VS Code Extension
 # Open repo in VS Code and press F5 to launch the Extension Development Host
 # In the host, open Command Palette and run commands below
 ```
 
 ## Quick Start (Docker)
 ```bash
 cd backend
 docker build -t ai-refactor-backend:latest .
 docker run --rm -p 8001:8001 -v "$PWD":/app --env-file .env ai-refactor-backend:latest
 ```
 
 ## VS Code Settings (File → Preferences → Settings)
 - `myAiRefactor.backend.host`: default `127.0.0.1`
 - `myAiRefactor.backend.port`: default `8001`
 - `myAiRefactor.domain`: `gaming|robotics|hpc|medical`
 - `myAiRefactor.optimizationProfile`: `latency|throughput|balanced`
 - `myAiRefactor.complianceTargets`: array of strings, e.g. `["iec62304","rt_safety"]`
 - `myAiRefactor.audit.timelineEnabled`: boolean
 - `myAiRefactor.audit.tuningEnabled`: boolean
 
 ## VS Code Commands
- **Start My AI Refactor Extension**: start event streaming.
- **Get AI Refactor Suggestions**: POST `/suggest` for the active editor file.
- **Apply Patch (AI)**: POST `/apply_patch` with the provided new text; records a timeline event; runs post-bench/compliance.
- **Show AI Timeline**: Webview panel listing events with Flag/Revert buttons.
- **Workspace: Analyze & Benchmark**: Calls `/workspace_analysis` and notifies where report is written.
- **Toggle AI Tuning / Reset AI Tuning**: Manage adaptive tuning.
- **Run Validation Pack**: Calls `/validate_pack`, then shows a summary webview with artifact paths.
 
 ## API Examples
 ```bash
 # Suggest
 curl -sS -X POST http://127.0.0.1:8001/suggest \
   -H 'Content-Type: application/json' \
   -d '{"file":"/tmp/x.py","text":"print(1)\n","domain":"gaming"}'
 
 # Apply patch
 curl -sS -X POST http://127.0.0.1:8001/apply_patch \
   -H 'Content-Type: application/json' \
   -d '{"file":"/tmp/x.py","newText":"def foo():\n    import logging\n    logging.info(1)\n","patch":"Replace print with logging","domain":"gaming","projectPath":"'"$PWD"'"}'
 
 # Timeline
 curl -sS "http://127.0.0.1:8001/timeline?project_path=$PWD"
 
 # Validation Pack (artifacts under backend/data/validation/series-id)
 curl -sS -X POST http://127.0.0.1:8001/validate_pack \
   -H 'Content-Type: application/json' \
   -d '{"domain":"gaming","path":"'"$PWD"'","seriesId":"demo-series-1"}'
 ```
 
 ## Workflow (End-to-End)
 1. **Profile-aware suggestions**: Use VS Code command “Get AI Refactor Suggestions”. The backend:
    - Parses the file, runs microprofiler on targets, and, if complex, invokes Gemini.
    - Annotates each suggestion with `audit.expected_impact`, `audit.arch`, `audit.compliance`, and `can_automerge`.
 2. **Apply patch & record**: Use “Apply Patch (AI)” to update the file; backend benchmarks and checks compliance, then appends an APPLIED event with a hash chain in `backend/data/timeline/`.
 3. **Review timeline**: Use “Show AI Timeline” to see steps, expected vs measured impact, flag issues, or revert a step.
 4. **Validate**: Run “Workspace: Analyze & Benchmark” or “Validation Pack” to produce artifacts and reports.
 5. **Tune**: If accepted/refused and benchmark deltas are consistent, tuning weights prioritize similar wins next time; manage via tuning commands.
 
 ## Notes on Gemini
 - File: `backend/analysis/openai_integration.py`.
 - Configure `backend/.env` with `GEMINI_API_KEY`.
 - When AST complexity crosses thresholds (e.g., many functions or long functions), `suggestion.py` tries `call_ai()` to draft a patch; suggestion `audit.provider` becomes `gemini`.
 - If the key/env is missing, the system gracefully degrades to rule-based suggestions.
 
 ## Data & Reports
 - Timeline JSONL: `backend/data/timeline/<project-id>.jsonl`
 - Reports: `backend/data/reports/last_workspace_report.json`
 - Benchmarks DB: `backend/data/benchmarks.jsonl`
 - Validation artifacts: `backend/data/validation/<seriesId>/`
 - Backups for revert: `backend/data/backups/*.bak`
 
 ## Troubleshooting
 - If `/suggest` returns 500, it now responds with `{status:"error", detail:"..."}` for easier debugging.
 - Large workspaces: analysis excludes `.venv`, `.git`, `node_modules`, `__pycache__`.
 - The timeline and validation features create files under `backend/data/`. Ensure write permissions.
 
 ## Roadmap
- Richer Tree-sitter analysis (`backend/analysis/tree_parser.py`).
- Stronger compliance packs (IEC 62304/MISRA C integration) and real benchmarks.
- GNN-based architecture invariant classifier (pluggable in place of `arch_guard.py`).

## Extension Dev Host: Exact Testing Steps
- **Configure settings**: set `myAiRefactor.backend.host=127.0.0.1`, `myAiRefactor.backend.port=8001`.
- **Gemini check**: `curl -sS http://127.0.0.1:8001/gemini_status` should show `configured:true` and a model name.
- **Complex suggestions**: open a complex file (e.g., `/Users/<you>/Desktop/python/long_function.py` with a long function or many functions) and run “Get AI Refactor Suggestions”. Expect a suggestion with `audit.expected_impact` and, when complex enough, `audit.provider: "gemini"`.
- **Apply & timeline**: run “Apply Patch (AI)” (paste new content), then “Show AI Timeline” to see APPLIED events. Use Flag/Revert buttons to annotate or restore.

## CI Usage
- **Workflow**: `.github/workflows/ci-analyze.yml` builds the backend image, runs the container, calls `/ci/analyze`, and uploads artifacts.
- **Setup**: add `GEMINI_API_KEY` to repository secrets.
- **Artifacts**: response JSON in `ci_artifacts/` and backend outputs under `backend/data/**` (timeline, reports, validation artifacts).

## Patent Appendix (Architecture & Claims Support)
- **Profiler-driven AST analysis**: `backend/analysis/suggestion.py` integrates `microprofiler.py` to attach `audit.expected_impact` (runtime/memory deltas) per function.
- **Domain-conditioned reasoning & compliance targets**: Explanations and audits reflect domain (`gaming|robotics|hpc|medical`) and optional `complianceTargets` influencing `can_automerge`.
- **Architecture invariants**: `arch_guard.py` evaluates patches against cross-boundary risks; violations disable automerge and are recorded in audits.
- **Tamper-evident timeline**: `timeline.py` appends events with chained hashes and backup paths, enabling auditable Flag/Revert operations.
- **Adaptive tuning loop**: `tuning.py` learns from accepted/refused steps to re-rank future suggestions, with explicit toggle/reset endpoints.
- **Validation packs**: Domain simulations generate JSON + PNG artifacts, enabling reproducible evidence of behavior under controlled series.
- **Operational guarantees**: Structured JSON errors on all critical endpoints, safe write scopes under `backend/data/`, workspace exclusions for stability.

## GNN Invariant Classifier (Pluggable)
- **Role**: Classifies architectural boundary risks per suggestion/patch and disables automerge on high risk. Integrated in `backend/analysis/suggestion.py` and exposed via `audit.gnn_invariant`.
- **Module**: `backend/analysis/gnn_invariant_classifier.py` provides a pluggable API with optional Torch model and a heuristic fallback.
Module implemented, integrated, and documented.
The system now classifies architectural boundary risks per suggestion, surfaces them in audits, and prevents automerge when necessary.
- **API**:
  - `InvariantClassifier(model_path: Optional[str])`
  - `InvariantClassifier.predict(graph: dict|None, patch: str, domain: str|None) -> dict`
  - `classify(graph, patch, domain) -> dict` (singleton helper)
- **Configuration**:
  - Env var `GNN_INVARIANT_MODEL` points to a TorchScript checkpoint (optional). If unavailable, the classifier falls back to heuristic mode.
  - No hard dependency on torch; gracefully degrades if not installed.
- **Integration**:
  - `suggestion.py` calls `gnn_invariant_classifier.classify(analysis_graph, patch, domain)` for each suggestion and attaches the result to `audit.gnn_invariant`.
  - If `risk_score >= 0.5` or `ok == False`, `can_automerge` is set to `False`.
- **Example outputs**:
  - Gaming (UI calls DB in a patch message):
    ```json
    {
      "ok": false,
      "risk_score": 0.70,
      "violations": [{"type":"layer_crossing","detail":"ui->data"}],
      "explanations": ["Heuristic classifier evaluated potential boundary crossings."],
      "provider": "heuristic"
    }
    ```
  - Robotics (controller writes to hardware GPIO from planning layer):
    ```json
    {
      "ok": false,
      "risk_score": 0.72,
      "violations": [{"type":"layer_crossing","detail":"control->hardware"}],
      "provider": "heuristic"
    }
    ```
  - Medical (unstructured logging hint in patch):
    ```json
    {
      "ok": false,
      "risk_score": 0.60,
      "violations": [{"type":"domain_policy","detail":"unstructured logging in medical domain"}],
      "provider": "heuristic"
    }
    ```
  - With Torch model (if configured):
    ```json
    {
      "ok": true,
      "risk_score": 0.18,
      "violations": [],
      "explanations": ["GNN model predicted architectural risk based on learned invariants."],
      "provider": "gnn",
      "model": "/path/to/checkpoint.pt"
    }
    ```

## Architecture → Workflow (Quick Reference)
- **[Extension → Backend]** `src/extension.js` calls `backend/app.py` endpoints:
  - `/suggest` → AST + micro-profiler + domain reasoning → audits (`expected_impact`, `arch`, `compliance`, `gnn_invariant`) → `can_automerge` gate.
  - `/apply_patch` → saves backup → benchmark/compliance → timeline `APPLIED` with hash chain.
  - `/timeline` → shows chain; UI can `FLAG` and `REVERT`.
  - `/validate_pack` → domain simulations produce JSON + PNG artifacts.
  - `/workspace_analysis` → orchestrates analysis/profile/compliance/benchmarks/suggestions into a report.

## Major Files & Folders (Condensed)
- `src/extension.js` → VS Code commands, timeline webview, validation webview.
- `package.json` → registers commands and settings.
- `backend/app.py` → FastAPI endpoints.
- `backend/analysis/` → core logic
  - `suggestion.py`, `microprofiler.py`, `arch_guard.py`, `compliance.py`, `benchmark.py`, `timeline.py`, `tuning.py`.
  - `domain_detect.py` (auto domain) · `gnn_invariant_classifier.py` (Torch/heuristic) · `validation_packs/runner.py` (plots/JSON).
- `backend/data/` → generated: `timeline/`, `reports/`, `validation/<series>/`, `backups/`, `case_studies/`.
- `backend/models/` → TorchScript checkpoints (e.g., `gnn_invariants.pt`).
- `scripts/case_study.sh` → clone → analyze → validate → archive.
- `scripts/gnn_export.py` → export minimal TorchScript model.
- `.github/workflows/ci-analyze.yml` → build, run, analyze, upload artifacts.

## Environment
- `backend/.env` keys:
  - `GEMINI_API_KEY=...` (optional; enables Gemini provider)
  - `GNN_INVARIANT_MODEL=backend/models/gnn_invariants.pt` (optional; enables GNN provider)

## Setup
```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 127.0.0.1 --port 8001

# Optional GNN model
cd .. && python scripts/gnn_export.py backend/models/gnn_invariants.pt
echo "GNN_INVARIANT_MODEL=backend/models/gnn_invariants.pt" >> backend/.env
```

## Master Test Checklist
- **[Suggestions]** Open a file → Command Palette → “Get AI Refactor Suggestions”
  - Expect `audit.expected_impact`, `audit.domain_impact`, `audit.arch`, `audit.compliance`, and `audit.gnn_invariant` with `can_automerge` gating.
- **[Apply + Timeline]** “Apply Patch (AI)” → “Show AI Timeline”
  - Verify `APPLIED` with `hash`/`prev_hash`. Use Flag/Revert and confirm refresh + file restore.
- **[Validation Pack]** “Run Validation Pack”
  - Webview shows JSON summary + artifact paths. Files at `backend/data/validation/<series>/`.
- **[Workspace Analysis]** “Workspace: Analyze & Benchmark”
  - Full report at `backend/data/reports/last_workspace_report.json`.
- **[Adaptive Tuning]**
  - Accept/refuse, then “Toggle AI Tuning”/“Reset AI Tuning”; re-run suggestions, verify ordering changes.
- **[Domain Auto-Detect]** Call `/suggest` without `domain`; check `audit.domain_detected`.
- **[GNN Switch]** Set `GNN_INVARIANT_MODEL` and restart backend; `/suggest` shows `provider:"gnn"`. Remove to see `"heuristic"`.
- **[Case Studies]** Run `scripts/case_study.sh <repo> <domain> <series>`; inspect `backend/data/case_studies/<series>/`.
```
# Case Studies & Evidence
- **Run scripted studies**:
  - Gaming (Godot): `scripts/case_study.sh https://github.com/godotengine/godot gaming godot-demo-1`
  - Robotics (ROS): `scripts/case_study.sh https://github.com/ros/ros_tutorials robotics ros-demo-1`
  - Medical (OpenAPS): `scripts/case_study.sh https://github.com/OpenAPS/openomni medical med-demo-1`
  - HPC (Numba): `scripts/case_study.sh https://github.com/numba/numba hpc hpc-demo-1`
- **Use the Extension Dev Host**:
  - Open the cloned workspace.
  - Run `Get AI Refactor Suggestions` and apply a safe patch with `Apply Patch (AI)`.
  - Run `Show AI Timeline` and capture screenshots of APPLIED/FLAGGED/REVERTED with the chain hash.
  - Run `Run Validation Pack` (new command) to produce JSON summary and artifact paths (take a screenshot).
- **Archive artifacts to `patent_evidence/`**:
  ```bash
  mkdir -p patent_evidence/screenshots
  cp -R backend/data/case_studies/* patent_evidence/ 2>/dev/null || true
  cp -R backend/data/validation/* patent_evidence/validation/ 2>/dev/null || true
  cp -R backend/data/reports patent_evidence/reports 2>/dev/null || true
  ```
- **Include in patent appendix**:
  - Validation plots (FPS, latency/jitter, throughput/memory) and JSONs.
  - `workspace_analysis.json` and `last_workspace_report.json`.
  - Suggestion audits showing `audit.domain_detected`, `audit.domain_impact`, `audit.gnn_invariant`, `can_automerge`.

# SoftPatent
Findings
You want a concise, end-to-end test checklist for all features across backend, extension, classifiers, validation packs, timeline, case studies, CI, and Docker.
Code locations to reference:
Backend: 
backend/app.py
, backend/analysis/
Extension: 
src/extension.js
, 
package.json
Scripts: 
scripts/case_study.sh
Docs: 
README.md
 (Case Studies & Evidence)
Prerequisites
Backend running on 127.0.0.1:8001 with your 
.env
 in 
backend/.env
 (e.g., GEMINI_API_KEY if using Gemini).
VS Code Extension (Dev Host) with settings:
myAiRefactor.backend.host=127.0.0.1
myAiRefactor.backend.port=8001
Backend Smoke Tests
Gemini status (optional):
bash
curl -sS http://127.0.0.1:8001/gemini_status
Suggest (simple file):
bash
echo 'def f():\n  print(\"hi\")\n' > /tmp/x.py
curl -sS -X POST http://127.0.0.1:8001/suggest \
  -H 'Content-Type: application/json' \
  -d '{"file":"/tmp/x.py","text":"def f():\n  print(\"hi\")\n","domain":"gaming"}'
# Expect: suggestions array with audit.domain_impact, audit.gnn_invariant, can_automerge
Apply Patch:
bash
curl -sS -X POST http://127.0.0.1:8001/apply_patch \
  -H 'Content-Type: application/json' \
  -d '{"file":"/tmp/x.py","new_text":"def f():\n  pass\n"}'
# Expect: status ok and timeline entry recorded
Timeline:
bash
curl -sS "http://127.0.0.1:8001/timeline?project_path=$(pwd)"
Workspace analysis:
bash
curl -sS -X POST http://127.0.0.1:8001/workspace_analysis \
  -H 'Content-Type: application/json' \
  -d '{"path":"'"$PWD"'","domain":"gaming"}'
# Expect: summary + report at backend/data/reports/last_workspace_report.json
Validation pack:
bash
curl -sS -X POST http://127.0.0.1:8001/validate_pack \
  -H 'Content-Type: application/json' \
  -d '{"domain":"gaming","path":"'"$PWD"'","seriesId":"demo-series-1"}'
# Expect: JSON index + PNG under backend/data/validation/demo-series-1/
Extension (UI) Tests
Get AI Refactor Suggestions: Open any .py and run the command. Verify:
audit.domain_impact notes match myAiRefactor.domain.
audit.gnn_invariant present; risky suggestions set can_automerge=false.
Apply Patch (AI): Paste new content, confirm success notification.
Show AI Timeline: Verify entries:
APPLIED events, chain hash visible.
Try Flag + Revert and see new events.
Run Validation Pack: New command
Select domain + seriesId.
Webview displays JSON summary and artifact paths.
Domain Auto-Detection Test
Temporarily omit domain when calling /suggest:
bash
curl -sS -X POST http://127.0.0.1:8001/suggest \
  -H 'Content-Type: application/json' \
  -d '{"file":"/tmp/x.py","text":"def f():\n  pass\n","path":"'"$PWD"'"}'
# Expect: audit.domain_detected set based on project signals
GNN Invariant Classifier Test
Heuristic mode (no Torch model):
Use a patch text that mentions cross-layers, e.g., “ui” and “db/sql”.
Expect audit.gnn_invariant.risk_score >= 0.5 and can_automerge=false.
Optional TorchScript mode:
Set GNN_INVARIANT_MODEL=/path/to/checkpoint.pt in 
backend/.env
.
Restart backend; provider: "gnn" will appear in results.
Validation Packs per Domain
Run per-domain packs and inspect artifacts:
bash
for d in gaming robotics medical hpc; do
  curl -sS -X POST http://127.0.0.1:8001/validate_pack \
    -H 'Content-Type: application/json' \
    -d "{\"domain\":\"$d\",\"path\":\"$PWD\",\"seriesId\":\"quick-$d\"}";
done
# See backend/data/validation/quick-*/ for JSON + PNG
Case Studies Script
Execute the script to clone public repos, analyze, validate, and archive:
bash
chmod +x scripts/case_study.sh
scripts/case_study.sh https://github.com/godotengine/godot gaming godot-demo-1
scripts/case_study.sh https://github.com/ros/ros_tutorials robotics ros-demo-1
scripts/case_study.sh https://github.com/OpenAPS/openomni medical med-demo-1
scripts/case_study.sh https://github.com/numba/numba hpc hpc-demo-1
# Artifacts: backend/data/case_studies/<series>/
Curate evidence:
bash
mkdir -p patent_evidence/screenshots
cp -R backend/data/case_studies/* patent_evidence/ 2>/dev/null || true
cp -R backend/data/validation/* patent_evidence/validation/ 2>/dev/null || true
cp -R backend/data/reports patent_evidence/reports 2>/dev/null || true
CI and Docker
Docker: build and run locally
bash
docker build -t ai-refactor-backend ./backend
docker run -p 8001:8001 --env-file backend/.env ai-refactor-backend
GitHub Actions: 
.github/workflows/ci-analyze.yml
Add GEMINI_API_KEY to repo Secrets.
Push a commit or trigger the workflow manually.
Verify uploaded artifacts (e.g., response JSON, backend/data/**).
Troubleshooting
Backend unreachable: confirm it’s listening on 8001 and extension settings point to 8001.
Missing artifacts: check backend/data/ paths for subfolders; permission issues are unlikely within the project.
Auto-detect domain is None: some repos may not expose clear cues; pass domain explicitly.
Status
All features have concrete test steps:
Backend endpoints verified with curl.
Extension commands verified via VS Code Dev Host.
Domain auto-detection and GNN invariants visible in audit.*.
Validation packs and case studies produce JSON/PNG and reports.
CI/Docker steps included for automation and auditability.
Feedback submitted



## Repository Map (What each folder/file does)
- **Root**
  - `README.md`: Full documentation, workflows, test steps, patent appendix.
  - `package.json`: VS Code extension manifest. Registers commands like `extension.runValidationPack`.
  - `src/extension.js`: Extension code. Calls backend endpoints, shows timeline/validation webviews.
  - `scripts/`
    - `case_study.sh`: Clone public repos, run `/workspace_analysis` and `/validate_pack`, archive artifacts.
    - `gnn_export.py`: Exports a tiny TorchScript model used by the invariant classifier.
  - `.github/workflows/ci-analyze.yml`: CI pipeline to build, run, and analyze with artifact upload.

- **backend/ (FastAPI service)**
  - `app.py`: Endpoints for suggest/apply/timeline/validate/benchmark/analyze/ci+tuning. Wires auto domain detection.
  - `.env`: Backend environment (keys, model paths). Example keys: `GEMINI_API_KEY`, `GNN_INVARIANT_MODEL`.
  - `Dockerfile`: Container for uvicorn app on 8001.
  - `data/` (generated)
    - `backups/`: File backups for revert.
    - `reports/`: `last_workspace_report.json` and others.
    - `timeline/`: Tamper-evident JSONL with chained hashes.
    - `validation/<seriesId>/`: JSON + PNG plots from validation packs.
    - `case_studies/<series>/`: Bundles from `scripts/case_study.sh`.
  - `models/`: TorchScript checkpoints (e.g., `gnn_invariants.pt`).
  - `analysis/` (core logic)
    - `suggestion.py`: AST analysis, micro-profiler, domain reasoning, integrates arch/compliance/gnn/tuning.
    - `microprofiler.py`: Estimates `audit.expected_impact` per function.
    - `arch_guard.py`: Rule checks for boundary crossings; disables automerge when violated.
    - `gnn_invariant_classifier.py`: Pluggable classifier; TorchScript model or heuristic fallback.
    - `domain_detect.py`: Infers likely domain from file structure/metadata.
    - `compliance.py`: Domain compliance notes; influences `can_automerge`.
    - `benchmark.py`: Domain metrics (e.g., FPS) and comparisons; records to DB.
    - `validation_packs/runner.py`: Generates time-series and plots per domain.
    - `timeline.py`: Append APPLIED/FLAGGED/REVERTED with chained hashes and backup paths.
    - `tuning.py`: Adaptive ranking from accept/reject feedback.
    - `openai_integration.py`: Gemini model configuration and calls.
    - `analyzer.py`, `profiler.py`: Project parsing, helpers.

## Claims-to-Tests Matrix (How to validate every claim)
- **[Profiler-driven suggestions]** `backend/analysis/suggestion.py`
  - Test: run “Get AI Refactor Suggestions” on a non-trivial file or:
    ```bash
    echo 'def f():\n  for i in range(1000): pass\n' > /tmp/prof.py
    curl -sS -X POST http://127.0.0.1:8001/suggest \
      -H 'Content-Type: application/json' \
      -d '{"file":"/tmp/prof.py","text":"def f():\n  for i in range(1000): pass\n","domain":"gaming"}' | jq '.suggestions[0].audit.expected_impact'
    ```

- **[Domain-tailored reasoning]** `_domain_rationale()` and `audit.domain_impact`
  - Test: call `/suggest` with `domain` set to each of `gaming|robotics|hpc|medical` and inspect `audit.domain_impact.notes`.

- **[Architecture guardrails]** `arch_guard.py` and GNN `gnn_invariant_classifier.py`
  - Test: craft a patch mentioning cross-layers (e.g., "ui" and "db") and ensure:
    - `audit.arch.ok == false` or `audit.gnn_invariant.risk_score >= 0.5`
    - `can_automerge == false` in the suggestion.

- **[Compliance checks]** `compliance.py`
  - Test: set `myAiRefactor.complianceTargets` to a list (e.g., `iec62304`) and run “Get AI Refactor Suggestions”; verify `audit.compliance.summary.warn >= 1` disables automerge when relevant.

- **[Tamper-evident timeline]** `timeline.py`
  - Test: “Apply Patch (AI)”, then “Show AI Timeline”. Verify:
    - New APPLIED event with `prev_hash`/`hash` fields.
    - Flag + Revert creates additional events and restores backup.

- **[Validation packs + benchmarks]** `validation_packs/runner.py`, `benchmark.py`
  - Test: run `Run Validation Pack` in the extension or:
    ```bash
    curl -sS -X POST http://127.0.0.1:8001/validate_pack \
      -H 'Content-Type: application/json' \
      -d '{"domain":"gaming","path":"'"$PWD"'","seriesId":"matrix-demo"}'
    # Inspect backend/data/validation/matrix-demo/*.json|*.png
    ```

- **[Adaptive tuning]** `tuning.py`
  - Test: accept/refuse suggestions, then re-run “Get AI Refactor Suggestions”. Use “Toggle AI Tuning”/“Reset AI Tuning” and observe ranking changes.

- **[Domain auto-detection]** `domain_detect.py` used by `/suggest`
  - Test: omit `domain` in `/suggest` body; verify `audit.domain_detected` is present.

- **[GNN provider switching]** `gnn_invariant_classifier.py`
  - Test: ensure `backend/.env` has `GNN_INVARIANT_MODEL=backend/models/gnn_invariants.pt`, restart backend, and check `audit.gnn_invariant.provider == "gnn"`. Remove var to fall back to `heuristic`.

- **[Containerized + CI ready]** `backend/Dockerfile`, `.github/workflows/ci-analyze.yml`
  - Test: build and run Docker locally; trigger CI and download artifacts from the run.

## Full Walkthrough (Step-by-step)
1. **Start Backend**: `uvicorn app:app --reload --host 127.0.0.1 --port 8001` in `backend/` (with `.env` configured).
2. **Launch Extension Dev Host**: Press F5 in VS Code.
3. **Suggestions**: Open a file → “Get AI Refactor Suggestions” → verify audits: `expected_impact`, `domain_impact`, `gnn_invariant`, `compliance`, and `can_automerge`.
4. **Apply Patch**: “Apply Patch (AI)” → confirm success → open “Show AI Timeline” and capture chain hash.
5. **Run Validation**: “Run Validation Pack” → select domain/series → view JSON summary and artifacts; open PNGs from disk.
6. **Workspace Analysis**: Run “Workspace: Analyze & Benchmark”; check `backend/data/reports/last_workspace_report.json`.
7. **Case Studies**: Execute `scripts/case_study.sh <repo> <domain> <series>` for 3–4 public repos; copy results into `patent_evidence/`.
8. **Docker/CI**: Build Docker image; in CI, configure `GEMINI_API_KEY` and inspect uploaded artifacts for auditability.

## Updates: New Domain Variants (Satellite, Sustainability, Speech Therapy, Medical)

- **Domains Added**: `satellite`, `sustainability`, `speech_therapy`, `medical`.
- **Extension UI**:
  - Validation Pack picker includes new domains (`src/extension.js`).
  - `myAiRefactor.domain` enum extended (`package.json`).
- **Benchmarks (`backend/analysis/benchmark.py`)**:
  - `satellite`: `control_loop_jitter_ms` (lower is better).
  - `sustainability`: `pipeline_throughput_mb_s` (higher is better).
  - `speech_therapy`: `inference_latency_ms` (lower is better).
  - `medical`: `samples_per_min` (higher is better).
  - Comparison logic updated to detect lower/higher‑is‑better metrics.
- **Validation Packs (`backend/analysis/validation_packs/`)**:
  - `sustainability.py`, `speech_therapy.py`, `medical.py`, `robotics.py` added.
  - `runner.py` wires: `gaming`, `hpc`, `satellite`, `sustainability`, `speech_therapy`, `medical`, `robotics`.
- **Compliance (`backend/analysis/compliance.py`)**:
  - Added domain rules for `satellite`, `sustainability`, `speech_therapy`.
- **Domain Auto‑Detect (`backend/analysis/domain_detect.py`)**:
  - Added cues for `satellite`, `sustainability`, `speech_therapy`.

### Quick Test

```bash
# Benchmark (satellite)
curl -sS -X POST http://127.0.0.1:8001/benchmark \
  -H 'Content-Type: application/json' \
  -d '{"domain":"satellite","path":"'"$PWD"'"}' | jq '.benchmark.result'

# Validation pack (speech_therapy)
curl -sS -X POST http://127.0.0.1:8001/validate_pack \
  -H 'Content-Type: application/json' \
  -d '{"domain":"speech_therapy","path":"'"$PWD"'","seriesId":"demo-speech"}' | jq '.index'

# Compliance (sustainability)
curl -sS -X POST http://127.0.0.1:8001/compliance \
  -H 'Content-Type: application/json' \
  -d '{"domain":"sustainability","path":"'"$PWD"'"}' | jq '.compliance.summary'
```
