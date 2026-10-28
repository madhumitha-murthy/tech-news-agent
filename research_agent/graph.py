"""
research_agent/graph.py — The agent loop, written as a LangGraph state graph.

    START → agent ──(asked for tools)──→ tools ──→ agent   (loop)
              └────(final answer)──────→ grounding → END

- agent:     the model reads the conversation and either requests tool calls
             or writes a final answer.
- tools:     our code validates and runs each requested tool, records the
             result as evidence, and sends it back to the model.
- grounding: checks the final answer against the evidence; refuses if it
             isn't supported.

A tool-call budget (max_tool_calls) stops runaway loops: once it is spent, the
model must answer from what it already has.
"""

import json
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from research_agent.grounding import REFUSAL, Similarity, check_grounding, embedding_similarity
from research_agent.llm import ChatModel
from research_agent.tools import TOOLS, Tool, validate_args

DEFAULT_MAX_TOOL_CALLS = 6
MAX_RESULT_CHARS = 6000  # cap on what one tool result sends back to the model

SYSTEM_PROMPT = """You are a research assistant for AI and tech news.
Use the tools to find information before answering. Answer ONLY from what the
tools return, cite the article titles you used, and keep answers concise.
If the tools return nothing relevant, say you couldn't find it. Never guess."""


class AgentState(TypedDict):
    question: str
    messages: list[dict]
    pending_calls: list[dict]
    answer: str
    sources: list[dict]
    tool_calls_made: int
    max_tool_calls: int
    grounding: dict
    refused: bool
    trace: list[dict]


def build_agent(
    model: ChatModel,
    tools: dict[str, Tool] = TOOLS,
    similarity: Similarity = embedding_similarity,
):
    """Compile the agent graph. Tools and similarity are injectable for tests."""

    def agent_node(state: AgentState) -> dict:
        messages = list(state["messages"])
        budget_left = state["max_tool_calls"] - state["tool_calls_made"]
        available = list(tools.values()) if budget_left > 0 else []
        if budget_left <= 0:
            messages.append({"role": "user", "text": "Tool limit reached. Answer now from what you have."})

        start = time.perf_counter()
        turn = model.decide(SYSTEM_PROMPT, messages, available)
        latency = round((time.perf_counter() - start) * 1000)

        calls = turn.tool_calls if budget_left > 0 else []  # no tools once the budget is spent
        messages.append({"role": "assistant", "text": turn.text, "tool_calls": calls, "raw": turn.raw})
        event = {"node": "agent", "latency_ms": latency, "tool_calls": calls, "answer_chars": len(turn.text)}
        return {
            "messages": messages,
            "pending_calls": calls,
            "answer": "" if calls else turn.text,
            "trace": state["trace"] + [event],
        }

    def tools_node(state: AgentState) -> dict:
        messages = list(state["messages"])
        sources = list(state["sources"])
        seen = {s.get("link") for s in sources}
        made = state["tool_calls_made"]
        events = []

        for call in state["pending_calls"]:
            name, args = call["name"], call.get("args", {})
            start = time.perf_counter()
            error, result = None, None

            if made >= state["max_tool_calls"]:
                error = "Skipped: tool limit reached."
            elif name not in tools:
                error = f"Unknown tool '{name}'."
            else:
                error = validate_args(tools[name], args)
                if error is None:
                    try:
                        result = tools[name].func(**args)
                        made += 1
                    except Exception as exc:  # report failures to the model instead of crashing
                        error = f"{name} failed: {exc}"
                        made += 1

            if error is None and tools[name].returns_sources and isinstance(result, list):
                for item in result:
                    if item.get("link") not in seen:
                        seen.add(item.get("link"))
                        sources.append(item)

            payload = {"error": error} if error else result
            text = json.dumps(payload, default=str)
            if len(text) > MAX_RESULT_CHARS:
                payload = {"truncated": text[:MAX_RESULT_CHARS]}
            messages.append({"role": "tool", "name": name, "result": payload})
            events.append({
                "node": "tools",
                "tool": name,
                "args": args,
                "ok": error is None,
                "error": error,
                "n_results": len(result) if isinstance(result, list) else None,
                "latency_ms": round((time.perf_counter() - start) * 1000),
            })

        return {
            "messages": messages,
            "pending_calls": [],
            "sources": sources,
            "tool_calls_made": made,
            "trace": state["trace"] + events,
        }

    def grounding_node(state: AgentState) -> dict:
        verdict = check_grounding(state["answer"], state["sources"], similarity)
        refused = not verdict["grounded"]
        return {
            "grounding": verdict,
            "refused": refused,
            "answer": REFUSAL if refused else state["answer"],
            "trace": state["trace"] + [{"node": "grounding", **verdict}],
        }

    def route_after_agent(state: AgentState) -> str:
        return "tools" if state["pending_calls"] else "grounding"

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("grounding", grounding_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "grounding": "grounding"})
    graph.add_edge("tools", "agent")
    graph.add_edge("grounding", END)
    return graph.compile()


def run_question(agent, question: str, max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS) -> dict[str, Any]:
    """Run one question through a compiled agent and return a plain result dict."""
    start = time.perf_counter()
    state = agent.invoke(
        {
            "question": question,
            "messages": [{"role": "user", "text": question}],
            "pending_calls": [],
            "answer": "",
            "sources": [],
            "tool_calls_made": 0,
            "max_tool_calls": max_tool_calls,
            "grounding": {},
            "refused": False,
            "trace": [],
        },
        config={"recursion_limit": 4 * max_tool_calls + 10},
    )
    return {
        "question": question,
        "answer": state["answer"],
        "refused": state["refused"],
        "tools_called": [e["tool"] for e in state["trace"] if e["node"] == "tools" and e["ok"]],
        "tool_calls_made": state["tool_calls_made"],
        "sources": [{k: s.get(k) for k in ("title", "source", "link")} for s in state["sources"]],
        "grounding": state["grounding"],
        "latency_s": round(time.perf_counter() - start, 2),
        "trace": state["trace"],
    }
