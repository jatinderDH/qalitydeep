"""Sandbox abstraction for safe code execution."""
from __future__ import annotations
import subprocess
import tempfile
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    """Result of executing code in a sandbox."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    error: Optional[str] = None


class LocalSandbox:
    """Execute code in a local subprocess with resource limits."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def execute_python(self, code: str) -> ExecutionResult:
        return self._execute(code, suffix=".py", cmd_prefix=["python3"])

    def execute_node(self, code: str) -> ExecutionResult:
        return self._execute(code, suffix=".js", cmd_prefix=["node"])

    def _execute(self, code: str, suffix: str, cmd_prefix: list) -> ExecutionResult:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            f.flush()
            tmp_path = f.name

        try:
            result = subprocess.run(
                [*cmd_prefix, tmp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                timed_out=True,
                error=f"Timed out after {self.timeout}s",
            )
        except FileNotFoundError as e:
            return ExecutionResult(
                success=False,
                error=f"Runtime not found: {e}",
            )
        finally:
            os.unlink(tmp_path)
