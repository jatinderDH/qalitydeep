from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

# Load .env then .env.local so API keys and LLM_BACKEND are available (local overrides)
_app_dir = Path(__file__).resolve().parent
from dotenv import load_dotenv
load_dotenv(_app_dir / ".env")
load_dotenv(_app_dir / ".env.local", override=True)

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from qalitydeep.auth import create_user_and_key, validate_api_key
from qalitydeep.config import get_settings
from qalitydeep.evals import evaluate_case
from qalitydeep.exports import build_run_pdf, export_run_csv
from qalitydeep.models import EvalRun
from qalitydeep.remote_eval import build_eval_payload, send_to_remote_eval
from qalitydeep.storage import (
    build_eval_run,
    list_datasets,
    list_eval_runs,
    load_dataset_cases,
    load_eval_run,
    save_uploaded_dataset,
    save_eval_run,
)


def _page_header() -> None:
    st.set_page_config(page_title="QAlityDeep – Multi-agent QA", layout="wide")
    st.title("QAlityDeep – Multi-agent LLM QA")
    st.caption("Pre-deploy CI/CD evaluation for LangGraph-based multi-agent systems.")


def _sidebar() -> None:
    settings = get_settings()
    with st.sidebar:
        st.subheader("Environment")
        st.text(f"Env: {settings.app_env}")
        st.text(f"Backend: {settings.llm_backend}")
        st.text(f"Data dir: {settings.data_dir}")
        st.markdown("---")
        st.markdown("**Metrics**")
        st.markdown(
            "- correctness, relevancy, hallucination\n"
            "- tool_correctness (uses real tools)\n"
            "- trajectory, coordination\n"
            "- langsmith_trajectory (if LANGSMITH_API_KEY set)"
        )


def _handle_dataset_upload() -> None:
    st.subheader("Datasets")
    uploaded = st.file_uploader("Upload dataset (CSV, JSON, JSONL)", type=["csv", "json", "jsonl"])
    name = st.text_input("Dataset name (optional)")
    desc = st.text_area("Description (optional)", height=60)
    if uploaded and st.button("Save dataset"):
        tmp_path = Path(get_settings().data_dir) / uploaded.name
        tmp_path.write_bytes(uploaded.getvalue())
        ds = save_uploaded_dataset(tmp_path, name=name or None, description=desc)
        st.success(f"Saved dataset '{ds.dataset_id}'")

    datasets = list_datasets()
    if not datasets:
        st.info("No datasets found yet. Upload one above.")
        return

    st.markdown("### Existing datasets")
    for ds in datasets:
        st.write(f"- `{ds.dataset_id}` – {ds.name} ({ds.source_path.name})")


def _run_eval_ui() -> None:
    st.subheader("Run Evaluation")

    datasets = list_datasets()
    if not datasets:
        st.info("Upload a dataset first.")
        return

    ds_ids = [d.dataset_id for d in datasets]
    selected_id = st.selectbox("Dataset", ds_ids)
    metric_opts = [
        "correctness",
        "relevancy",
        "hallucination",
        "tool_correctness",
        "trajectory",
        "coordination",
    ]
    selected_metrics = st.multiselect("Metrics", metric_opts, default=["correctness", "relevancy"])

    max_cases = st.number_input("Max cases (for quick iteration)", min_value=1, value=20)

    if st.button("Run evaluation"):
        ds = {d.dataset_id: d for d in datasets}[selected_id]
        cases = load_dataset_cases(ds)[:max_cases]

        results = []
        progress = st.progress(0.0)
        for i, case in enumerate(cases):
            results.append(evaluate_case(case, selected_metrics))
            progress.progress((i + 1) / len(cases))

        run = build_eval_run(
            dataset_id=ds.dataset_id,
            graph_name="multi_agent",
            metrics=selected_metrics,
            cases=results,
        )
        save_eval_run(run)
        st.success(f"Run {run.run_id} completed.")
        st.query_params["run_id"] = run.run_id
        _show_run(run)


def _show_run(run: EvalRun) -> None:
    st.subheader(f"Run {run.run_id}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Cases", len(run.cases))
    with col2:
        metrics_summary = run.summary.get("metrics", {})
        for name, data in metrics_summary.items():
            st.metric(
                f"{name} avg",
                f"{data.get('avg'):.3f}",
                f"{data.get('pass_rate'):.0%} pass",
            )

    records = []
    for c in run.cases:
        row = {"test_case_id": c.test_case_id, "actual_output": c.actual_output}
        row.update({f"m_{k}": v for k, v in c.metrics.items()})
        records.append(row)
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True)

        metric_cols = [c for c in df.columns if c.startswith("m_")]
        if metric_cols:
            for col in metric_cols:
                fig = px.histogram(df, x=col, nbins=10, title=f"Distribution of {col}")
                st.plotly_chart(fig, use_container_width=True)

    with st.expander("Traces & communications"):
        case_ids = [c.test_case_id for c in run.cases]
        if case_ids:
            selected_case = st.selectbox("Test case", case_ids)
            case = next(c for c in run.cases if c.test_case_id == selected_case)
            st.markdown("**Trajectory (messages)**")
            msgs = case.trajectory.get("messages", [])
            for msg in msgs:
                st.markdown(f"- **{msg.get('type')}**: {msg.get('content')}")
            st.markdown("**Milestones**")
            for m in case.trajectory.get("milestones", []):
                st.markdown(f"- {m}")

    st.markdown("### Export")
    col_csv, col_pdf, col_remote = st.columns(3)
    with col_csv:
        if st.button("Download CSV"):
            tmp = Path(get_settings().data_dir) / f"{run.run_id}.csv"
            export_run_csv(run, tmp)
            with tmp.open("rb") as f:
                st.download_button("Save CSV", data=f, file_name=tmp.name, mime="text/csv")
    with col_pdf:
        if st.button("Download PDF"):
            pdf_buf = build_run_pdf(run)
            st.download_button(
                "Save PDF",
                data=pdf_buf,
                file_name=f"{run.run_id}.pdf",
                mime="application/pdf",
            )

    with col_remote:
        st.markdown("**Remote eval**")
        if st.button("Download payload (JSON)"):
            payload = build_eval_payload(run)
            st.download_button(
                "Save JSON",
                data=json.dumps(payload, indent=2),
                file_name=f"{run.run_id}_eval_payload.json",
                mime="application/json",
            )
        if get_settings().remote_eval_api_url and get_settings().remote_eval_api_key:
            if st.button("Send to remote eval"):
                resp = send_to_remote_eval(run)
                if "error" in resp:
                    st.error(f"Remote eval error: {resp['error']}")
                else:
                    data = resp.get("data") or {}
                    st.success(f"Sent. Run id: {data.get('id', 'n/a')}")


