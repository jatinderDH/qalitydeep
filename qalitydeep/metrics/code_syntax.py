"""Code syntax validation metric for QAlityDeep."""

import ast
import json
import subprocess
from typing import Any, Optional

from .base import BaseMetric

# Heuristic keyword sets for auto-detection
_PYTHON_KEYWORDS = {"def ", "class ", "import ", "from ", "elif ", "except "}
_JS_KEYWORDS = {"function ", "const ", "let ", "var ", "=> ", "console."}


def _detect_language(code: str) -> str:
    """Best-effort language detection from code content.

    Returns one of ``"python"``, ``"javascript"``, ``"json"``, or ``"unknown"``.
    """
    stripped = code.strip()

    # Try JSON first -- it's cheap and unambiguous
    if stripped.startswith(("{", "[")):
        try:
            json.loads(stripped)
            return "json"
        except (json.JSONDecodeError, TypeError):
            pass

    # Count keyword hits
    py_hits = sum(1 for kw in _PYTHON_KEYWORDS if kw in code)
    js_hits = sum(1 for kw in _JS_KEYWORDS if kw in code)

    if py_hits > js_hits:
        return "python"
    if js_hits > py_hits:
        return "javascript"
    if py_hits > 0:
        return "python"

    return "unknown"


def _validate_python(code: str) -> tuple[bool, str]:
    """Return (valid, error_message) for Python source."""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as exc:
        return False, f"Python SyntaxError: {exc}"


def _validate_json(code: str) -> tuple[bool, str]:
    """Return (valid, error_message) for JSON content."""
    try:
        json.loads(code)
        return True, ""
    except (json.JSONDecodeError, TypeError) as exc:
        return False, f"JSON error: {exc}"


def _validate_javascript(code: str) -> tuple[bool, str]:
    """Return (valid, error_message) for JavaScript via Node.js syntax check."""
    try:
        result = subprocess.run(
            ["node", "-e", code],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, ""
        error_msg = (result.stderr or result.stdout).strip()
        return False, f"JavaScript error: {error_msg}"
    except FileNotFoundError:
        return False, "Node.js is not installed or not found on PATH."
    except subprocess.TimeoutExpired:
        return False, "JavaScript validation timed out (>5 s)."


class CodeSyntaxMetric(BaseMetric):
    """Validates that code in actual_output is syntactically correct.

    Parameters
    ----------
    language : str
        One of ``"python"``, ``"json"``, ``"javascript"``, or ``"auto"``
        (default). When ``"auto"``, the language is inferred from the
        code content using simple heuristics.
    """

    name: str = "code_syntax"

    _VALIDATORS = {
        "python": _validate_python,
        "json": _validate_json,
        "javascript": _validate_javascript,
    }

    def __init__(self, language: str = "auto", threshold: float = 0.5) -> None:
        self._language = language.lower()
        self.threshold = threshold
        self.score: Optional[float] = None
        self.reason: str = ""

    def measure(self, test_case: Any) -> None:
        code = test_case.actual_output

        language = self._language
        if language == "auto":
            language = _detect_language(code)

        validator = self._VALIDATORS.get(language)
        if validator is None:
            self.score = 0.0
            self.reason = (
                f"Unsupported or undetected language: '{language}'. "
                "Supported languages: python, json, javascript."
            )
            return

        valid, error_msg = validator(code)
        if valid:
            self.score = 1.0
            self.reason = f"Code is syntactically valid ({language})."
        else:
            self.score = 0.0
            self.reason = error_msg
