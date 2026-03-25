# Contributing to QAlityDeep

Thank you for your interest in contributing to QAlityDeep! This guide will help you get started.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/qalitydeep/qalitydeep.git
   cd qalitydeep
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   # or: .venv\Scripts\activate  # Windows
   ```

3. Install in development mode:
   ```bash
   pip install -e ".[all]"
   ```

4. Verify the installation:
   ```bash
   qalitydeep --version
   qalitydeep doctor
   ```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check qalitydeep/        # lint
ruff format qalitydeep/        # format
```

Line length is 120 characters. Target Python version is 3.9.

## Adding a New Metric

1. Create a new file in `qalitydeep/metrics/` (e.g., `my_metric.py`).
2. Subclass `BaseMetric` from `qalitydeep.metrics.base`.
3. Implement the `measure(self, test_case)` method.
4. Register it in `qalitydeep/metrics/__init__.py`:
   ```python
   from .my_metric import MyMetric
   register_metric("my_metric", MyMetric)
   ```

Example:

```python
from .base import BaseMetric

class MyMetric(BaseMetric):
    """Check if output contains a greeting."""
    name = "greeting_check"

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.score = None
        self.reason = ""

    def measure(self, test_case) -> None:
        output = getattr(test_case, "actual_output", "") or ""
        greetings = ["hello", "hi", "hey", "greetings"]
        found = any(g in output.lower() for g in greetings)
        self.score = 1.0 if found else 0.0
        self.reason = "Greeting found" if found else "No greeting detected"
```

## Project Structure

```
qalitydeep/
  __init__.py          # Package init, version, exports
  cli.py               # Typer CLI (7 commands)
  config.py            # Pydantic Settings
  models.py            # Data models (TestCase, EvalRun, etc.)
  evals.py             # Evaluation pipeline (DeepEval + programmatic)
  eval_config.py       # YAML config schema (Pydantic models)
  yaml_loader.py       # YAML config loader
  decorators.py        # @eval_suite, @eval_case
  discovery.py         # Python eval file discovery
  storage.py           # JSON-based persistence
  metrics/             # Metric implementations
    base.py            # BaseMetric ABC
    programmatic.py    # Deterministic metrics
    code_syntax.py     # Syntax validation
    code_diff.py       # AST-level diff
    code_execution.py  # Sandboxed execution
  formatters/          # Output formatters
    table.py           # Rich terminal tables
    json_fmt.py        # JSON output
    junit.py           # JUnit XML for CI/CD
```

## Pull Request Process

1. Fork the repository and create a feature branch.
2. Make your changes with clear commit messages.
3. Run `ruff check` and `ruff format` before committing.
4. Open a pull request with a description of your changes.
5. Ensure CI checks pass.

## Reporting Issues

Use [GitHub Issues](https://github.com/qalitydeep/qalitydeep/issues) to report bugs or request features. Include:
- QAlityDeep version (`qalitydeep --version`)
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