def _api_playground() -> None:
    st.subheader("API Playground")
    st.caption("Send evaluation requests with your API key. Create an account to get a key.")
    settings = get_settings()
    api_url = settings.eval_api_url.rstrip("/")

    with st.expander("Get API key", expanded=True):
        email = st.text_input("Email", placeholder="you@example.com", key="playground_email")
        if st.button("Create account / Get key"):
            if not email or "@" not in email:
                st.warning("Enter a valid email.")
            else:
                try:
                    _, key = create_user_and_key(email)
                    st.success("API key created. Copy it now — it won't be shown again.")
                    st.code(key, language=None)
                except Exception as e:
                    st.error(str(e))

    api_key = st.text_input("API key", type="password", placeholder="qd_...")

    st.markdown("### Request")
    metrics = st.multiselect(
        "Metrics",
        ["correctness", "relevancy", "hallucination"],
        default=["correctness", "relevancy"],
        key="playground_metrics",
    )
    st.markdown("**Test cases**")
    n_cases = st.number_input("Number of cases", min_value=1, max_value=10, value=1, key="playground_n")
    cases = []
    for i in range(int(n_cases)):
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                inp = st.text_area(f"Input {i+1}", value="How tall is Mount Everest?", key=f"inp_{i}")
                exp = st.text_area(f"Expected output (optional) {i+1}", value="", key=f"exp_{i}")
            with col2:
                actual = st.text_area(f"Actual output {i+1}", value="No clue, pretty tall I guess?", key=f"act_{i}")
                name = st.text_input(f"Name (optional) {i+1}", value=f"case_{i+1}", key=f"name_{i}")
            cases.append({"input": inp, "actualOutput": actual, "expectedOutput": exp or None, "name": name or None})

    if st.button("Send request"):
        if not api_key:
            st.error("Enter your API key first.")
            return
        if not validate_api_key(api_key):
            st.error("Invalid API key. Create one in the expander above.")
            return
        payload = {"metrics": metrics, "llmTestCases": cases}
        headers = {"Content-Type": "application/json", "X-API-Key": api_key}
        start = time.perf_counter()
        try:
            resp = requests.post(f"{api_url}/v1/evaluate", json=payload, headers=headers, timeout=60)
            elapsed = (time.perf_counter() - start) * 1000
        except requests.RequestException as e:
            st.error(f"Request failed: {e}")
            st.info("Ensure the API server is running: uvicorn qalitydeep.api_server:app --port 8000")
            return

        st.markdown("### Response")
        col_status, col_time = st.columns(2)
        with col_status:
            st.metric("Status", resp.status_code)
        with col_time:
            st.metric("Time", f"{elapsed:.0f} ms")

        try:
            data = resp.json()
        except Exception:
            st.code(resp.text)
            return

        if resp.status_code == 200:
            st.success("Success")
            results = data.get("results", [])
            summary = data.get("summary", {})
            for k, v in summary.items():
                if isinstance(v, dict) and "avg" in v:
                    st.metric(k, f"{v['avg']:.3f}", f"{v.get('pass_rate', 0):.0%} pass")
            if results:
                rows = []
                for r in results:
                    row = {"name": r.get("name"), **r.get("metrics", {})}
                    rows.append(row)
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.error(data.get("detail", resp.text))

        with st.expander("Raw response"):
            st.json(data)


def _runs_overview() -> None:
    st.subheader("Past Runs")
    runs = list_eval_runs()
    if not runs:
        st.info("No runs yet.")
        return
    rows = []
    for r in runs:
        row = {
            "run_id": r.run_id,
            "dataset_id": r.dataset_id,
            "graph_name": r.graph_name,
            "created_at": r.created_at,
        }
        for name, data in r.summary.get("metrics", {}).items():
            row[f"{name}_avg"] = data.get("avg")
            row[f"{name}_pass_rate"] = data.get("pass_rate")
        rows.append(row)
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)


def main() -> None:
    _page_header()
    _sidebar()

    run_id_param = st.query_params.get("run_id")
    if isinstance(run_id_param, list):
        run_id_param = run_id_param[0] if run_id_param else None

    tab_datasets, tab_run, tab_playground, tab_history = st.tabs(
        ["Datasets", "Current run", "API Playground", "History"]
    )

    with tab_datasets:
        _handle_dataset_upload()

    with tab_run:
        if run_id_param:
            existing = load_eval_run(run_id_param)
            if existing:
                _show_run(existing)
        _run_eval_ui()

    with tab_playground:
        _api_playground()

    with tab_history:
        _runs_overview()


if __name__ == "__main__":
    main()

