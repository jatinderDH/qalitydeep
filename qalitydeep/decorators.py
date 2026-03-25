"""Decorators for defining evaluation suites in Python."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class EvalCaseDef:
    """A single evaluation case definition."""
    input: str
    expected_output: Optional[str] = None
    expected_tool_calls: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    language: Optional[str] = None
    id: Optional[str] = None


@dataclass
class EvalSuiteDef:
    """A decorated evaluation suite definition."""
    name: str
    description: str = ""
    metrics: List[str] = field(default_factory=list)
    threshold: float = 0.5
    provider: Optional[str] = None
    model: Optional[str] = None
    fn: Optional[Callable] = None
    tags: Optional[List[str]] = None

    def get_cases(self) -> List[EvalCaseDef]:
        """Call the decorated function to get test cases."""
        if self.fn is None:
            return []
        result = self.fn()
        if isinstance(result, list):
            return result
        return [result]


# Global registry of discovered suites
_REGISTERED_SUITES: List[EvalSuiteDef] = []


def eval_suite(
    metrics: Optional[List[str]] = None,
    threshold: float = 0.5,
    name: Optional[str] = None,
    description: str = "",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    tags: Optional[List[str]] = None,
):
    """Decorator to define an evaluation suite.

    Usage:
        @eval_suite(metrics=["correctness", "code_syntax"])
        def test_code_gen():
            return [
                eval_case(input="Write fibonacci", expected_output="def fib(n): ..."),
            ]
    """
    def decorator(fn: Callable) -> Callable:
        suite = EvalSuiteDef(
            name=name or fn.__name__,
            description=description or fn.__doc__ or "",
            metrics=metrics or ["correctness", "relevancy"],
            threshold=threshold,
            provider=provider,
            model=model,
            fn=fn,
            tags=tags,
        )
        _REGISTERED_SUITES.append(suite)
        fn._eval_suite = suite  # attach metadata
        return fn
    return decorator


def eval_case(
    input: str,
    expected_output: Optional[str] = None,
    expected_tool_calls: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[List[str]] = None,
    language: Optional[str] = None,
    id: Optional[str] = None,
) -> EvalCaseDef:
    """Create an evaluation case definition.

    Usage:
        eval_case(input="What is 2+2?", expected_output="4")
    """
    return EvalCaseDef(
        input=input,
        expected_output=expected_output,
        expected_tool_calls=expected_tool_calls,
        tags=tags,
        language=language,
        id=id,
    )


def get_registered_suites() -> List[EvalSuiteDef]:
    """Return all suites registered via @eval_suite decorator."""
    return list(_REGISTERED_SUITES)


def clear_registered_suites() -> None:
    """Clear all registered suites (useful for testing)."""
    _REGISTERED_SUITES.clear()
