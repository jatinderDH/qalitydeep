"""Evaluation pipeline: DeepEval metrics + LangSmith trajectory eval."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

from deepeval.metrics import (
    AnswerRelevancyMetric,
    GEval,
    HallucinationMetric,
    ToolCorrectnessMetric,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall

from .config import get_settings
from .langgraph_flows import run_multi_agent_workflow
from .metrics import METRIC_REGISTRY, get_metric as get_new_metric
from .models import EvalCaseResult, TestCase
from .tools import get_all_tools


def get_deepeval_model():
    """Return the LLM for DeepEval metrics from config. Uses Anthropic or OpenAI; falls back to the other if the chosen backend's key is missing."""
    settings = get_settings()
    anthropic_key = (
        getattr(settings, "anthropic_api_key", None)
        or os.environ.get("ANTHROPIC_API_KEY")
    )
    openai_key = (
        getattr(settings, "openai_api_key", None)
        or os.environ.get("OPENAI_API_KEY")
    )

    use_anthropic = (
        settings.llm_backend == "anthropic"
        and anthropic_key
        or (settings.llm_backend == "openai" and not openai_key and anthropic_key)
    )
    if use_anthropic and anthropic_key:
        from deepeval.models import AnthropicModel

        return AnthropicModel(
            model=settings.anthropic_model,
            api_key=anthropic_key,
            temperature=0,
        )
    if openai_key:
        from deepeval.models import GPTModel

        return GPTModel(
            model=settings.openai_model,
            api_key=openai_key,
        )
    raise ValueError(
        "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env.local, "
        "and optionally LLM_BACKEND=anthropic or openai."
    )


def build_metrics(selected: Iterable[str]):
    selected_set = {m.lower() for m in selected}
    metrics = []
    eval_model = get_deepeval_model()

    def _geval(name: str, criteria: str, evaluation_params: list):
        return GEval(
            name=name,
            criteria=criteria,
            evaluation_params=evaluation_params,
            threshold=0.5,
            model=eval_model,
        )

    if "correctness" in selected_set:
        metrics.append(
            _geval(
                "correctness",
                "Is the actual output semantically equivalent to the expected output?",
                [
                    LLMTestCaseParams.ACTUAL_OUTPUT,
                    LLMTestCaseParams.EXPECTED_OUTPUT,
                ],
            )
        )
    if "relevancy" in selected_set:
        metrics.append(
            AnswerRelevancyMetric(threshold=0.5, model=eval_model)
        )
    if "hallucination" in selected_set:
        metrics.append(HallucinationMetric(threshold=0.5, model=eval_model))
    if "tool_correctness" in selected_set:
        available = [ToolCall(name=t.name) for t in get_all_tools()]
        metrics.append(
            ToolCorrectnessMetric(
                threshold=0.5,
                available_tools=available,
                model=eval_model,
            )
        )
    if "coordination" in selected_set:
        metrics.append(
            _geval(
                "coordination",
                "Given the trajectory, decide if the agents communicate clearly, "
                "respect milestones, and avoid contradictions.",
                [LLMTestCaseParams.CONTEXT],
            )
        )
    if "trajectory" in selected_set:
        metrics.append(
            _geval(
                "trajectory",
                "Given the trajectory and final answer, judge whether the steps "
                "taken were efficient and appropriate to reach the answer.",
                [LLMTestCaseParams.CONTEXT],
            )
        )
    return metrics


# Set of metric names that require DeepEval/LLM
LLM_METRICS = {"correctness", "relevancy", "hallucination", "tool_correctness", "coordination", "trajectory", "langsmith_trajectory"}

# Set of metric names from the new registry (programmatic)
def get_all_metric_names() -> list[str]:
    """Return all available metric names (both LLM and programmatic)."""
    names = set(LLM_METRICS)
    names.update(METRIC_REGISTRY.keys())
    return sorted(names)


def is_programmatic_metric(name: str) -> bool:
    """Check if a metric can be evaluated without an LLM call."""
    return name in METRIC_REGISTRY


