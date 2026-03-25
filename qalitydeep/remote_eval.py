"""Remote eval API: build and send eval payloads to an external evaluation service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from .config import get_settings
from .models import EvalRun


def _messages_to_input(trajectory: Dict[str, Any]) -> str:
    msgs = trajectory.get("messages", [])
    for msg in msgs:
        if msg.get("type") == "HumanMessage":
            return str(msg.get("content") or "")
    return ""


def _trajectory_to_context_list(trajectory: Dict[str, Any]) -> List[str]:
    parts: List[str] = []
    for msg in trajectory.get("messages", []):
        parts.append(f"{msg.get('type')}: {msg.get('content')}")
    return parts


def _tools_log_to_api_format(trajectory: Dict[str, Any]) -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for entry in trajectory.get("tool_calls_log", []):
        tools.append(
            {
                "name": entry.get("name"),
                "description": "",
                "inputParameters": entry.get("input") or {},
                "output": str(entry.get("output") or ""),
                "reasoning": "",
            }
        )
    return tools


def build_eval_payload(
    run: EvalRun,
    metric_collection: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a generic eval API payload (single-turn).
    Structure: metricCollection, llmTestCases (input, actualOutput, name, retrievalContext, context, toolsCalled, expectedTools), hyperparameters, identifier.
    """
    settings = get_settings()
    collection = metric_collection or settings.remote_eval_collection

    llm_test_cases: List[Dict[str, Any]] = []
    for case in run.cases:
        traj = case.trajectory or {}
        input_text = _messages_to_input(traj)
        context_list = _trajectory_to_context_list(traj)
        tools_called = _tools_log_to_api_format(traj)

        llm_test_cases.append(
            {
                "input": input_text,
                "actualOutput": case.actual_output,
                "name": case.test_case_id,
                "retrievalContext": context_list,
                "context": context_list,
                "toolsCalled": tools_called,
                "expectedTools": [],
            }
        )

    return {
        "metricCollection": collection,
        "llmTestCases": llm_test_cases,
        "hyperparameters": {
            "source": "qalitydeep",
            "graph": run.graph_name,
        },
        "identifier": run.run_id,
    }


def send_to_remote_eval(run: EvalRun) -> Dict[str, Any]:
    """
    POST eval payload to the configured remote eval API.
    Returns JSON response or dict with 'error' key.
    """
    settings = get_settings()
    api_key = settings.remote_eval_api_key
    api_url = settings.remote_eval_api_url
    if not api_url:
        return {"error": "REMOTE_EVAL_API_URL not configured"}
    if not api_key:
        return {"error": "REMOTE_EVAL_API_KEY not configured"}

    payload = build_eval_payload(run)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
    except Exception as exc:
        return {"error": f"Request failed: {exc}"}

    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "body": resp.text}
    try:
        return resp.json()
    except Exception:
        return {"error": "Invalid JSON response", "body": resp.text}
