#!/usr/bin/env python3
"""
Export a tiny TorchScript model for the GNN invariant classifier.
This does NOT build a real GNN; it's a lightweight MLP placeholder that
accepts a 2D feature vector [text_len_norm, domain_idx_norm] and outputs a risk logit.

Usage:
  python3 scripts/gnn_export.py backend/models/gnn_invariants.pt
Requires: torch
"""
import sys

try:
    import torch
    import torch.nn as nn
except Exception as e:
    print("ERROR: torch is not installed (pip install torch)")
    print(e)
    sys.exit(1)

class TinyRisk(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
        )
    def forward(self, x):
        return self.net(x).squeeze(-1)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "backend/models/gnn_invariants.pt"
    m = TinyRisk().eval()
    ex = torch.rand(1, 2)
    with torch.no_grad():
        m(ex)
    ts = torch.jit.trace(m, ex)
    ts.save(out)
    print(f"Saved TorchScript model to: {out}")

if __name__ == "__main__":
    main()
