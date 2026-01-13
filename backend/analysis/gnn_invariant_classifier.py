import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
import torch
import torch.nn as nn
import torch.optim as optim
from torch_geometric.nn import GCNConv, global_mean_pool
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class GNNInvariantClassifier(nn.Module):
    """GNN-based invariant classifier for code optimizations."""
    
    def __init__(self, input_dim: int = 128, hidden_dim: int = 64, output_dim: int = 32):
        super().__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x, edge_index, batch=None):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index).relu()
        if batch is not None:
            x = global_mean_pool(x, batch)
        return self.fc(x)

class OptimizationDatabase:
    """Database for storing and retrieving code optimizations."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path.home() / ".code_optimizations.json")
        self.optimizations = self._load_optimizations()
        
    def _load_optimizations(self) -> List[Dict[str, Any]]:
        """Load optimizations from the database file."""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load optimizations: {e}")
        return []
    
    def save_optimization(self, optimization: Dict[str, Any]) -> str:
        """Save an optimization to the database."""
        try:
            optimization['id'] = hashlib.sha256(
                (optimization['original_code'] + optimization['optimized_code']).encode()
            ).hexdigest()
            
            self.optimizations.append(optimization)
            
            # Save to file
            with open(self.db_path, 'w') as f:
                json.dump(self.optimizations, f, indent=2)
                
            return optimization['id']
        except (IOError, KeyError) as e:
            print(f"Error saving optimization: {e}")
            raise

def get_classifier() -> GNNInvariantClassifier:
    """Get or create a GNN classifier instance."""
    model = GNNInvariantClassifier()
    # Load pre-trained weights if available
    model_path = Path(__file__).parent / "models" / "gnn_invariants.pt"
    if model_path.exists():
        try:
            model.load_state_dict(torch.load(model_path))
        except Exception as e:
            print(f"Warning: Failed to load model weights: {e}")
    return model

# Global database instance
_optimization_db = OptimizationDatabase()

def store_optimization(
    original_code: str,
    optimized_code: str,
    performance_improvement: float,
    domain: str = "general",
    metadata: Optional[Dict] = None
) -> str:
    """Store a code optimization in the database."""
    if not original_code or not optimized_code:
        raise ValueError("Original and optimized code cannot be empty")
        
    if not isinstance(performance_improvement, (int, float)) or performance_improvement < 0:
        raise ValueError("Performance improvement must be a non-negative number")
    
    optimization = {
        'original_code': original_code,
        'optimized_code': optimized_code,
        'performance_improvement': float(performance_improvement),
        'domain': domain,
        'metadata': metadata or {},
        'timestamp': str(datetime.utcnow())
    }
    
    return _optimization_db.save_optimization(optimization)

def find_similar_optimization(
    code: str,
    threshold: float = 0.8,
    domain: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Find a similar optimization in the database."""
    if not code:
        raise ValueError("Code cannot be empty")
        
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1")
    
    # Simple similarity check (replace with actual GNN-based similarity)
    best_match = None
    best_score = threshold
    
    for opt in _optimization_db.optimizations:
        if domain and opt.get('domain') != domain:
            continue
            
        # Simple string similarity (replace with actual code embedding)
        score = sum(c1 == c2 for c1, c2 in zip(code, opt['original_code'])) / max(len(code), len(opt['original_code']))
        
        if score > best_score:
            best_score = score
            best_match = opt
    
    return best_match