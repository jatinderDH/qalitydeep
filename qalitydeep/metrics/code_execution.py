"""Code execution metric - runs code and validates output."""
from __future__ import annotations
import subprocess
import tempfile
import os
from typing import Any

from .base import BaseMetric

class CodeExecutionMetric(BaseMetric):
    name = "code_execution"

    def __init__(self, threshold: float = 0.5, timeout: int = 10, language: str = "python"):
        self.threshold = threshold
        self.timeout = timeout
        self.language = language
        self.score = None
        self.reason = ""

    def measure(self, test_case: Any) -> None:
        code = getattr(test_case, "actual_output", "") or ""
        expected_output = getattr(test_case, "expected_output", "") or ""

        if not code.strip():
            self.score = 0.0
            self.reason = "Empty code"
            return

        try:
            result = self._execute(code)
        except subprocess.TimeoutExpired:
            self.score = 0.0
            self.reason = f"Execution timed out after {self.timeout}s"
            return
        except Exception as e:
            self.score = 0.0
            self.reason = f"Execution error: {e}"
            return

        if result.returncode != 0:
            self.score = 0.0
            stderr = result.stderr.strip()[:500]  # truncate long errors
            self.reason = f"Exit code {result.returncode}: {stderr}"
            return

        stdout = result.stdout.strip()

        if not expected_output.strip():
            # No expected output — just check it runs successfully
            self.score = 1.0
            self.reason = f"Executed successfully. Output: {stdout[:200]}"
            return

        # Compare output
        if stdout == expected_output.strip():
            self.score = 1.0
            self.reason = "Output matches expected"
        else:
            # Partial match scoring
            from difflib import SequenceMatcher
            ratio = SequenceMatcher(None, stdout, expected_output.strip()).ratio()
            self.score = ratio
            self.reason = (
                f"Output mismatch (similarity: {ratio:.2f}). "
                f"Got: {stdout[:200]}. Expected: {expected_output.strip()[:200]}"
            )

    def _execute(self, code: str) -> subprocess.CompletedProcess:
        if self.language == "python":
            return self._execute_python(code)
        elif self.language in ("javascript", "js", "node"):
            return self._execute_node(code)
        else:
            raise ValueError(f"Unsupported language: {self.language}")

    def _execute_python(self, code: str) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            f.flush()
            tmp_path = f.name

        try:
            return subprocess.run(
                ["python3", tmp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        finally:
            os.unlink(tmp_path)

    def _execute_node(self, code: str) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            f.flush()
            tmp_path = f.name

        try:
            return subprocess.run(
                ["node", tmp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        finally:
            os.unlink(tmp_path)
