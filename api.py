

"""
FastAPI backend — thin HTTP layer over the existing pipeline.

Run:  uv run uvicorn api:app --reload --port 8000

The pipeline logic itself (guardrails, classifier, RAG, generator,
validator, executor, formatter) is completely untouched — this file
only exposes it over HTTP for the Next.js frontend to call.

FIX (2026-08-26) — production traffic is now traced, not just eval
traffic. Every real request gets tagged with a fresh request_id and
the "production" tag (vs eval's "eval" tag), using the exact same
run_config mechanism and TokenUsageCallback the eval harness uses.

FIX (2026-09-20) — PostgreSQL connection support. New endpoints let
the frontend connect a session to a real PostgreSQL/Neon database
(POST /db/connect), disconnect back to the demo database (POST
/db/disconnect), check current status (GET /db/status), and fetch a
frontend-safe schema view (GET /schema — table/column/type/PK/FK only,
NEVER sample row data, regardless of what the LLM itself sees
internally per db/postgres_connector.py's INCLUDE_SAMPLE_ROWS_IN_LLM_CONTEXT).
/query now accepts an optional session_id and passes it straight
through to run_pipeline() — omitting it (old frontend clients, the
eval harness, direct calls) behaves exactly as before: the demo
database, unchanged.
"""
import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, model_validator
from typing import Optional

from pipeline import run_pipeline
from llm_client import MOCK_MODE
from logger import read_logs, log_run
from token_usage import TokenUsageCallback
from db import connection_manager as db_conn
from db.postgres_connector import build_connection_url, ConnectionError_
from schema.schema_rag import get_full_schema

app = FastAPI(title="Text-to-SQL Pipeline API")

# IMPORTANT: keep this set to your actual deployed Vercel domain, e.g.
# allow_origins=["https://datapilot-dp.vercel.app"] — do NOT revert
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
    session_id: Optional[str] = None


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

    session_id: optional. If this session is connected to a real
    PostgreSQL database (see POST /db/connect), the whole pipeline
    transparently runs against that database instead of the demo one.
    Omitting it — or passing a session that never connected — is the
    exact same demo-database behavior this endpoint always had.

    Every call is tagged and traced to LangSmith (if configured) under
    the "production" tag, and its token usage/cost is logged locally
    regardless of whether LangSmith tracing is even on.
    """
    request_id = str(uuid.uuid4())
    token_callback = TokenUsageCallback()

    run_config = {
        "run_name": "production::query",
        "tags": ["production"],
        "metadata": {
            "request_id": request_id,
            "has_selected_option": bool(req.selected_option),
            "session_id": req.session_id,
        },
        "callbacks": [token_callback],
    }

    start_time = time.time()
    result = run_pipeline(
        req.query,
        selected_option=req.selected_option,
        run_config=run_config,
        request_id=request_id,
        session_id=req.session_id,
    )
    total_time_ms = round((time.time() - start_time) * 1000, 1)

    result["_metrics"] = {
        "total_time_ms": total_time_ms,
        "llm_calls": token_callback.llm_calls,
        "input_tokens": token_callback.input_tokens,
        "output_tokens": token_callback.output_tokens,
        "estimated_cost_usd": round(token_callback.estimated_cost_usd(), 6),
    }

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


# ============================================================
# Database connection endpoints (demo database is unaffected by
# any of these — it's always available and never modified here)
# ============================================================

class DbConnectRequest(BaseModel):
    session_id: str

    # Option A: a ready-made connection string (what Neon/Supabase/RDS
    # give you directly — the recommended path, paste it as-is).
    connection_string: Optional[str] = None

    # Option B: individual fields, for people who'd rather fill a form.
    # Ignored if connection_string is provided.
    host: Optional[str] = None
    port: Optional[int] = 5432
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    sslmode: Optional[str] = "require"

    @model_validator(mode="after")
    def _one_form_or_the_other(self):
        if self.connection_string:
            return self
        if not all([self.host, self.database, self.username]):
            raise ValueError(
                "Provide either connection_string, or at minimum host + database + username."
            )
        return self


@app.post("/db/connect")
def db_connect(req: DbConnectRequest):
    """
    Connects this session to a real PostgreSQL database and switches
    it to using that database for every subsequent /query call — the
    demo database is completely unaffected and stays available to
    every OTHER session throughout.

    Returns the same shape as GET /db/status on success. On failure,
    responds 400 with a user-safe error message (never a raw driver
    traceback) and leaves the session on whatever it was using before.
    """
    url = req.connection_string or build_connection_url(
        req.host, req.port, req.database, req.username, req.password or "", req.sslmode
    )
    try:
        return db_conn.connect(req.session_id, url)
    except ConnectionError_ as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/db/disconnect")
def db_disconnect(session_id: str):
    """Reverts a session back to the demo database. Always succeeds."""
    return db_conn.disconnect(session_id)


@app.get("/db/status")
def db_status(session_id: str):
    return db_conn.status(session_id)


@app.get("/schema")
def schema(session_id: Optional[str] = None):
    """
    Frontend-safe schema view for SchemaPanel — table names, column
    names/types, primary keys, foreign keys. Deliberately NEVER
    includes sample row data, regardless of whether the LLM itself
    sees a couple of sample rows internally for grounding (see
    db/postgres_connector.py's INCLUDE_SAMPLE_ROWS_IN_LLM_CONTEXT) —
    those are two different trust boundaries and this endpoint only
    ever serves the stricter one.

    Works identically for the demo database (session_id omitted, or a
    session that's never connected to Postgres) and a connected one —
    same get_full_schema() call either way, just stripped of row data.
    """
    full_schema = get_full_schema(session_id=session_id)
    tables = []
    for table_name, info in full_schema.items():
        tables.append({
            "name": table_name,
            "columns": [{"name": c[0], "type": c[1]} for c in info["columns"]],
            "primary_key": info.get("primary_key", []),
            "foreign_keys": info.get("foreign_keys", []),
        })
    return {"tables": tables}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)