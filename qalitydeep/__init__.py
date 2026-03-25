"""QAlityDeep - Pre-deploy CI/CD QA for LLM and AI-agent outputs."""

from .config import get_settings
from .decorators import eval_case, eval_suite

__version__ = "0.2.0"

__all__ = [
    "get_settings",
    "eval_case",
    "eval_suite",
    "__version__",
]
