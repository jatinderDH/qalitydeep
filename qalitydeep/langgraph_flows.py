"""Multi-agent LangGraph workflow with real tools and trajectory logging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from .llm_backends import get_chat_model
from .tools import get_all_tools


class ConversationState(TypedDict):
    messages: List[BaseMessage]
    milestones: List[str]
    tools_used: List[str]
    tool_calls_log: List[Dict[str, Any]]
    meta: Dict[str, Any]


@dataclass
class AgentContext:
    name: str
    system_prompt: str
    temperature: float = 0.1
    use_tools: bool = False

    def run(self, state: ConversationState) -> ConversationState:
        llm = get_chat_model(temperature=self.temperature)
        if self.use_tools:
            llm = llm.bind_tools(get_all_tools())

        messages = [
            SystemMessage(content=self.system_prompt),
            *state["messages"],
        ]
        response = llm.invoke(messages)

        state["messages"].append(response)
        return state


def _planner_node(state: ConversationState) -> ConversationState:
    planner = AgentContext(
        name="planner",
        system_prompt=(
            "You are a planning agent. Break the user's goal into 2-4 "
            "clear milestones. Reply with a numbered list of milestones."
        ),
    )
    updated = planner.run(state)
    content = updated["messages"][-1].content
    lines = [l.strip("- ").strip() for l in str(content).splitlines() if l.strip()]
    milestones = [l for l in lines if any(ch.isalpha() for ch in l)]
    updated["milestones"].extend(milestones)
    return updated


def _worker_node(state: ConversationState) -> ConversationState:
    worker = AgentContext(
        name="worker",
        system_prompt=(
            "You are a senior agent. Use the milestones as guidance. "
            "When you need policy, refund, or shipping info use the provided tools: "
            "search_policy, get_refund_eligibility, calculate_shipping_estimate. "
            "Then produce a concise, accurate answer."
        ),
        use_tools=True,
    )
    return worker.run(state)


def _route_after_worker(state: ConversationState) -> Literal["tools", "reviewer"]:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "reviewer"


def _tools_node(state: ConversationState) -> ConversationState:
    tool_node = ToolNode(get_all_tools())
    result = tool_node.invoke(state)

    # Log each tool call for ToolCorrectnessMetric and trajectory eval
    last_ai = state["messages"][-1]
    if isinstance(last_ai, AIMessage) and getattr(last_ai, "tool_calls", None):
        for tc in last_ai.tool_calls:
            name = tc.get("name", "")
            args = tc.get("args") or {}
            state["tools_used"].append(name)
            # Find corresponding ToolMessage in result
            out = ""
            for msg in result["messages"]:
                if isinstance(msg, ToolMessage) and getattr(msg, "tool_call_id", None) == tc.get("id"):
                    out = str(msg.content)
                    break
            state["tool_calls_log"].append({
                "name": name,
                "input": args,
                "output": out,
            })

    state["messages"].extend(result["messages"])
    return state


def _reviewer_node(state: ConversationState) -> ConversationState:
    reviewer = AgentContext(
        name="reviewer",
        system_prompt=(
            "You are a critical reviewer. Check if the last assistant "
            "message follows the milestones and is correct. If fixes are "
            "needed, rewrite the answer. Otherwise, briefly approve."
        ),
    )
    return reviewer.run(state)


def build_multi_agent_graph() -> StateGraph:
    graph = StateGraph(ConversationState)

    graph.add_node("planner", _planner_node)
    graph.add_node("worker", _worker_node)
    graph.add_node("tools", _tools_node)
    graph.add_node("reviewer", _reviewer_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "worker")
    graph.add_conditional_edges("worker", _route_after_worker, {"tools": "tools", "reviewer": "reviewer"})
    graph.add_edge("tools", "worker")
    graph.add_edge("reviewer", END)

    return graph


def _messages_to_trajectory_dict(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    out = []
    for msg in messages:
        entry = {"type": msg.__class__.__name__, "content": str(msg.content)}
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            entry["tool_calls"] = [
                {"name": tc.get("name"), "args": tc.get("args")}
                for tc in msg.tool_calls
            ]
        if isinstance(msg, ToolMessage):
            entry["tool_call_id"] = getattr(msg, "tool_call_id", None)
        out.append(entry)
    return out


def run_multi_agent_workflow(
    prompt: str,
    langsmith_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from .langsmith_integration import tracing_config

    graph = build_multi_agent_graph().compile()

    initial_state: ConversationState = {
        "messages": [HumanMessage(content=prompt)],
        "milestones": [],
        "tools_used": [],
        "tool_calls_log": [],
        "meta": {},
    }

    config = langsmith_config if langsmith_config is not None else tracing_config()
    final_state = graph.invoke(initial_state, config=config)

    messages = final_state["messages"]
    final_answer = messages[-1].content if messages else ""

    trajectory = {
        "messages": _messages_to_trajectory_dict(messages),
        "milestones": final_state["milestones"],
        "tools_used": final_state["tools_used"],
        "tool_calls_log": final_state["tool_calls_log"],
    }

    out: Dict[str, Any] = {
        "output": str(final_answer),
        "trajectory": trajectory,
    }

    # Explicit trajectory eval callback (LangSmith/agentevals)
    from .langsmith_integration import run_trajectory_eval

    te = run_trajectory_eval(trajectory)
    if te.get("score") is not None:
        out["langsmith_trajectory_score"] = float(te["score"]) if isinstance(te["score"], (int, float)) else (1.0 if te["score"] else 0.0)
        out["langsmith_trajectory_comment"] = te.get("comment") or ""

    return out
