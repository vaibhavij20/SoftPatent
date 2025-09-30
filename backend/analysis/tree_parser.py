def get_python_parser():
def parse_python_code(code):
from tree_sitter import Language, Parser
from pathlib import Path
import os

LIB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'build', 'my-languages.so')

def get_python_parser():
    if not os.path.exists(LIB_PATH):
        raise FileNotFoundError(f"Tree-sitter language library not found at {LIB_PATH}. Build it as documented." )
    PY_LANG = Language(LIB_PATH, 'python')
    parser = Parser()
    parser.set_language(PY_LANG)
    return parser

def parse_python_code(code):
    parser = get_python_parser()
    tree = parser.parse(code.encode('utf8'))
    return tree
