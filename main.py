# main.py — Orchestrator: run the full pipeline once

import os
import time
from dotenv import load_dotenv
from agents.fetcher import fetch_all
from agents.filter import filter_articles
from agents.summariser import summarise_all
from agents.emailer import send_email
from agents.storer import store_articles
from metrics.tracker import PipelineMetrics

load_dotenv()


def run():
    metrics = PipelineMetrics()

    print("=" * 50)
    print("Tech News Agent — Starting pipeline")
    print("=" * 50)

    # Step 1: Fetch
    articles = fetch_all()
    metrics.record_fetch_total(len(articles))

    # Step 2: Filter
    filtered = filter_articles(articles)
    metrics.record_filter(before=len(articles), after=len(filtered))

    if not filtered:
        print("[main] No relevant articles found today. Skipping email.")
        metrics.record_summarise(0, 0, 0, 0)
        metrics.record_email(False, os.getenv("RECIPIENT_EMAIL", ""), 0)
        metrics.finalise()
        return

    # Step 3: Summarise
    t0 = time.time()
    summarised = summarise_all(filtered)
    summarise_duration = time.time() - t0
    success = sum(1 for a in summarised if a.get("ai_summary"))
    metrics.record_summarise(
        total=len(summarised),
        success=success,
        failed=len(summarised) - success,
        duration_sec=summarise_duration,
    )

    # Step 4: Store in vector DB for RAG queries
    print("[main] Storing articles in vector database...")
    store_articles(summarised)

    # Step 5: Send Email
    email_ok = False
    try:
        send_email(summarised)
        email_ok = True
    except Exception as e:
        print(f"[main] Email failed: {e}")

    metrics.record_email(
        success=email_ok,
        recipient=os.getenv("RECIPIENT_EMAIL", ""),
        articles_sent=len(summarised),
    )
    metrics.finalise()


if __name__ == "__main__":
    run()
