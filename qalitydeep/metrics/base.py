"""Base metric classes for QAlityDeep."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


class BaseMetric(ABC):
    """Base class for all QAlityDeep metrics."""

    name: str = ""
    score: Optional[float] = None
    reason: str = ""
    threshold: float = 0.5

    @abstractmethod
    def measure(self, test_case: Any) -> None:
        """Evaluate and set self.score and self.reason."""
        ...

    @property
    def passed(self) -> bool:
        return self.score is not None and self.score >= self.threshold


@dataclass
class MetricResult:
    """Immutable result snapshot from a metric evaluation."""

    name: str
    score: float
    reason: str = ""
    passed: bool = True
