# run.py - CLI to ask the research agent a question
# Usage: python -m research_agent.run "What's new in AI agents?"

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
        f.write(json.dumps({"answer": result["answer"], "refused": result["refused"]}) + "\n")
    return path


def main():
    load_dotenv()
    if len(sys.argv) < 2:
        print('Usage: python -m research_agent.run "your question here"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    agent = build_agent(GeminiModel())
    result = run_question(agent, question)

    print("\n" + "=" * 60)
    for e in result["trace"]:
        if e["node"] == "tools":
            status = "ok" if e["ok"] else f"err: {e['error']}"
            print(f"  [{e['tool']}] {e['args']} -> {e['n_results']} results ({status})")

    print("=" * 60)
    print(result["answer"])
    print("=" * 60)

    if result["sources"]:
        print("\nSources:")
        for s in result["sources"]:
            print(f"  - {s['title']} ({s['source']})")

    print(f"\nGrounding: {result['grounding']}")
    trace_path = save_trace(result)
    print(f"Latency: {result['latency_s']}s | Trace saved: {trace_path}")


if __name__ == "__main__":
    main()
