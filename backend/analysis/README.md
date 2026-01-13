# Code Analysis and Optimization Tool

A comprehensive tool for analyzing and optimizing Python code with support for domain-specific optimizations.

## Features

- **Code Parsing**: Parse Python code using tree-sitter for detailed AST analysis
- **Performance Profiling**: Identify performance bottlenecks in your code
- **Code Quality Checks**: Detect common code smells and anti-patterns
- **Domain-Specific Optimizations**: Specialized optimizations for different domains (HPC, Gaming, etc.)
- **Caching**: Built-in caching for improved performance on repeated analyses

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Patent/backend/analysis
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up tree-sitter**
   ```bash
   python setup_tree_sitter.py
   export TREE_SITTER_LIBS=$(pwd)/build
   ```

## Usage

### Basic Usage

```python
from suggestion import generate_suggestions

# Analyze a code snippet
suggestions = generate_suggestions(
    filename="example.py",
    code="""
    def example():
        # This function does something
        return 42
    """,
    domain="hpc"  # Optional domain for domain-specific suggestions
)

for suggestion in suggestions:
    print(f"{suggestion['message']}\n  Suggestion: {suggestion['patch']}\n")
```

### Using the Cache System

```python
from cache_utils import cached

@cached()
def expensive_operation(x, y):
    # This result will be cached
    return x * y

# First call - computes and caches the result
result1 = expensive_operation(10, 20)

# Second call with same arguments - returns cached result
result2 = expensive_operation(10, 20)
```

## Running Tests

To run the test suite:

```bash
python -m unittest discover tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
