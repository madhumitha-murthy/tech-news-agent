# metrics/evaluator.py — Evaluate pipeline runs from saved metrics logs

import json
from pathlib import Path
from datetime import datetime

METRICS_DIR = Path(__file__).parent / "data"


def load_all_runs():
    """Load all saved metric runs."""
    runs = []
    for f in sorted(METRICS_DIR.glob("run_*.json")):
        with open(f) as fp:
            runs.append(json.load(fp))
    return runs


def evaluate():
    """Print a summary evaluation across all runs."""
    runs = load_all_runs()
    if not runs:
        print("[evaluator] No runs found.")
        return

    total_runs = len(runs)
    success_runs = sum(1 for r in runs if r["pipeline"].get("status") == "success")
    avg_articles = sum(r["filter"].get("articles_after", 0) for r in runs) / total_runs
    avg_duration = sum(r["pipeline"].get("total_duration_sec", 0) for r in runs) / total_runs
    avg_summary_rate = sum(r["summarise"].get("success_rate", 0) for r in runs) / total_runs

    print("\n" + "=" * 50)
    print("PIPELINE EVALUATION REPORT")
    print("=" * 50)
    print(f"  Total runs        : {total_runs}")
    print(f"  Success rate      : {round(success_runs / total_runs * 100, 1)}%")
    print(f"  Avg articles/run  : {round(avg_articles, 1)}")
    print(f"  Avg duration      : {round(avg_duration, 1)}s")
    print(f"  Avg summary rate  : {round(avg_summary_rate, 1)}%")
    print("=" * 50)

    # Per-source fetch averages
    source_counts = {}
    for r in runs:
        for source, count in r["fetch"].items():
            if source != "total":
                source_counts.setdefault(source, []).append(count)

    print("\n  Avg articles per source:")
    for source, counts in sorted(source_counts.items()):
        print(f"    {source:<25} {round(sum(counts)/len(counts), 1)}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    evaluate()
