"""QAlityDeep CLI - Pre-deploy CI/CD QA for LLM and AI-agent outputs.

Built with Typer + Rich.  Entry-point: ``qalitydeep = "qalitydeep.cli:app"``
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .eval_config import EvalConfig, EvalSuite, EvalTestCase
from .metrics import METRIC_REGISTRY, get_metric, list_available_metrics
from .models import EvalCaseResult, EvalRun, TestCase

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LLM_METRICS = {
    "correctness",
    "relevancy",
    "hallucination",
    "tool_correctness",
    "coordination",
    "trajectory",
}

console = Console()

# ---------------------------------------------------------------------------
# Typer application
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="qalitydeep",
    help="Pre-deploy CI/CD QA for LLM and AI-agent outputs.",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# Version callback
# ---------------------------------------------------------------------------

def _version_callback(value: bool) -> None:
    if value:
        console.print(f"qalitydeep [bold cyan]{__version__}[/bold cyan]")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """QAlityDeep -- Pre-deploy CI/CD QA for LLM and AI-agent outputs."""


# ---------------------------------------------------------------------------
# Helpers: metric splitting
# ---------------------------------------------------------------------------

def _split_metrics(metrics: List[str]) -> tuple:
    """Split a list of metric names into (programmatic, llm, unknown)."""
    programmatic = [m for m in metrics if m in METRIC_REGISTRY]
    llm = [m for m in metrics if m in LLM_METRICS]
    unknown = [m for m in metrics if m not in METRIC_REGISTRY and m not in LLM_METRICS]
    return programmatic, llm, unknown


# ---------------------------------------------------------------------------
# Helper: evaluate_case_simple  (no LangGraph, programmatic metrics only)
# ---------------------------------------------------------------------------

def evaluate_case_simple(
    test_case_id: str,
    input_text: str,
    actual_output: str,
    expected_output: Optional[str],
    selected_metrics: List[str],
    threshold: float = 0.5,
) -> EvalCaseResult:
    """Evaluate using the new metrics system (no LangGraph workflow)."""
    start = time.perf_counter()

    # Build a lightweight object that satisfies the metric `.measure()` API.
    class _SimpleTestCase:
        pass

    tc = _SimpleTestCase()
    tc.input = input_text  # type: ignore[attr-defined]
    tc.actual_output = actual_output  # type: ignore[attr-defined]
    tc.expected_output = expected_output  # type: ignore[attr-defined]

    metric_scores: dict[str, float] = {}
    metric_reasons: dict[str, str] = {}

    for metric_name in selected_metrics:
        if metric_name not in METRIC_REGISTRY:
            continue
        metric = get_metric(metric_name, threshold=threshold)
        try:
            metric.measure(tc)
        except Exception as exc:  # noqa: BLE001
            metric_reasons[metric_name] = f"Error: {exc}"
            continue
        if metric.score is not None:
            metric_scores[metric_name] = float(metric.score)
        metric_reasons[metric_name] = metric.reason

    latency_ms = (time.perf_counter() - start) * 1000

    return EvalCaseResult(
        test_case_id=test_case_id,
        actual_output=actual_output,
        metrics=metric_scores,
        metric_reasons=metric_reasons,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# Helper: run a single YAML/Python suite
# ---------------------------------------------------------------------------

def _run_suite(
    suite: EvalSuite,
    config: EvalConfig,
    threshold_override: Optional[float],
) -> tuple:
    """Run all test cases in *suite* and return ``(results, threshold)``."""
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    resolved = config.resolve_suite(suite)
    metrics = resolved.metrics or config.defaults.metrics
    threshold = threshold_override if threshold_override is not None else (resolved.threshold or 0.5)

    programmatic, llm, unknown = _split_metrics(metrics)

    if unknown:
        console.print(
            f"  [yellow]Warning:[/yellow] Unknown metrics ignored: {', '.join(unknown)}"
        )

    results: list[EvalCaseResult] = []
    total = len(resolved.test_cases)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"Suite: {resolved.name}", total=total)

        for idx, tc in enumerate(resolved.test_cases):
            case_id = tc.id or f"{resolved.name}_{idx}"

            # Determine actual_output -------------------------------------------
            actual_output = tc.actual_output  # may be None

            if actual_output is None and llm:
                # Need to invoke the LangGraph workflow to obtain actual_output
                try:
                    from .langgraph_flows import run_multi_agent_workflow

                    run = run_multi_agent_workflow(tc.input)
                    actual_output = run["output"]
                except Exception as exc:  # noqa: BLE001
                    console.print(
                        f"  [red]Error running workflow for case {case_id}:[/red] {exc}"
                    )
                    results.append(
                        EvalCaseResult(
                            test_case_id=case_id,
                            actual_output="",
                            metrics={m: 0.0 for m in metrics},
                            metric_reasons={m: f"Workflow error: {exc}" for m in metrics},
                            latency_ms=0.0,
                        )
                    )
                    progress.update(task, advance=1)
                    continue

            if actual_output is None and not llm:
                # Programmatic-only but no actual_output -- use expected_output
                # as a self-check, or skip gracefully.
                if tc.expected_output is not None:
                    actual_output = tc.expected_output
                else:
                    console.print(
                        f"  [yellow]Warning:[/yellow] Case {case_id} has no "
                        "actual_output and no expected_output. Skipping."
                    )
                    progress.update(task, advance=1)
                    continue

            # Evaluate programmatic metrics ------------------------------------
            start = time.perf_counter()
            prog_result = evaluate_case_simple(
                test_case_id=case_id,
                input_text=tc.input,
                actual_output=actual_output,
                expected_output=tc.expected_output,
                selected_metrics=programmatic,
                threshold=threshold,
            )
            prog_latency = (time.perf_counter() - start) * 1000

            # Evaluate LLM metrics (via DeepEval + existing evaluate_case_api) --
            llm_scores: dict[str, float] = {}
            llm_reasons: dict[str, str] = {}
            llm_latency = 0.0

            if llm:
                try:
                    from .evals import evaluate_case_api

                    llm_start = time.perf_counter()
                    api_result = evaluate_case_api(
                        input_text=tc.input,
                        actual_output=actual_output,
                        expected_output=tc.expected_output,
                        selected_metrics=llm,
                    )
                    llm_latency = (time.perf_counter() - llm_start) * 1000
                    llm_scores = api_result.get("metrics", {})
                    llm_reasons = api_result.get("reasons", {})
                except Exception as exc:  # noqa: BLE001
                    llm_reasons = {m: f"LLM eval error: {exc}" for m in llm}

            # Merge results -----------------------------------------------------
            merged_scores = {**prog_result.metrics, **llm_scores}
            merged_reasons = {**prog_result.metric_reasons, **llm_reasons}
            total_latency = prog_latency + llm_latency

            results.append(
                EvalCaseResult(
                    test_case_id=case_id,
                    actual_output=actual_output,
                    metrics=merged_scores,
                    metric_reasons=merged_reasons,
                    latency_ms=total_latency,
                )
            )
            progress.update(task, advance=1)

    return results, metrics, threshold


# ---------------------------------------------------------------------------
# Helper: format & print results
# ---------------------------------------------------------------------------

def _format_output(
    run: EvalRun,
    output_format: str,
    threshold: float,
    junit_file: Optional[str],
) -> None:
    """Render the eval run in the requested format."""
    if output_format == "json":
        from .formatters import JsonFormatter

        console.print(JsonFormatter().format_run(run))

    elif output_format == "junit":
        from .formatters import JUnitFormatter

        fmt = JUnitFormatter()
        xml = fmt.format_run(run, threshold=threshold)
        console.print(xml)
        if junit_file:
            fmt.write_file(run, junit_file, threshold=threshold)
            console.print(f"\n[green]JUnit XML written to {junit_file}[/green]")

    else:  # table (default)
        from .formatters import TableFormatter

        TableFormatter(console=console).format_run(run, threshold=threshold)


# ---------------------------------------------------------------------------
# Command: run
# ---------------------------------------------------------------------------

@app.command(
    help="Run evaluations from YAML config, Python eval files, or a legacy dataset.",
    rich_help_panel="Evaluation",
)
def run(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file. Auto-discovers qalitydeep.yaml when omitted.",
        exists=False,
        rich_help_panel="Config",
    ),
    suite_name: Optional[str] = typer.Option(
        None,
        "--suite",
        "-s",
        help="Run only a specific suite by name.",
        rich_help_panel="Config",
    ),
    output: str = typer.Option(
        "table",
        "--output",
        "-o",
        help="Output format: table, json, or junit.",
        rich_help_panel="Output",
    ),
    junit_file: Optional[str] = typer.Option(
        None,
        "--junit-file",
        help="Path to write JUnit XML file.",
        rich_help_panel="Output",
    ),
    threshold: Optional[float] = typer.Option(
        None,
        "--threshold",
        "-t",
        help="Override pass/fail threshold (0.0 - 1.0).",
        rich_help_panel="Config",
    ),
    fail_on_error: bool = typer.Option(
        True,
        "--fail-on-error/--no-fail-on-error",
        help="Exit code 1 when any case fails the threshold.",
        rich_help_panel="Config",
    ),
    # Legacy flags (backwards-compatible with old run-eval) ------------------
    dataset_id: Optional[str] = typer.Option(
        None,
        "--dataset-id",
        help="[Legacy] Run against a stored dataset (like old run-eval).",
        rich_help_panel="Legacy",
    ),
    metrics_csv: Optional[str] = typer.Option(
        None,
        "--metrics",
        help="[Legacy] Comma-separated metric names.",
        rich_help_panel="Legacy",
    ),
    graph_name: str = typer.Option(
        "multi_agent",
        "--graph-name",
        help="[Legacy] Graph name for the LangGraph workflow.",
        rich_help_panel="Legacy",
    ),
) -> None:
    # ------------------------------------------------------------------
    # Legacy path: --dataset-id supplied
    # ------------------------------------------------------------------
    if dataset_id is not None:
        _run_legacy(
            dataset_id=dataset_id,
            metrics_csv=metrics_csv,
            graph_name=graph_name,
            output_format=output,
            junit_file=junit_file,
            threshold_override=threshold,
            fail_on_error=fail_on_error,
        )
        return

    # ------------------------------------------------------------------
    # New path: YAML config or Python discovery
    # ------------------------------------------------------------------
    from .yaml_loader import find_config as _find_config, load_config as _load_config

    cfg_path: Optional[Path] = None
    if config is not None:
        cfg_path = Path(config)
        if not cfg_path.exists():
            console.print(f"[red]Config file not found:[/red] {cfg_path}")
            raise typer.Exit(code=1)
    else:
        cfg_path = _find_config()

    eval_config: Optional[EvalConfig] = None
    if cfg_path is not None:
        try:
            eval_config = _load_config(cfg_path)
            console.print(
                f"[dim]Loaded config from {cfg_path}[/dim]\n"
            )
        except Exception as exc:
            console.print(f"[red]Error loading config:[/red] {exc}")
            raise typer.Exit(code=1) from exc

    # Fall back to Python suite discovery if no YAML config
    if eval_config is None or not eval_config.suites:
        eval_config = eval_config or EvalConfig()
        try:
            from .discovery import discover_python_suites

            py_suites = discover_python_suites()
            if py_suites:
                console.print(
                    f"[dim]Discovered {len(py_suites)} Python eval suite(s)[/dim]\n"
                )
                for ps in py_suites:
                    cases = ps.get_cases()
                    eval_config.suites.append(
                        EvalSuite(
                            name=ps.name,
                            description=ps.description,
                            metrics=ps.metrics or None,
                            threshold=ps.threshold,
                            test_cases=[
                                EvalTestCase(
                                    id=c.id,
                                    input=c.input,
                                    expected_output=c.expected_output,
                                    expected_tool_calls=c.expected_tool_calls,
                                    tags=c.tags,
                                    language=c.language,
                                )
                                for c in cases
                            ],
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            console.print(f"[yellow]Warning:[/yellow] Python discovery failed: {exc}")

    if not eval_config.suites:
        console.print(
            "[red]No suites found.[/red] "
            "Create a qalitydeep.yaml or add eval_*.py files, "
            "then try again. Run [bold]qalitydeep init[/bold] to scaffold."
        )
        raise typer.Exit(code=1)

    # Filter to a single suite if --suite was specified
    suites = eval_config.suites
    if suite_name:
        suites = [s for s in suites if s.name == suite_name]
        if not suites:
            available = ", ".join(s.name for s in eval_config.suites)
            console.print(
                f"[red]Suite '{suite_name}' not found.[/red] Available: {available}"
            )
            raise typer.Exit(code=1)

    # Run each suite -------------------------------------------------------
    from .storage import build_eval_run, save_eval_run

    all_results: list[EvalCaseResult] = []
    all_metrics: list[str] = []
    effective_threshold = threshold if threshold is not None else eval_config.defaults.threshold
    any_failure = False

    for suite in suites:
        results, suite_metrics, suite_threshold = _run_suite(
            suite, eval_config, threshold
        )
        all_results.extend(results)

        # Collect unique metrics
        for m in suite_metrics:
            if m not in all_metrics:
                all_metrics.append(m)

        # Check for failures
        for r in results:
            for score in r.metrics.values():
                if score < suite_threshold:
                    any_failure = True
                    break

    # Build & persist the run -----------------------------------------------
    dataset_label = cfg_path.stem if cfg_path else "python_suites"
    eval_run = build_eval_run(
        dataset_id=dataset_label,
        graph_name=graph_name,
        metrics=all_metrics,
        cases=all_results,
    )
    try:
        save_eval_run(eval_run)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]Warning:[/yellow] Could not save run: {exc}")

    # Format output ---------------------------------------------------------
    console.print()
    _format_output(eval_run, output, effective_threshold, junit_file)

    # Exit code -------------------------------------------------------------
    if any_failure and fail_on_error:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Legacy run helper (old run-eval behaviour)
# ---------------------------------------------------------------------------

def _run_legacy(
    dataset_id: str,
    metrics_csv: Optional[str],
    graph_name: str,
    output_format: str,
    junit_file: Optional[str],
    threshold_override: Optional[float],
    fail_on_error: bool,
) -> None:
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

    from .evals import evaluate_case
    from .storage import (
        build_eval_run,
        list_datasets,
        load_dataset_cases,
        save_eval_run,
    )

    if not metrics_csv:
        console.print("[red]--metrics is required when using --dataset-id[/red]")
        raise typer.Exit(code=1)

    metric_list = [m.strip() for m in metrics_csv.split(",") if m.strip()]
    threshold = threshold_override if threshold_override is not None else 0.5

    datasets = {d.dataset_id: d for d in list_datasets()}
    if dataset_id not in datasets:
        console.print(
            f"[red]Dataset '{dataset_id}' not found.[/red] "
            f"Available: {list(datasets)}"
        )
        raise typer.Exit(code=1)

    ds = datasets[dataset_id]
    cases = load_dataset_cases(ds)

    results: list[EvalCaseResult] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Evaluating", total=len(cases))
        for case in cases:
            start = time.perf_counter()
            result = evaluate_case(case, metric_list)
            result.latency_ms = (time.perf_counter() - start) * 1000
            results.append(result)
            progress.update(task, advance=1)

    run = build_eval_run(
        dataset_id=ds.dataset_id,
        graph_name=graph_name,
        metrics=metric_list,
        cases=results,
    )
    save_eval_run(run)

    _format_output(run, output_format, threshold, junit_file)

    # Check for failures
    if fail_on_error:
        for r in results:
            for score in r.metrics.values():
                if score < threshold:
                    raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Command: init
# ---------------------------------------------------------------------------

@app.command(
    help="Scaffold a new QAlityDeep project with sample config and eval files.",
    rich_help_panel="Setup",
)
def init() -> None:
    from .scaffolding import run_init

    try:
        run_init()
    except KeyboardInterrupt:
        console.print("\n[dim]Aborted.[/dim]")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Init failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


# ---------------------------------------------------------------------------
# Command: doctor
# ---------------------------------------------------------------------------

@app.command(
    help="Check environment, dependencies, and configuration health.",
    rich_help_panel="Setup",
)
def doctor() -> None:
    from .doctor import run_doctor

    try:
        all_ok = run_doctor()
    except Exception as exc:
        console.print(f"[red]Doctor failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if not all_ok:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Command: watch
# ---------------------------------------------------------------------------

@app.command(
    help="Watch config and eval files for changes, re-running evaluations automatically.",
    rich_help_panel="Evaluation",
)
def watch(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file.",
        exists=False,
        rich_help_panel="Config",
    ),
    output: str = typer.Option(
        "table",
        "--output",
        "-o",
        help="Output format: table, json, or junit.",
        rich_help_panel="Output",
    ),
) -> None:
    from .watcher import EvalWatcher
    from .yaml_loader import find_config as _find_config, load_config as _load_config

    def on_change(changed_files: list) -> None:
        """Callback triggered by the watcher on file changes."""
        try:
            # Re-invoke the run logic in-process
            from .storage import build_eval_run, save_eval_run

            cfg_path = Path(config) if config else _find_config()
            if cfg_path is None:
                console.print("[yellow]No config file found. Skipping.[/yellow]")
                return
            eval_config = _load_config(cfg_path)

            all_results: list[EvalCaseResult] = []
            all_metrics: list[str] = []

            for suite in eval_config.suites:
                results, suite_metrics, _ = _run_suite(suite, eval_config, None)
                all_results.extend(results)
                for m in suite_metrics:
                    if m not in all_metrics:
                        all_metrics.append(m)

            eval_run = build_eval_run(
                dataset_id=cfg_path.stem,
                graph_name="multi_agent",
                metrics=all_metrics,
                cases=all_results,
            )
            save_eval_run(eval_run)
            _format_output(eval_run, output, eval_config.defaults.threshold, None)

        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Evaluation error:[/red] {exc}")

    watcher = EvalWatcher(on_change=on_change)

    try:
        watcher.start()
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching.[/dim]")


# ---------------------------------------------------------------------------
# Command: serve-api
# ---------------------------------------------------------------------------

@app.command(
    name="serve-api",
    help="Start the FastAPI evaluation server.",
    rich_help_panel="Server",
)
def serve_api(
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="Bind address.",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="Listening port.",
    ),
) -> None:
    try:
        from .api_server import run_server
    except ImportError as exc:
        console.print(
            "[red]FastAPI server dependencies missing.[/red] "
            "Install with: [bold]pip install qalitydeep\\[api][/bold]"
        )
        raise typer.Exit(code=1) from exc

    console.print(
        Panel(
            f"[bold]Host:[/bold]  {host}\n[bold]Port:[/bold]  {port}",
            title="QAlityDeep API Server",
            border_style="green",
            expand=False,
        )
    )
    run_server(host=host, port=port)


# ---------------------------------------------------------------------------
# Command: history
# ---------------------------------------------------------------------------

@app.command(
    help="List recent evaluation runs.",
    rich_help_panel="Data",
)
def history() -> None:
    from .storage import list_eval_runs

    runs = list_eval_runs()
    if not runs:
        console.print("[dim]No evaluation runs found.[/dim]")
        return

    table = Table(
        title="Recent Evaluation Runs",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Run ID", style="bold")
    table.add_column("Dataset")
    table.add_column("Graph")
    table.add_column("Metrics")
    table.add_column("Cases", justify="right")
    table.add_column("Avg Score", justify="right")
    table.add_column("Pass Rate", justify="right")
    table.add_column("Created At")

    for run in runs:
        # Compute aggregate stats
        avg_scores: list[float] = []
        pass_count = 0
        total_count = len(run.cases)
        threshold = 0.5

        for case in run.cases:
            scores = list(case.metrics.values())
            if scores:
                avg_scores.extend(scores)
            if all(s >= threshold for s in scores):
                pass_count += 1

        overall_avg = sum(avg_scores) / len(avg_scores) if avg_scores else 0.0
        pass_rate = (pass_count / total_count * 100) if total_count else 0.0

        avg_style = "green" if overall_avg >= threshold else "red"
        rate_style = "green" if pass_rate == 100.0 else ("yellow" if pass_rate >= 50 else "red")

        table.add_row(
            run.run_id,
            run.dataset_id,
            run.graph_name,
            ", ".join(run.metrics[:3]) + ("..." if len(run.metrics) > 3 else ""),
            str(total_count),
            f"[{avg_style}]{overall_avg:.3f}[/{avg_style}]",
            f"[{rate_style}]{pass_rate:.1f}%[/{rate_style}]",
            run.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Command: metrics
# ---------------------------------------------------------------------------

@app.command(
    help="List all available evaluation metrics.",
    rich_help_panel="Info",
)
def metrics() -> None:
    table = Table(
        title="Available Metrics",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Name", style="bold")
    table.add_column("Type", justify="center")
    table.add_column("Description")

    # Programmatic metrics from registry
    for name in sorted(METRIC_REGISTRY):
        cls = METRIC_REGISTRY[name]
        description = (cls.__doc__ or "").strip().split("\n")[0]
        table.add_row(name, Text("programmatic", style="green"), description)

    # LLM-based metrics
    llm_descriptions = {
        "correctness": "Semantic equivalence between actual and expected output (GEval).",
        "relevancy": "Answer relevancy to the input question (DeepEval).",
        "hallucination": "Detect hallucinated content not grounded in context (DeepEval).",
        "tool_correctness": "Validate correct tool usage against expected tool calls (DeepEval).",
        "coordination": "Multi-agent communication clarity and consistency (GEval).",
        "trajectory": "Efficiency and appropriateness of reasoning steps (GEval).",
    }
    for name in sorted(LLM_METRICS):
        description = llm_descriptions.get(name, "LLM-based metric.")
        table.add_row(name, Text("llm", style="yellow"), description)

    console.print(table)


# ---------------------------------------------------------------------------
# Backwards-compatible entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """Legacy entry point kept for backwards compatibility."""
    app(argv)


if __name__ == "__main__":
    app()
