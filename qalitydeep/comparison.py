"""Run comparison and regression detection for QAlityDeep."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import EvalCaseResult, EvalRun


@dataclass
class CaseComparison:
    """Comparison result for a single test case."""
    test_case_id: str
    baseline_scores: Dict[str, float]
    candidate_scores: Dict[str, float]
    deltas: Dict[str, float]  # candidate - baseline
    status: str  # "improved", "regressed", "unchanged", "new", "removed"


@dataclass
class MetricSummary:
    """Aggregate comparison for a single metric."""
    name: str
    baseline_avg: float
    candidate_avg: float
    delta: float  # candidate_avg - baseline_avg
    improved_count: int
    regressed_count: int
    unchanged_count: int


@dataclass
class ComparisonResult:
    """Full comparison between two eval runs."""
    baseline_run_id: str
    candidate_run_id: str
    case_comparisons: List[CaseComparison]
    metric_summaries: List[MetricSummary]
    total_improved: int
    total_regressed: int
    total_unchanged: int
    total_new: int
    total_removed: int

    @property
    def has_regressions(self) -> bool:
        return self.total_regressed > 0


@dataclass
class RegressionCheckResult:
    """Result of checking for regressions against thresholds."""
    passed: bool
    violations: List[str] = field(default_factory=list)
    # violations are human-readable strings like:
    # "correctness avg 0.72 below minimum 0.85"
    # "hallucination dropped 0.08 (max allowed: 0.05)"


def compare_runs(baseline: EvalRun, candidate: EvalRun) -> ComparisonResult:
    """Compare two evaluation runs case-by-case.

    Cases are matched by test_case_id. Cases present in only one run
    are marked as "new" or "removed".
    """
    # Build lookup maps
    baseline_map = {c.test_case_id: c for c in baseline.cases}
    candidate_map = {c.test_case_id: c for c in candidate.cases}

    all_case_ids = sorted(set(baseline_map.keys()) | set(candidate_map.keys()))
    all_metric_names = sorted(set(baseline.metrics) | set(candidate.metrics))

    case_comparisons: List[CaseComparison] = []

    # Per-metric accumulators
    metric_baselines: Dict[str, List[float]] = {m: [] for m in all_metric_names}
    metric_candidates: Dict[str, List[float]] = {m: [] for m in all_metric_names}
    metric_improved: Dict[str, int] = {m: 0 for m in all_metric_names}
    metric_regressed: Dict[str, int] = {m: 0 for m in all_metric_names}
    metric_unchanged: Dict[str, int] = {m: 0 for m in all_metric_names}

    total_improved = 0
    total_regressed = 0
    total_unchanged = 0
    total_new = 0
    total_removed = 0

    EPSILON = 0.001  # scores within this are "unchanged"

    for case_id in all_case_ids:
        b_case = baseline_map.get(case_id)
        c_case = candidate_map.get(case_id)

        if b_case is None:
            # New case in candidate
            case_comparisons.append(CaseComparison(
                test_case_id=case_id,
                baseline_scores={},
                candidate_scores=c_case.metrics,
                deltas={},
                status="new",
            ))
            total_new += 1
            for m, s in c_case.metrics.items():
                if m in metric_candidates:
                    metric_candidates[m].append(s)
            continue

        if c_case is None:
            # Removed case
            case_comparisons.append(CaseComparison(
                test_case_id=case_id,
                baseline_scores=b_case.metrics,
                candidate_scores={},
                deltas={},
                status="removed",
            ))
            total_removed += 1
            for m, s in b_case.metrics.items():
                if m in metric_baselines:
                    metric_baselines[m].append(s)
            continue

        # Both exist — compare
        deltas: Dict[str, float] = {}
        case_status = "unchanged"
        any_improved = False
        any_regressed = False

        for m in all_metric_names:
            b_score = b_case.metrics.get(m)
            c_score = c_case.metrics.get(m)

            if b_score is not None:
                metric_baselines[m].append(b_score)
            if c_score is not None:
                metric_candidates[m].append(c_score)

            if b_score is not None and c_score is not None:
                delta = c_score - b_score
                deltas[m] = delta

                if delta > EPSILON:
                    any_improved = True
                    metric_improved[m] += 1
                elif delta < -EPSILON:
                    any_regressed = True
                    metric_regressed[m] += 1
                else:
                    metric_unchanged[m] += 1

        if any_regressed:
            case_status = "regressed"
            total_regressed += 1
        elif any_improved:
            case_status = "improved"
            total_improved += 1
        else:
            case_status = "unchanged"
            total_unchanged += 1

        case_comparisons.append(CaseComparison(
            test_case_id=case_id,
            baseline_scores=b_case.metrics,
            candidate_scores=c_case.metrics,
            deltas=deltas,
            status=case_status,
        ))

    # Build metric summaries
    metric_summaries: List[MetricSummary] = []
    for m in all_metric_names:
        b_scores = metric_baselines[m]
        c_scores = metric_candidates[m]
        b_avg = sum(b_scores) / len(b_scores) if b_scores else 0.0
        c_avg = sum(c_scores) / len(c_scores) if c_scores else 0.0

        metric_summaries.append(MetricSummary(
            name=m,
            baseline_avg=b_avg,
            candidate_avg=c_avg,
            delta=c_avg - b_avg,
            improved_count=metric_improved.get(m, 0),
            regressed_count=metric_regressed.get(m, 0),
            unchanged_count=metric_unchanged.get(m, 0),
        ))

    return ComparisonResult(
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate.run_id,
        case_comparisons=case_comparisons,
        metric_summaries=metric_summaries,
        total_improved=total_improved,
        total_regressed=total_regressed,
        total_unchanged=total_unchanged,
        total_new=total_new,
        total_removed=total_removed,
    )


def check_regression(
    run: EvalRun,
    baseline: Optional[EvalRun] = None,
    max_regression: float = 0.05,
    min_scores: Optional[Dict[str, float]] = None,
) -> RegressionCheckResult:
    """Check if a run violates regression thresholds.

    Two types of checks:
    1. Absolute minimum scores: fail if any metric avg is below min_scores[metric]
    2. Relative regression: fail if any metric dropped more than max_regression vs baseline
    """
    violations: List[str] = []

    # Calculate metric averages for the current run
    metric_avgs: Dict[str, float] = {}
    for metric_name in run.metrics:
        scores = [c.metrics.get(metric_name) for c in run.cases if metric_name in c.metrics]
        if scores:
            metric_avgs[metric_name] = sum(scores) / len(scores)

    # Check absolute minimums
    if min_scores:
        for metric_name, min_score in min_scores.items():
            avg = metric_avgs.get(metric_name)
            if avg is not None and avg < min_score:
                violations.append(
                    f"{metric_name} avg {avg:.3f} below minimum {min_score:.3f}"
                )

    # Check relative regression against baseline
    if baseline is not None:
        baseline_avgs: Dict[str, float] = {}
        for metric_name in baseline.metrics:
            scores = [c.metrics.get(metric_name) for c in baseline.cases if metric_name in c.metrics]
            if scores:
                baseline_avgs[metric_name] = sum(scores) / len(scores)

        for metric_name, current_avg in metric_avgs.items():
            baseline_avg = baseline_avgs.get(metric_name)
            if baseline_avg is not None:
                drop = baseline_avg - current_avg
                if drop > max_regression:
                    violations.append(
                        f"{metric_name} dropped {drop:.3f} from {baseline_avg:.3f} to {current_avg:.3f} "
                        f"(max allowed regression: {max_regression:.3f})"
                    )

    return RegressionCheckResult(
        passed=len(violations) == 0,
        violations=violations,
    )


def get_latest_run(dataset_id: Optional[str] = None) -> Optional[EvalRun]:
    """Get the most recent eval run, optionally filtered by dataset_id."""
    from .storage import list_eval_runs

    runs = list_eval_runs()  # already sorted by created_at desc
    if dataset_id:
        runs = [r for r in runs if r.dataset_id == dataset_id]
    return runs[0] if runs else None
