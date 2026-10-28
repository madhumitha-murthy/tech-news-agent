# tools.py - Tool definitions for the research agent
# Each tool = a function + JSON schema that Gemini sees

from dataclasses import dataclass
from typing import Any, Callable

MAX_RESULTS = 10

# Tools whose output counts as citable evidence
SOURCE_TOOLS = {"search_articles", "search_arxiv", "compare_articles"}


@dataclass
class Tool:
    name: str
    description: str
    params_schema: dict
    fn: Callable[..., Any]


# --- Tool implementations ---

def search_articles(query: str, top_k: int = 5) -> list[dict]:
    from pipeline.retriever import retrieve
    return retrieve(query, top_k=max(1, min(int(top_k), MAX_RESULTS)))


def search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    import arxiv
    from config import ARXIV_CATEGORIES

    cat_filter = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    search = arxiv.Search(
        query=f"({query}) AND ({cat_filter})",
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
    from pipeline.summariser import summarise_article
    return summarise_article({"title": "", "summary": text})


def compare_articles(titles: list[str]) -> list[dict]:
    from pipeline.retriever import retrieve
    results = []
    for t in titles[:3]:
        hits = retrieve(t, top_k=1)
        if hits:
            results.append(hits[0])
    return results


# --- Tool registry ---

TOOLS: dict[str, Tool] = {
    "search_articles": Tool(
        name="search_articles",
        description="Search stored tech/AI news articles. Use this first for news questions.",
        params_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top_k": {"type": "integer", "description": "Number of results (1-10)"},
            },
            "required": ["query"],
        },
        fn=search_articles,
    ),
    "search_arxiv": Tool(
        name="search_arxiv",
        description="Search ArXiv for recent AI/ML/NLP research papers.",
        params_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Research topic"},
                "max_results": {"type": "integer", "description": "Number of papers (1-10)"},
            },
            "required": ["query"],
        },
        fn=search_arxiv,
    ),
    "summarise": Tool(
        name="summarise",
        description="Summarise a long text into 2-3 sentences using Gemini.",
        params_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarise"},
            },
            "required": ["text"],
        },
        fn=summarise,
    ),
    "compare_articles": Tool(
        name="compare_articles",
        description="Fetch 2-3 stored articles by title for side-by-side comparison.",
        params_schema={
            "type": "object",
            "properties": {
                "titles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Article titles to look up",
                },
            },
            "required": ["titles"],
        },
        fn=compare_articles,
    ),
}


def validate_args(tool: Tool, args: dict) -> str | None:
    """Check required args exist and types are roughly correct. Returns error string or None."""
    schema = tool.params_schema
    props = schema.get("properties", {})

    for req in schema.get("required", []):
        if req not in args:
            return f"Missing required arg '{req}' for {tool.name}"

    for key, val in args.items():
        if key not in props:
            return f"Unknown arg '{key}' for {tool.name}"
        expected = props[key].get("type", "")
        if expected == "string" and (not isinstance(val, str) or not val.strip()):
            return f"Arg '{key}' must be a non-empty string"
        if expected == "integer" and not isinstance(val, (int, float)):
            return f"Arg '{key}' must be an integer"
        if expected == "array" and (not isinstance(val, list) or not val):
            return f"Arg '{key}' must be a non-empty list"

    return None
