"""A/B testing for comparing models and prompts in QAlityDeep."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .eval_config import EvalSuite, EvalTestCase
from .models import EvalCaseResult


@dataclass
class VariantConfig:
    """Configuration for a single A/B test variant."""
    name: str
    provider: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VariantResult:
    """Results for a single variant."""
    name: str
    config: VariantConfig
    cases: List[EvalCaseResult]
    metric_averages: Dict[str, float] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0


@dataclass
class MetricComparison:
    """Statistical comparison of a single metric across variants."""
    metric_name: str
    variant_scores: Dict[str, float]  # variant_name -> average score
    best_variant: str
    delta: float  # difference between best and second best
    p_value: Optional[float] = None  # statistical significance
    significant: Optional[bool] = None  # p < 0.05


@dataclass
class ABTestResult:
    """Complete A/B test results."""
    variants: List[VariantResult]
    metric_comparisons: List[MetricComparison]
    winner: Optional[str] = None  # overall best variant

    def summary_dict(self) -> Dict[str, Any]:
        """Return a summary suitable for JSON serialization."""
        return {
            "variants": [
                {
                    "name": v.name,
                    "metric_averages": v.metric_averages,
                    "total_latency_ms": v.total_latency_ms,
                    "total_cost_usd": v.total_cost_usd,
                }
                for v in self.variants
            ],
            "metric_comparisons": [
                {
                    "metric": mc.metric_name,
                    "scores": mc.variant_scores,
                    "best": mc.best_variant,
                    "delta": mc.delta,
                    "p_value": mc.p_value,
                    "significant": mc.significant,
                }
                for mc in self.metric_comparisons
            ],
            "winner": self.winner,
        }


def run_ab_test(
    suite: EvalSuite,
    variants: List[VariantConfig],
    selected_metrics: List[str],
    threshold: float = 0.5,
) -> ABTestResult:
    """Run the same test suite against multiple model/prompt variants.

    For each variant, runs all test cases and collects metrics.
    Then compares variants statistically.
    """
    import time
    from .cli import evaluate_case_simple
    from .metrics import METRIC_REGISTRY

    variant_results: List[VariantResult] = []

    # Determine which metrics are programmatic
    programmatic = [m for m in selected_metrics if m in METRIC_REGISTRY]

    for variant in variants:
        cases: List[EvalCaseResult] = []
        total_latency = 0.0
        total_cost = 0.0

        for idx, tc in enumerate(suite.test_cases):
            case_id = tc.id or f"{suite.name}_{idx}"
            actual_output = tc.actual_output or tc.expected_output or ""

            result: Optional[EvalCaseResult] = None

            # If variant has a different model, we'd call the LLM here
            # For now, use programmatic metrics on existing outputs
            if programmatic:
                start = time.perf_counter()
                result = evaluate_case_simple(
                    test_case_id=case_id,
                    input_text=tc.input,
                    actual_output=actual_output,
                    expected_output=tc.expected_output,
                    selected_metrics=programmatic,
                    threshold=threshold,
                )
                latency = (time.perf_counter() - start) * 1000
                result.latency_ms = latency
                total_latency += latency
                cases.append(result)

            if result and result.estimated_cost_usd:
                total_cost += result.estimated_cost_usd

        # Calculate metric averages
        metric_avgs: Dict[str, float] = {}
        for m in selected_metrics:
            scores = [c.metrics.get(m) for c in cases if m in c.metrics]
            if scores:
                metric_avgs[m] = sum(scores) / len(scores)

        variant_results.append(VariantResult(
            name=variant.name,
            config=variant,
            cases=cases,
            metric_averages=metric_avgs,
            total_latency_ms=total_latency,
            total_cost_usd=total_cost,
        ))

    # Compare variants per metric
    metric_comparisons = _compare_metrics(variant_results, selected_metrics)

    # Determine overall winner (variant with highest average across all metrics)
    winner = _determine_winner(variant_results, selected_metrics)

    return ABTestResult(
        variants=variant_results,
        metric_comparisons=metric_comparisons,
        winner=winner,
    )


def _compare_metrics(
    variants: List[VariantResult],
    metrics: List[str],
) -> List[MetricComparison]:
    """Compare each metric across all variants with optional statistics."""
    comparisons: List[MetricComparison] = []

    for metric_name in metrics:
        variant_scores: Dict[str, float] = {}
        variant_score_lists: Dict[str, List[float]] = {}

        for v in variants:
            avg = v.metric_averages.get(metric_name, 0.0)
            variant_scores[v.name] = avg
            # Collect per-case scores for statistical testing
            per_case = [c.metrics.get(metric_name) for c in v.cases if metric_name in c.metrics]
            variant_score_lists[v.name] = [s for s in per_case if s is not None]

        # Find best variant
        if variant_scores:
            best = max(variant_scores, key=variant_scores.get)
            sorted_scores = sorted(variant_scores.values(), reverse=True)
            delta = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else 0.0
        else:
            best = ""
            delta = 0.0

        # Statistical significance (t-test between top 2 variants if scipy available)
        p_value = None
        significant = None
        if len(variants) >= 2:
            try:
                from scipy import stats
                sorted_variants = sorted(variant_scores.items(), key=lambda x: x[1], reverse=True)
                v1_name = sorted_variants[0][0]
                v2_name = sorted_variants[1][0]
                v1_scores = variant_score_lists.get(v1_name, [])
                v2_scores = variant_score_lists.get(v2_name, [])
                if len(v1_scores) >= 2 and len(v2_scores) >= 2:
                    _, p_value = stats.ttest_ind(v1_scores, v2_scores)
                    significant = p_value < 0.05
            except ImportError:
                pass  # scipy not installed, skip statistical tests

        comparisons.append(MetricComparison(
            metric_name=metric_name,
            variant_scores=variant_scores,
            best_variant=best,
            delta=delta,
            p_value=p_value,
            significant=significant,
        ))

    return comparisons


def _determine_winner(
    variants: List[VariantResult],
    metrics: List[str],
) -> Optional[str]:
    """Determine the overall winning variant across all metrics."""
    if not variants or not metrics:
        return None

    # Simple approach: average of all metric averages per variant
    variant_totals: Dict[str, float] = {}
    for v in variants:
        total = 0.0
        count = 0
        for m in metrics:
            if m in v.metric_averages:
                total += v.metric_averages[m]
                count += 1
        variant_totals[v.name] = total / count if count > 0 else 0.0

    return max(variant_totals, key=variant_totals.get) if variant_totals else None
