"""
metrics/relevance_drift.py — Retrieval relevance drift detection for the RAG query interface.

How it works
------------
Each time the RAG query interface retrieves articles, the cosine similarity scores
(1 - ChromaDB distance) represent how semantically aligned the indexed content is
with the query.  As the article corpus ages or topic coverage shifts, these scores
can drift downward — a signal that the ChromaDB index should be refreshed.

This module:
1. Logs per-query relevance scores to metrics/data/relevance_*.json
2. Builds a baseline from the first BASELINE_RUNS query runs
3. Flags drift when the rolling mean score drops > DRIFT_THRESHOLD_SIGMAS
   standard deviations below the baseline mean

Usage (in query.py)
-------------------
    from metrics.relevance_drift import log_query_scores, check_relevance_drift

    articles = retrieve(query, top_k=5)
    log_query_scores(query, [a["score"] for a in articles])
    drift = check_relevance_drift()
    if drift["drift_detected"]:
        print(f"[drift] {drift['message']}")
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

METRICS_DIR = Path(__file__).parent / "data"
BASELINE_RUNS = int(os.getenv("DRIFT_BASELINE_RUNS", "5"))    # runs used to build baseline
ROLLING_WINDOW = int(os.getenv("DRIFT_ROLLING_WINDOW", "5"))  # recent runs to compare
DRIFT_THRESHOLD_SIGMAS = float(os.getenv("DRIFT_SIGMA_THRESHOLD", "2.0"))

METRICS_DIR.mkdir(parents=True, exist_ok=True)


def log_query_scores(query: str, scores: list[float]) -> None:
    """
    Persist retrieval scores for a single query to metrics/data/relevance_*.json.

    Parameters
    ----------
    query  : the user's question string
    scores : list of cosine similarity scores (1 - ChromaDB distance) for retrieved articles
    """
    if not scores:
        return

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "scores": [round(s, 4) for s in scores],
        "mean_score": round(mean(scores), 4),
        "n_retrieved": len(scores),
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    path = METRICS_DIR / f"relevance_{ts}.json"
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2)


def _load_relevance_runs() -> list[dict]:
    """Load all saved relevance records in chronological order."""
    files = sorted(METRICS_DIR.glob("relevance_*.json"))
    runs = []
    for f in files:
        try:
            with open(f) as fh:
                runs.append(json.load(fh))
        except (json.JSONDecodeError, KeyError):
            continue
    return runs


def check_relevance_drift() -> dict:
    """
    Check whether retrieval relevance scores have drifted from the baseline.

    Returns a dict with:
        drift_detected  : bool
        message         : human-readable explanation
        baseline_mean   : float or None
        recent_mean     : float or None
        shift_sigmas    : float or None (negative = scores dropped)
        recommendation  : str
    """
    runs = _load_relevance_runs()
    n = len(runs)

    if n < BASELINE_RUNS + 1:
        return {
            "drift_detected": False,
            "message": f"Accumulating baseline ({n}/{BASELINE_RUNS} runs recorded). No drift check yet.",
            "baseline_mean": None,
            "recent_mean": None,
            "shift_sigmas": None,
            "recommendation": "Continue running queries to build a baseline.",
        }

    # Baseline: mean of per-run mean_scores from the first BASELINE_RUNS runs
    baseline_scores = [r["mean_score"] for r in runs[:BASELINE_RUNS]]
    baseline_mean = mean(baseline_scores)
    baseline_std = stdev(baseline_scores) if len(baseline_scores) > 1 else 0.01
    baseline_std = max(baseline_std, 1e-4)  # guard divide-by-zero

    # Recent window: last ROLLING_WINDOW runs
    recent_scores = [r["mean_score"] for r in runs[-ROLLING_WINDOW:]]
    recent_mean = mean(recent_scores)

    shift_sigmas = (recent_mean - baseline_mean) / baseline_std
    drift_detected = shift_sigmas < -DRIFT_THRESHOLD_SIGMAS

    if drift_detected:
        message = (
            f"RELEVANCE DRIFT DETECTED — recent mean score {recent_mean:.3f} is "
            f"{abs(shift_sigmas):.1f}σ below baseline {baseline_mean:.3f}. "
            f"Indexed articles may no longer match query topics."
        )
        recommendation = "Re-run main.py to refresh the ChromaDB index with recent articles."
    else:
        message = (
            f"No drift — recent mean {recent_mean:.3f} vs baseline {baseline_mean:.3f} "
            f"({shift_sigmas:+.2f}σ)."
        )
        recommendation = "Index is healthy."

    return {
        "drift_detected": drift_detected,
        "message": message,
        "baseline_mean": round(baseline_mean, 4),
        "recent_mean": round(recent_mean, 4),
        "shift_sigmas": round(shift_sigmas, 3),
        "n_runs_total": n,
        "recommendation": recommendation,
    }
