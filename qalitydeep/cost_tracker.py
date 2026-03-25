"""Token cost estimation for LLM API calls."""
from __future__ import annotations
from typing import Dict, Optional

# Prices per 1M tokens (input, output) as of March 2026
MODEL_PRICES: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.0},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-20250414": {"input": 0.80, "output": 4.0},
    # Ollama (local, free)
    "llama3.1": {"input": 0.0, "output": 0.0},
    "llama3": {"input": 0.0, "output": 0.0},
    "mistral": {"input": 0.0, "output": 0.0},
}


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Estimate cost in USD for a given model and token usage."""
    prices = MODEL_PRICES.get(model)
    if prices is None:
        # Try prefix matching (e.g., "gpt-4o-2024..." -> "gpt-4o")
        # Sort keys longest-first so more specific prefixes match first
        for key in sorted(MODEL_PRICES, key=len, reverse=True):
            if model.startswith(key):
                prices = MODEL_PRICES[key]
                break

    if prices is None:
        return 0.0  # Unknown model

    input_cost = (prompt_tokens / 1_000_000) * prices["input"]
    output_cost = (completion_tokens / 1_000_000) * prices["output"]
    return input_cost + output_cost


def format_cost(cost_usd: float) -> str:
    """Format cost for display."""
    if cost_usd == 0:
        return "free"
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    return f"${cost_usd:.2f}"
