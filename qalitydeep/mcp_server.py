"""MCP (Model Context Protocol) server for QAlityDeep.

Exposes evaluation tools that AI coding assistants (Claude Code, Cursor, etc.)
can invoke during development to verify code and LLM outputs.

Usage:
    qalitydeep mcp-server          # start stdio server
    qalitydeep mcp-server --sse    # start SSE server (port 8080)
"""
from __future__ import annotations

import json
import ast
from typing import Any, Optional

# Try to import MCP SDK — graceful degradation if not installed
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


def create_server() -> "Server":
    """Create and configure the QAlityDeep MCP server."""
    if not HAS_MCP:
        raise ImportError(
            "MCP SDK not installed. Install with: pip install mcp"
        )

    server = Server("qalitydeep")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available QAlityDeep tools."""
        return [
            Tool(
                name="evaluate_code",
                description=(
                    "Evaluate AI-generated code for syntax correctness, structural quality, "
                    "and optionally compare against expected output. Returns detailed scores "
                    "and reasons for each metric checked."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The code to evaluate",
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language (python, javascript, json). Default: auto-detect.",
                            "default": "python",
                        },
                        "expected_output": {
                            "type": "string",
                            "description": "Expected code output for comparison (optional).",
                        },
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Metrics to run. Default: ['code_syntax', 'code_diff']. Available: code_syntax, code_diff, code_execution, exact_match, contains, json_valid.",
                        },
                    },
                    "required": ["code"],
                },
            ),
            Tool(
                name="check_syntax",
                description=(
                    "Quick syntax check for code. Returns pass/fail with error details "
                    "if the code has syntax errors. Supports Python, JavaScript, and JSON."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The code to check",
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language (python, javascript, json). Default: auto-detect.",
                            "default": "python",
                        },
                    },
                    "required": ["code"],
                },
            ),
            Tool(
                name="evaluate_text",
                description=(
                    "Evaluate an LLM text response against expected output. "
                    "Checks for exact match, substring containment, and format validity."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "actual_output": {
                            "type": "string",
                            "description": "The actual text output to evaluate",
                        },
                        "expected_output": {
                            "type": "string",
                            "description": "The expected/reference output",
                        },
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Metrics to run. Default: ['exact_match', 'contains']. Available: exact_match, contains, contains_all, regex_match, json_valid, starts_with.",
                        },
                    },
                    "required": ["actual_output"],
                },
            ),
            Tool(
                name="run_eval_suite",
                description=(
                    "Run a QAlityDeep evaluation suite from a YAML config file. "
                    "Returns summary with pass/fail status, metric scores, and any failures."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "config_path": {
                            "type": "string",
                            "description": "Path to qalitydeep.yaml config file. Default: auto-discover in current directory.",
                        },
                        "suite_name": {
                            "type": "string",
                            "description": "Run only a specific suite by name (optional).",
                        },
                    },
                },
            ),
            Tool(
                name="list_metrics",
                description="List all available evaluation metrics with descriptions.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool invocation."""
        try:
            if name == "evaluate_code":
                result = _evaluate_code(arguments)
            elif name == "check_syntax":
                result = _check_syntax(arguments)
            elif name == "evaluate_text":
                result = _evaluate_text(arguments)
            elif name == "run_eval_suite":
                result = _run_eval_suite(arguments)
            elif name == "list_metrics":
                result = _list_metrics()
            else:
                result = {"error": f"Unknown tool: {name}"}

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as exc:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(exc)}, indent=2),
            )]

    return server


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _evaluate_code(args: dict) -> dict:
    """Evaluate code with programmatic metrics."""
    from .metrics import get_metric, METRIC_REGISTRY

    code = args.get("code", "")
    language = args.get("language", "python")
    expected = args.get("expected_output")
    metric_names = args.get("metrics", ["code_syntax", "code_diff"])

    class _TC:
        pass
    tc = _TC()
    tc.input = f"Evaluate {language} code"
    tc.actual_output = code
    tc.expected_output = expected or ""

    results = {}
    overall_pass = True

    for name in metric_names:
        if name not in METRIC_REGISTRY:
            results[name] = {"score": None, "reason": f"Unknown metric: {name}"}
            continue

        metric = get_metric(name)
        try:
            metric.measure(tc)
            passed = metric.score is not None and metric.score >= 0.5
            results[name] = {
                "score": metric.score,
                "passed": passed,
                "reason": metric.reason,
            }
            if not passed:
                overall_pass = False
        except Exception as exc:
            results[name] = {"score": 0.0, "passed": False, "reason": str(exc)}
            overall_pass = False

    return {
        "status": "PASSED" if overall_pass else "FAILED",
        "metrics": results,
        "language": language,
    }


