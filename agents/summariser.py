# summariser.py — Summarize articles using Gemini API (free)

import os
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-2.0-flash"


def summarise_article(article):
    """Generate a 2-3 line summary of an article using Gemini."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"""Summarize the following tech/AI article in exactly 2-3 concise sentences.
Focus on: what it is, why it matters, and any key numbers or facts.
Keep it simple and clear.

Title: {article['title']}
Content: {article['summary']}

Summary:"""

    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[summariser] Error summarising '{article['title']}': {e}")
        return article.get("summary", "")[:200] + "..."


def summarise_all(articles):
    """Summarize all articles with delay to respect free tier rate limits."""
    print(f"[summariser] Summarising {len(articles)} articles...")
    for i, article in enumerate(articles):
        print(f"[summariser] {i+1}/{len(articles)}: {article['title'][:60]}...")
        article["ai_summary"] = summarise_article(article)
        time.sleep(4)  # free tier: 15 req/min → 1 request per 4s
    return articles
