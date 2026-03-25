<div align="center">

# QAlityDeep

**Pre-deploy CI/CD QA for LLM and AI-agent outputs**

Verify that your LLM responses, AI-generated code, and agent outputs are correct -- before they ship.

[![PyPI version](https://img.shields.io/pypi/v/qalitydeep.svg)](https://pypi.org/project/qalitydeep/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/jatinderDH/qalitydeep/actions/workflows/ci.yml/badge.svg)](https://github.com/jatinderDH/qalitydeep/actions/workflows/ci.yml)

</div>

---

## Why QAlityDeep?

73% of developers use AI coding tools, but 46% don't trust the output. There's a gap between "AI wrote this" and "we shipped this." QAlityDeep fills that gap.

- **The missing testing layer** -- QAlityDeep sits between AI-generated output and your production deploy, catching regressions, hallucinations, and broken code before they reach users.
- **Works with ANY LLM output** -- ChatGPT, Claude, Cursor, Copilot, custom agents, RAG pipelines, or any system that produces text or code.
- **9 programmatic metrics** -- free, instant, no API key required. Validate syntax, match patterns, run code, and compare ASTs in milliseconds.
- **6 LLM-as-judge metrics** -- semantic correctness, relevancy, hallucination detection, tool call validation, multi-agent coordination, and trajectory analysis.
- **CI/CD native** -- JUnit XML output, configurable thresholds, non-zero exit codes on failure. Drop it into GitHub Actions, GitLab CI, or any pipeline.

---

## Quick Start (60 seconds)

```bash
# Install
pip install qalitydeep

# Scaffold a project with sample config and eval files
qalitydeep init

# Run your first evaluation
qalitydeep run
```

`qalitydeep init` creates a `qalitydeep.yaml` config file with sample test suites and an `evals/` directory with Python-based eval definitions. `qalitydeep run` loads the config, executes all test cases against the configured metrics, and prints a pass/fail results table.

---

## Installation

**Core** (CLI + programmatic metrics):

```bash
pip install qalitydeep
```

**With Streamlit dashboard:**

```bash
pip install "qalitydeep[dashboard]"
```

**With FastAPI server:**

```bash
pip install "qalitydeep[api]"
```

**Everything:**

```bash
pip install "qalitydeep[all]"
```

**Development (editable install):**

```bash
git clone https://github.com/jatinderDH/qalitydeep.git
cd qalitydeep
pip install -e ".[all]"
```

Requires **Python 3.9+**. Tested on Python 3.9 through 3.13.

---

## Configuration

QAlityDeep uses a `qalitydeep.yaml` file in your project root. Run `qalitydeep init` to generate one, or create it manually.

```yaml
version: "1"

# Default settings applied to all suites unless overridden
defaults:
  metrics: [correctness, relevancy]   # Metrics to run on every test case
  threshold: 0.7                       # Minimum score to pass (0.0 - 1.0)

suites:
  # A QA suite for chatbot responses
  - name: chatbot_qa
    description: "Verify support chatbot answers"
    test_cases:
      - input: "What is your refund policy?"
        expected_output: "We offer a 30-day full refund on all purchases"

      - input: "Do you ship internationally?"
        expected_output: "Yes, we ship worldwide with delivery in 5-10 business days"

      - input: "How do I reset my password?"
        expected_output: "Go to Settings > Account > Reset Password"

  # A code quality suite with different metrics
  - name: code_quality
    description: "Validate AI-generated code"
    metrics: [code_syntax, exact_match]   # Override default metrics for this suite
    threshold: 0.8                         # Override default threshold
    test_cases:
      - input: "Write a hello world function"
        expected_output: |
          def hello():
              return "Hello, World!"

      # When actual_output is provided, the LLM is not invoked --
      # the output is evaluated directly against the metrics.
      - input: "Write a fibonacci function"
        actual_output: |
          def fib(n):
              if n <= 1:
                  return n
              return fib(n - 1) + fib(n - 2)
        expected_output: |
          def fib(n):
              if n <= 1:
                  return n
              return fib(n - 1) + fib(n - 2)
```

### Configuration reference

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Config format version. Currently `"1"`. |
| `defaults.metrics` | list[string] | Metrics applied to all suites unless overridden. |
| `defaults.threshold` | float | Global pass/fail threshold (0.0 - 1.0). |
| `defaults.provider` | string | LLM backend: `openai`, `anthropic`, or `ollama`. |
| `defaults.model` | string | Model name override (e.g. `gpt-4.1-mini`). |
| `suites[].name` | string | Unique name for the suite. |
| `suites[].description` | string | Human-readable description. |
| `suites[].metrics` | list[string] | Override `defaults.metrics` for this suite. |
| `suites[].threshold` | float | Override `defaults.threshold` for this suite. |
| `suites[].test_cases[].input` | string | The prompt or input text. |
| `suites[].test_cases[].expected_output` | string | The expected correct output. |
| `suites[].test_cases[].actual_output` | string | Pre-computed output (skips LLM invocation). |
| `suites[].test_cases[].language` | string | Language hint for code metrics: `python`, `javascript`, `json`. |
| `suites[].test_cases[].tags` | list[string] | Tags for filtering and organization. |

---

## Python API

Define evaluation suites directly in Python using decorators. Place files matching `eval_*.py` in your project and QAlityDeep discovers them automatically.

```python
from qalitydeep import eval_suite, eval_case


@eval_suite(metrics=["code_syntax", "exact_match"], threshold=0.8)
def test_basic_functions():
    """Test basic Python function generation."""
    return [
        eval_case(
            input="Write a function that adds two numbers",
            expected_output="def add(a, b):\n    return a + b",
        ),
        eval_case(
            input="Write a function that checks if a number is even",
            expected_output="def is_even(n):\n    return n % 2 == 0",
        ),
    ]


@eval_suite(metrics=["correctness", "relevancy"], threshold=0.7)
def test_qa_responses():
    """Test customer support responses."""
    return [
        eval_case(
            input="What is your refund policy?",
            expected_output="We offer a 30-day full refund on all purchases",
        ),
    ]
```

Run with:

```bash
qalitydeep run
```

QAlityDeep discovers `eval_*.py` files in the current directory and `evals/` subdirectory, executing all `@eval_suite`-decorated functions.

---

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `qalitydeep run` | Run evaluations from YAML config, Python eval files, or a legacy dataset. |
| `qalitydeep init` | Scaffold a new project with sample config and eval files. |
| `qalitydeep doctor` | Check environment, dependencies, and configuration health. |
| `qalitydeep watch` | Watch config and eval files for changes, re-running evaluations automatically. |
| `qalitydeep serve-api` | Start the FastAPI evaluation server. |
| `qalitydeep history` | List recent evaluation runs with scores and pass rates. |
| `qalitydeep metrics` | List all available evaluation metrics. |

### `qalitydeep run`

The primary command. Loads configuration, executes test suites, and reports results.

```bash
# Run all suites from auto-discovered config
qalitydeep run

# Run a specific config file
qalitydeep run --config path/to/qalitydeep.yaml

# Run only one suite
qalitydeep run --suite chatbot_qa

# Output as JSON
qalitydeep run --output json

# Output as JUnit XML (for CI systems)
qalitydeep run --output junit --junit-file results.xml

# Override the pass/fail threshold
qalitydeep run --threshold 0.9

# Don't fail the process on threshold violations
qalitydeep run --no-fail-on-error
```

**Flags:**

| Flag | Short | Description |
|------|-------|-------------|
| `--config` | `-c` | Path to config file. Auto-discovers `qalitydeep.yaml` when omitted. |
| `--suite` | `-s` | Run only a specific suite by name. |
| `--output` | `-o` | Output format: `table` (default), `json`, or `junit`. |
| `--junit-file` | | Path to write JUnit XML file. |
| `--threshold` | `-t` | Override pass/fail threshold (0.0 - 1.0). |
| `--fail-on-error` / `--no-fail-on-error` | | Exit code 1 when any case fails the threshold (default: enabled). |

### `qalitydeep watch`

Watches your config and eval files for changes and automatically re-runs evaluations.

```bash
qalitydeep watch
qalitydeep watch --config my_config.yaml --output json
```

### `qalitydeep serve-api`

Starts a FastAPI server for programmatic evaluation via HTTP.

```bash
qalitydeep serve-api --host 0.0.0.0 --port 8000
```

Requires the `api` extra: `pip install "qalitydeep[api]"`.

---

## Available Metrics

### Programmatic Metrics

Free, instant, no API key required. These run locally and return results in milliseconds.

| Metric | What it checks | Details |
|--------|---------------|---------|
| `exact_match` | Exact string equality | Score 1.0 if `actual_output` exactly matches `expected_output` (whitespace-trimmed). |
| `contains` | Substring presence | Score 1.0 if `expected_output` is found as a substring in `actual_output`. |
| `contains_all` | Multiple substring presence | Score = fraction of required substrings found in `actual_output`. |
| `regex_match` | Regex pattern matching | Score 1.0 if the regex pattern matches anywhere in `actual_output`. |
| `json_valid` | Valid JSON check | Score 1.0 if `actual_output` is parseable as valid JSON. |
| `starts_with` | Prefix check | Score 1.0 if `actual_output` starts with the given prefix. |
| `code_syntax` | Python/JS/JSON syntax validity | Parses code using `ast` (Python), `node` (JS), or `json` module. Auto-detects language. |
| `code_diff` | AST-level code similarity | Compares code structure using AST analysis (Python) with text similarity fallback. Weighted: 70% AST + 30% text. |
| `code_execution` | Run code and check output | Executes code in a sandboxed subprocess, compares stdout to `expected_output`. Supports Python and Node.js. |

### LLM-as-Judge Metrics

Require an API key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`). These use an LLM to evaluate output quality semantically.

| Metric | What it checks | Details |
|--------|---------------|---------|
| `correctness` | Semantic equivalence | GEval-based scoring of whether `actual_output` conveys the same meaning as `expected_output`. |
| `relevancy` | Answer relevancy | DeepEval `AnswerRelevancyMetric` -- does the answer address the input question? |
| `hallucination` | Fact grounding | DeepEval `HallucinationMetric` -- detects claims not grounded in the provided context. |
| `tool_correctness` | Tool call accuracy | Validates that the agent called the right tools with correct parameters. |
| `coordination` | Multi-agent alignment | GEval-based scoring of communication clarity and consistency across agents. |
| `trajectory` | Step efficiency | GEval-based analysis of reasoning step appropriateness and efficiency. |

---

## CI/CD Integration

### GitHub Actions

```yaml
name: LLM Eval
on: [push, pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install qalitydeep

      - run: qalitydeep run --output junit --junit-file results.xml

      - uses: dorny/test-reporter@v1
        if: always()
        with:
          name: QAlityDeep Results
          path: results.xml
          reporter: java-junit
```

**How it works:**

1. `qalitydeep run` loads your `qalitydeep.yaml` and executes all test suites.
2. `--output junit` formats results as JUnit XML, the standard CI test format.
3. `--junit-file results.xml` writes the XML to disk for the test reporter.
4. If any test case scores below the configured threshold, `qalitydeep run` exits with code 1, failing the CI pipeline.
5. The `dorny/test-reporter` step renders results as a GitHub check with inline annotations.

### Other CI Systems

QAlityDeep works with any CI system that supports exit codes and JUnit XML:

```bash
# GitLab CI, CircleCI, Jenkins, etc.
pip install qalitydeep
qalitydeep run --output junit --junit-file results.xml --threshold 0.8
```

Exit code 0 means all cases passed. Exit code 1 means at least one case fell below the threshold. Use `--no-fail-on-error` to always exit 0 (useful for advisory-only runs).

---

## Environment Variables

Configure LLM backends and integrations via environment variables. Copy `.env.example` to `.env.local` and fill in your values.

```bash
cp .env.example .env.local
```

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_BACKEND` | LLM provider: `openai`, `anthropic`, or `ollama` | `openai` |
| `OPENAI_API_KEY` | OpenAI API key (required when `LLM_BACKEND=openai`) | -- |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4.1-mini` |
| `ANTHROPIC_API_KEY` | Anthropic API key (required when `LLM_BACKEND=anthropic`) | -- |
| `ANTHROPIC_MODEL` | Anthropic model name | `claude-3-5-sonnet-20241022` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `llama3.1` |
| `LANGSMITH_API_KEY` | LangSmith API key (optional, for trajectory evals) | -- |
| `LANGSMITH_PROJECT` | LangSmith project name | `qalitydeep-predeploy` |
| `QALITYDEEP_DATA_DIR` | Directory for storing datasets and run results | `./data` |
| `APP_ENV` | Application environment: `dev`, `test`, or `prod` | `dev` |

Programmatic metrics (exact_match, code_syntax, etc.) do not require any API key. You only need an API key when using LLM-as-judge metrics like `correctness`, `relevancy`, or `hallucination`.

---

## Project Structure

```
qalitydeep/
  __init__.py              # Package entry: exports eval_suite, eval_case
  cli.py                   # Typer CLI application (7 commands)
  eval_config.py           # Pydantic models for YAML config
  models.py                # Core data models (TestCase, EvalRun, EvalCaseResult)
  yaml_loader.py           # YAML config discovery and parsing
  decorators.py            # @eval_suite and eval_case() Python API
  discovery.py             # Auto-discover eval_*.py files
  scaffolding.py           # qalitydeep init project generator
  doctor.py                # qalitydeep doctor health checks
  watcher.py               # File watcher for qalitydeep watch
  evals.py                 # LLM-as-judge evaluation logic
  metrics/
    __init__.py             # Metric registry and discovery
    base.py                 # BaseMetric abstract class
    programmatic.py         # ExactMatch, Contains, Regex, JSON, StartsWith
    code_syntax.py          # Python/JS/JSON syntax validation
    code_diff.py            # AST-level code comparison
    code_execution.py       # Sandboxed code execution
  formatters/
    __init__.py             # Formatter registry
    table.py                # Rich table output
    json_fmt.py             # JSON output
    junit.py                # JUnit XML output
  llm_backends.py          # OpenAI / Anthropic / Ollama abstraction
  langgraph_flows.py       # LangGraph multi-agent workflows
  api_server.py            # FastAPI server (qalitydeep serve-api)
  storage.py               # JSON-based run persistence
  cost_tracker.py          # LLM cost estimation
  sandbox.py               # Code execution sandboxing
  templates/               # Scaffolding templates
data/
  datasets/                # Uploaded evaluation datasets (CSV/JSON)
  runs/                    # Persisted evaluation run results (JSON)
  sample/                  # Sample datasets for demos
pyproject.toml             # Package configuration (hatchling)
qalitydeep.yaml            # Your evaluation config (created by init)
streamlit_app.py           # Streamlit dashboard UI
```

---

## Contributing

Contributions are welcome. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on setting up a development environment, running tests, and submitting pull requests.

```bash
# Development setup
git clone https://github.com/jatinderDH/qalitydeep.git
cd qalitydeep
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"

# Run tests
pytest

# Lint and format
ruff check .
ruff format .
```

---

## License

MIT License. See [LICENSE](LICENSE) for the full text.

---

## Links

- [Documentation](https://github.com/jatinderDH/qalitydeep/wiki)
- [PyPI Package](https://pypi.org/project/qalitydeep/)
- [GitHub Issues](https://github.com/jatinderDH/qalitydeep/issues)
- [Changelog](CHANGELOG.md)
