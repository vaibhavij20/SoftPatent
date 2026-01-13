#!/usr/bin/env python3
"""
Setup script for tree-sitter language bindings.
This script will clone and build the tree-sitter-python parser.
"""
import os
import subprocess
import sys
from pathlib import Path

def setup_tree_sitter():
    """Set up tree-sitter Python parser."""
    try:
        # Create build directory
        build_dir = Path(__file__).parent / "build"
        build_dir.mkdir(exist_ok=True)
        os.chdir(build_dir)

        # Clone tree-sitter-python if not exists
        if not (build_dir / "tree-sitter-python").exists():
            print("Cloning tree-sitter-python...")
            subprocess.run(["git", "clone", "https://github.com/tree-sitter/tree-sitter-python"], 
                         check=True)

        # Build the language library
        print("Building tree-sitter-python...")
        os.chdir("tree-sitter-python")
        
        # Build the library
        subprocess.run(["cc", "-fPIC", "-c", "-I./src", "src/parser.c"], check=True)
        subprocess.run(["cc", "-fPIC", "-c", "-I./src", "src/scanner.c"], check=True)
        subprocess.run(["cc", "-shared", "-o", "../my-languages.so", "parser.o", "scanner.o", "-lstdc++"], 
                      check=True)
        
        print("\n✅ Successfully built tree-sitter-python library at:")
        print(f"   {build_dir.absolute()}/my-languages.so")
        print("\nAdd this to your environment:")
        print(f"export TREE_SITTER_LIBS={build_dir.absolute()}")
        
    except Exception as e:
        print(f"❌ Error setting up tree-sitter: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    setup_tree_sitter()
