"""
research_agent/grounding.py — Is the final answer supported by the sources?

The agent may only answer from articles its tools actually returned. We split
the answer into sentences and compare each one with every source (title +
summary) using sentence embeddings. A sentence counts as supported if its best
cosine similarity reaches SENTENCE_THRESHOLD. The answer passes if at least
ANSWER_THRESHOLD of its sentences are supported; otherwise the agent refuses.

Embedding similarity is a cheap, explainable proxy, not proof: it catches
answers that drift away from the sources, but it can't verify every detail.
"""

import os
import re
from functools import lru_cache
from typing import Callable

SENTENCE_THRESHOLD = float(os.getenv("GROUNDING_SENTENCE_THRESHOLD", "0.45"))
ANSWER_THRESHOLD = float(os.getenv("GROUNDING_ANSWER_THRESHOLD", "0.6"))
REFUSAL = "I couldn't find enough evidence in the sources I searched to answer that reliably."

# similarity(sentences, sources) -> one row of scores per sentence
Similarity = Callable[[list[str], list[str]], list[list[float]]]


@lru_cache(maxsize=1)
def _encoder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")  # same model the vector store uses


def embedding_similarity(sentences: list[str], sources: list[str]) -> list[list[float]]:
    model = _encoder()
    a = model.encode(sentences, normalize_embeddings=True)
    b = model.encode(sources, normalize_embeddings=True)
    return (a @ b.T).tolist()


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\[\d+\]", "", text)  # drop citation markers like [1]
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip(" -*•\t") for p in parts if len(p.strip(" -*•\t")) > 20]


def check_grounding(answer: str, sources: list[dict], similarity: Similarity = embedding_similarity) -> dict:
    """Return the grounding verdict plus the numbers behind it."""
    sentences = split_sentences(answer)
    source_texts = [f"{s.get('title', '')}. {s.get('summary', '')}" for s in sources]

    if not source_texts:
        return {"grounded": False, "reason": "no sources retrieved", "supported_fraction": 0.0, "sentences": 0}
    if not sentences:
        return {"grounded": False, "reason": "empty answer", "supported_fraction": 0.0, "sentences": 0}

    scores = similarity(sentences, source_texts)
    best = [max(row) for row in scores]
    supported = sum(1 for s in best if s >= SENTENCE_THRESHOLD)
    fraction = supported / len(sentences)
    return {
        "grounded": fraction >= ANSWER_THRESHOLD,
        "reason": "ok" if fraction >= ANSWER_THRESHOLD else "too few sentences supported by sources",
        "supported_fraction": round(fraction, 3),
        "sentences": len(sentences),
        "min_best_score": round(min(best), 3),
    }
