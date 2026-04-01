# storer.py — Store articles in ChromaDB vector store

import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent / "vectorstore")
COLLECTION_NAME = "tech_news"

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"  # fast, free, runs locally
)


def get_collection():
    """Get or create the ChromaDB collection."""
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )


def store_articles(articles):
    """Embed and store articles in ChromaDB. Skips duplicates by URL."""
    collection = get_collection()
    existing = set(collection.get()["ids"])

    new_docs, new_ids, new_metas = [], [], []

    for article in articles:
        # Use URL as unique ID
        doc_id = article.get("link", "")[:100]
        if not doc_id or doc_id in existing:
            continue

        # Text to embed: title + summary
        text = f"{article.get('title', '')}. {article.get('ai_summary', article.get('summary', ''))}"

        new_docs.append(text)
        new_ids.append(doc_id)
        new_metas.append({
            "title": article.get("title", "")[:200],
            "source": article.get("source", ""),
            "link": article.get("link", ""),
            "summary": article.get("ai_summary", article.get("summary", ""))[:500],
            "stored_at": datetime.now().isoformat(),
        })

    if new_docs:
        collection.add(documents=new_docs, ids=new_ids, metadatas=new_metas)
        print(f"[storer] Stored {len(new_docs)} new articles. Total in DB: {collection.count()}")
    else:
        print(f"[storer] No new articles to store. Total in DB: {collection.count()}")

    return len(new_docs)
