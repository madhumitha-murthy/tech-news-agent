# test_research_agent.py - Agent loop tests using scripted model (no API calls)

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from research_agent.graph import build_agent, run_question
from research_agent.grounding import REFUSAL, check_grounding, split_sentences
from research_agent.llm import FakeModel, ModelResponse
from research_agent.tools import TOOLS, Tool, validate_args

SAMPLE_ARTICLE = {
    "title": "Lab releases open agent framework",
    "source": "TechCrunch AI",
    "link": "https://example.com/agent-framework",
    "summary": "An AI lab released an open-source framework for building tool-using agents.",
}


def make_test_tools(log):
    """Create fake tools that log calls instead of hitting real APIs."""
    def search(query, top_k=5):
        log.append(("search_articles", query))
        return [SAMPLE_ARTICLE]

    def broken_tool(text):
        raise RuntimeError("service down")

    return {
        "search_articles": Tool("search_articles", "search", TOOLS["search_articles"].params_schema, search),
        "summarise": Tool("summarise", "summarise", TOOLS["summarise"].params_schema, broken_tool),
    }


def high_sim(sentences, sources):
    return [[0.9 for _ in sources] for _ in sentences]


def low_sim(sentences, sources):
    return [[0.1 for _ in sources] for _ in sentences]


GOOD_ANSWER = "An AI lab released an open-source framework for building tool-using agents."


def test_agent_calls_tool_then_answers():
    log = []
    model = FakeModel([
        ModelResponse(tool_calls=[{"name": "search_articles", "args": {"query": "agent framework"}}]),
        ModelResponse(text=GOOD_ANSWER),
    ])
    result = run_question(build_agent(model, make_test_tools(log), high_sim), "New agent frameworks?")

    assert log == [("search_articles", "agent framework")]
    assert result["tools_called"] == ["search_articles"]
    assert result["refused"] is False
    assert result["answer"] == GOOD_ANSWER
    assert result["sources"][0]["link"] == SAMPLE_ARTICLE["link"]
    assert model.calls[1]["messages"][-1]["role"] == "tool"


def test_step_limit_stops_loop():
    log = []
    always_search = ModelResponse(tool_calls=[{"name": "search_articles", "args": {"query": "x"}}])
    model = FakeModel([always_search], repeat_last=True)
    result = run_question(build_agent(model, make_test_tools(log), high_sim), "loop?", max_calls=3)

    assert result["calls_used"] == 3
    assert len(log) == 3
    assert model.calls[-1]["tools"] == []  # no tools offered after budget spent


def test_ungrounded_answer_refused():
    model = FakeModel([
        ModelResponse(tool_calls=[{"name": "search_articles", "args": {"query": "q"}}]),
        ModelResponse(text="The framework was acquired for ten billion dollars by a bank."),
    ])
    result = run_question(build_agent(model, make_test_tools([]), low_sim), "q")
    assert result["refused"] is True
    assert result["answer"] == REFUSAL


def test_no_sources_means_refusal():
    model = FakeModel([ModelResponse(text="Here is an answer from memory with no tools.")])
    result = run_question(build_agent(model, make_test_tools([]), high_sim), "q")
    assert result["refused"] is True
    assert result["grounding"]["reason"] == "no sources retrieved"


def test_unknown_and_broken_tools_dont_crash():
    model = FakeModel([
        ModelResponse(tool_calls=[
            {"name": "delete_database", "args": {}},
            {"name": "summarise", "args": {"text": "some text"}},
        ]),
        ModelResponse(text="Could not complete that request."),
    ])
    result = run_question(build_agent(model, make_test_tools([]), high_sim), "q")
    errors = [e["error"] for e in result["trace"] if e["node"] == "tools"]
    assert "Unknown tool 'delete_database'" in errors
    assert any("service down" in e for e in errors)
    assert result["refused"] is True


def test_validate_args():
    tool = TOOLS["search_articles"]
    assert validate_args(tool, {"query": "agents"}) is None
    assert "Missing required" in validate_args(tool, {})
    assert "Unknown arg" in validate_args(tool, {"query": "a", "limit": 3})
    assert "non-empty string" in validate_args(tool, {"query": ""})


def test_grounding_fraction():
    answer = "First sentence about agent frameworks here. Second sentence about something unrelated."

    def mixed_sim(sentences, sources):
        return [[0.9], [0.1]]

    verdict = check_grounding(answer, [SAMPLE_ARTICLE], mixed_sim)
    assert verdict["supported_fraction"] == 0.5
    assert verdict["grounded"] is False


def test_split_sentences():
    text = "Agents can now call tools reliably [1]. Ok.\n- Another full sentence about LLM agents."
    result = split_sentences(text)
    assert "Agents can now call tools reliably ." in result
    assert "Another full sentence about LLM agents." in result
    assert len(result) == 2  # "Ok." is too short, gets dropped


def test_compute_metrics():
    from eval.run_eval import compute_metrics

    base = {"calls_used": 1, "latency_s": 2.0, "supported_fraction": 1.0, "error": None}
    records = [
        {**base, "answerable": True, "expected_tools": ["search_articles"],
         "tools_called": ["search_articles"], "refused": False},
        {**base, "answerable": True, "expected_tools": ["search_arxiv"],
         "tools_called": ["search_articles"], "refused": True},
        {**base, "answerable": False, "expected_tools": [],
         "tools_called": [], "refused": True},
    ]
    m = compute_metrics(records)
    assert m["grounded_answer_rate"] == 0.5
    assert m["false_refusal_rate"] == 0.5
    assert m["correct_refusal_rate"] == 1.0
    assert m["tool_selection_accuracy"] == 0.5
