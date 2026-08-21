"""
FastAPI backend — thin HTTP layer over the existing pipeline.

Run:  uv run uvicorn api:app --reload --port 8000

This replaces the Streamlit UI. The pipeline logic itself
(guardrails, classifier, RAG, generator, validator, executor,
formatter) is completely untouched — this file only exposes it
over HTTP for the Next.js frontend to call.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from pipeline import run_pipeline
from llm_client import MOCK_MODE
from logger import read_logs

app = FastAPI(title="Text-to-SQL Pipeline API")

# Allow the Next.js dev server (and your deployed frontend) to call this API.
# Tighten allow_origins to your actual deployed frontend URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    """
    return run_pipeline(req.query, selected_option=req.selected_option)


@app.get("/logs")
def logs(limit: int = 20):
    return read_logs(limit=limit)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)