def _check_syntax(args: dict) -> dict:
    """Quick syntax check."""
    code = args.get("code", "")
    language = args.get("language", "python")

    if language == "python":
        try:
            ast.parse(code)
            return {"valid": True, "language": "python", "message": "Syntax OK"}
        except SyntaxError as e:
            return {
                "valid": False,
                "language": "python",
                "error": str(e),
                "line": e.lineno,
                "offset": e.offset,
            }
    elif language == "json":
        try:
            json.loads(code)
            return {"valid": True, "language": "json", "message": "Valid JSON"}
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "language": "json",
                "error": str(e),
                "line": e.lineno,
                "column": e.colno,
            }
    elif language in ("javascript", "js"):
        import subprocess
        try:
            result = subprocess.run(
                ["node", "--check", "-e", code],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return {"valid": True, "language": "javascript", "message": "Syntax OK"}
            else:
                return {"valid": False, "language": "javascript", "error": result.stderr.strip()}
        except FileNotFoundError:
            return {"valid": None, "language": "javascript", "error": "Node.js not found"}
        except subprocess.TimeoutExpired:
            return {"valid": None, "language": "javascript", "error": "Syntax check timed out"}

    return {"valid": None, "language": language, "error": f"Unsupported language: {language}"}


def _evaluate_text(args: dict) -> dict:
    """Evaluate text output with programmatic metrics."""
    from .metrics import get_metric, METRIC_REGISTRY

    actual = args.get("actual_output", "")
    expected = args.get("expected_output", "")
    metric_names = args.get("metrics", ["exact_match", "contains"])

    class _TC:
        pass
    tc = _TC()
    tc.input = "Evaluate text"
    tc.actual_output = actual
    tc.expected_output = expected

    results = {}
    overall_pass = True

    for name in metric_names:
        if name not in METRIC_REGISTRY:
            results[name] = {"score": None, "reason": f"Unknown metric: {name}"}
            continue

        metric = get_metric(name)
        try:
            metric.measure(tc)
            passed = metric.score is not None and metric.score >= 0.5
            results[name] = {
                "score": metric.score,
                "passed": passed,
                "reason": metric.reason,
            }
            if not passed:
                overall_pass = False
        except Exception as exc:
            results[name] = {"score": 0.0, "passed": False, "reason": str(exc)}
            overall_pass = False

    return {
        "status": "PASSED" if overall_pass else "FAILED",
        "metrics": results,
    }


def _run_eval_suite(args: dict) -> dict:
    """Run an eval suite from a YAML config file."""
    from pathlib import Path
    from .yaml_loader import find_config, load_config
    from .storage import build_eval_run, save_eval_run

    config_path = args.get("config_path")
    suite_name = args.get("suite_name")

    if config_path:
        cfg_path = Path(config_path)
        if not cfg_path.exists():
            return {"error": f"Config file not found: {config_path}"}
    else:
        cfg_path = find_config()
        if cfg_path is None:
            return {"error": "No qalitydeep.yaml found. Run 'qalitydeep init' first."}

    try:
        config = load_config(cfg_path)
    except Exception as exc:
        return {"error": f"Failed to load config: {exc}"}

    suites = config.suites
    if suite_name:
        suites = [s for s in suites if s.name == suite_name]
        if not suites:
            available = [s.name for s in config.suites]
            return {"error": f"Suite '{suite_name}' not found. Available: {available}"}

    # Run evaluations using the CLI helper
    from .cli import _run_suite, _split_metrics
    from .models import EvalCaseResult

    all_results = []
    all_metrics = []

    for suite in suites:
        results, suite_metrics, threshold = _run_suite(suite, config, None)
        all_results.extend(results)
        for m in suite_metrics:
            if m not in all_metrics:
                all_metrics.append(m)

    # Build summary
    total = len(all_results)
    passed = sum(1 for r in all_results if all(s >= 0.5 for s in r.metrics.values()))

    # Per-metric averages
    metric_avgs = {}
    for m in all_metrics:
        scores = [r.metrics.get(m) for r in all_results if m in r.metrics]
        if scores:
            metric_avgs[m] = sum(scores) / len(scores)

    # Failures detail
    failures = []
    for r in all_results:
        for m, s in r.metrics.items():
            if s < 0.5:
                failures.append({
                    "case_id": r.test_case_id,
                    "metric": m,
                    "score": s,
                    "reason": r.metric_reasons.get(m, ""),
                })

    return {
        "status": "PASSED" if passed == total else "FAILED",
        "total_cases": total,
        "passed": passed,
        "failed": total - passed,
        "metric_averages": metric_avgs,
        "failures": failures[:10],  # Limit to first 10 failures
    }


def _list_metrics() -> dict:
    """List all available metrics."""
    from .metrics import METRIC_REGISTRY, list_available_metrics

    programmatic = {}
    for name in sorted(METRIC_REGISTRY):
        cls = METRIC_REGISTRY[name]
        doc = (cls.__doc__ or "").strip().split("\n")[0]
        programmatic[name] = doc

    llm_metrics = {
        "correctness": "Semantic equivalence between actual and expected output (requires API key).",
        "relevancy": "Answer relevancy to the input question (requires API key).",
        "hallucination": "Detect hallucinated content not grounded in context (requires API key).",
        "tool_correctness": "Validate correct tool usage (requires API key).",
        "coordination": "Multi-agent communication clarity (requires API key).",
        "trajectory": "Efficiency of reasoning steps (requires API key).",
    }

    return {
        "programmatic_metrics": programmatic,
        "llm_metrics": llm_metrics,
        "total": len(programmatic) + len(llm_metrics),
    }


# ---------------------------------------------------------------------------
# Server runner
# ---------------------------------------------------------------------------

async def run_stdio_server() -> None:
    """Run the MCP server over stdio (default mode)."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Entry point for running the MCP server."""
    import asyncio
    asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
