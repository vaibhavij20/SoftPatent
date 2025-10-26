import os
from typing import Any, Dict, Optional

# Optional: torch and torch_geometric are not hard requirements.
# The classifier will gracefully fall back to heuristic mode if these are missing
try:
    import torch  # type: ignore
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False


class InvariantClassifier:
    """
    Pluggable classifier for architectural invariant risk.

    Strategy:
    - If a torch model checkpoint is provided and torch is available, load it and run inference.
    - Otherwise, use a simple heuristic on the provided graph + patch text.

    Inputs:
    - graph: a project graph as produced by `analyzer.analyze_project()` (or None)
    - patch: text describing the suggested change
    - domain: 'gaming' | 'robotics' | 'hpc' | 'medical' | None

    Output schema (example):
    {
      "ok": true,
      "risk_score": 0.12,             # 0..1 (1 = high risk)
      "violations": [
         {"type": "layer_crossing", "detail": "ui->data access"}
      ],
      "explanations": ["Why the risk was predicted"],
      "provider": "gnn|heuristic",
      "model": "path-or-name-if-any"
    }
    """

    def __init__(self, model_path: Optional[str] = None, provider_name: str = "heuristic") -> None:
        self.model_path = model_path or os.getenv("GNN_INVARIANT_MODEL")
        self.provider_name = provider_name
        self.model = None
        if self.model_path and TORCH_AVAILABLE:
            try:
                self.model = torch.jit.load(self.model_path)
                self.provider_name = "gnn"
            except Exception:
                self.model = None
                self.provider_name = "heuristic"

    def predict(self, graph: Optional[Dict[str, Any]], patch: str, domain: Optional[str]) -> Dict[str, Any]:
        # If we have a model, attempt inference
        if self.model is not None and TORCH_AVAILABLE:
            try:
                # Minimal representation: derive simple numeric features
                # In a real system, this would convert the project graph into a tensor dataset
                text_len = len(patch or "")
                domain_idx = {"gaming": 0, "robotics": 1, "hpc": 2, "medical": 3}.get((domain or "").lower(), 4)
                x = torch.tensor([float(text_len % 1024) / 1024.0, float(domain_idx) / 4.0]).float().unsqueeze(0)
                with torch.no_grad():
                    y = self.model(x).sigmoid().item() if hasattr(self.model, "__call__") else 0.1
                risk = max(0.0, min(1.0, float(y)))
                ok = risk < 0.5
                return {
                    "ok": ok,
                    "risk_score": risk,
                    "violations": [] if ok else [{"type": "gnn_predicted_risk", "detail": f"risk={risk:.2f}"}],
                    "explanations": ["GNN model predicted architectural risk based on learned invariants."],
                    "provider": self.provider_name,
                    "model": self.model_path,
                }
            except Exception as e:
                # Fall back to heuristic on any failure
                return self._heuristic(graph, patch, domain, error=str(e))
        # Heuristic
        return self._heuristic(graph, patch, domain)

    def _heuristic(self, graph: Optional[Dict[str, Any]], patch: str, domain: Optional[str], error: Optional[str] = None) -> Dict[str, Any]:
        """Simple rule-of-thumb detector for obvious boundary crossings.
        Looks for sensitive keywords and cross-layer terms in the patch text.
        """
        txt = (patch or "").lower()
        risk = 0.0
        violations = []
        # Indicators of crossing layers or mixing concerns
        cues = [
            ("ui->data", ["ui", "view", "react"], ["db", "sql", "orm", "repository"]),
            ("control->hardware", ["control", "planner"], ["gpio", "spi", "i2c", "sensor"]),
            ("api->internal", ["api", "endpoint"], ["internal", "private"]),
        ]
        for name, left, right in cues:
            if any(l in txt for l in left) and any(r in txt for r in right):
                violations.append({"type": "layer_crossing", "detail": name})
                risk = max(risk, 0.7)
        # Domain cue
        d = (domain or "").lower()
        if d == "medical" and ("print(" in txt or "debug" in txt):
            violations.append({"type": "domain_policy", "detail": "unstructured logging in medical domain"})
            risk = max(risk, 0.6)
        ok = risk < 0.5
        out = {
            "ok": ok,
            "risk_score": risk if risk > 0 else 0.1,
            "violations": violations,
            "explanations": ["Heuristic classifier evaluated potential boundary crossings."],
            "provider": "heuristic",
            "model": None,
        }
        if error:
            out["note"] = f"model_error: {error}"
        return out

    # Optional training API (stub)
    def fit(self, dataset_path: str, epochs: int = 5) -> Dict[str, Any]:
        """Train or fine-tune the model on a user-provided dataset (stub)."""
        if not TORCH_AVAILABLE:
            return {"status": "error", "detail": "torch not installed"}
        # Placeholder: load dataset, define model, train, and save
        return {"status": "ok", "detail": "training stub completed"}


# Singleton with env-configurable checkpoint
_classifier_singleton: Optional[InvariantClassifier] = None

def get_classifier() -> InvariantClassifier:
    global _classifier_singleton
    if _classifier_singleton is None:
        _classifier_singleton = InvariantClassifier()
    return _classifier_singleton


def classify(graph: Optional[Dict[str, Any]], patch: str, domain: Optional[str]) -> Dict[str, Any]:
    return get_classifier().predict(graph, patch, domain)
