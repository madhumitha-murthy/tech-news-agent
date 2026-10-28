# grounding.py - Check if the agent's answer is supported by retrieved sources
#
# Split the answer into sentences, compare each against source texts via
# sentence embeddings. If too few sentences are supported -> refuse.

import os
import re
from functools import lru_cache
from typing import Callable

SENT_THRESHOLD = float(os.getenv("GROUNDING_SENTENCE_THRESHOLD", "0.45"))
ANSWER_THRESHOLD = float(os.getenv("GROUNDING_ANSWER_THRESHOLD", "0.6"))
REFUSAL = "I couldn't find enough evidence in the sources to answer that reliably."

Similarity = Callable[[list[str], list[str]], list[list[float]]]


@lru_cache(maxsize=1)
def _get_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def embedding_similarity(sentences: list[str], sources: list[str]) -> list[list[float]]:
    enc = _get_encoder()
    a = enc.encode(sentences, normalize_embeddings=True)
    b = enc.encode(sources, normalize_embeddings=True)
    return (a @ b.T).tolist()


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\[\d+\]", "", text)  # strip citation markers
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip(" -*\t") for p in parts if len(p.strip(" -*\t")) > 20]


def check_grounding(answer: str, sources: list[dict], similarity: Similarity = embedding_similarity) -> dict:
    sentences = split_sentences(answer)
    source_texts = [f"{s.get('title', '')}. {s.get('summary', '')}" for s in sources]

    if not source_texts:
        return {"grounded": False, "reason": "no sources retrieved", "supported_fraction": 0.0, "sentences": 0}
    if not sentences:
        return {"grounded": False, "reason": "empty answer", "supported_fraction": 0.0, "sentences": 0}

    scores = similarity(sentences, source_texts)
    best_per_sent = [max(row) for row in scores]
    n_supported = sum(1 for s in best_per_sent if s >= SENT_THRESHOLD)
    frac = n_supported / len(sentences)

    return {
        "grounded": frac >= ANSWER_THRESHOLD,
        "reason": "ok" if frac >= ANSWER_THRESHOLD else "too few sentences supported",
        "supported_fraction": round(frac, 3),
        "sentences": len(sentences),
        "min_best_score": round(min(best_per_sent), 3),
    }
