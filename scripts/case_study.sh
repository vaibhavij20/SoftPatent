#!/usr/bin/env bash
set -euo pipefail

# Case Study Runner
# Clones a public repo, runs analysis/validation, captures artifacts and logs.
# Usage:
#   scripts/case_study.sh <repo_url> <domain> [series_id]
# Example:
#   scripts/case_study.sh https://github.com/godotengine/godot gaming godot-demo-1
#   scripts/case_study.sh https://github.com/ros/ros_tutorials robotics ros-demo-1
#   scripts/case_study.sh https://github.com/OpenAPS/openomni medical med-demo-1

if [ $# -lt 2 ]; then
  echo "Usage: $0 <repo_url> <domain> [series_id]" >&2
  exit 1
fi

REPO_URL="$1"
DOMAIN="$2"
SERIES_ID="${3:-cs-$(date +%s)}"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
ART_DIR="$BACKEND_DIR/data/case_studies/$SERIES_ID"
LOG="$ART_DIR/run.log"

mkdir -p "$ART_DIR"
: >"$LOG"

say() { echo "[$(date +%T)] $*" | tee -a "$LOG"; }

say "Cloning $REPO_URL ..."
WORKDIR="/tmp/cs-$SERIES_ID"
rm -rf "$WORKDIR" && git clone --depth=1 "$REPO_URL" "$WORKDIR" >>"$LOG" 2>&1 || true

say "Backend must be running at 127.0.0.1:8001"
BASE="http://127.0.0.1:8001"

# 1) Workspace analysis
say "Running workspace_analysis ..."
curl -sS -X POST "$BASE/workspace_analysis" \
  -H 'Content-Type: application/json' \
  -d "{\"path\":\"$WORKDIR\",\"domain\":\"$DOMAIN\"}" | tee "$ART_DIR/workspace_analysis.json" >>"$LOG" 2>&1

# 2) Validation pack
say "Running validate_pack ..."
curl -sS -X POST "$BASE/validate_pack" \
  -H 'Content-Type: application/json' \
  -d "{\"domain\":\"$DOMAIN\",\"path\":\"$WORKDIR\",\"seriesId\":\"$SERIES_ID\"}" | tee "$ART_DIR/validate_pack.json" >>"$LOG" 2>&1

# 3) Optional: Suggest on representative file (heuristic pick)
# Only consider readable Python files to avoid permissions/binary issues
REP_FILE=""
while IFS= read -r f; do
  if [ -r "$f" ]; then REP_FILE="$f"; break; fi
done < <(find "$WORKDIR" -type f -name "*.py" 2>/dev/null | head -n 50)

if [ -n "$REP_FILE" ]; then
  say "Generating suggestions for $REP_FILE ..."
  FILE_TEXT=$(python3 - "$REP_FILE" <<'PY'
import sys, json
p=sys.argv[1] if len(sys.argv)>1 else None
try:
    if not p:
        raise RuntimeError('no file path provided')
    with open(p,'r',encoding='utf-8',errors='ignore') as f:
        t=f.read()
except Exception as e:
    t=f"<error reading file: {e}>"
print(json.dumps(t))
PY
)
  curl -sS -X POST "$BASE/suggest" \
    -H 'Content-Type: application/json' \
    -d "{\"file\":\"$REP_FILE\",\"text\":$FILE_TEXT,\"domain\":\"$DOMAIN\"}" | tee "$ART_DIR/suggest.json" >>"$LOG" 2>&1 || true
else
  say "No readable Python files found for suggestion sampling; skipping suggest step."
fi

# 4) Archive backend data and screenshots placeholders
say "Archiving artifacts ..."
# Validation artifacts are under backend/data/validation/$SERIES_ID
if [ -d "$BACKEND_DIR/data/validation/$SERIES_ID" ]; then
  cp -R "$BACKEND_DIR/data/validation/$SERIES_ID" "$ART_DIR/validation" || true
fi
# Copy reports
if [ -d "$BACKEND_DIR/data/reports" ]; then
  cp -R "$BACKEND_DIR/data/reports" "$ART_DIR/reports" || true
fi
# Placeholder screenshots directory (user captures)
mkdir -p "$ART_DIR/screenshots"

say "Done. Artifacts under: $ART_DIR"
[Run case studies again with hardened script]
These are safe, networked operations and may take several minutes per repo:
bash
chmod +x scripts/case_study.sh
scripts/case_study.sh https://github.com/godotengine/godot gaming godot-demo-1
scripts/case_study.sh https://github.com/ros/ros_tutorials robotics ros-demo-1
scripts/case_study.sh https://github.com/OpenAPS/openomni medical med-demo-1
scripts/case_study.sh https://github.com/numba/numba hpc hpc-demo-1

mkdir -p patent_evidence/screenshots
cp -R backend/data/case_studies/* patent_evidence/ 2>/dev/null || true
cp -R backend/data/validation/* patent_evidence/validation/ 2>/dev/null || true
cp -R backend/data/reports patent_evidence/reports 2>/dev/null || true
[In the Extension Dev Host]
Open each cloned repo.
Run “Get AI Refactor Suggestions”; apply a safe patch with “Apply Patch (AI)”.
Run “Show AI Timeline” and take screenshots (APPLIED/FLAGGED/REVERTED with the chain hash).
Run “Run Validation Pack” and screenshot the summary + artifact list. Place screenshots in patent_evidence/screenshots/.
Status
Implementation is complete:
Case study automation, UI validation command, domain detection, domain-specific reasoning, GNN invariants, and updated 
README.md
.