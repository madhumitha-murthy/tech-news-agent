# filter.py — Filter articles by relevance to defined topics

from config import TOPICS, TOP_N


def score_article(article):
    """Score an article based on how many topic keywords it matches."""
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    score = sum(1 for topic in TOPICS if topic.lower() in text)
    return score


def filter_articles(articles):
    """Filter and rank articles by topic relevance, return top N."""
    scored = []
    for article in articles:
        score = score_article(article)
        if score > 0:
            scored.append({**article, "score": score})

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    top = scored[:TOP_N]
    print(f"[filter] {len(scored)} relevant articles found, returning top {len(top)}")
    return top
