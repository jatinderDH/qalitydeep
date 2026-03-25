"""Real tools for the multi-agent worker; used for tool-correctness evaluation."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
def search_policy(query: str) -> str:
    """Search company policy by keyword. Use for refund, shipping, returns, warranty."""
    policies = {
        "refund": "30-day full refund at no extra cost. Original packaging preferred.",
        "shipping": "Standard 3-5 business days. Express 1-2 days available.",
        "returns": "Returns accepted within 30 days. Item must be unused.",
        "warranty": "1-year manufacturer warranty on all products.",
        "international": "We ship to most countries. Duties may apply.",
    }
    q = query.lower()
    for key, text in policies.items():
        if key in q or q in key:
            return text
    return f"No policy found for '{query}'. Available: refund, shipping, returns, warranty, international."


@tool
def get_refund_eligibility(order_id: str, reason: str) -> str:
    """Check if an order is eligible for refund. Pass order_id and reason."""
    if not order_id or not reason:
        return "Please provide order_id and reason."
    return "Eligible for 30-day full refund. Initiate return from your account."


@tool
def calculate_shipping_estimate(region: str, express: bool = False) -> str:
    """Estimate delivery: region (e.g. US, EU, APAC), express=True for 1-2 days."""
    if express:
        return f"Express to {region}: 1-2 business days."
    return f"Standard to {region}: 3-5 business days."


def get_all_tools() -> list:
    """Return tools list for bind_tools and for ToolCorrectnessMetric available_tools."""
    return [search_policy, get_refund_eligibility, calculate_shipping_estimate]
