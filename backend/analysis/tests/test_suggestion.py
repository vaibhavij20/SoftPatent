"""Tests for suggestion module."""
import ast
import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from suggestion import generate_suggestions, _compute_ast_metrics, _run_python_quality_checks

class TestSuggestionSystem(unittest.TestCase):
    """Test cases for the suggestion system."""
    
    def setUp(self):
        """Set up test data."""
        self.test_code = ("""
import os  # Unused import
import sys  # Unused import

def long_function_with_many_parameters(a, b, c, d, e, f, g, h, i, j):
    # This function has too many parameters
    return a + b + c + d + e + f + g + h + i + j
    
def function_with_print():
    # Using print instead of logging
    print("This should be a log message")
    
unused_var = 42  # Unused variable
""".strip())
    
    def test_compute_ast_metrics(self):
        """Test AST metrics computation."""
        metrics = _compute_ast_metrics(ast.parse(self.test_code))
        self.assertIn("function_count", metrics)
        self.assertIn("class_count", metrics)
        self.assertIn("call_sites", metrics)
        self.assertIn("max_function_statements", metrics)
    
    def test_python_quality_checks(self):
        """Test Python quality checks."""
        tree = ast.parse(self.test_code)
        suggestions = _run_python_quality_checks(tree, self.test_code, "test.py")
        
        # Should find unused imports
        self.assertTrue(any(s['message'].startswith("Unused import") for s in suggestions))
        
        # Should find long function with many parameters
        self.assertTrue(any("too many parameters" in s['message'].lower() for s in suggestions))
    
    def test_generate_suggestions(self):
        """Test the main suggestion generation."""
        suggestions = generate_suggestions(
            filename="test.py",
            code=self.test_code,
            domain="hpc"
        )
        
        # Should find at least one suggestion
        self.assertGreater(len(suggestions), 0)
        
        # Each suggestion should have required fields
        for suggestion in suggestions:
            self.assertIn('message', suggestion)
            self.assertIn('patch', suggestion)
            self.assertIn('reason', suggestion)
            self.assertIn('audit', suggestion)

class TestDomainSpecificRules(unittest.TestCase):
    """Test domain-specific suggestion rules."""
    
    def test_gaming_domain_rules(self):
        """Test gaming domain specific rules."""
        code = """
        def game_loop():
            while True:
                # Using print in game loop
                print("Game loop running...")
                # Time.sleep in game loop
                import time
                time.sleep(0.1)
        """
        
        suggestions = generate_suggestions(
            filename="game.py",
            code=code,
            domain="gaming"
        )
        
        # Should find print in game loop
        self.assertTrue(any("print" in s['message'].lower() and "game loop" in s['message'].lower() for s in suggestions))
        
        # Should find sleep in game loop
        self.assertTrue(any("time.sleep() in game loop" in s['message'] for s in suggestions))

if __name__ == "__main__":
    unittest.main()
