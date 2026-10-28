# tests/test_research_agent.py — agent loop tests with a scripted model (no API calls)

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from research_agent.graph import build_agent, run_question
from research_agent.grounding import REFUSAL, check_grounding, split_sentences
from research_agent.llm import FakeModel, ModelTurn
from research_agent.tools import TOOLS, Tool, validate_args

ARTICLE = {
    "title": "Lab releases open agent framework",
    "source": "TechCrunch AI",
    "link": "https://example.com/agent-framework",
    "summary": "An AI lab released an open-source framework for building tool-using agents.",
}


def fake_tools(calls_log):
    def search(query, top_k=5):
        calls_log.append(("search_articles", query))
        return [ARTICLE]

    def broken(text):
        raise RuntimeError("service down")

    return {
        "search_articles": Tool("search_articles", "search", TOOLS["search_articles"].parameters, search, True),
        "summarise": Tool("summarise", "summarise", TOOLS["summarise"].parameters, broken),
    }


def high_similarity(sentences, sources):
    return [[0.9 for _ in sources] for _ in sentences]


def low_similarity(sentences, sources):
    return [[0.1 for _ in sources] for _ in sentences]


GOOD_ANSWER = "An AI lab released an open-source framework for building tool-using agents."


def test_agent_calls_tool_then_answers():
    log = []
    model = FakeModel([
        ModelTurn(tool_calls=[{"name": "search_articles", "args": {"query": "agent framework"}}]),
        ModelTurn(text=GOOD_ANSWER),
    ])
    result = run_question(build_agent(model, fake_tools(log), high_similarity), "Any new agent frameworks?")

    assert log == [("search_articles", "agent framework")]
    assert result["tools_called"] == ["search_articles"]
    assert result["refused"] is False
    assert result["answer"] == GOOD_ANSWER
    assert result["sources"][0]["link"] == ARTICLE["link"]
    # the tool result was sent back to the model on its second turn
    assert model.calls[1]["messages"][-1]["role"] == "tool"


def test_step_limit_stops_the_loop():
    log = []
    always_search = ModelTurn(tool_calls=[{"name": "search_articles", "args": {"query": "x"}}])
    model = FakeModel([always_search], repeat_last=True)
    result = run_question(build_agent(model, fake_tools(log), high_similarity), "loop?", max_tool_calls=3)

    assert result["tool_calls_made"] == 3
    assert len(log) == 3
    # after the budget is spent, the model is called without tools
    assert model.calls[-1]["tools"] == []


def test_ungrounded_answer_is_refused():
    model = FakeModel([
        ModelTurn(tool_calls=[{"name": "search_articles", "args": {"query": "q"}}]),
        ModelTurn(text="The framework was acquired for ten billion dollars by a bank."),
    ])
    result = run_question(build_agent(model, fake_tools([]), low_similarity), "q")
    assert result["refused"] is True
    assert result["answer"] == REFUSAL


def test_answer_without_sources_is_refused():
    model = FakeModel([ModelTurn(text="Here is an answer from memory with no tools used at all.")])
    result = run_question(build_agent(model, fake_tools([]), high_similarity), "q")
    assert result["refused"] is True
    assert result["grounding"]["reason"] == "no sources retrieved"


def test_unknown_tool_and_failures_are_reported_not_raised():
    model = FakeModel([
        ModelTurn(tool_calls=[
            {"name": "delete_database", "args": {}},
            {"name": "summarise", "args": {"text": "long text"}},
        ]),
        ModelTurn(text="I could not complete that request with the available tools."),
    ])
    result = run_question(build_agent(model, fake_tools([]), high_similarity), "q")
    errors = [e["error"] for e in result["trace"] if e["node"] == "tools"]
    assert "Unknown tool 'delete_database'." in errors
    assert any("service down" in e for e in errors)
    assert result["refused"] is True  # nothing to ground the answer in


def test_validate_args():
    tool = TOOLS["search_articles"]
    assert validate_args(tool, {"query": "agents"}) is None
    assert "Missing required" in validate_args(tool, {})
    assert "Unknown argument" in validate_args(tool, {"query": "a", "limit": 3})
    assert "non-empty string" in validate_args(tool, {"query": ""})


def test_grounding_fraction():
    answer = "First sentence about agent frameworks here. Second sentence about something else entirely."

    def mixed(sentences, sources):
        return [[0.9], [0.1]]

    verdict = check_grounding(answer, [ARTICLE], mixed)
    assert verdict["supported_fraction"] == 0.5
    assert verdict["grounded"] is False  # below the 0.6 threshold


def test_split_sentences_drops_citations_and_short_fragments():
    text = "Agents can now call tools reliably [1]. Ok.\n- Another full sentence about LLM agents."
    assert split_sentences(text) == [
        "Agents can now call tools reliably .",
        "Another full sentence about LLM agents.",
    ]


def test_compute_metrics():
    from eval.run_eval import compute_metrics

    base = {"tool_calls_made": 1, "latency_s": 2.0, "supported_fraction": 1.0, "error": None}
    records = [
        {**base, "answerable": True, "expected_tools": ["search_articles"], "tools_called": ["search_articles"], "refused": False},
        {**base, "answerable": True, "expected_tools": ["search_arxiv"], "tools_called": ["search_articles"], "refused": True},
        {**base, "answerable": False, "expected_tools": [], "tools_called": [], "refused": True},
    ]
    m = compute_metrics(records)
    assert m["grounded_answer_rate"] == 0.5
    assert m["false_refusal_rate"] == 0.5
    assert m["correct_refusal_rate"] == 1.0
    assert m["tool_selection_accuracy"] == 0.5
