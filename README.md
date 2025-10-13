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
# SoftPatent
