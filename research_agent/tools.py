"""
research_agent/tools.py — The tools the research agent can call.

Each tool is a plain Python function plus a JSON-schema description. The model
only ever sees the description; our code (graph.py) runs the function and sends
the result back. Heavy imports (ChromaDB, arxiv, Gemini) happen inside the
functions so tests can run without them.
"""

from dataclasses import dataclass
from typing import Any, Callable

MAX_RESULTS = 10  # upper bound on results per call, whatever the model asks for


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema for the arguments
    func: Callable[..., Any]
    returns_sources: bool = False  # True if results are articles usable as evidence


# ── Tool functions ────────────────────────────────────────────────────────────

def search_articles(query: str, top_k: int = 5) -> list[dict]:
    """Semantic search over articles stored by the daily pipeline (ChromaDB)."""
    from agents.retriever import retrieve

    return retrieve(query, top_k=max(1, min(int(top_k), MAX_RESULTS)))


def search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """Live search of recent ArXiv papers in the configured AI categories."""
    import arxiv

    from config import ARXIV_CATEGORIES

    categories = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    search = arxiv.Search(
        query=f"({query}) AND ({categories})",
        max_results=max(1, min(int(max_results), MAX_RESULTS)),
        sort_by=arxiv.SortCriterion.Relevance,
    )
    return [
        {
            "title": r.title,
            "source": "ArXiv",
            "link": r.entry_id,
            "summary": r.summary[:500],
            "published": str(r.published.date()),
        }
        for r in arxiv.Client().results(search)
    ]


def summarise(text: str) -> str:
    """Summarise a piece of text in 2-3 sentences with Gemini."""
    from agents.summariser import summarise_article

    return summarise_article({"title": "", "summary": text})


def compare_articles(titles: list[str]) -> list[dict]:
    """Look up 2-3 stored articles by title and return them side by side.

    The comparison itself is written by the agent from these results; this tool
    only fetches the best match for each title.
    """
    from agents.retriever import retrieve

    found = []
    for title in titles[:3]:
        matches = retrieve(title, top_k=1)
        if matches:
            found.append(matches[0])
    return found


# ── Registry ──────────────────────────────────────────────────────────────────

TOOLS: dict[str, Tool] = {
    "search_articles": Tool(
        name="search_articles",
        description=(
            "Search the tech-news articles collected by the daily pipeline "
            "(blogs, tech news sites, ArXiv). Use this first for questions about "
            "recent AI and tech news."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for."},
                "top_k": {"type": "integer", "description": "Number of results, 1-10."},
            },
            "required": ["query"],
        },
        func=search_articles,
        returns_sources=True,
    ),
    "search_arxiv": Tool(
        name="search_arxiv",
        description=(
            "Search ArXiv live for research papers in AI, NLP and machine learning. "
            "Use this for questions about research papers or when stored articles "
            "don't cover a research topic."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Research topic keywords."},
                "max_results": {"type": "integer", "description": "Number of papers, 1-10."},
            },
            "required": ["query"],
        },
        func=search_arxiv,
        returns_sources=True,
    ),
    "summarise": Tool(
        name="summarise",
        description="Summarise a long piece of text into 2-3 sentences.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Text to summarise."}},
            "required": ["text"],
        },
        func=summarise,
    ),
    "compare_articles": Tool(
        name="compare_articles",
        description=(
            "Fetch 2-3 stored articles by their titles, side by side, so you can "
            "compare them. Use after search_articles has found the titles."
        ),
        parameters={
            "type": "object",
            "properties": {
                "titles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "2-3 article titles to compare.",
                }
            },
            "required": ["titles"],
        },
        func=compare_articles,
        returns_sources=True,
    ),
}


def validate_args(tool: Tool, args: dict) -> str | None:
    """Return an error message if required arguments are missing or mistyped."""
    props = tool.parameters.get("properties", {})
    for name in tool.parameters.get("required", []):
        if name not in args:
            return f"Missing required argument '{name}' for {tool.name}."
    for name, value in args.items():
        if name not in props:
            return f"Unknown argument '{name}' for {tool.name}."
        expected = props[name]["type"]
        ok = {
            "string": isinstance(value, str) and value.strip() != "",
            "integer": isinstance(value, (int, float)),
            "array": isinstance(value, list) and len(value) > 0,
        }.get(expected, True)
        if not ok:
            return f"Argument '{name}' for {tool.name} must be a non-empty {expected}."
    return None
