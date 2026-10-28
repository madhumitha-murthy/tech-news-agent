"""
eval/run_eval.py — Evaluate the research agent on eval/questions.json.

    python -m eval.run_eval

Writes results/metrics.json (summary) and results/eval_details.csv (one row per
question, including the answer, so you can also judge correctness by hand).

What the metrics mean
---------------------
- grounded_answer_rate:  answerable questions that got a grounded (non-refused) answer
- correct_refusal_rate:  out-of-scope questions the agent correctly refused
- tool_selection_accuracy: questions where every expected tool was called
- false_refusal_rate:    answerable questions the agent refused
These measure behaviour, not factual correctness. Read the answers in the CSV
to judge correctness yourself.
"""

import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
QUESTIONS = Path(__file__).parent / "questions.json"
RESULTS_DIR = ROOT / "results"
SLEEP_S = float(os.getenv("EVAL_SLEEP_S", "10"))  # free-tier rate limit


def compute_metrics(records: list[dict]) -> dict:
    """Summarise per-question records. Pure function, so it can be unit-tested."""
    answerable = [r for r in records if r["answerable"]]
    unanswerable = [r for r in records if not r["answerable"]]
    with_tools = [r for r in records if r["expected_tools"]]
    completed = [r for r in records if not r.get("error")]

    def rate(items, cond):
        return round(sum(1 for r in items if cond(r)) / len(items), 3) if items else None

    grounded = [r for r in answerable if not r["refused"] and not r.get("error")]
    return {
        "questions": len(records),
        "errors": len(records) - len(completed),
        "grounded_answer_rate": rate(answerable, lambda r: not r["refused"] and not r.get("error")),
        "correct_refusal_rate": rate(unanswerable, lambda r: r["refused"]),
        "false_refusal_rate": rate(answerable, lambda r: r["refused"]),
        "tool_selection_accuracy": rate(with_tools, lambda r: set(r["expected_tools"]) <= set(r["tools_called"])),
        "avg_tool_calls": round(mean(r["tool_calls_made"] for r in completed), 2) if completed else None,
        "avg_latency_s": round(mean(r["latency_s"] for r in completed), 2) if completed else None,
        "avg_supported_fraction": round(mean(r["supported_fraction"] for r in grounded), 3) if grounded else None,
    }


def main() -> None:
    load_dotenv()
    from agents.storer import get_collection
    from research_agent.graph import DEFAULT_MAX_TOOL_CALLS, build_agent, run_question
    from research_agent.grounding import ANSWER_THRESHOLD, SENTENCE_THRESHOLD
    from research_agent.llm import DEFAULT_MODEL, GeminiModel

    questions = json.loads(QUESTIONS.read_text())
    agent = build_agent(GeminiModel())
    records = []

    for i, q in enumerate(questions, 1):
        print(f"[eval] {i}/{len(questions)} {q['id']}: {q['question']}")
        record = {**q, "answer": "", "refused": False, "tools_called": [], "tool_calls_made": 0,
                  "latency_s": 0.0, "supported_fraction": 0.0, "error": None}
        for attempt in range(2):
            try:
                result = run_question(agent, q["question"])
                record.update({
                    "answer": result["answer"],
                    "refused": result["refused"],
                    "tools_called": result["tools_called"],
                    "tool_calls_made": result["tool_calls_made"],
                    "latency_s": result["latency_s"],
                    "supported_fraction": result["grounding"].get("supported_fraction", 0.0),
                    "error": None,
                })
                break
            except Exception as exc:  # e.g. rate limit; retry once after a pause
                record["error"] = str(exc)[:200]
                print(f"[eval]   error: {record['error']}")
                time.sleep(30)
        records.append(record)
        time.sleep(SLEEP_S)

    metrics = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": DEFAULT_MODEL,
        "max_tool_calls": DEFAULT_MAX_TOOL_CALLS,
        "grounding_thresholds": {"sentence": SENTENCE_THRESHOLD, "answer": ANSWER_THRESHOLD},
        "articles_in_vector_store": get_collection().count(),
        **compute_metrics(records),
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    with (RESULTS_DIR / "eval_details.csv").open("w", newline="") as f:
        fields = ["id", "category", "question", "answerable", "expected_tools", "tools_called",
                  "refused", "supported_fraction", "tool_calls_made", "latency_s", "error", "answer"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            writer.writerow({**r, "expected_tools": "|".join(r["expected_tools"]),
                             "tools_called": "|".join(r["tools_called"])})

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
