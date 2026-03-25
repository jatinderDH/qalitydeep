"""Deterministic (programmatic) metrics for QAlityDeep."""

import json
import re
from typing import Any, List, Optional

from .base import BaseMetric


class ExactMatchMetric(BaseMetric):
    """Score 1.0 if actual_output exactly matches expected_output (stripped)."""

    name: str = "exact_match"

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self.score: Optional[float] = None
        self.reason: str = ""

    def measure(self, test_case: Any) -> None:
        actual = test_case.actual_output.strip()
        expected = test_case.expected_output.strip()
        if actual == expected:
            self.score = 1.0
            self.reason = "Actual output exactly matches expected output."
        else:
            self.score = 0.0
            self.reason = "Actual output does not match expected output."


class ContainsMetric(BaseMetric):
    """Score 1.0 if a substring is found in actual_output.

    The substring can be provided at init time, or it falls back to
    ``test_case.expected_output`` when no init argument is given.
    """

    name: str = "contains"

    def __init__(self, substring: Optional[str] = None, threshold: float = 0.5) -> None:
        self._substring = substring
        self.threshold = threshold
        self.score: Optional[float] = None
        self.reason: str = ""

    def measure(self, test_case: Any) -> None:
        substring = self._substring if self._substring is not None else test_case.expected_output
        actual = test_case.actual_output
        if substring in actual:
            self.score = 1.0
            self.reason = f"Substring '{substring}' found in actual output."
        else:
            self.score = 0.0
            self.reason = f"Substring '{substring}' not found in actual output."


class ContainsAllMetric(BaseMetric):
    """Score = fraction of required substrings found in actual_output."""

    name: str = "contains_all"

    def __init__(self, substrings: Optional[List[str]] = None, threshold: float = 0.5) -> None:
        self._substrings = substrings or []
        self.threshold = threshold
        self.score: Optional[float] = None
        self.reason: str = ""

    def measure(self, test_case: Any) -> None:
        if not self._substrings:
            self.score = 1.0
            self.reason = "No substrings to check; trivially passes."
            return

        actual = test_case.actual_output
        found = [s for s in self._substrings if s in actual]
        self.score = len(found) / len(self._substrings)
        missing = [s for s in self._substrings if s not in actual]
        if missing:
            self.reason = f"Missing substrings: {missing}"
        else:
            self.reason = "All required substrings found in actual output."


class RegexMatchMetric(BaseMetric):
    """Score 1.0 if the regex pattern matches actual_output."""

    name: str = "regex_match"

    def __init__(self, pattern: str = "", threshold: float = 0.5) -> None:
        self._pattern = pattern
        self.threshold = threshold
        self.score: Optional[float] = None
        self.reason: str = ""

    def measure(self, test_case: Any) -> None:
        actual = test_case.actual_output
        if re.search(self._pattern, actual):
            self.score = 1.0
            self.reason = f"Pattern '{self._pattern}' matched in actual output."
        else:
            self.score = 0.0
            self.reason = f"Pattern '{self._pattern}' did not match in actual output."


class JsonValidMetric(BaseMetric):
    """Score 1.0 if actual_output is valid JSON."""

    name: str = "json_valid"

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self.score: Optional[float] = None
        self.reason: str = ""

    def measure(self, test_case: Any) -> None:
        try:
            json.loads(test_case.actual_output)
            self.score = 1.0
            self.reason = "Actual output is valid JSON."
        except (json.JSONDecodeError, TypeError) as exc:
            self.score = 0.0
            self.reason = f"Invalid JSON: {exc}"


class StartsWithMetric(BaseMetric):
    """Score 1.0 if actual_output starts with the given prefix."""

    name: str = "starts_with"

    def __init__(self, prefix: str = "", threshold: float = 0.5) -> None:
        self._prefix = prefix
        self.threshold = threshold
        self.score: Optional[float] = None
        self.reason: str = ""

    def measure(self, test_case: Any) -> None:
        actual = test_case.actual_output
        if actual.startswith(self._prefix):
            self.score = 1.0
            self.reason = f"Actual output starts with '{self._prefix}'."
        else:
            self.score = 0.0
            self.reason = f"Actual output does not start with '{self._prefix}'."
