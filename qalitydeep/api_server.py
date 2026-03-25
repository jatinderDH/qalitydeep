"""REST API for evaluation. Requires valid API key in header."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from .auth import create_user_and_key, validate_api_key
from .evals import evaluate_case_api


class LLMTestCaseItem(BaseModel):
    input: str = Field(..., description="User input / prompt")
    actualOutput: str = Field(..., description="Model output to evaluate")
    expectedOutput: Optional[str] = Field(None, description="Expected answer (for correctness)")
    name: Optional[str] = Field(None, description="Test case id")


class EvaluateRequest(BaseModel):
    metricCollection: Optional[str] = Field(None, description="Metric set name (ignored; use metrics)")
    metrics: Optional[List[str]] = Field(
        default=["correctness", "relevancy", "hallucination"],
        description="Metrics to run",
    )
    llmTestCases: List[LLMTestCaseItem] = Field(..., description="Test cases")


class CaseResult(BaseModel):
    name: Optional[str]
    metrics: Dict[str, float]
    reasons: Dict[str, str]


class EvaluateResponse(BaseModel):
    success: bool = True
    results: List[CaseResult]
    summary: Dict[str, Any]


class CreateApiKeyRequest(BaseModel):
    email: EmailStr = Field(..., description="User email to enroll and create API key")


class CreateApiKeyResponse(BaseModel):
    user_id: str
    api_key: str


def _get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    qality_api_key: Optional[str] = Header(None, alias="QAlity_API_Key"),
    authorization: Optional[str] = Header(None),
) -> str:
    key = qality_api_key or x_api_key
    if not key and authorization and authorization.startswith("Bearer "):
        key = authorization[7:].strip()
    if not key:
        raise HTTPException(
            401,
            "Missing API key. Use QAlity_API_Key, X-API-Key or Authorization: Bearer <key>",
        )
    user_id = validate_api_key(key)
    if not user_id:
        raise HTTPException(401, "Invalid API key")
    return user_id


app = FastAPI(title="QAlityDeep Eval API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_eval_sync(body: EvaluateRequest) -> tuple[List[CaseResult], Dict[str, Any]]:
    """Run eval in thread to avoid uvloop/DeepEval conflict."""
    metrics = body.metrics or ["correctness", "relevancy", "hallucination"]
    results: List[CaseResult] = []
    all_scores: Dict[str, List[float]] = {}

    for tc in body.llmTestCases:
        out = evaluate_case_api(
            input_text=tc.input,
            actual_output=tc.actualOutput,
            expected_output=tc.expectedOutput,
            selected_metrics=metrics,
        )
        for k, v in out["metrics"].items():
            all_scores.setdefault(k, []).append(v)
        results.append(
            CaseResult(
                name=tc.name,
                metrics=out["metrics"],
                reasons=out.get("reasons", {}),
            )
        )

    summary: Dict[str, Any] = {"num_cases": len(results)}
    for k, scores in all_scores.items():
        summary[k] = {"avg": sum(scores) / len(scores), "pass_rate": sum(1 for s in scores if s >= 0.5) / len(scores)}
    return results, summary


@app.post("/v1/evaluate", response_model=EvaluateResponse)
async def evaluate(
    body: EvaluateRequest,
    _user_id: str = Depends(_get_api_key),
):
    """Evaluate LLM outputs. Requires valid API key in X-API-Key or Authorization header."""
    results, summary = await asyncio.to_thread(_run_eval_sync, body)
    return EvaluateResponse(success=True, results=results, summary=summary)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/api-keys", response_model=CreateApiKeyResponse)
async def create_api_key(body: CreateApiKeyRequest):
    """Create a user (if needed) and return a new API key. Key is only returned once."""
    user_id, api_key = create_user_and_key(body.email)
    return CreateApiKeyResponse(user_id=user_id, api_key=api_key)


def run_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run("qalitydeep.api_server:app", host=host, port=port, reload=True)
