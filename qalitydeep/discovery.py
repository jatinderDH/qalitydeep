"""Discover Python evaluation files and collect suites."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import List, Optional

from .decorators import EvalSuiteDef, clear_registered_suites, get_registered_suites


# File patterns to search for
EVAL_FILE_PATTERNS = ["eval_*.py", "*_eval.py", "test_eval_*.py"]


def discover_eval_files(directory: Optional[Path] = None) -> List[Path]:
    """Find all evaluation Python files in the given directory."""
    search_dir = directory or Path.cwd()

    # Also check evals/ subdirectory
    search_dirs = [search_dir]
    evals_dir = search_dir / "evals"
    if evals_dir.exists():
        search_dirs.append(evals_dir)

    files: List[Path] = []
    for d in search_dirs:
        for pattern in EVAL_FILE_PATTERNS:
            files.extend(d.glob(pattern))

    return sorted(set(files))


def load_eval_module(file_path: Path) -> None:
    """Import a Python file as a module to trigger @eval_suite decorators."""
    module_name = f"qalitydeep_eval_{file_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load eval file: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


def discover_python_suites(directory: Optional[Path] = None) -> List[EvalSuiteDef]:
    """Discover and load all Python eval suites from a directory.

    Finds eval_*.py and *_eval.py files, imports them to trigger
    @eval_suite decorators, and returns all collected suites.
    """
    clear_registered_suites()

    files = discover_eval_files(directory)
    for f in files:
        try:
            load_eval_module(f)
        except Exception as e:
            # Log but don't fail - some files may have import errors
            import warnings
            warnings.warn(f"Failed to load eval file {f}: {e}")

    return get_registered_suites()
