"""
research_agent/run.py — Ask the research agent a question from the command line.

    python -m research_agent.run "What's new in AI agents this week?"

Prints the answer, the tools it called and its sources, and saves the full
step-by-step trace to results/traces/<timestamp>.jsonl.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from research_agent.graph import build_agent, run_question
from research_agent.llm import GeminiModel

TRACE_DIR = Path(__file__).parent.parent / "results" / "traces"


def save_trace(result: dict) -> Path:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    path = TRACE_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
    with path.open("w") as f:
        f.write(json.dumps({"question": result["question"]}) + "\n")
        for event in result["trace"]:
            f.write(json.dumps(event, default=str) + "\n")
        f.write(json.dumps({"final_answer": result["answer"], "refused": result["refused"]}) + "\n")
    return path


def main() -> None:
    load_dotenv()
    if len(sys.argv) < 2:
        print('Usage: python -m research_agent.run "your question"')
        sys.exit(1)

    agent = build_agent(GeminiModel())
    result = run_question(agent, " ".join(sys.argv[1:]))

    print("\n" + "=" * 60)
    for event in result["trace"]:
        if event["node"] == "tools":
            status = "ok" if event["ok"] else f"error: {event['error']}"
            print(f"[tool] {event['tool']}({event['args']}) -> {event['n_results']} results, {status}")
    print("=" * 60)
    print(result["answer"])
    print("=" * 60)
    for s in result["sources"]:
        print(f"- {s['title']} ({s['source']})")
    print(f"\nGrounding: {result['grounding']}")
    print(f"Latency: {result['latency_s']}s | Trace: {save_trace(result)}")


if __name__ == "__main__":
    main()
