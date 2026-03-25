"""Health check for QAlityDeep configuration."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Tuple

from rich.console import Console
from rich.table import Table

console = Console()


def run_doctor() -> bool:
    """Run all health checks. Returns True if all pass."""
    console.print()
    console.print("[bold]QAlityDeep Doctor[/bold] - Checking your configuration...\n")

    checks: List[Tuple[str, bool, str]] = []

    # 1. Python version
    py_version = sys.version_info
    ok = py_version >= (3, 9)
    checks.append((
        "Python version",
        ok,
        f"Python {py_version.major}.{py_version.minor}.{py_version.micro}" +
        ("" if ok else " (requires >= 3.9)"),
    ))

    # 2. Config file
    config_exists = any(
        (Path.cwd() / name).exists()
        for name in ["qalitydeep.yaml", "qalitydeep.yml", ".qalitydeep.yaml", ".qalitydeep.yml"]
    )
    checks.append((
        "Config file",
        config_exists,
        "Found" if config_exists else "Not found - run 'qalitydeep init'",
    ))

    # 3. DeepEval
    try:
        import deepeval
        checks.append(("DeepEval", True, f"v{deepeval.__version__}"))
    except ImportError:
        checks.append(("DeepEval", False, "Not installed - pip install deepeval"))

    # 4. LLM Backend keys
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    has_openai = bool(openai_key) and not openai_key.startswith("sk-...")
    checks.append((
        "OpenAI API Key",
        has_openai,
        "Set" if has_openai else "Not set",
    ))

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    has_anthropic = bool(anthropic_key) and not anthropic_key.startswith("sk-ant-...")
    checks.append((
        "Anthropic API Key",
        has_anthropic,
        "Set" if has_anthropic else "Not set",
    ))

    # 5. At least one LLM key
    has_any_llm = has_openai or has_anthropic
    checks.append((
        "LLM Backend Available",
        has_any_llm,
        "OK" if has_any_llm else "Set OPENAI_API_KEY or ANTHROPIC_API_KEY",
    ))

    # 6. Data directory
    from .config import get_settings
    try:
        settings = get_settings()
        data_ok = settings.data_dir.exists()
        checks.append((
            "Data directory",
            data_ok,
            str(settings.data_dir) + (" (exists)" if data_ok else " (will be created)"),
        ))
    except Exception as e:
        checks.append(("Data directory", False, str(e)))

    # 7. LangSmith (optional)
    langsmith_key = os.environ.get("LANGSMITH_API_KEY", "")
    has_langsmith = bool(langsmith_key) and not langsmith_key.startswith("lsm_...")
    checks.append((
        "LangSmith (optional)",
        True,  # Always "ok" since it's optional
        "Configured" if has_langsmith else "Not configured (optional)",
    ))

    # 8. Available metrics
    try:
        from .metrics import list_available_metrics
        metric_names = list_available_metrics()
        checks.append((
            "Built-in Metrics",
            True,
            f"{len(metric_names)} available: {', '.join(metric_names)}",
        ))
    except Exception as e:
        checks.append(("Built-in Metrics", False, str(e)))

    # Display results
    table = Table(title="Health Check Results", show_header=True)
    table.add_column("Check", style="bold")
    table.add_column("Status", width=6)
    table.add_column("Details")

    all_passed = True
    for name, passed, detail in checks:
        status = "[green]\u2713[/green]" if passed else "[red]\u2717[/red]"
        if not passed and "optional" not in name.lower():
            all_passed = False
        table.add_row(name, status, detail)

    console.print(table)
    console.print()

    if all_passed:
        console.print("[green bold]All checks passed![/green bold] You're ready to run evaluations.\n")
    else:
        console.print("[yellow bold]Some checks failed.[/yellow bold] Fix the issues above and run 'qalitydeep doctor' again.\n")

    return all_passed
