# metrics/tracker.py — Track pipeline performance metrics

import json
import time
from datetime import datetime
from pathlib import Path

METRICS_DIR = Path(__file__).parent / "data"
METRICS_DIR.mkdir(exist_ok=True)


class PipelineMetrics:
    def __init__(self):
        self.run_date = datetime.now().isoformat()
        self.pipeline_start = time.time()
        self.data = {
            "run_date": self.run_date,
            "fetch": {},
            "filter": {},
            "summarise": {},
            "email": {},
            "pipeline": {},
        }

    # ── Fetch metrics ─────────────────────────────────────────────────────────
    def record_fetch(self, source: str, count: int):
        self.data["fetch"][source] = count

    def record_fetch_total(self, total: int):
        self.data["fetch"]["total"] = total

    # ── Filter metrics ────────────────────────────────────────────────────────
    def record_filter(self, before: int, after: int):
        self.data["filter"] = {
            "articles_before": before,
            "articles_after": after,
            "filter_rate": round((before - after) / max(before, 1) * 100, 1),
        }

    # ── Summarise metrics ─────────────────────────────────────────────────────
    def record_summarise(self, total: int, success: int, failed: int, duration_sec: float):
        self.data["summarise"] = {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / max(total, 1) * 100, 1),
            "avg_time_per_article_sec": round(duration_sec / max(total, 1), 2),
        }

    # ── Email metrics ─────────────────────────────────────────────────────────
    def record_email(self, success: bool, recipient: str, articles_sent: int):
        self.data["email"] = {
            "success": success,
            "recipient": recipient,
            "articles_sent": articles_sent,
        }

    # ── Pipeline summary ──────────────────────────────────────────────────────
    def finalise(self):
        elapsed = round(time.time() - self.pipeline_start, 2)
        self.data["pipeline"] = {
            "total_duration_sec": elapsed,
            "status": "success" if self.data["email"].get("success") else "failed",
        }
        self._save()
        self._print_report()

    def _save(self):
        filename = METRICS_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(self.data, f, indent=2)
        print(f"[metrics] Saved to {filename}")

    def _print_report(self):
        print("\n" + "=" * 50)
        print("PIPELINE METRICS REPORT")
        print("=" * 50)
        print(f"  Date          : {self.run_date[:19]}")
        print(f"  Articles fetched  : {self.data['fetch'].get('total', 0)}")
        print(f"  After filter  : {self.data['filter'].get('articles_after', 0)} "
              f"({self.data['filter'].get('filter_rate', 0)}% filtered out)")
        print(f"  Summarised    : {self.data['summarise'].get('success', 0)}/"
              f"{self.data['summarise'].get('total', 0)} "
              f"({self.data['summarise'].get('success_rate', 0)}% success)")
        print(f"  Email sent    : {'✅' if self.data['email'].get('success') else '❌'}")
        print(f"  Total time    : {self.data['pipeline'].get('total_duration_sec', 0)}s")
        print("=" * 50 + "\n")
