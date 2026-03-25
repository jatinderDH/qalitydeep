"""Interactive project scaffolding for QAlityDeep."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

SAMPLE_CONFIG = '''version: "1"

defaults:
  metrics: [correctness, relevancy]
  threshold: 0.7

suites:
  - name: sample_qa
    description: "Sample QA evaluation suite"
    test_cases:
      - input: "What is your refund policy?"
        expected_output: "We offer a 30-day full refund on all purchases"

      - input: "Do you ship internationally?"
        expected_output: "Yes, we ship worldwide with delivery in 5-10 business days"

      - input: "How do I reset my password?"
        expected_output: "Go to Settings > Account > Reset Password"

  - name: code_quality
    description: "Sample code quality checks"
    metrics: [code_syntax, exact_match]
    test_cases:
      - input: "Write a hello world function"
        expected_output: |
          def hello():
              return "Hello, World!"
'''

SAMPLE_EVAL_PY = '''"""Sample Python-based evaluation definitions."""
from qalitydeep import eval_suite, eval_case


@eval_suite(metrics=["code_syntax", "exact_match"], threshold=0.8)
def test_basic_functions():
    """Test basic Python function generation."""
    return [
        eval_case(
            input="Write a function that adds two numbers",
            expected_output="""def add(a, b):
    return a + b""",
        ),
        eval_case(
            input="Write a function that checks if a number is even",
            expected_output="""def is_even(n):
    return n % 2 == 0""",
        ),
    ]
'''


def run_init(directory: Optional[Path] = None) -> None:
    """Run the interactive init scaffolding."""
    target_dir = directory or Path.cwd()

    console.print()
    console.print(Panel.fit(
        "[bold cyan]QAlityDeep Setup[/bold cyan]",
        subtitle="Pre-deploy QA for LLM outputs",
    ))
    console.print()

    # Check if config already exists
    config_path = target_dir / "qalitydeep.yaml"
    if config_path.exists():
        overwrite = Prompt.ask(
            "  [yellow]qalitydeep.yaml already exists.[/yellow] Overwrite?",
            choices=["y", "n"],
            default="n",
        )
        if overwrite != "y":
            console.print("  [dim]Keeping existing config.[/dim]")
            return

    # Ask for LLM backend
    backend = Prompt.ask(
        "  LLM backend",
        choices=["openai", "anthropic", "ollama"],
        default="openai",
    )

    # Check for API keys
    key_status = _check_api_keys(backend)

    # Write config file
    config_content = SAMPLE_CONFIG
    if backend != "openai":
        config_content = config_content  # Same config works for all backends

    config_path.write_text(config_content, encoding="utf-8")
    console.print(f"  [green]\u2713[/green] Created {config_path.name}")

    # Create evals directory
    evals_dir = target_dir / "evals"
    evals_dir.mkdir(exist_ok=True)
    console.print(f"  [green]\u2713[/green] Created evals/ directory")

    # Write sample eval Python file
    sample_eval = evals_dir / "eval_sample.py"
    if not sample_eval.exists():
        sample_eval.write_text(SAMPLE_EVAL_PY, encoding="utf-8")
        console.print(f"  [green]\u2713[/green] Created evals/eval_sample.py")

    # Create .env.local if it doesn't exist
    env_path = target_dir / ".env.local"
    if not env_path.exists():
        env_content = f"LLM_BACKEND={backend}\n"
        if backend == "openai":
            env_content += "OPENAI_API_KEY=sk-...\n"
        elif backend == "anthropic":
            env_content += "ANTHROPIC_API_KEY=sk-ant-...\n"
        env_path.write_text(env_content, encoding="utf-8")
        console.print(f"  [green]\u2713[/green] Created .env.local")

    console.print()
    console.print(Panel.fit(
        "[green]Setup complete![/green]\n\n"
        "  Run [bold]qalitydeep run[/bold] to execute your first evaluation\n"
        "  Run [bold]qalitydeep doctor[/bold] to check your configuration\n"
        "  Edit [bold]qalitydeep.yaml[/bold] to add your own test cases",
        title="Next Steps",
    ))


def _check_api_keys(backend: str) -> dict:
    """Check if required API keys are set in environment."""
    status = {}

    if backend in ("openai",):
        key = os.environ.get("OPENAI_API_KEY", "")
        if key and not key.startswith("sk-..."):
            console.print("  [green]\u2713[/green] OPENAI_API_KEY detected")
            status["openai"] = True
        else:
            console.print("  [yellow]\u26a0[/yellow] OPENAI_API_KEY not set - add it to .env.local")
            status["openai"] = False

    if backend in ("anthropic",):
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if key and not key.startswith("sk-ant-..."):
            console.print("  [green]\u2713[/green] ANTHROPIC_API_KEY detected")
            status["anthropic"] = True
        else:
            console.print("  [yellow]\u26a0[/yellow] ANTHROPIC_API_KEY not set - add it to .env.local")
            status["anthropic"] = False

    if backend == "ollama":
        console.print("  [green]\u2713[/green] Ollama selected (no API key needed)")
        status["ollama"] = True

    return status
