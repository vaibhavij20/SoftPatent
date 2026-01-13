import os
import sys
import unittest
import tempfile
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

class TestGNNInvariantClassifier(unittest.TestCase):
    """Test cases for GNN Invariant Classifier."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before running tests."""
        from analysis.gnn_invariant_classifier import GNNInvariantClassifier
        cls.test_data_dir = Path(__file__).parent / "test_data"
        cls.test_data_dir.mkdir(exist_ok=True)
        
    def test_optimization_storage(self):
        """Test storing and retrieving optimizations."""
        from analysis.gnn_invariant_classifier import (
            store_optimization,
            find_similar_optimization
        )
        
        # Test data
        test_code = "def example(): return sum(i for i in range(10))"
        optimized_code = "def example(): return 45"  # Sum of 0-9
        
        # Store optimization
        optimization_id = store_optimization(
            original_code=test_code,
            optimized_code=optimized_code,
            performance_improvement=0.5,
            domain="test"
        )
        
        self.assertIsNotNone(optimization_id, "Failed to store optimization")
        
        # Find similar optimization
        similar = find_similar_optimization(test_code, threshold=0.8)
        self.assertIsNotNone(similar, "Failed to find similar optimization")
        self.assertEqual(similar["optimized_code"], optimized_code)
        
    def test_invalid_input_handling(self):
        """Test handling of invalid inputs."""
        from analysis.gnn_invariant_classifier import find_similar_optimization
        
        with self.assertRaises(ValueError):
            find_similar_optimization("", threshold=1.5)  # Invalid threshold
            
        with self.assertRaises(ValueError):
            find_similar_optimization(None)  # None input

if __name__ == "__main__":
    unittest.main()