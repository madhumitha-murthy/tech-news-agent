# retriever.py — Semantic search over stored articles using ChromaDB

from agents.storer import get_collection


def retrieve(query: str, top_k: int = 5):
    """Search ChromaDB for articles semantically similar to the query."""
    collection = get_collection()

    if collection.count() == 0:
        print("[retriever] Vector store is empty. Run main.py first to fetch and store articles.")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
    )

    articles = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        articles.append({
            "title": meta.get("title", ""),
            "source": meta.get("source", ""),
            "link": meta.get("link", ""),
            "summary": meta.get("summary", ""),
            "score": round(1 - results["distances"][0][i], 3),  # cosine similarity
        })

    return articles
