"""File watcher for auto-re-evaluation on config changes."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional, Set

from rich.console import Console

console = Console()

# File patterns to watch
WATCH_PATTERNS = {"*.yaml", "*.yml", "eval_*.py", "*_eval.py"}


class EvalWatcher:
    """Watches eval config files and triggers re-evaluation on changes."""

    def __init__(
        self,
        directory: Optional[Path] = None,
        on_change: Optional[Callable] = None,
        debounce_seconds: float = 1.0,
    ):
        self.directory = directory or Path.cwd()
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self._file_mtimes: dict[str, float] = {}
        self._running = False

    def _get_watched_files(self) -> Set[Path]:
        """Find all files matching watch patterns."""
        files: Set[Path] = set()
        for pattern in WATCH_PATTERNS:
            files.update(self.directory.glob(pattern))
            evals_dir = self.directory / "evals"
            if evals_dir.exists():
                files.update(evals_dir.glob(pattern))
        return files

    def _check_for_changes(self) -> list[Path]:
        """Check if any watched files have been modified."""
        changed: list[Path] = []
        current_files = self._get_watched_files()

        for file_path in current_files:
            try:
                mtime = file_path.stat().st_mtime
            except OSError:
                continue

            key = str(file_path)
            if key in self._file_mtimes:
                if mtime > self._file_mtimes[key]:
                    changed.append(file_path)
            self._file_mtimes[key] = mtime

        return changed

    def start(self) -> None:
        """Start watching for file changes (blocking)."""
        self._running = True

        console.print(f"\n[bold cyan]Watching for changes...[/bold cyan]")
        console.print(f"  Directory: {self.directory}")
        console.print(f"  Patterns: {', '.join(WATCH_PATTERNS)}")
        console.print(f"  Press [bold]Ctrl+C[/bold] to stop\n")

        # Initial scan to set baseline mtimes
        self._check_for_changes()

        # Run initial evaluation
        if self.on_change:
            console.print("[dim]Running initial evaluation...[/dim]\n")
            try:
                self.on_change([])
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]\n")

        try:
            while self._running:
                time.sleep(self.debounce_seconds)
                changed = self._check_for_changes()
                if changed:
                    file_names = ", ".join(f.name for f in changed)
                    console.print(f"\n[yellow]Changed: {file_names}[/yellow]")
                    console.print("[dim]Re-running evaluation...[/dim]\n")
                    if self.on_change:
                        try:
                            self.on_change(changed)
                        except Exception as e:
                            console.print(f"[red]Error: {e}[/red]\n")
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped watching.[/dim]")

    def stop(self) -> None:
        """Stop watching."""
        self._running = False
