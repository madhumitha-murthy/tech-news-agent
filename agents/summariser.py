# summariser.py — Summarize articles using Gemini API (free)

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")  # free tier model


def summarise_article(article):
    """Generate a 2-3 line summary of an article using Gemini."""
    prompt = f"""Summarize the following tech/AI article in exactly 2-3 concise sentences.
Focus on: what it is, why it matters, and any key numbers or facts.
Keep it simple and clear.

Title: {article['title']}
Content: {article['summary']}

Summary:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[summariser] Error summarising '{article['title']}': {e}")
        return article.get("summary", "")[:200] + "..."


def summarise_all(articles):
    """Summarize all articles."""
    print(f"[summariser] Summarising {len(articles)} articles...")
    for i, article in enumerate(articles):
        print(f"[summariser] {i+1}/{len(articles)}: {article['title'][:60]}...")
        article["ai_summary"] = summarise_article(article)
    return articles
