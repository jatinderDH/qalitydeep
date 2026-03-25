"""Code diff comparison metric using text and AST analysis."""
from __future__ import annotations
import ast
import difflib
from typing import Any

from .base import BaseMetric

class CodeDiffMetric(BaseMetric):
    name = "code_diff"

    def __init__(self, threshold: float = 0.5, language: str = "auto"):
        self.threshold = threshold
        self.language = language
        self.score = None
        self.reason = ""

    def measure(self, test_case: Any) -> None:
        actual = getattr(test_case, "actual_output", "") or ""
        expected = getattr(test_case, "expected_output", "") or ""

        if not expected:
            self.score = 1.0  # no expected = pass
            self.reason = "No expected output to compare against"
            return

        # Text-level similarity
        text_ratio = difflib.SequenceMatcher(None, actual.strip(), expected.strip()).ratio()

        # Try AST-level comparison for Python
        ast_ratio = None
        lang = self._detect_language(actual, expected)
        if lang == "python":
            try:
                actual_ast = ast.dump(ast.parse(actual), annotate_fields=False)
                expected_ast = ast.dump(ast.parse(expected), annotate_fields=False)
                ast_ratio = difflib.SequenceMatcher(None, actual_ast, expected_ast).ratio()
            except SyntaxError:
                pass  # fall back to text only

        if ast_ratio is not None:
            self.score = 0.3 * text_ratio + 0.7 * ast_ratio
            self.reason = f"Text similarity: {text_ratio:.2f}, AST similarity: {ast_ratio:.2f}"
        else:
            self.score = text_ratio
            self.reason = f"Text similarity: {text_ratio:.2f} (AST comparison not available)"

    def _detect_language(self, actual: str, expected: str) -> str:
        if self.language != "auto":
            return self.language
        combined = actual + expected
        python_indicators = ["def ", "class ", "import ", "from ", "if __name__"]
        if any(kw in combined for kw in python_indicators):
            return "python"
        return "unknown"
