My AI Refactor Extension - Full scaffold (advanced)
This scaffold includes:
- WebSocket streaming between extension and backend (ws://127.0.0.1:8000/ws).
- Tree-sitter parser helper: backend/analysis/tree_parser.py (you must build the language lib as described in comments).
- OpenAI integration stub: backend/analysis/openai_integration.py — set OPENAI_API_KEY to enable (and install openai).
- GNN training notebook scaffold: backend/analysis/gnn_training.ipynb (requires PyTorch & PyG).

Run backend (Windows):
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --host 127.0.0.1 --port 8000

Run extension (VS Code):
npm install
Press F5 -> Extension Development Host
Run command: Start My AI Refactor Extension

Notes:
- Tree-sitter requires building a shared library with the desired language grammars.
- OpenAI integration is a stub; you must set OPENAI_API_KEY in env and install openai package.
- GNN notebook is a scaffold; install PyTorch and PyG separately to run.

