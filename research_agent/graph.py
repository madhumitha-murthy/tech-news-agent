# graph.py - LangGraph agent loop: agent -> tools -> agent -> grounding -> done

import json
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from research_agent.grounding import REFUSAL, check_grounding, embedding_similarity
from research_agent.llm import ChatModel
from research_agent.tools import SOURCE_TOOLS, TOOLS, Tool, validate_args

MAX_TOOL_CALLS = 6
MAX_RESULT_LEN = 6000

SYSTEM_PROMPT = (
    "You are a tech news research assistant. Use the provided tools to find "
    "information before answering. Only answer from tool results, cite article "
    "titles, and be concise. If tools return nothing relevant, say so."
)


class AgentState(TypedDict):
    question: str
    messages: list[dict]
    pending_calls: list[dict]
    answer: str
    sources: list[dict]
    calls_used: int
    max_calls: int
    grounding: dict
    refused: bool
    trace: list[dict]


def build_agent(model, tools=TOOLS, similarity=embedding_similarity):
    """Wire up the LangGraph state machine."""

    def agent_node(state: AgentState) -> dict:
        msgs = list(state["messages"])
        budget = state["max_calls"] - state["calls_used"]

        avail = list(tools.values()) if budget > 0 else []
        if budget <= 0:
            msgs.append({"role": "user", "text": "Tool budget spent. Answer with what you have."})

        t0 = time.perf_counter()
        resp = model.decide(SYSTEM_PROMPT, msgs, avail)
        latency = round((time.perf_counter() - t0) * 1000)

        calls = resp.tool_calls if budget > 0 else []
        msgs.append({
            "role": "assistant", "text": resp.text,
            "tool_calls": calls, "raw": resp.raw,
        })

        return {
            "messages": msgs,
            "pending_calls": calls,
            "answer": "" if calls else resp.text,
            "trace": state["trace"] + [{
                "node": "agent", "latency_ms": latency,
                "tool_calls": calls, "answer_len": len(resp.text),
            }],
        }

    def tools_node(state: AgentState) -> dict:
        msgs = list(state["messages"])
        sources = list(state["sources"])
        seen_links = {s.get("link") for s in sources}
        used = state["calls_used"]
        events = []

        for call in state["pending_calls"]:
            name, args = call["name"], call.get("args", {})
            t0 = time.perf_counter()
            err, result = None, None

            if used >= state["max_calls"]:
                err = "Skipped: tool budget spent"
            elif name not in tools:
                err = f"Unknown tool '{name}'"
            else:
                err = validate_args(tools[name], args)
                if err is None:
                    try:
                        result = tools[name].fn(**args)
                        used += 1
                    except Exception as e:
                        err = f"{name} failed: {e}"
                        used += 1

            # Collect sources from tools that return articles
            if err is None and name in SOURCE_TOOLS and isinstance(result, list):
                for item in result:
                    link = item.get("link")
                    if link and link not in seen_links:
                        seen_links.add(link)
                        sources.append(item)

            payload = {"error": err} if err else result
            text = json.dumps(payload, default=str)
            if len(text) > MAX_RESULT_LEN:
                payload = {"truncated": text[:MAX_RESULT_LEN]}

            msgs.append({"role": "tool", "name": name, "result": payload})
            events.append({
                "node": "tools", "tool": name, "args": args,
                "ok": err is None, "error": err,
                "n_results": len(result) if isinstance(result, list) else None,
                "latency_ms": round((time.perf_counter() - t0) * 1000),
            })

        return {
            "messages": msgs,
            "pending_calls": [],
            "sources": sources,
            "calls_used": used,
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

    def route(state: AgentState) -> str:
        return "tools" if state["pending_calls"] else "grounding"

    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)
    g.add_node("grounding", grounding_node)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route, {"tools": "tools", "grounding": "grounding"})
    g.add_edge("tools", "agent")
    g.add_edge("grounding", END)
    return g.compile()


def run_question(agent, question: str, max_calls: int = MAX_TOOL_CALLS) -> dict[str, Any]:
    """Run a question through the agent graph and return structured results."""
    t0 = time.perf_counter()
    state = agent.invoke(
        {
            "question": question,
            "messages": [{"role": "user", "text": question}],
            "pending_calls": [],
            "answer": "",
            "sources": [],
            "calls_used": 0,
            "max_calls": max_calls,
            "grounding": {},
            "refused": False,
            "trace": [],
        },
        config={"recursion_limit": 4 * max_calls + 10},
    )
    return {
        "question": question,
        "answer": state["answer"],
        "refused": state["refused"],
        "tools_called": [e["tool"] for e in state["trace"] if e["node"] == "tools" and e["ok"]],
        "calls_used": state["calls_used"],
        "sources": [
            {k: s.get(k) for k in ("title", "source", "link")}
            for s in state["sources"]
        ],
        "grounding": state["grounding"],
        "latency_s": round(time.perf_counter() - t0, 2),
        "trace": state["trace"],
    }
