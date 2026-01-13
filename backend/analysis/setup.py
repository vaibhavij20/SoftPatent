#!/usr/bin/env python3
"""
Setup script for the analysis package.
This script installs dependencies and sets up the tree-sitter Python parser.
"""
import os
import subprocess
import sys
from pathlib import Path

def install_dependencies():
    """Install required Python packages."""
    print("Installing Python dependencies...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "tree-sitter",
        "numpy",
        "scikit-learn",
        "networkx",
        "tqdm",
        "pyyaml"
    ])

def setup_tree_sitter():
    """Set up tree-sitter Python parser."""
    print("Setting up tree-sitter Python parser...")
    
    # Create necessary directories
    build_dir = Path(__file__).parent / "build"
    build_dir.mkdir(exist_ok=True)
    
    # Install tree-sitter CLI if not already installed
    try:
        subprocess.run(["tree-sitter", "--version"], 
                      check=True, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing tree-sitter CLI...")
        subprocess.check_call(["npm", "install", "-g", "tree-sitter-cli"])
    
    # Clone tree-sitter-python if it doesn't exist
    python_grammar_dir = Path("tree-sitter-python")
    if not python_grammar_dir.exists():
        print("Cloning tree-sitter-python...")
        subprocess.check_call(["git", "clone", "https://github.com/tree-sitter/tree-sitter-python"])
    
    # Build the language library
    print("Building tree-sitter Python parser...")
    os.chdir("tree-sitter-python")
    subprocess.check_call(["tree-sitter", "generate"])
    subprocess.check_call(["cc", "-fPIC", "-I./src", "-c", "src/parser.c", "-o", "parser.o"])
    subprocess.check_call(["cc", "-fPIC", "-I./src", "-c", "src/scanner.c", "-o", "scanner.o"])
    subprocess.check_call(["cc", "-shared", "-o", "../build/my-languages.so", "parser.o", "scanner.o", "-lstdc++"])
    os.chdir("..")
    
    print("\n✅ Setup completed successfully!")
    print(f"Tree-sitter Python parser built at: {build_dir}/my-languages.so")

def main():
    """Main function to run the setup."""
    try:
        install_dependencies()
        setup_tree_sitter()
    except subprocess.CalledProcessError as e:
        print(f"Error during setup: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