def evaluate_case_simple(
    test_case_id: str,
    input_text: str,
    actual_output: str,
    expected_output: str | None,
    selected_metrics: list[str],
    threshold: float = 0.5,
) -> EvalCaseResult:
    """Evaluate using only the new metrics system (no LangGraph workflow).

    This is used when:
    1. All metrics are programmatic (no LLM needed)
    2. The test case already has actual_output provided
    """
    import time
    start = time.perf_counter()

    # Create a simple test case object for metric.measure()
    class _SimpleTC:
        pass
    tc = _SimpleTC()
    tc.input = input_text
    tc.actual_output = actual_output
    tc.expected_output = expected_output

    metric_scores: Dict[str, float] = {}
    metric_reasons: Dict[str, str] = {}

    for metric_name in selected_metrics:
        if metric_name in METRIC_REGISTRY:
            metric = get_new_metric(metric_name, threshold=threshold)
            metric.measure(tc)
            if metric.score is not None:
                metric_scores[metric_name] = float(metric.score)
            if metric.reason:
                metric_reasons[metric_name] = metric.reason

    latency_ms = (time.perf_counter() - start) * 1000

    return EvalCaseResult(
        test_case_id=test_case_id,
        actual_output=actual_output,
        metrics=metric_scores,
        metric_reasons=metric_reasons,
        latency_ms=latency_ms,
    )


def _tool_calls_from_log(tool_calls_log: List[Dict[str, Any]]) -> List[ToolCall]:
    out = []
    for e in tool_calls_log:
        name = e.get("name") or ""
        inp = e.get("input")
        out_val = e.get("output")
        out.append(ToolCall(name=name, input=inp, output=out_val))
    return out


def _expected_tools_from_case(case: TestCase) -> List[ToolCall]:
    if not case.expected_tool_calls:
        return []
    return [
        ToolCall(
            name=d.get("name", ""),
            input=d.get("input"),
            output=d.get("output"),
        )
        for d in case.expected_tool_calls
    ]


def evaluate_case(
    case: TestCase,
    selected_metrics: Iterable[str],
) -> EvalCaseResult:
    metrics = build_metrics(selected_metrics)

    run = run_multi_agent_workflow(case.prompt)
    actual_output = run["output"]
    trajectory = run["trajectory"]
    context = _trajectory_to_context(trajectory)

    tools_called = _tool_calls_from_log(trajectory.get("tool_calls_log", []))
    expected_tools = _expected_tools_from_case(case)

    context_list = [context] if context else []
    test_case = LLMTestCase(
        input=case.prompt,
        actual_output=actual_output,
        expected_output=case.expected_output,
        retrieval_context=context_list,
        context=context_list,
        tools_called=tools_called,
        expected_tools=expected_tools,
    )

    metric_scores: Dict[str, float] = {}
    metric_reasons: Dict[str, str] = {}

    # LangSmith trajectory eval (explicit callback result)
    if run.get("langsmith_trajectory_score") is not None:
        metric_scores["langsmith_trajectory"] = float(run["langsmith_trajectory_score"])
        if run.get("langsmith_trajectory_comment"):
            metric_reasons["langsmith_trajectory"] = run["langsmith_trajectory_comment"]

    for metric in metrics:
        metric.measure(test_case)
        name = getattr(metric, "name", metric.__class__.__name__)
        score = getattr(metric, "score", None)
        reason = getattr(metric, "reason", "")
        if score is not None:
            metric_scores[name] = float(score)
        if reason:
            metric_reasons[name] = str(reason)

    return EvalCaseResult(
        test_case_id=case.id,
        actual_output=actual_output,
        metrics=metric_scores,
        metric_reasons=metric_reasons,
        trajectory=trajectory,
    )


def _trajectory_to_context(trajectory: Dict[str, Any]) -> str:
    parts: List[str] = []
    for msg in trajectory.get("messages", []):
        parts.append(f"{msg.get('type')}: {msg.get('content')}")
    return "\n".join(parts)


def evaluate_case_api(
    input_text: str,
    actual_output: str,
    expected_output: Optional[str] = None,
    selected_metrics: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Evaluate without running graph. For API: user provides input + actualOutput.
    Metrics: correctness, relevancy, hallucination (no trajectory needed).
    """
    metrics = selected_metrics or ["correctness", "relevancy", "hallucination"]
    allowed = {"correctness", "relevancy", "hallucination"}
    filtered = [m for m in metrics if m.lower() in allowed]
    if not filtered:
        filtered = ["correctness", "relevancy"]

    built = build_metrics(filtered)
    context_list = [expected_output] if expected_output else []
    test_case = LLMTestCase(
        input=input_text,
        actual_output=actual_output,
        expected_output=expected_output or "",
        retrieval_context=context_list,
        context=context_list,
        tools_called=[],
        expected_tools=[],
    )

    scores: Dict[str, float] = {}
    reasons: Dict[str, str] = {}
    for metric in built:
        metric.measure(test_case)
        name = getattr(metric, "name", metric.__class__.__name__)
        score = getattr(metric, "score", None)
        reason = getattr(metric, "reason", "")
        if score is not None:
            scores[name] = float(score)
        if reason:
            reasons[name] = str(reason)

    return {"metrics": scores, "reasons": reasons}
