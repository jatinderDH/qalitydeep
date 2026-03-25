"""Rich-based table formatter for terminal output."""
from __future__ import annotations
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.text import Text

from ..models import EvalRun, EvalCaseResult


class TableFormatter:
    """Produces rich terminal tables for eval run results."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format_run(self, run: EvalRun, threshold: float = 0.5) -> None:
        """Print the full eval run to the terminal.

        Parameters
        ----------
        run:
            A completed evaluation run with case results.
        threshold:
            Score at or above which a metric is considered passing.
        """
        self._print_header(run)

        metric_names = run.metrics
        for case in run.cases:
            self._print_case_table(case, metric_names, threshold)

        self._print_summary(run, threshold)

    def format_progress(
        self, current: int, total: int, case_name: str
    ) -> None:
        """Display a live progress indicator for a running evaluation."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task(
                f"Evaluating {case_name}", total=total, completed=current
            )
            progress.update(task, completed=current)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _print_header(self, run: EvalRun) -> None:
        header_text = (
            f"[bold]Run ID:[/bold]    {run.run_id}\n"
            f"[bold]Dataset:[/bold]   {run.dataset_id}\n"
            f"[bold]Graph:[/bold]     {run.graph_name}\n"
            f"[bold]Metrics:[/bold]   {', '.join(run.metrics)}\n"
            f"[bold]Started:[/bold]   {run.created_at:%Y-%m-%d %H:%M:%S}"
        )
        self.console.print(
            Panel(header_text, title="QAlityDeep Eval Run", border_style="blue")
        )

    def _print_case_table(
        self,
        case: EvalCaseResult,
        metric_names: List[str],
        threshold: float,
    ) -> None:
        table = Table(
            title=f"Test Case: {case.test_case_id}",
            show_lines=True,
        )
        table.add_column("Metric", style="bold")
        table.add_column("Score", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Reason", max_width=60)

        all_pass = True
        for metric in metric_names:
            score = case.metrics.get(metric)
            if score is None:
                table.add_row(metric, "N/A", "-", "")
                continue

            score_style = "green" if score >= threshold else "red"
            passed = score >= threshold
            if not passed:
                all_pass = False
            status = Text("PASS", style="bold green") if passed else Text("FAIL", style="bold red")
            reason = case.metric_reasons.get(metric, "")

            table.add_row(
                metric,
                f"[{score_style}]{score:.3f}[/{score_style}]",
                status,
                reason,
            )

        case_status = (
            Text("  PASSED", style="bold green")
            if all_pass
            else Text("  FAILED", style="bold red")
        )
        table.add_row("", "", case_status, "", end_section=True)

        self.console.print(table)
        self.console.print()

    def _print_summary(self, run: EvalRun, threshold: float) -> None:
        total = len(run.cases)
        passed = 0
        for case in run.cases:
            if all(s >= threshold for s in case.metrics.values()):
                passed += 1

        pass_rate = (passed / total * 100) if total else 0.0

        # Build aggregate scores per metric
        agg_lines: list[str] = []
        for metric in run.metrics:
            scores = [
                c.metrics[metric]
                for c in run.cases
                if metric in c.metrics
            ]
            if scores:
                avg = sum(scores) / len(scores)
                style = "green" if avg >= threshold else "red"
                agg_lines.append(
                    f"  [{style}]{metric}: {avg:.3f}[/{style}]"
                )

        total_time = run.summary.get("total_time_s", 0)
        estimated_cost = run.summary.get("estimated_cost_usd", 0)

        summary_text = (
            f"[bold]Cases:[/bold]       {passed}/{total} passed "
            f"({pass_rate:.1f}%)\n"
            + "\n".join(agg_lines)
            + (f"\n[bold]Total time:[/bold]  {total_time:.1f}s" if total_time else "")
            + (
                f"\n[bold]Est. cost:[/bold]   ${estimated_cost:.4f}"
                if estimated_cost
                else ""
            )
        )

        overall = pass_rate == 100.0
        border = "green" if overall else "red"
        status_label = (
            "[bold green]PASSED[/bold green]"
            if overall
            else "[bold red]FAILED[/bold red]"
        )

        self.console.print(
            Panel(
                summary_text + f"\n\n[bold]Status:[/bold] {status_label}",
                title="Summary",
                border_style=border,
            )
        )
