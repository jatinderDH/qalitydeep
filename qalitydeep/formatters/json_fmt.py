"""JSON output formatter."""
from __future__ import annotations
import json
from typing import Any, Dict
from ..models import EvalRun

class JsonFormatter:
    def format_run(self, run: EvalRun) -> str:
        return run.model_dump_json(indent=2)

    def format_summary(self, run: EvalRun) -> str:
        summary = {
            "run_id": run.run_id,
            "dataset_id": run.dataset_id,
            "metrics": run.metrics,
            "summary": run.summary,
            "total_cases": len(run.cases),
            "created_at": run.created_at.isoformat(),
        }
        return json.dumps(summary, indent=2)
