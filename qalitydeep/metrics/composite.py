"""Composite metrics — weighted combinations and conditional pipelines."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .base import BaseMetric


class CompositeMetric(BaseMetric):
    """A metric that combines multiple sub-metrics with weights.

    Example:
        quality = CompositeMetric(
            name="quality_score",
            components=[
                ("exact_match", 0.4),
                ("contains", 0.3),
                ("code_syntax", 0.3),
            ],
        )
    """

    def __init__(
        self,
        name: str = "composite",
        components: Optional[List[Tuple[str, float]]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = name
        self.components: List[Tuple[str, float]] = components or []
        self._sub_scores: Dict[str, Optional[float]] = {}
        self._sub_reasons: Dict[str, str] = {}

    def measure(self, test_case: Any) -> None:
        from . import get_metric, METRIC_REGISTRY

        if not self.components:
            self.score = 0.0
            self.reason = "No component metrics defined."
            return

        total_weight = sum(w for _, w in self.components)
        if total_weight == 0:
            self.score = 0.0
            self.reason = "Total weight is zero."
            return

        weighted_sum = 0.0
        evaluated_weight = 0.0
        parts: list[str] = []

        for metric_name, weight in self.components:
            try:
                if metric_name in METRIC_REGISTRY:
                    sub_metric = get_metric(metric_name, threshold=self.threshold)
                else:
                    # Try loading as custom metric
                    from ..plugins import load_custom_metric
                    cls = load_custom_metric(metric_name)
                    sub_metric = cls(threshold=self.threshold)

                sub_metric.measure(test_case)

                if sub_metric.score is not None:
                    self._sub_scores[metric_name] = sub_metric.score
                    self._sub_reasons[metric_name] = sub_metric.reason
                    weighted_sum += sub_metric.score * weight
                    evaluated_weight += weight
                    parts.append(f"{metric_name}: {sub_metric.score:.3f} (w={weight:.2f})")
                else:
                    self._sub_scores[metric_name] = None
                    parts.append(f"{metric_name}: N/A (w={weight:.2f})")

            except Exception as exc:
                self._sub_scores[metric_name] = None
                self._sub_reasons[metric_name] = f"Error: {exc}"
                parts.append(f"{metric_name}: ERROR (w={weight:.2f})")

        if evaluated_weight > 0:
            self.score = weighted_sum / evaluated_weight
        else:
            self.score = 0.0

        self.reason = "Composite: " + "; ".join(parts)

    @property
    def sub_scores(self) -> Dict[str, Optional[float]]:
        """Return individual sub-metric scores after measurement."""
        return self._sub_scores

    @property
    def sub_reasons(self) -> Dict[str, str]:
        """Return individual sub-metric reasons after measurement."""
        return self._sub_reasons


class ConditionalMetric(BaseMetric):
    """A metric that runs a secondary metric only if a gate metric passes.

    Example:
        conditional = ConditionalMetric(
            name="conditional_hallucination",
            gate_metric="correctness",
            gate_threshold=0.5,  # only check hallucination if correctness >= 0.5
            then_metric="hallucination",
        )
    """

    def __init__(
        self,
        name: str = "conditional",
        gate_metric: str = "",
        gate_threshold: float = 0.5,
        then_metric: str = "",
        else_score: float = 1.0,  # score to return if gate fails
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = name
        self.gate_metric_name = gate_metric
        self.gate_threshold = gate_threshold
        self.then_metric_name = then_metric
        self.else_score = else_score

    def measure(self, test_case: Any) -> None:
        from . import get_metric, METRIC_REGISTRY

        if not self.gate_metric_name or not self.then_metric_name:
            self.score = 0.0
            self.reason = "Gate metric or then metric not specified."
            return

        # Run gate metric
        try:
            if self.gate_metric_name in METRIC_REGISTRY:
                gate = get_metric(self.gate_metric_name, threshold=self.gate_threshold)
            else:
                from ..plugins import load_custom_metric
                cls = load_custom_metric(self.gate_metric_name)
                gate = cls(threshold=self.gate_threshold)

            gate.measure(test_case)
        except Exception as exc:
            self.score = 0.0
            self.reason = f"Gate metric '{self.gate_metric_name}' error: {exc}"
            return

        gate_score = gate.score if gate.score is not None else 0.0

        if gate_score >= self.gate_threshold:
            # Gate passed — run the then_metric
            try:
                if self.then_metric_name in METRIC_REGISTRY:
                    then = get_metric(self.then_metric_name, threshold=self.threshold)
                else:
                    from ..plugins import load_custom_metric
                    cls = load_custom_metric(self.then_metric_name)
                    then = cls(threshold=self.threshold)

                then.measure(test_case)
                self.score = then.score
                self.reason = (
                    f"Gate '{self.gate_metric_name}' passed ({gate_score:.3f} >= {self.gate_threshold}). "
                    f"{self.then_metric_name}: {then.reason}"
                )
            except Exception as exc:
                self.score = 0.0
                self.reason = f"Then metric '{self.then_metric_name}' error: {exc}"
        else:
            # Gate failed — return else_score
            self.score = self.else_score
            self.reason = (
                f"Gate '{self.gate_metric_name}' failed ({gate_score:.3f} < {self.gate_threshold}). "
                f"Returning default score {self.else_score}."
            )


class AverageMetric(BaseMetric):
    """Simple unweighted average of multiple metrics.

    Convenience wrapper around CompositeMetric with equal weights.
    """

    def __init__(
        self,
        name: str = "average",
        metric_names: Optional[List[str]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.name = name
        self.metric_names = metric_names or []

    def measure(self, test_case: Any) -> None:
        if not self.metric_names:
            self.score = 0.0
            self.reason = "No metrics specified for averaging."
            return

        weight = 1.0 / len(self.metric_names)
        composite = CompositeMetric(
            name=self.name,
            components=[(m, weight) for m in self.metric_names],
            threshold=self.threshold,
        )
        composite.measure(test_case)
        self.score = composite.score
        self.reason = composite.reason
