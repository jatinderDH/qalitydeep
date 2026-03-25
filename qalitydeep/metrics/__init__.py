"""QAlityDeep metrics subpackage.

Provides a registry of built-in metrics and utilities for discovering and
instantiating them by name.
"""

from typing import Dict, List, Type

from .base import BaseMetric, MetricResult
from .code_diff import CodeDiffMetric
from .code_execution import CodeExecutionMetric
from .code_syntax import CodeSyntaxMetric
from .programmatic import (
    ContainsAllMetric,
    ContainsMetric,
    ExactMatchMetric,
    JsonValidMetric,
    RegexMatchMetric,
    StartsWithMetric,
)

# ---------------------------------------------------------------------------
# Metric registry
# ---------------------------------------------------------------------------

METRIC_REGISTRY: Dict[str, Type[BaseMetric]] = {}


def register_metric(name: str, cls: Type[BaseMetric]) -> None:
    """Register a metric class under *name*."""
    METRIC_REGISTRY[name] = cls


def get_metric(name: str, **kwargs) -> BaseMetric:
    """Instantiate and return a metric by its registered name.

    Raises ``KeyError`` if *name* is not in the registry.
    """
    if name not in METRIC_REGISTRY:
        raise KeyError(
            f"Unknown metric '{name}'. "
            f"Available: {list_available_metrics()}"
        )
    return METRIC_REGISTRY[name](**kwargs)


def list_available_metrics() -> List[str]:
    """Return a sorted list of all registered metric names."""
    return sorted(METRIC_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Auto-register built-in metrics
# ---------------------------------------------------------------------------

register_metric("exact_match", ExactMatchMetric)
register_metric("contains", ContainsMetric)
register_metric("contains_all", ContainsAllMetric)
register_metric("regex_match", RegexMatchMetric)
register_metric("json_valid", JsonValidMetric)
register_metric("starts_with", StartsWithMetric)
register_metric("code_syntax", CodeSyntaxMetric)
register_metric("code_diff", CodeDiffMetric)
register_metric("code_execution", CodeExecutionMetric)

__all__ = [
    # Base classes
    "BaseMetric",
    "MetricResult",
    # Programmatic metrics
    "ExactMatchMetric",
    "ContainsMetric",
    "ContainsAllMetric",
    "RegexMatchMetric",
    "JsonValidMetric",
    "StartsWithMetric",
    # Code metrics
    "CodeSyntaxMetric",
    "CodeDiffMetric",
    "CodeExecutionMetric",
    # Registry utilities
    "METRIC_REGISTRY",
    "register_metric",
    "get_metric",
    "list_available_metrics",
]
