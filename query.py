# query.py — Interactive CLI to query stored articles using RAG

import os
from dotenv import load_dotenv
from google import genai
from agents.retriever import retrieve
from metrics.relevance_drift import log_query_scores, check_relevance_drift

load_dotenv()

MODEL = "gemini-2.0-flash"


def generate_answer(query: str, articles: list) -> str:
    """Use Gemini to generate a concise answer based on retrieved articles."""
    context = ""
    for i, a in enumerate(articles, 1):
        context += f"\n[{i}] {a['title']} ({a['source']})\n{a['summary']}\n"

    prompt = f"""You are a tech news assistant. Answer the user's question based ONLY on the articles below.
Be concise and cite article numbers like [1], [2] when referencing them.
If the articles don't contain relevant information, say so honestly.

Articles:
{context}

User question: {query}

Answer:"""

    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return response.text.strip()
    except Exception as e:
        # Fallback: just show the articles without AI answer
        return f"[Gemini unavailable: {e}]\n\nHere are the most relevant articles found:\n" + \
               "\n".join(f"- {a['title']} → {a['link']}" for a in articles)


def run_query(query: str):
    """Run a single RAG query."""
    print(f"\n🔍 Searching for: '{query}'")

    articles = retrieve(query, top_k=5)

    if not articles:
        print("No relevant articles found. Run 'python main.py' first to fetch articles.\n")
        return

    print(f"📚 Found {len(articles)} relevant articles\n")

    # Log retrieval scores and check for relevance drift
    scores = [a["score"] for a in articles]
    log_query_scores(query, scores)
    drift = check_relevance_drift()
    if drift["drift_detected"]:
        print(f"⚠️  [drift] {drift['message']}")
        print(f"   → {drift['recommendation']}\n")

    answer = generate_answer(query, articles)

    print("=" * 60)
    print("💬 Answer:")
    print("=" * 60)
    print(answer)
    print()
    print("=" * 60)
    print("📰 Sources:")
    print("=" * 60)
    for i, a in enumerate(articles, 1):
        print(f"[{i}] {a['title']}")
        print(f"     {a['source']} | Score: {a['score']}")
        print(f"     {a['link']}\n")


def main():
    """Interactive query loop."""
    print("\n🤖 Tech News Agent — RAG Query Interface")
    print("Type your question or 'quit' to exit.\n")

    while True:
        try:
            query = input("❓ Ask: ").strip()
            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            run_query(query)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
