"""Load and validate QAlityDeep YAML configuration files."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, List

import yaml

from .eval_config import EvalConfig, EvalSuite, EvalTestCase


# Default config file names to search for (in order)
CONFIG_FILES = ["qalitydeep.yaml", "qalitydeep.yml", ".qalitydeep.yaml", ".qalitydeep.yml"]


def find_config(directory: Optional[Path] = None) -> Optional[Path]:
    """Find a QAlityDeep config file in the given directory (or CWD)."""
    search_dir = directory or Path.cwd()
    for name in CONFIG_FILES:
        path = search_dir / name
        if path.exists():
            return path
    return None


def load_config(path: Path) -> EvalConfig:
    """Load and validate a QAlityDeep YAML config file."""
    text = path.read_text(encoding="utf-8")
    # Support environment variable substitution: $VAR or ${VAR}
    text = _substitute_env_vars(text)
    data = yaml.safe_load(text) or {}
    return EvalConfig.model_validate(data)


def load_config_auto(directory: Optional[Path] = None) -> EvalConfig:
    """Find and load config from directory, raising if not found."""
    path = find_config(directory)
    if path is None:
        raise FileNotFoundError(
            f"No QAlityDeep config found. Run 'qalitydeep init' to create one, "
            f"or create {CONFIG_FILES[0]} manually."
        )
    return load_config(path)


def _substitute_env_vars(text: str) -> str:
    """Replace $VAR and ${VAR} patterns with environment variable values."""
    def replacer(match: re.Match) -> str:
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, match.group(0))
    return re.sub(r'\$\{(\w+)\}|\$(\w+)', replacer, text)
