from __future__ import annotations

import csv
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .models import EvalRun


def export_run_csv(run: EvalRun, path: Path) -> None:
    fieldnames = ["test_case_id", "actual_output"]
    metric_keys = sorted({m for c in run.cases for m in c.metrics.keys()})
    fieldnames.extend(metric_keys)

    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in run.cases:
            row = {"test_case_id": c.test_case_id, "actual_output": c.actual_output}
            for k in metric_keys:
                row[k] = c.metrics.get(k)
            writer.writerow(row)


def build_run_pdf(run: EvalRun) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 15 * mm
    y = height - margin

    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, f"QAlityDeep Evaluation Report – {run.run_id}")
    y -= 20

    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Dataset: {run.dataset_id} | Graph: {run.graph_name}")
    y -= 15
    c.drawString(margin, y, f"Metrics: {', '.join(run.metrics)}")
    y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Summary")
    y -= 16
    c.setFont("Helvetica", 10)

    metrics = run.summary.get("metrics", {})
    for name, data in metrics.items():
        line = f"{name}: avg={data.get('avg'):.3f}, pass_rate={data.get('pass_rate'):.2%}"
        c.drawString(margin, y, line)
        y -= 14
        if y < margin:
            c.showPage()
            y = height - margin

    if y < margin + 40:
        c.showPage()
        y = height - margin

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Per-case overview (first 20)")
    y -= 16
    c.setFont("Helvetica", 9)

    for idx, case in enumerate(run.cases[:20]):
        line = f"{idx+1}. {case.test_case_id} | " + ", ".join(
            f"{k}={v:.2f}" for k, v in case.metrics.items()
        )
        c.drawString(margin, y, line[:180])
        y -= 12
        if y < margin:
            c.showPage()
            y = height - margin

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

