# fetcher.py — Fetch articles from all sources

import feedparser
import arxiv
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config import RSS_FEEDS, ARXIV_MAX_RESULTS

load_dotenv()

def fetch_rss_feeds():
    """Fetch articles from all RSS feeds."""
    articles = []
    cutoff = datetime.now() - timedelta(hours=24)

    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                articles.append({
                    "source": source,
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "published": entry.get("published", ""),
                })
        except Exception as e:
            print(f"[fetcher] Error fetching {source}: {e}")

    return articles


def fetch_arxiv():
    """Fetch latest AI/ML papers from ArXiv."""
    articles = []
    try:
        search = arxiv.Search(
            query="artificial intelligence OR large language model OR NLP OR agentic AI",
            max_results=ARXIV_MAX_RESULTS,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )
        for result in search.results():
            articles.append({
                "source": "ArXiv",
                "title": result.title,
                "link": result.entry_id,
                "summary": result.summary[:300] + "...",
                "published": str(result.published),
            })
    except Exception as e:
        print(f"[fetcher] ArXiv error: {e}")

    return articles


def fetch_all():
    """Fetch from all sources and return combined list."""
    print("[fetcher] Fetching from RSS feeds...")
    rss = fetch_rss_feeds()

    print("[fetcher] Fetching from ArXiv...")
    arxiv_articles = fetch_arxiv()

    all_articles = rss + arxiv_articles
    print(f"[fetcher] Total fetched: {len(all_articles)} articles")
    return all_articles
