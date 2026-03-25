from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    id: str
    prompt: str
    expected_output: Optional[str] = None
    expected_tool_calls: Optional[List[Dict[str, Any]]] = None
    agent_trace: Optional[Dict[str, Any]] = None


class Dataset(BaseModel):
    dataset_id: str
    name: str
    description: str = ""
    source_path: Path
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationTurn(BaseModel):
    """A single turn in a multi-turn conversation."""
    role: str  # "user", "assistant", "system"
    content: str


class EvalCaseResult(BaseModel):
    test_case_id: str
    actual_output: str
    metrics: Dict[str, float]
    metric_reasons: Dict[str, str]
    trajectory: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    token_usage: Optional[Dict[str, int]] = None


class EvalRun(BaseModel):
    run_id: str
    dataset_id: str
    graph_name: str
    metrics: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    summary: Dict[str, Any] = Field(default_factory=dict)
    cases: List[EvalCaseResult] = Field(default_factory=list)

