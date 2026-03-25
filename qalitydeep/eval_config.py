from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class EvalTestCase(BaseModel):
    """A single test case in a suite."""
    id: Optional[str] = None
    input: str
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None  # if provided, skip LLM call and evaluate directly
    expected_tool_calls: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    language: Optional[str] = None  # for code metrics: python, javascript, json


class RegressionConfig(BaseModel):
    """Regression detection settings."""
    baseline: str = "latest"  # run_id or "latest"
    max_regression: float = 0.05  # fail if any metric drops more than this
    min_scores: Optional[Dict[str, float]] = None  # per-metric minimum thresholds


class EvalSuite(BaseModel):
    """A named collection of test cases with shared settings."""
    name: str
    description: str = ""
    metrics: Optional[List[str]] = None  # overrides defaults.metrics
    threshold: Optional[float] = None  # overrides defaults.threshold
    provider: Optional[str] = None  # override LLM backend for this suite
    model: Optional[str] = None  # override model name
    test_cases: List[EvalTestCase] = Field(default_factory=list)
    tags: Optional[List[str]] = None


class EvalDefaults(BaseModel):
    """Default settings applied to all suites unless overridden."""
    metrics: List[str] = Field(default_factory=lambda: ["correctness", "relevancy"])
    threshold: float = 0.5
    provider: Optional[str] = None
    model: Optional[str] = None


class EvalConfig(BaseModel):
    """Top-level evaluation configuration (parsed from qalitydeep.yaml)."""
    version: str = "1"
    defaults: EvalDefaults = Field(default_factory=EvalDefaults)
    suites: List[EvalSuite] = Field(default_factory=list)
    regression: Optional[RegressionConfig] = None

    def resolve_suite(self, suite: EvalSuite) -> EvalSuite:
        """Apply defaults to a suite, returning a new suite with resolved values."""
        return EvalSuite(
            name=suite.name,
            description=suite.description,
            metrics=suite.metrics or self.defaults.metrics,
            threshold=suite.threshold if suite.threshold is not None else self.defaults.threshold,
            provider=suite.provider or self.defaults.provider,
            model=suite.model or self.defaults.model,
            test_cases=suite.test_cases,
            tags=suite.tags,
        )
