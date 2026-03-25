# Changelog

All notable changes to QAlityDeep will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-26

### Added

- **Packaging**: pip-installable package with `pyproject.toml` and `hatchling` build backend.
- **CLI**: Complete Typer + Rich CLI with 7 commands: `run`, `init`, `doctor`, `watch`, `serve-api`, `history`, `metrics`.
- **YAML Configuration**: Define evaluation suites in `qalitydeep.yaml` with version-controlled, PR-reviewable test cases.
- **Python API**: `@eval_suite` and `@eval_case` decorators for programmatic evaluation definitions.
- **Programmatic Metrics** (9 total, free and instant):
  - `exact_match` — exact string equality check.
  - `contains` — substring presence check.
  - `contains_all` — multiple substring fraction check.
  - `regex_match` — regex pattern matching.
  - `json_valid` — JSON validity check.
  - `starts_with` — prefix check.
  - `code_syntax` — Python/JS/JSON syntax validation via `ast.parse`.
  - `code_diff` — AST-level structural code comparison.
  - `code_execution` — sandboxed code execution with output comparison.
- **LLM-as-Judge Metrics** (6 total, via DeepEval):
  - `correctness`, `relevancy`, `hallucination`, `tool_correctness`, `coordination`, `trajectory`.
- **Output Formats**: Rich terminal tables, JSON, and JUnit XML for CI/CD integration.
- **Onboarding**: `qalitydeep init` scaffolding, `qalitydeep doctor` health checks, bundled sample datasets.
- **File Watcher**: `qalitydeep watch` auto-reruns evaluations on config/eval file changes.
- **Cost Tracking**: Token cost estimation per model (OpenAI, Anthropic, Ollama).
- **Legacy Support**: Backwards-compatible `--dataset-id` and `--metrics` flags for existing users.

### Infrastructure

- Multi-LLM backend support: OpenAI, Anthropic (Claude), Ollama.
- LangGraph-based multi-agent workflow (Planner, Worker, Tools, Reviewer).
- Streamlit dashboard with Plotly charts.
- FastAPI evaluation server with API key authentication.
- JSON-based storage for datasets and evaluation runs.

[0.1.0]: https://github.com/jatinderDH/qalitydeep/releases/tag/v0.1.0
