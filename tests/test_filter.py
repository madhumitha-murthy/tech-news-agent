# tests/test_filter.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.filter import score_article, filter_articles


SAMPLE_ARTICLES = [
    {"title": "New LLM from OpenAI beats GPT-4", "summary": "OpenAI releases a new large language model."},
    {"title": "Singapore tech scene booms in 2025", "summary": "Singapore AI startup funding hits record highs."},
    {"title": "Recipe: How to bake a chocolate cake", "summary": "Mix flour, eggs, sugar and cocoa."},
    {"title": "Agentic AI frameworks compared", "summary": "LangGraph vs CrewAI for building AI agents with NLP."},
]


def test_score_relevant_article():
    article = {"title": "New LLM research", "summary": "Large language model fine-tuning with LoRA."}
    assert score_article(article) > 0


def test_score_irrelevant_article():
    article = {"title": "Best chocolate cake recipe", "summary": "Bake at 180 degrees for 30 minutes."}
    assert score_article(article) == 0


def test_filter_removes_irrelevant():
    results = filter_articles(SAMPLE_ARTICLES)
    titles = [a["title"] for a in results]
    assert "Recipe: How to bake a chocolate cake" not in titles


def test_filter_keeps_relevant():
    results = filter_articles(SAMPLE_ARTICLES)
    titles = [a["title"] for a in results]
    assert any("LLM" in t or "AI" in t or "Singapore" in t for t in titles)


def test_filter_sorted_by_score():
    results = filter_articles(SAMPLE_ARTICLES)
    scores = [a["score"] for a in results]
    assert scores == sorted(scores, reverse=True)


def test_filter_respects_top_n(monkeypatch):
    import config
    monkeypatch.setattr(config, "TOP_N", 2)
    # reload filter to pick up patched TOP_N
    import importlib
    import agents.filter as f_module
    importlib.reload(f_module)
    results = f_module.filter_articles(SAMPLE_ARTICLES * 10)
    assert len(results) <= 2
