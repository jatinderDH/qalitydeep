from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from .config import get_settings
from .models import Dataset, EvalRun, EvalCaseResult, TestCase


def _data_dir() -> Path:
    return get_settings().data_dir


def datasets_dir() -> Path:
    return _data_dir() / "datasets"


def runs_dir() -> Path:
    return _data_dir() / "runs"


def save_uploaded_dataset(file_path: Path, name: str | None = None, description: str = "") -> Dataset:
    dataset_id = name or file_path.stem
    dataset_id = dataset_id.replace(" ", "_").lower()

    target = datasets_dir() / file_path.name
    if file_path.resolve() != target.resolve():
        target.write_bytes(file_path.read_bytes())

    ds = Dataset(
        dataset_id=dataset_id,
        name=name or file_path.stem,
        description=description,
        source_path=target,
    )
    _save_dataset_meta(ds)
    return ds


def _dataset_meta_path() -> Path:
    return datasets_dir() / "datasets_index.json"


def _save_dataset_meta(dataset: Dataset) -> None:
    index_path = _dataset_meta_path()
    items: List[dict]
    if index_path.exists():
        items = json.loads(index_path.read_text())
        items = [i for i in items if i["dataset_id"] != dataset.dataset_id]
    else:
        items = []
    items.append(dataset.model_dump(mode="json"))
    index_path.write_text(json.dumps(items, indent=2))


def list_datasets() -> List[Dataset]:
    index_path = _dataset_meta_path()
    if not index_path.exists():
        return []
    items = json.loads(index_path.read_text())
    return [Dataset.model_validate(i) for i in items]


def load_dataset_cases(dataset: Dataset) -> List[TestCase]:
    path = dataset.source_path
    if path.suffix.lower() in {".csv"}:
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".json", ".jsonl"}:
        if path.suffix.lower() == ".jsonl":
            records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        else:
            content = json.loads(path.read_text())
            records = content if isinstance(content, list) else content.get("data", [])
        df = pd.DataFrame(records)
    else:
        raise ValueError(f"Unsupported dataset format: {path.suffix}")

    required_cols = {"prompt"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Dataset missing required columns: {required_cols}")

    cases: List[TestCase] = []
    for i, row in df.iterrows():
        trace = row.get("agent_trace") or row.get("trace_json")
        if isinstance(trace, str):
            try:
                trace = json.loads(trace)
            except json.JSONDecodeError:
                trace = {"raw": trace}

        expected_tool_calls = row.get("expected_tool_calls")
        if expected_tool_calls is not None and isinstance(expected_tool_calls, str) and not pd.isna(expected_tool_calls):
            try:
                expected_tool_calls = json.loads(expected_tool_calls)
            except json.JSONDecodeError:
                expected_tool_calls = None
        if expected_tool_calls is not None and not isinstance(expected_tool_calls, list):
            expected_tool_calls = None

        case = TestCase(
            id=str(row.get("id") or i),
            prompt=str(row["prompt"]),
            expected_output=str(row["expected_output"]) if "expected_output" in df.columns and not pd.isna(row["expected_output"]) else None,
            expected_tool_calls=expected_tool_calls,
            agent_trace=trace,
        )
        cases.append(case)
    return cases


def save_eval_run(run: EvalRun) -> None:
    runs_dir().mkdir(parents=True, exist_ok=True)
    path = runs_dir() / f"{run.run_id}.json"
    path.write_text(run.model_dump_json(indent=2))


def load_eval_run(run_id: str) -> EvalRun | None:
    path = runs_dir() / f"{run_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return EvalRun.model_validate(data)


def list_eval_runs() -> List[EvalRun]:
    runs_dir().mkdir(parents=True, exist_ok=True)
    items: List[EvalRun] = []
    for p in runs_dir().glob("*.json"):
        data = json.loads(p.read_text())
        items.append(EvalRun.model_validate(data))
    items.sort(key=lambda r: r.created_at, reverse=True)
    return items


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def build_eval_run(
    dataset_id: str,
    graph_name: str,
    metrics: Iterable[str],
    cases: Iterable[EvalCaseResult],
) -> EvalRun:
    case_list = list(cases)
    summary = _summarise_metrics(case_list)
    return EvalRun(
        run_id=new_run_id(),
        dataset_id=dataset_id,
        graph_name=graph_name,
        metrics=list(metrics),
        cases=case_list,
        summary=summary,
    )


def _summarise_metrics(cases: List[EvalCaseResult]) -> dict:
    if not cases:
        return {}
    metric_keys = sorted({m for c in cases for m in c.metrics.keys()})
    summary: dict = {"num_cases": len(cases), "metrics": {}}
    for key in metric_keys:
        scores = [c.metrics.get(key) for c in cases if key in c.metrics]
        if not scores:
            continue
        avg = float(sum(scores) / len(scores))
        passed = sum(1 for s in scores if s >= 0.5)
        summary["metrics"][key] = {
            "avg": avg,
            "pass_rate": passed / len(scores),
        }
    return summary

