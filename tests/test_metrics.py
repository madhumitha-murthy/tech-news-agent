# tests/test_metrics.py

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch
from pathlib import Path


def test_pipeline_metrics_saves_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("metrics.tracker.METRICS_DIR", Path(tmpdir)):
            from metrics.tracker import PipelineMetrics
            import importlib, metrics.tracker as m
            importlib.reload(m)
            m.METRICS_DIR = Path(tmpdir)

            pm = m.PipelineMetrics()
            pm.record_fetch("TechCrunch", 10)
            pm.record_fetch_total(50)
            pm.record_filter(50, 15)
            pm.record_summarise(15, 14, 1, 30.0)
            pm.record_email(True, "test@gmail.com", 15)
            pm.finalise()

        saved = list(Path(tmpdir).glob("run_*.json"))
        assert len(saved) == 1

        with open(saved[0]) as f:
            data = json.load(f)

        assert data["fetch"]["total"] == 50
        assert data["filter"]["articles_after"] == 15
        assert data["summarise"]["success_rate"] > 90
        assert data["email"]["success"] is True
        assert data["pipeline"]["status"] == "success"
