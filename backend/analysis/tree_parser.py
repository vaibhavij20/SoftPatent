"""
Tree-sitter based parser for Python code.

This module provides functionality to parse Python code into an abstract syntax tree (AST)
using the tree-sitter library. It can parse both code strings and files.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any, List, cast

# Try to import tree-sitter
HAS_TREE_SITTER = True
try:
    from tree_sitter import Language, Parser, Node, Tree
    
    # Define the path to the tree-sitter Python grammar
    TREE_SITTER_PYTHON_GRAMMAR = os.path.join(
        os.path.dirname(__file__), 'tree-sitter-python', 'grammar.js'
    )
    
    # Define the path to the compiled language library
    LANGUAGE_LIBRARY = os.path.join(
        os.path.dirname(__file__), 'build', 'my-languages.so'
    )
    
    # Check if the language library exists
    HAS_LANGUAGE_LIBRARY = os.path.exists(LANGUAGE_LIBRARY)
    
except ImportError:
    HAS_TREE_SITTER = False
    HAS_LANGUAGE_LIBRARY = False

def get_python_parser() -> Parser:
    """Initialize and return a Python parser.
    
    This function initializes a tree-sitter parser for Python code.
    
    Returns:
        Parser: A configured tree-sitter Parser instance for Python.
        
    Raises:
        RuntimeError: If there's an error initializing the parser or if tree-sitter is not available.
    """
    if not HAS_TREE_SITTER:
        raise RuntimeError("tree-sitter is not installed. Please install it with: pip install tree-sitter")
    
    if not HAS_LANGUAGE_LIBRARY:
        raise RuntimeError(
            "Python language library not found. Please build it first using the build.py script."
            " See the README for instructions on how to build the language library."
        )
    
    try:
        # Load the Python language from the compiled library
        python_language = Language(LANGUAGE_LIBRARY)
        
        # Create and configure the parser
        parser = Parser()
        parser.set_language(python_language)
        
        return parser
        
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Python parser: {str(e)}") from e


def parse_python_code(code: Union[str, bytes], encoding: str = 'utf8') -> Tree:
    """Parse Python source code into a syntax tree.
    
    Args:
        code: The Python source code to parse, either as a string or bytes.
        encoding: The encoding to use if code is provided as a string.
                 Defaults to 'utf8'.
                  
    Returns:
        Tree: A tree-sitter syntax tree representing the parsed code.
        
    Raises:
        TypeError: If the input code is not a string or bytes.
        UnicodeError: If there's an encoding/decoding error.
        RuntimeError: If parsing fails.
    """
    try:
        # Ensure code is bytes
        if isinstance(code, str):
            code = code.encode(encoding)
        elif not isinstance(code, bytes):
            raise TypeError(f"Expected str or bytes, got {type(code).__name__}")
            
        # Get parser and parse the code
        parser = get_python_parser()
        return parser.parse(code)
        
    except UnicodeError as e:
        raise UnicodeError(f"Error decoding code with encoding {encoding}: {str(e)}") from e
    except Exception as e:
        raise RuntimeError(f"Error parsing Python code: {str(e)}") from e


def parse_python_file(file_path: Union[str, os.PathLike], encoding: str = 'utf8') -> Tree:
    """Parse a Python file into a syntax tree.
    
    Args:
        file_path: Path to the Python file to parse.
        encoding: The encoding to use when reading the file. Defaults to 'utf8'.
                 
    Returns:
        Tree: A tree-sitter syntax tree representing the parsed file.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory.
        PermissionError: If there are permission issues reading the file.
        RuntimeError: If parsing fails.
    """
    try:
        file_path = Path(file_path)
        
        # Basic file validation
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if file_path.is_dir():
            raise IsADirectoryError(f"Expected a file, got a directory: {file_path}")
            
        # Read the file content
        with open(file_path, 'rb') as f:
            code = f.read()
            
        # Parse the code
        return parse_python_code(code, encoding)
        
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except IsADirectoryError:
        raise IsADirectoryError(f"Expected a file, got a directory: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied when reading file: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Error parsing file {file_path}: {str(e)}") from e


# Example usage
if __name__ == "__main__":
    # Example 1: Parse a code string
    sample_code = """
    def hello():
        print("Hello, world!")
        return 42
    """
    
    try:
        tree = parse_python_code(sample_code)
        print(f"Successfully parsed code. Root node type: {tree.root_node.type}")
    except Exception as e:
        print(f"Error parsing code: {e}")
    
    # Example 2: Parse a file
    try:
        # This would be the path to a Python file in a real scenario
        # tree = parse_python_file("path/to/your/file.py")
        # print(f"Successfully parsed file. Root node type: {tree.root_node.type}")
        pass
    except Exception as e:
        print(f"Error parsing file: {e}")
