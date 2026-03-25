"""Agent loop and tool-chain evaluation metrics."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from .base import BaseMetric


class ToolSequenceMetric(BaseMetric):
    """Check if tools were called in the expected order.

    Compares actual tool calls (from trajectory or actual_output) against
    expected_tool_calls (from test case). Supports:
    - strict: exact sequence match
    - subset: expected calls must appear in order (but other calls allowed between)
    """
    name = "tool_sequence"

    def __init__(self, mode: str = "subset", **kwargs):
        super().__init__(**kwargs)
        self.mode = mode  # "strict" or "subset"

    def measure(self, test_case: Any) -> None:
        actual_calls = self._extract_tool_calls(test_case)
        expected_calls = self._extract_expected_calls(test_case)

        if not expected_calls:
            self.score = 1.0
            self.reason = "No expected tool calls specified; sequence check skipped."
            return

        if not actual_calls:
            self.score = 0.0
            self.reason = f"Expected {len(expected_calls)} tool call(s) but none were made."
            return

        actual_names = [c.get("name", "") for c in actual_calls]
        expected_names = [c.get("name", "") for c in expected_calls]

        if self.mode == "strict":
            if actual_names == expected_names:
                self.score = 1.0
                self.reason = f"Tool sequence matches exactly: {' -> '.join(expected_names)}."
            else:
                # Partial credit based on longest common subsequence
                lcs_len = self._lcs_length(actual_names, expected_names)
                self.score = lcs_len / len(expected_names)
                self.reason = (
                    f"Tool sequence mismatch. Expected: {' -> '.join(expected_names)}, "
                    f"Got: {' -> '.join(actual_names)}."
                )
        else:  # subset
            # Check if expected_names appear as a subsequence in actual_names
            matched = 0
            j = 0
            for name in actual_names:
                if j < len(expected_names) and name == expected_names[j]:
                    matched += 1
                    j += 1

            self.score = matched / len(expected_names)
            if self.score == 1.0:
                self.reason = f"All expected tools called in order: {' -> '.join(expected_names)}."
            else:
                missing = expected_names[j:]
                self.reason = f"Missing or out-of-order tools: {', '.join(missing)}."

    def _extract_tool_calls(self, test_case: Any) -> List[Dict]:
        """Extract actual tool calls from test case."""
        # Try trajectory
        trajectory = getattr(test_case, "trajectory", None)
        if trajectory and isinstance(trajectory, dict):
            calls = trajectory.get("tool_calls_log", [])
            if calls:
                return calls

        # Try parsing actual_output as JSON
        output = getattr(test_case, "actual_output", "") or ""
        try:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "tool_calls" in parsed:
                return parsed["tool_calls"]
        except (json.JSONDecodeError, TypeError):
            pass

        return []

    def _extract_expected_calls(self, test_case: Any) -> List[Dict]:
        """Extract expected tool calls."""
        expected = getattr(test_case, "expected_tool_calls", None)
        if expected and isinstance(expected, list):
            return expected

        # Try expected_output as JSON
        exp_output = getattr(test_case, "expected_output", "") or ""
        try:
            parsed = json.loads(exp_output)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        return []

    def _lcs_length(self, a: Sequence, b: Sequence) -> int:
        """Compute length of longest common subsequence."""
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i-1] == b[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return dp[m][n]


class LoopDetectionMetric(BaseMetric):
    """Detect if an agent entered unnecessary loops or repeated actions.

    Analyzes tool call patterns to find repeated sequences.
    Score 1.0 = no loops, decreases with loop count.
    """
    name = "loop_detection"

    def measure(self, test_case: Any) -> None:
        calls = self._extract_tool_calls(test_case)

        if len(calls) < 2:
            self.score = 1.0
            self.reason = "Too few tool calls to detect loops."
            return

        names = [c.get("name", "") for c in calls]

        # Detect exact consecutive repetitions
        consecutive_repeats = 0
        for i in range(1, len(names)):
            if names[i] == names[i-1]:
                consecutive_repeats += 1

        # Detect repeated subsequences of length 2+
        pattern_repeats = 0
        for length in range(2, len(names) // 2 + 1):
            for i in range(len(names) - length * 2 + 1):
                pattern = names[i:i+length]
                next_pattern = names[i+length:i+length*2]
                if pattern == next_pattern:
                    pattern_repeats += 1

        total_loops = consecutive_repeats + pattern_repeats

        if total_loops == 0:
            self.score = 1.0
            self.reason = "No loops detected in tool call sequence."
        else:
            # Penalty: each loop reduces score by 0.15
            self.score = max(0.0, 1.0 - total_loops * 0.15)
            self.reason = (
                f"Detected {total_loops} loop(s): "
                f"{consecutive_repeats} consecutive repetition(s), "
                f"{pattern_repeats} pattern repetition(s). "
                f"Tool sequence: {' -> '.join(names)}."
            )

    def _extract_tool_calls(self, test_case: Any) -> List[Dict]:
        trajectory = getattr(test_case, "trajectory", None)
        if trajectory and isinstance(trajectory, dict):
            calls = trajectory.get("tool_calls_log", [])
            if calls:
                return calls
        output = getattr(test_case, "actual_output", "") or ""
        try:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "tool_calls" in parsed:
                return parsed["tool_calls"]
        except (json.JSONDecodeError, TypeError):
            pass
        return []


class ToolEfficiencyMetric(BaseMetric):
    """Score based on tool call count vs expected count.

    Fewer unnecessary calls = higher score.
    If expected_output contains a number, use that as the expected call count.
    Otherwise, assume optimal is the number of unique tool names used.
    """
    name = "tool_efficiency"

    def measure(self, test_case: Any) -> None:
        calls = self._extract_tool_calls(test_case)
        actual_count = len(calls)

        if actual_count == 0:
            self.score = 1.0
            self.reason = "No tool calls made."
            return

        # Determine expected count
        expected = getattr(test_case, "expected_output", None)
        expected_count = None
        if expected:
            try:
                expected_count = int(expected)
            except (ValueError, TypeError):
                pass

        # Try expected_tool_calls length
        expected_calls = getattr(test_case, "expected_tool_calls", None)
        if expected_count is None and expected_calls and isinstance(expected_calls, list):
            expected_count = len(expected_calls)

        # Fallback: optimal = number of unique tools
        if expected_count is None:
            unique_names = set(c.get("name", "") for c in calls)
            expected_count = len(unique_names)

        if expected_count == 0:
            self.score = 1.0
            self.reason = "Expected zero tool calls."
            return

        if actual_count <= expected_count:
            self.score = 1.0
            self.reason = f"Efficient: {actual_count} calls (expected: {expected_count})."
        else:
            # Score decreases linearly: 2x expected = 0.5, 3x = 0.33, etc.
            self.score = expected_count / actual_count
            excess = actual_count - expected_count
            self.reason = f"{excess} extra tool call(s): {actual_count} actual vs {expected_count} expected."

    def _extract_tool_calls(self, test_case: Any) -> List[Dict]:
        trajectory = getattr(test_case, "trajectory", None)
        if trajectory and isinstance(trajectory, dict):
            calls = trajectory.get("tool_calls_log", [])
            if calls:
                return calls
        output = getattr(test_case, "actual_output", "") or ""
        try:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "tool_calls" in parsed:
                return parsed["tool_calls"]
        except (json.JSONDecodeError, TypeError):
            pass
        return []
