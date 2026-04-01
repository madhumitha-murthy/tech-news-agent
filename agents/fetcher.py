# fetcher.py — Fetch articles from all sources

import feedparser
import requests
import praw
import arxiv
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config import RSS_FEEDS, ARXIV_CATEGORIES, ARXIV_MAX_RESULTS, REDDIT_SUBREDDITS, REDDIT_POST_LIMIT

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


def fetch_reddit():
    """Fetch top posts from ML/AI subreddits."""
    articles = []
    try:
        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "tech-news-agent/1.0"),
        )
        for subreddit_name in REDDIT_SUBREDDITS:
            subreddit = reddit.subreddit(subreddit_name)
            for post in subreddit.hot(limit=REDDIT_POST_LIMIT):
                if not post.stickied:
                    articles.append({
                        "source": f"Reddit r/{subreddit_name}",
                        "title": post.title,
                        "link": f"https://reddit.com{post.permalink}",
                        "summary": post.selftext[:300] if post.selftext else post.title,
                        "published": str(datetime.fromtimestamp(post.created_utc)),
                    })
    except Exception as e:
        print(f"[fetcher] Reddit error: {e}")

    return articles


def fetch_all():
    """Fetch from all sources and return combined list."""
    print("[fetcher] Fetching from RSS feeds...")
    rss = fetch_rss_feeds()

    print("[fetcher] Fetching from ArXiv...")
    arxiv_articles = fetch_arxiv()

    print("[fetcher] Fetching from Reddit...")
    reddit = fetch_reddit()

    all_articles = rss + arxiv_articles + reddit
    print(f"[fetcher] Total fetched: {len(all_articles)} articles")
    return all_articles
