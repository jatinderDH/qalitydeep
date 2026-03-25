"""LangSmith tracing and explicit trajectory-eval callbacks."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from .config import get_settings


def tracing_config() -> Dict[str, Any]:
    """Config for LangGraph invoke to enable LangSmith tracing when API key is set."""
    settings = get_settings()
    if not settings.langsmith_api_key:
        return {}
    os.environ["LANGSMITH_TRACING"] = "true"
    if settings.langsmith_project:
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)

    return {
        "configurable": {"thread_id": "qalitydeep-eval"},
        "run_name": "qalitydeep_multi_agent",
        "tags": ["qalitydeep", "multi_agent"],
    }


def is_langsmith_available() -> bool:
    return bool(get_settings().langsmith_api_key)


def _trajectory_to_langchain_messages(trajectory: Dict[str, Any]) -> List[BaseMessage]:
    """Convert our trajectory dict to LangChain messages for agentevals."""
    messages: List[BaseMessage] = []
    for m in trajectory.get("messages", []):
        typ = m.get("type")
        content = m.get("content") or ""
        if typ == "HumanMessage":
            messages.append(HumanMessage(content=content))
        elif typ == "AIMessage":
            tool_calls = m.get("tool_calls")
            if tool_calls:
                messages.append(
                    AIMessage(
                        content=content,
                        tool_calls=[
                            {
                                "id": f"call_{i}",
                                "name": tc.get("name", ""),
                                "args": tc.get("args") or {},
                            }
                            for i, tc in enumerate(tool_calls)
                        ],
                    )
                )
            else:
                messages.append(AIMessage(content=content))
        elif typ == "ToolMessage":
            messages.append(
                ToolMessage(
                    content=content,
                    tool_call_id=m.get("tool_call_id") or "call_0",
                )
            )
    return messages


def run_trajectory_eval(
    trajectory: Dict[str, Any],
    reference_trajectory: Optional[List[BaseMessage]] = None,
) -> Dict[str, Any]:
    """
    Run LangSmith/agentevals trajectory evaluation (LLM-as-judge).
    Returns dict with keys: score (bool/float), comment (str), key (str).
    """
    if not is_langsmith_available():
        return {"score": None, "comment": "LangSmith not configured", "key": "trajectory_accuracy"}

    try:
        from agentevals.trajectory.llm import (
            TRAJECTORY_ACCURACY_PROMPT,
            TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE,
            create_trajectory_llm_as_judge,
        )
    except ImportError:
        return {"score": None, "comment": "agentevals not installed", "key": "trajectory_accuracy"}

    outputs = _trajectory_to_langchain_messages(trajectory)
    if not outputs:
        return {"score": None, "comment": "Empty trajectory", "key": "trajectory_accuracy"}

    if reference_trajectory:
        evaluator = create_trajectory_llm_as_judge(
            model="openai:gpt-4o-mini",
            prompt=TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE,
        )
        evaluation = evaluator(
            outputs=outputs,
            reference_outputs=reference_trajectory,
        )
    else:
        evaluator = create_trajectory_llm_as_judge(
            model="openai:gpt-4o-mini",
            prompt=TRAJECTORY_ACCURACY_PROMPT,
        )
        evaluation = evaluator(outputs=outputs)

    return {
        "score": evaluation.get("score"),
        "comment": evaluation.get("comment"),
        "key": evaluation.get("key", "trajectory_accuracy"),
    }


def run_trajectory_match_eval(
    trajectory: Dict[str, Any],
    reference_trajectory: List[BaseMessage],
    mode: str = "superset",
) -> Dict[str, Any]:
    """
    Run trajectory match evaluator (strict / unordered / subset / superset).
    reference_trajectory must be LangChain messages (e.g. from test case).
    """
    if not is_langsmith_available():
        return {"score": None, "comment": "LangSmith not configured", "key": f"trajectory_{mode}_match"}

    try:
        from agentevals.trajectory.match import create_trajectory_match_evaluator
    except ImportError:
        return {"score": None, "comment": "agentevals not installed", "key": f"trajectory_{mode}_match"}

    outputs = _trajectory_to_langchain_messages(trajectory)
    if not outputs:
        return {"score": False, "comment": "Empty trajectory", "key": f"trajectory_{mode}_match"}

    evaluator = create_trajectory_match_evaluator(trajectory_match_mode=mode)
    evaluation = evaluator(
        outputs=outputs,
        reference_outputs=reference_trajectory,
    )
    return {
        "score": evaluation.get("score"),
        "comment": evaluation.get("comment"),
        "key": evaluation.get("key", f"trajectory_{mode}_match"),
    }
