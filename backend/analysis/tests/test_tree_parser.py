"""Tests for tree_parser module."""
import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tree_parser import get_python_parser, parse_python_code, parse_python_file

class TestTreeParser(unittest.TestCase):
    """Test cases for tree_parser module."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Check if tree-sitter is available
        try:
            from tree_sitter import Language, Parser
            cls.tree_sitter_available = True
        except ImportError:
            cls.tree_sitter_available = False
            return
            
        # Set up test data
        cls.test_code = """
        def hello():
            print("Hello, world!")
            return 42
            
        class Test:
            def method(self):
                pass
        """
        
        # Create a test file
        cls.test_file = Path("test_parser.py")
        cls.test_file.write_text(cls.test_code)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test files."""
        if hasattr(cls, 'test_file') and cls.test_file.exists():
            cls.test_file.unlink()
    
    def test_get_python_parser(self):
        """Test parser initialization."""
        if not self.tree_sitter_available:
            self.skipTest("tree-sitter not available")
            
        parser = get_python_parser()
        self.assertIsNotNone(parser)
        self.assertIsNotNone(parser.language)
    
    def test_parse_python_code(self):
        """Test parsing code from string."""
        if not self.tree_sitter_available:
            self.skipTest("tree-sitter not available")
            
        result = parse_python_code(self.test_code)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.root_node)
    
    def test_parse_python_file(self):
        """Test parsing code from file."""
        if not self.tree_sitter_available:
            self.skipTest("tree-sitter not available")
            
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(self.test_code.encode('utf-8'))
            temp_file = f.name
        
        try:
            result = parse_python_file(temp_file)
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.root_node)
        finally:
            # Clean up
            import os
            os.unlink(temp_file)
    
    def test_parse_error_handling(self):
        """Test error handling for invalid input."""
        if not self.tree_sitter_available:
            self.skipTest("tree-sitter not available")
            
        # Test with invalid code
        with self.assertRaises(Exception):
            parse_python_code("def invalid code")
            
        # Test with non-existent file
        with self.assertRaises(FileNotFoundError):
            parse_python_file("non_existent_file.py")

if __name__ == "__main__":
    unittest.main()
