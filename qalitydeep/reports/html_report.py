"""Interactive HTML report generator for QAlityDeep eval runs."""
from __future__ import annotations

import html
from datetime import datetime
from typing import Any, Dict, List

from ..models import EvalCaseResult, EvalRun


class HtmlReportGenerator:
    """Generate self-contained HTML reports from eval runs."""

    PASS_COLOR = "#00b894"
    FAIL_COLOR = "#e94560"
    DARK_NAVY = "#1a1a2e"
    DARK_BLUE = "#16213e"
    ACCENT = "#0f3460"

    def generate(self, run: EvalRun, threshold: float = 0.5) -> str:
        """Generate a complete HTML report as a string."""
        pass_count, total = self._pass_fail(run, threshold)
        fail_count = total - pass_count
        pass_rate = (pass_count / total * 100) if total else 0
        overall = "PASS" if pass_rate == 100 else "FAIL"
        metric_avgs = self._metric_averages(run)
        timestamp = run.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QAlityDeep Report - {_esc(run.run_id)}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#f0f2f5;color:#333;line-height:1.6}}
header{{background:linear-gradient(135deg,{self.DARK_NAVY},{self.DARK_BLUE});color:#fff;padding:2rem;text-align:center}}
header h1{{font-size:1.6rem;font-weight:700;margin-bottom:.5rem}}
header .meta{{font-size:.85rem;opacity:.85;display:flex;flex-wrap:wrap;justify-content:center;gap:.5rem 1.5rem}}
.status-badge{{display:inline-block;padding:.25rem .75rem;border-radius:4px;font-weight:700;font-size:.9rem;margin-top:.75rem}}
.status-pass{{background:{self.PASS_COLOR};color:#fff}}
.status-fail{{background:{self.FAIL_COLOR};color:#fff}}
.container{{max-width:960px;margin:0 auto;padding:1.5rem 1rem}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1rem;margin-bottom:2rem}}
.card{{background:#fff;border-radius:8px;padding:1.25rem;box-shadow:0 1px 3px rgba(0,0,0,.1);text-align:center}}
.card .label{{font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;color:#666;margin-bottom:.35rem}}
.card .value{{font-size:1.6rem;font-weight:700}}
.card .value.good{{color:{self.PASS_COLOR}}}
.card .value.bad{{color:{self.FAIL_COLOR}}}
.card .value.neutral{{color:{self.ACCENT}}}
h2{{font-size:1.15rem;margin-bottom:1rem;color:{self.DARK_BLUE}}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
th{{background:{self.ACCENT};color:#fff;padding:.65rem .75rem;text-align:left;font-size:.8rem;text-transform:uppercase;letter-spacing:.03em;cursor:pointer;user-select:none;white-space:nowrap}}
th:hover{{background:{self.DARK_BLUE}}}
td{{padding:.6rem .75rem;border-bottom:1px solid #eee;font-size:.88rem}}
tr:last-child td{{border-bottom:none}}
.pass-cell{{color:{self.PASS_COLOR};font-weight:600}}
.fail-cell{{color:{self.FAIL_COLOR};font-weight:600}}
details{{margin:0}}
details summary{{cursor:pointer;list-style:none;display:flex;align-items:center;gap:.5rem}}
details summary::-webkit-details-marker{{display:none}}
details summary::before{{content:"\\25B6";font-size:.65rem;transition:transform .2s}}
details[open] summary::before{{transform:rotate(90deg)}}
.expand-content{{padding:.75rem;background:#f8f9fa;border-radius:4px;margin-top:.5rem;font-size:.82rem}}
.expand-content .reason{{margin-bottom:.5rem}}
.expand-content .reason strong{{color:{self.ACCENT}}}
.expand-content .output-preview{{background:#fff;border:1px solid #e0e0e0;border-radius:4px;padding:.5rem;margin-top:.5rem;white-space:pre-wrap;word-break:break-word;max-height:200px;overflow-y:auto;font-family:monospace;font-size:.8rem}}
.section{{margin-bottom:2rem}}
.bar-group{{background:#fff;border-radius:8px;padding:1.25rem;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:1rem}}
.bar-group h3{{font-size:.9rem;margin-bottom:.75rem;color:{self.DARK_BLUE}}}
.bar-row{{display:flex;align-items:center;margin-bottom:.4rem;font-size:.82rem}}
.bar-label{{width:80px;text-align:right;padding-right:.5rem;color:#666;flex-shrink:0}}
.bar-track{{flex:1;height:18px;background:#eee;border-radius:3px;overflow:hidden;position:relative}}
.bar-fill{{height:100%;border-radius:3px;transition:width .3s}}
.bar-count{{width:30px;text-align:left;padding-left:.4rem;color:#888;font-size:.75rem}}
footer{{text-align:center;padding:1.5rem;font-size:.78rem;color:#999}}
@media(max-width:600px){{
  header h1{{font-size:1.2rem}}
  .cards{{grid-template-columns:1fr 1fr}}
  th,td{{padding:.45rem .4rem;font-size:.78rem}}
  .bar-label{{width:60px;font-size:.75rem}}
}}
</style>
</head>
<body>
<header>
<h1>QAlityDeep Evaluation Report</h1>
<div class="meta">
<span>Run: <strong>{_esc(run.run_id)}</strong></span>
<span>Dataset: <strong>{_esc(run.dataset_id)}</strong></span>
<span>Graph: <strong>{_esc(run.graph_name)}</strong></span>
<span>{_esc(timestamp)}</span>
</div>
<div class="status-badge status-{'pass' if overall == 'PASS' else 'fail'}">{overall}</div>
</header>
<div class="container">
<div class="section">
<h2>Summary</h2>
<div class="cards">
<div class="card"><div class="label">Total Cases</div><div class="value neutral">{total}</div></div>
<div class="card"><div class="label">Passed</div><div class="value good">{pass_count}</div></div>
<div class="card"><div class="label">Failed</div><div class="value bad">{fail_count}</div></div>
<div class="card"><div class="label">Pass Rate</div><div class="value {'good' if pass_rate >= 80 else 'bad'}">{pass_rate:.1f}%</div></div>
{self._metric_cards(metric_avgs, threshold)}
</div>
</div>
<div class="section">
<h2>Results</h2>
{self._results_table(run, threshold)}
</div>
<div class="section">
<h2>Metric Distributions</h2>
{self._distribution_bars(run)}
</div>
</div>
<footer>Generated by <strong>QAlityDeep</strong> &middot; {_esc(now)}</footer>
<script>
document.querySelectorAll("th[data-col]").forEach(th=>{{
  th.addEventListener("click",()=>{{
    const table=th.closest("table"),tbody=table.querySelector("tbody");
    const col=+th.dataset.col,rows=[...tbody.querySelectorAll("tr")];
    const asc=th.dataset.sort!=="asc";
    table.querySelectorAll("th").forEach(h=>delete h.dataset.sort);
    th.dataset.sort=asc?"asc":"desc";
    rows.sort((a,b)=>{{
      let va=a.children[col]?.textContent.trim()??"";
      let vb=b.children[col]?.textContent.trim()??"";
      const na=parseFloat(va),nb=parseFloat(vb);
      if(!isNaN(na)&&!isNaN(nb))return asc?na-nb:nb-na;
      return asc?va.localeCompare(vb):vb.localeCompare(va);
    }});
    rows.forEach(r=>tbody.appendChild(r));
  }});
}});
</script>
</body>
</html>"""

    def write_file(self, run: EvalRun, path: str, threshold: float = 0.5) -> None:
        """Write HTML report to a file."""
        content = self.generate(run, threshold)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pass_fail(self, run: EvalRun, threshold: float) -> tuple[int, int]:
        passed = sum(
            1 for c in run.cases if all(v >= threshold for v in c.metrics.values())
        )
        return passed, len(run.cases)

    def _metric_averages(self, run: EvalRun) -> Dict[str, float]:
        if not run.cases:
            return {}
        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for case in run.cases:
            for name, val in case.metrics.items():
                totals[name] = totals.get(name, 0.0) + val
                counts[name] = counts.get(name, 0) + 1
        return {k: totals[k] / counts[k] for k in totals}

    def _metric_cards(self, avgs: Dict[str, float], threshold: float) -> str:
        parts: List[str] = []
        for name, avg in avgs.items():
            css = "good" if avg >= threshold else "bad"
            parts.append(
                f'<div class="card"><div class="label">{_esc(name)}</div>'
                f'<div class="value {css}">{avg:.2f}</div></div>'
            )
        return "\n".join(parts)

    def _results_table(self, run: EvalRun, threshold: float) -> str:
        if not run.cases:
            return "<p>No test cases.</p>"
        metric_names = run.metrics or list(run.cases[0].metrics.keys())
        header_cols = "".join(
            f'<th data-col="{i + 1}">{_esc(m)}</th>' for i, m in enumerate(metric_names)
        )
        rows: List[str] = []
        for case in run.cases:
            case_pass = all(case.metrics.get(m, 0) >= threshold for m in metric_names)
            status_cls = "pass-cell" if case_pass else "fail-cell"
            status_txt = "PASS" if case_pass else "FAIL"
            score_cells = ""
            for m in metric_names:
                v = case.metrics.get(m, 0.0)
                cls = "pass-cell" if v >= threshold else "fail-cell"
                score_cells += f'<td class="{cls}">{v:.2f}</td>'
            reasons_html = ""
            for m in metric_names:
                reason = case.metric_reasons.get(m, "-")
                reasons_html += (
                    f'<div class="reason"><strong>{_esc(m)}:</strong> '
                    f'{_esc(reason)}</div>'
                )
            output_preview = _esc(_truncate(case.actual_output, 500))
            rows.append(
                f"<tr><td><details><summary>{_esc(case.test_case_id)}</summary>"
                f'<div class="expand-content">{reasons_html}'
                f'<div class="output-preview">{output_preview}</div>'
                f"</div></details></td>"
                f"{score_cells}"
                f'<td class="{status_cls}">{status_txt}</td></tr>'
            )
        status_col = len(metric_names) + 1
        return (
            f'<table><thead><tr><th data-col="0">Test Case</th>'
            f"{header_cols}"
            f'<th data-col="{status_col}">Status</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
        )

    def _distribution_bars(self, run: EvalRun) -> str:
        if not run.cases:
            return "<p>No data.</p>"
        metric_names = run.metrics or list(run.cases[0].metrics.keys())
        buckets = ["0-.2", ".2-.4", ".4-.6", ".6-.8", ".8-1"]
        ranges = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
        colors = [self.FAIL_COLOR, "#e17055", "#fdcb6e", "#74b9ff", self.PASS_COLOR]
        sections: List[str] = []
        for m in metric_names:
            scores = [c.metrics.get(m, 0.0) for c in run.cases]
            counts = [sum(1 for s in scores if lo <= s < hi) for lo, hi in ranges]
            max_c = max(counts) if counts else 1
            bars = ""
            for i, (label, cnt) in enumerate(zip(buckets, counts)):
                pct = (cnt / max_c * 100) if max_c else 0
                bars += (
                    f'<div class="bar-row">'
                    f'<span class="bar-label">{label}</span>'
                    f'<div class="bar-track">'
                    f'<div class="bar-fill" style="width:{pct}%;background:{colors[i]}"></div>'
                    f'</div><span class="bar-count">{cnt}</span></div>'
                )
            sections.append(
                f'<div class="bar-group"><h3>{_esc(m)}</h3>{bars}</div>'
            )
        return "\n".join(sections)


# ------------------------------------------------------------------
# Module-level utilities
# ------------------------------------------------------------------

def _esc(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text))


def _truncate(text: str, length: int = 500) -> str:
    """Truncate text with ellipsis if needed."""
    if len(text) <= length:
        return text
    return text[:length] + "..."
