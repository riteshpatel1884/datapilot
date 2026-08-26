# """
# FastAPI backend — thin HTTP layer over the existing pipeline.

# Run:  uv run uvicorn api:app --reload --port 8000

# This replaces the Streamlit UI. The pipeline logic itself
# (guardrails, classifier, RAG, generator, validator, executor,
# formatter) is completely untouched — this file only exposes it
# over HTTP for the Next.js frontend to call.
# """
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import Optional

# from pipeline import run_pipeline
# from llm_client import MOCK_MODE
# from logger import read_logs

# app = FastAPI(title="Text-to-SQL Pipeline API")

# # Allow the Next.js dev server (and your deployed frontend) to call this API.
# # Tighten allow_origins to your actual deployed frontend URL in production.
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# class QueryRequest(BaseModel):
#     query: str
#     selected_option: Optional[str] = None


# @app.get("/health")
# def health():
#     return {"status": "ok", "mock_mode": MOCK_MODE}


# @app.post("/query")
# def query(req: QueryRequest):
#     """
#     Runs the full pipeline. Returns one of:
#       {"type": "error", "message": "..."}
#       {"type": "clarify", "question": "...", "options": [...]}
#       {"type": "result", "summary": "...", "table": [...], "sql_used": "...", "row_count": N}
#     """
#     return run_pipeline(req.query, selected_option=req.selected_option)


# @app.get("/logs")
# def logs(limit: int = 20):
#     return read_logs(limit=limit)


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)


"""
FastAPI backend — thin HTTP layer over the existing pipeline.

Run:  uv run uvicorn api:app --reload --port 8000

The pipeline logic itself (guardrails, classifier, RAG, generator,
validator, executor, formatter) is completely untouched — this file
only exposes it over HTTP for the Next.js frontend to call.

FIX (2026-08-26) — production traffic is now traced, not just eval
traffic. Previously /query called run_pipeline() with no run_config,
so real user questions were completely invisible to LangSmith — only
the eval harness's test runs ever showed up there. Every real request
now gets tagged with a fresh request_id and the "production" tag (vs
eval's "eval" tag), using the exact same run_config mechanism and the
exact same TokenUsageCallback (shared via token_usage.py, not
duplicated) that the eval harness already used. Filter by tag in
LangSmith to see production vs eval traffic separately.
"""
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from pipeline import run_pipeline
from llm_client import MOCK_MODE
from logger import read_logs, log_run
from token_usage import TokenUsageCallback

app = FastAPI(title="Text-to-SQL Pipeline API")

# IMPORTANT: keep this set to your actual deployed Vercel domain, e.g.
# allow_origins=["https://datapilot-zeta.vercel.app"] — do NOT revert
# to allow_origins=["*"]. This file doesn't know your current locked
# value, so verify it's unchanged from your existing deployed api.py
# before replacing that file with this one.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://datapilot-dp.vercel.app"],  # <-- verify this matches your real domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    selected_option: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": MOCK_MODE}


@app.post("/query")
def query(req: QueryRequest):
    """
    Runs the full pipeline. Returns one of:
      {"type": "error", "message": "..."}
      {"type": "clarify", "question": "...", "options": [...]}
      {"type": "result", "summary": "...", "table": [...], "sql_used": "...", "row_count": N}

    Every call is now tagged and traced to LangSmith (if configured)
    under the "production" tag, and its token usage/cost is logged
    locally regardless of whether LangSmith tracing is even on —
    same TokenUsageCallback the eval harness uses, so the two are
    directly comparable.
    """
    request_id = str(uuid.uuid4())
    token_callback = TokenUsageCallback()

    run_config = {
        "run_name": "production::query",
        "tags": ["production"],
        "metadata": {
            "request_id": request_id,
            "has_selected_option": bool(req.selected_option),
        },
        "callbacks": [token_callback],
    }

    result = run_pipeline(req.query, selected_option=req.selected_option, run_config=run_config)

    # Separate, lightweight log entry just for cost — doesn't touch or
    # duplicate pipeline.py's own per-stage logging, just correlates by
    # request_id so the two can be cross-referenced if needed.
    log_run({
        "request_id": request_id,
        "event": "production_query_cost",
        "llm_calls": token_callback.llm_calls,
        "input_tokens": token_callback.input_tokens,
        "output_tokens": token_callback.output_tokens,
        "estimated_cost_usd": round(token_callback.estimated_cost_usd(), 6),
    })

    return result


@app.get("/logs")
def logs(limit: int = 20):
    return read_logs(limit=limit)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)